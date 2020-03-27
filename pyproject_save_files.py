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

    return PurePath('/') / PurePath(longer_path).relative_to(prefix)


def locate_record(root, python3_sitelib, python3_sitearch):
    """return path to record stripped of root path."""

    records = list((Path(root) / Path(python3_sitelib).relative_to('/')).glob('*.dist-info/RECORD'))
    records.extend(list((Path(root) / Path(python3_sitearch).relative_to('/')).glob('*.dist-info/RECORD')))

    if len(records) == 0:
        raise FileNotFoundError("Did not find RECORD file")
    if len(records) > 1:
        raise FileExistsError("Multiple *.dist-info directories")

    record_path = str(records[0])
    return Path("/") / Path(delete_commonpath(record_path, root))


def read_record(root, record_path):
    """returns parsed list of triplets like: [(path, hash, size), ...]"""

    root = Path(root)
    record_path = Path(record_path)
    # can't join both absolute like paths properly
    try:
        record_path = Path(record_path).relative_to("/")
    except ValueError:
        record_path = Path(record_path)

    with open(root / record_path, newline='', encoding='utf-8') as f:
        content = csv.reader(f, delimiter=',', quotechar='"', lineterminator=os.linesep)
        yield from content


def parse_record(record_path, record_content):
    """return list of paths stripped of root

    params:
    record_path: path to record file stripped of root
    record_content: list of files relative to directory where dist-info directory is

    Example:
        parse_record("/usr/lib/python3.7/site-packages/requests-2.22.0.dist-info/RECORD", ["requests", ...])
            -> ["/usr/lib/python3.7/site-packages/requests", ...]
    """
    record_path = PurePath(record_path)

    site_dir = PurePath(record_path).parent.parent
    files = [PurePath(os.path.normpath(Path(site_dir)/row[0])) for row in record_content]
    return files



def is_subpath(parent, child):
    """
    Check whether the given child is a subpath of parent.
    Expects both arguments to be absolute Paths (no checks are done).
    """
    try:
        child.relative_to(parent)
    except ValueError:
        return False
    else:
        return True


def find_metadata(parsed_record_content, python3_sitedir, record_path):
    """go through parsed RECORD content, returns tuple:
    (path to directory containing metadata, [paths to all metadata files]).

    find_metadata(["/usr/lib/python3.7/site-packages/requests/__init__.py, ..."],
                   "/usr/lib/python3.7/site-packages",
                   "/usr/lib/python3.7/site-packages/requests-2.10.dist-info/RECORD")
            -> ("/usr/lib/python3.7/site-packages/requests-2.10.dist-info/,
                ["/usr/lib/python3.7/site-packages/requests-2.10.dist-info/RECORD", ...])
    """
    record_path = PurePath(record_path)
    metadata_dir = record_path.parent
    return f"{metadata_dir}/", [str(path) for path in parsed_record_content if is_subpath(metadata_dir, path)]


def find_extension(python3_sitedir, parsed_record_content):
    """list paths to extensions"""

    return [str(path) for path in parsed_record_content
            if path.parent == python3_sitedir and path.match('*.so')]


def find_script(python3_sitedir, parsed_record_content):
    """list paths to scripts and theire pycache files"""

    scripts = [str(path) for path in parsed_record_content if path.match(f"{python3_sitedir}/*.py")]
    pycache = []
    for script in scripts:

        filename = delete_commonpath(script, python3_sitedir)  # without suffix
        filename = PurePath(filename).stem
        pycache.extend([str(path) for path in parsed_record_content if path.match(f"{python3_sitedir}/__pycache__/{filename}*.pyc")])
    return scripts, scripts + pycache


def find_package(python3_sitelib, python3_sitearch, parsed_record_content):
    """return tuple([package dirs], [all package files])"""

    packages = set()
    for sitedir in (python3_sitelib, python3_sitearch):

        sitedir_len = len(sitedir.parts)
        for path in parsed_record_content:
            if len(path.parts) > (sitedir_len + 1) and is_subpath(sitedir, path):
                package = PurePath(*path.parts[:(sitedir_len + 1)])
                if not ".dist-info" in package.name and not "__pycache__" == package.name:
                    packages.add(f"{package}/")
    files = []
    for package in packages:
        files += [str(path) for path in parsed_record_content if is_subpath(package, path)]

    return packages, files


def find_executable(bindir, parsed_record_content):
    """return all files in bindir"""

    executables = []
    bindir_content = [str(path) for path in parsed_record_content if is_subpath(bindir, path)]
    for file in bindir_content:
        # do not list .pyc files, because pyproject-rpm-macro deletes them in bindir
        if not file.endswith(".pyc"):
            executables.append(file)
    return executables, bindir_content


def get_modules(packages, extension_files,
                scripts):
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
        key = Path(script).stem
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
    record_path = os.path.normpath(record_path)
    python3_sitearch = os.path.normpath(python3_sitearch)
    python3_sitelib = os.path.normpath(python3_sitelib)

    if os.path.commonpath((python3_sitelib, record_path)) == python3_sitelib:
        modules_dir = python3_sitelib
    elif os.path.commonpath((python3_sitearch, record_path)) == python3_sitearch:
        modules_dir = python3_sitearch
    else:
        assert False, f"""python3_sitelib: {python3_sitelib} or python3_sitearch: {python3_sitearch} does not
        contain RECORD file: {record_path}"""

    return PurePath(modules_dir)


def classify_paths(record_path, parsed_record_content, python3_sitelib, python3_sitearch, bindir):
    """return dict with logical representation of files"""

    python3_sitedir = get_modules_directory(record_path, python3_sitelib, python3_sitearch)
    packages, package_files = find_package(python3_sitelib, python3_sitearch, parsed_record_content)
    for file in package_files:
        file = PurePath(file)
        parsed_record_content.remove(file)
    metadata_dir, metadata_files = find_metadata(parsed_record_content, python3_sitedir, record_path)
    for file in metadata_files:
        file = PurePath(file)
        parsed_record_content.remove(file)
    extension_files = find_extension(python3_sitedir, parsed_record_content)
    for file in extension_files:
        file = PurePath(file)
        parsed_record_content.remove(file)
    scripts, pycached = find_script(python3_sitedir, parsed_record_content)
    for file in pycached:
        file = PurePath(file)
        parsed_record_content.remove(file)
    executables, bindir_content = find_executable(bindir, parsed_record_content)
    for file in bindir_content:
        file = PurePath(file)
        parsed_record_content.remove(file)

    modules = get_modules(packages, extension_files, scripts)

    parsed_record_content = sorted([str(file) for file in parsed_record_content])
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


def generate_file_list(record_path, python3_sitelib, python3_sitearch,
                       paths_dict, modules_glob,
                       include_executables = False):
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
                            dirname = str(get_modules_directory(record_path, python3_sitelib, python3_sitearch))
                            modulename = PurePath(delete_commonpath(file, dirname)).stem
                            script_and_pycache.append(dirname + "/__pycache__/" + modulename + ".cpython-3" + pyminor +
                                                      "{,.opt-?}.pyc")
                        paths.update(set(script_and_pycache))
                    else:
                        paths.update(set((module["files"])))

    paths.update(set(paths_dict['metadata']['files']))

    return sorted(paths)


def parse_globs(nargs):
    """
    Parse nargs from the %pyproject_save_files macro

    Argument +bindir is treted as a flag, everything is a glob

    Returns globs, boolean flag whether to include executables from bindir
    """
    include_bindir = False

    if "+bindir" in nargs:
        include_bindir = True
        nargs.remove("+bindir")

    return nargs, include_bindir


def pyproject_save_files(buildroot, python3_sitelib, python3_sitearch,
                         bindir, globs_to_save):
    """
    Takes arguments from the %{pyproject_save_files} macro

    Returns list of paths for the %file section
    """
    record_path = locate_record(buildroot, python3_sitelib, python3_sitearch)
    parsed_record = parse_record(record_path, read_record(buildroot, record_path))
    paths_dict = classify_paths(record_path, parsed_record, python3_sitelib,
                                python3_sitearch, bindir)
    files = generate_file_list(record_path, python3_sitelib, python3_sitearch,
                               paths_dict, *parse_globs(globs_to_save))

    return files


def main(cli_args):
    file_section = pyproject_save_files(cli_args.buildroot,
                                        cli_args.python3_sitelib,
                                        cli_args.python3_sitearch,
                                        cli_args.bindir,
                                        cli_args.globs_to_save)

    cli_args.path_to_save.write_text("\n".join(file_section) + "\n")


def argparser():
    p = argparse.ArgumentParser()
    p.add_argument("path_to_save", help="Path to save list of paths for file secton", type=Path)
    p.add_argument('buildroot', type=Path)
    p.add_argument('python3_sitelib', type=PurePath)
    p.add_argument('python3_sitearch', type=PurePath)
    p.add_argument('bindir', type=PurePath)
    p.add_argument("globs_to_save", nargs="+")
    return p


if __name__ == '__main__':
    cli_args = argparser().parse_args()
    main(cli_args)
