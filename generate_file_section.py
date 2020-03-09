import argparse
import csv
import fnmatch
import os
import re
from pathlib import Path
from pathlib import PurePath
from pprint import pformat
from warnings import warn
import sys


def delete_commonpath(longer_path, prefix):
    """return string with deleted common path."""
    return str(PurePath(longer_path).relative_to(prefix))


def locate_record(root, python3_sitelib, python3_sitearch):
    """return path to record stripped of root path."""

    record_path = list((Path(root) / Path(python3_sitelib).relative_to('/')).glob('*.dist-info/RECORD'))
    record_path.extend(list((Path(root) / Path(python3_sitearch).relative_to('/')).glob('*.dist-info/RECORD')))

    if len(record_path) == 0:
        raise FileNotFoundError("Did not find RECORD file")
    if len(record_path) > 1:
        raise FileExistsError("Multiple *.dist-info directories")

    record_path = str(record_path[0])
    return "/" + delete_commonpath(record_path, root)


def read_record(root, record_path):
    """return parsed list [[[path], [hash], [size]], ...]"""

    # there is need to be able join absolute paths
    with open(f"{root}/{record_path}", newline='') as f:
        content = csv.reader(f, delimiter=',', quotechar='"', lineterminator=os.linesep)
        return list(content)


def parse_record(record_path, record_content):
    """return list of paths stripped of root

    params:
    record_path: path to record file stripped of root
    record_content: list of files relative to directory where dist-info directory is

    Example:
        parse_record("/usr/lib/python3.7/site-packages/requests-2.22.0.dist-info/RECORD", ["requests", ...])
            -> ["/usr/lib/python3.7/site-packages/requests", ...]
    """

    site_dir = PurePath(record_path).parent.parent
    files = [os.path.normpath(Path(site_dir)/row[0]) for row in record_content]
    return files


def pattern_filter(pattern, parsed_record_content):
    """filter list by given pattern."""

    matched = []
    comp = re.compile(pattern)
    for path in parsed_record_content:
        if comp.search(path):
            matched.append(path)
    return matched


def find_metadata(parsed_record_content, python3_sitedir, record_path):
    """go through parsed RECORD content, returns tuple:
    (path to directory containing metadata, [paths to all metadata files])."""

    dist_info = re.search(f"{re.escape(python3_sitedir)}/[^/]*", record_path)[0] + "/"

    return dist_info, [*pattern_filter(f"{re.escape(dist_info)}.*", parsed_record_content)]


def find_extension(python3_sitedir, parsed_record_content):
    """list paths to extensions"""

    return pattern_filter(f"{re.escape(python3_sitedir)}/[^/]*\\.so$", parsed_record_content)


def find_script(python3_sitedir, parsed_record_content):
    """list paths to scripts"""

    scripts = pattern_filter(f"{re.escape(python3_sitedir)}/[^/]*\\.py$", parsed_record_content)
    pycache = []
    for script in scripts:
        filename = delete_commonpath(script, python3_sitedir)[:-(len('.py'))]  # without suffix
        pycache.extend(pattern_filter(f"{re.escape(python3_sitedir)}/__pycache__/{filename}.*\\.pyc",
                                      parsed_record_content))

    return scripts, pycache


def find_package(python3_sitelib, python3_sitearch, parsed_record_content):
    """return tuple([package dirs], [all package files])"""

    packages = set()
    for sitedir in (python3_sitelib, python3_sitearch):
        python_files = pattern_filter(f"{re.escape(sitedir)}/.*/.*\\.py$", parsed_record_content)
        sitedir = Path(sitedir)
        for file in python_files:
            file = Path(file)
            if os.path.commonpath((sitedir, file)) == str(sitedir):
                py_package = file.parts[:len(sitedir.parts) + 1]
                py_package = "/".join(py_package) + "/"  # //usr/lib...
                packages.add(py_package[1:])  # getting rid of unwanted /

    files = []
    for package in packages:
        files += pattern_filter(f"{re.escape(package)}.*", parsed_record_content)

    return packages, files


def find_executable(bindir, parsed_record_content):
    """return all files in bindir"""

    executables = []
    bindir_content = pattern_filter(f"{re.escape(bindir)}.*", parsed_record_content)
    for file in bindir_content:
        # do not list .pyc files, because pyproject-rpm-macro deletes them in bindir
        if not file.endswith(".pyc"):
            executables.append(file)
    return executables, bindir_content


def get_modules(packages, extension_files, scripts):
    """helper function"""

    modules = {}

    for package in packages:
        key = Path(package).parts[-1]
        if key not in modules:
            modules[key] = []
        modules[key].append({
            "type": "package",
            "files": [package],
        })
    for script in scripts:
        key = Path(script)
        key = key.stem
        if key not in modules:
            modules[key] = []

        modules[key].append({
            "type": "script",
            "pycache": [script],
        })

    for extension in extension_files:
        key = Path(extension).stem
        key = Path(key).stem  # extensions have two suffixes
        if key not in modules:
            modules[key] = []
        modules[key].append({
            "type": "extension",
            "files": [extension]
        })

    return modules


def get_modules_directory(record_path, python3_sitelib, python3_sitearch):
    """find out directory where modules should be located"""
    if os.path.commonpath((python3_sitelib, record_path)) == python3_sitelib:
        modules_dir = python3_sitelib
    elif os.path.commonpath((python3_sitearch, record_path)) == python3_sitearch:
        modules_dir = python3_sitearch
    else:
        assert False, f"""python3_sitelib: {python3_sitelib} or python3_sitearch: {python3_sitearch} does not
        contain RECORD file: {record_path}"""

    return modules_dir


def classify_paths(record_path, parsed_record_content, python3_sitelib, python3_sitearch, bindir):
    """return dict with logical representation of files"""

    python3_sitedir = get_modules_directory(record_path, python3_sitelib, python3_sitearch)
    packages, package_files = find_package(python3_sitelib, python3_sitearch, parsed_record_content)
    for file in package_files:
        parsed_record_content.remove(file)
    metadata_dir, metadata_files = find_metadata(parsed_record_content, python3_sitedir, record_path)
    for file in metadata_files:
        parsed_record_content.remove(file)
    extension_files = find_extension(python3_sitedir, parsed_record_content)
    for file in extension_files:
        parsed_record_content.remove(file)
    scripts, pycached = find_script(python3_sitedir, parsed_record_content)
    for file in scripts + pycached:
        parsed_record_content.remove(file)
    executables, bindir_content = find_executable(bindir, parsed_record_content)
    for file in bindir_content:
        parsed_record_content.remove(file)

    modules = get_modules(packages, extension_files, scripts)

    parsed_record_content = sorted(parsed_record_content)
    if parsed_record_content:
        warn(f"Uncathegorized files: \n{pformat(parsed_record_content)}")

    paths = {
            "metadata": {
                "files": metadata_files,   # ends in slash = directory & contents
                "dirs": [metadata_dir],
                "docs": [],  # now always missing
                "licenses": [],  # now always missing
            },
            "modules": modules,
            "executables": {
                "files": executables
            },
            "other": {
                "files": parsed_record_content
            }
        }

    return paths


def generate_file_list(record_path, python3_sitelib, python3_sitearch, paths_dict, modules_glob,
                       include_executables=False):
    """generated list of files to be added to specfile %file"""
    paths = set(paths_dict["executables"]["files"]) if include_executables else set()
    modules = paths_dict["modules"]
    for glob in modules_glob:
        for names in modules:
            if fnmatch.fnmatch(re.escape(names), glob):
                for module in modules[names]:
                    if module["type"] == "script":
                        script_and_pycache = []
                        for file in module["pycache"]:
                            # adding pycached files
                            script_and_pycache.append(file)
                            pyminor = str(sys.version_info[1])
                            dirname = get_modules_directory(record_path, python3_sitelib, python3_sitearch)
                            modulename = PurePath(delete_commonpath(file, dirname)).stem
                            script_and_pycache.append(dirname + "/__pycache__/" + modulename + ".cpython-3" + pyminor +
                                                      "{,.opt-?}.pyc")
                        paths.update(set(script_and_pycache))
                    else:
                        paths.update(set((module["files"])))

    paths.update(set(paths_dict['metadata']['files']))

    return sorted(paths)


def pyproject_save_files_parse(module_globs: list):
    """parse input from %pyproject_save_files macro"""
    include_bindir = False

    if "+bindir" in module_globs:
        include_bindir = True
        module_globs.remove("+bindir")

    return [module_globs, include_bindir]


def pyproject_save_files(root, python3_sitelib, python3_sitearch, bindir, args):
    """return list of files for specfile

    args: arguments from %{pyproject_save_files} macro
    """
    record_path = locate_record(root, python3_sitelib, python3_sitearch)
    parsed_record = parse_record(record_path, (read_record(root, record_path)))

    paths_dict = classify_paths(record_path, parsed_record, python3_sitelib, python3_sitearch, bindir)

    files = generate_file_list(record_path, python3_sitelib, python3_sitearch,
                               paths_dict, *pyproject_save_files_parse(args))

    return files


parser = argparse.ArgumentParser()
parser.add_argument("path_to_save", help="Path to save list of paths for file secton")
parser.add_argument('buildroot')
parser.add_argument('python3_sitelib')
parser.add_argument('python3_sitearch')
parser.add_argument('bindir')
parser.add_argument("globs_to_save", nargs="+")


def main(cli_args):
    args = cli_args.__dict__
    path_to_save = args.pop("path_to_save")
    file_section = pyproject_save_files(*args.values())

    with open(path_to_save, "w") as file:
        file.writelines([path + "\n" for path in file_section])


if __name__ == '__main__':
    cli_args = parser.parse_args()
    main(cli_args)
