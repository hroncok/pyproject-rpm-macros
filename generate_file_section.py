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
from typing import List, Dict, Union, Tuple, Set, Any, Optional


def delete_commonpath(longer_path: Union[str, PurePath, Path], prefix: Union[str, PurePath, Path]) -> str:
    """return string with deleted common path."""

    return PurePath('/') / PurePath(longer_path).relative_to(prefix)


def locate_record(root: Path, python3_sitelib: PurePath, python3_sitearch: PurePath) -> Path:
    """return path to record stripped of root path."""

    records = list((Path(root) / Path(python3_sitelib).relative_to('/')).glob('*.dist-info/RECORD'))
    records.extend(list((Path(root) / Path(python3_sitearch).relative_to('/')).glob('*.dist-info/RECORD')))

    if len(records) == 0:
        raise FileNotFoundError("Did not find RECORD file")
    if len(records) > 1:
        raise FileExistsError("Multiple *.dist-info directories")

    record_path = str(records[0])
    return Path("/") / Path(delete_commonpath(record_path, root))


def read_record(root: Union[Path, str], record_path: Union[Path, str]) -> List[Any]:
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
        return list(content)


def parse_record(record_path: Union[Path, str], record_content: List[Tuple[str, str, str]]) -> List[PurePath]:
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


def pattern_filter(pattern: str, parsed_record_content: List[PurePath]) -> List[Optional[str]]:
    """filter list by given regex pattern."""

    comp = re.compile(pattern)
    return [str(path) for path in parsed_record_content if comp.search(str(path))]


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


def glob_filter(pattern: str, parsed_record_content: List[PurePath]) -> List[Optional[str]]:
    """filter list by given glob."""
    pattern_parts = Path(pattern).parts
    prefix = None
    if "**" in pattern_parts:
        ind = pattern_parts.index("**")
        prefix = PurePath(*pattern_parts[:ind])
        pattern = PurePath(*pattern_parts[ind+1:])

    matched = []
    for path in parsed_record_content:
        if prefix:
            if prefix in path.parents:
                path_without_prefix_parts = path.parts[len(prefix.parts):]
                path_without_prefix = PurePath(*path_without_prefix_parts)
                if path_without_prefix.match(str(pattern)):
                    matched.append(str(path))
        else:
            if path.match(pattern):
                matched.append(str(path))
    return matched


def find_metadata(parsed_record_content: List[PurePath], python3_sitedir: PurePath, record_path: PurePath) -> Tuple[str, List[str]]:
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
    # return dist_info, [*glob_filter(f"{dist_info}*", parsed_record_content)]


def find_extension(python3_sitedir: PurePath, parsed_record_content: List[PurePath]) -> List[str]:
    """list paths to extensions"""

    #return pattern_filter(f"{re.escape(python3_sitedir)}/[^/]*\\.so$", parsed_record_content)
    #return glob_filter(f"{python3_sitedir}/*.so", parsed_record_content)
    return [str(path) for path in parsed_record_content
            if path.parent == python3_sitedir and path.match('*.so')]


def find_script(python3_sitedir: PurePath, parsed_record_content: List[PurePath]) -> Tuple[List[str], List[str]]:
    """list paths to scripts"""

#    scripts = glob_filter(f"{python3_sitedir}/*.py", parsed_record_content)
    scripts = pattern_filter(f"{re.escape(str(python3_sitedir))}/[^/]*\\.py$", parsed_record_content)
    scripts = [str(path) for path in parsed_record_content if path.match(f"{python3_sitedir}/*.py")]
    pycache = []
    for script in scripts:
        ## scripts are all .py files in directory where dist-info is saved
        #scripts = [path for path in parsed_record_content if path.match(f"{python3_sitedir}/*.py")]
        # scripts = pattern_filter(f"{re.escape(str(python3_sitedir))}/[^/]*\\.py$", parsed_record_content) # todo: delete

        filename = delete_commonpath(script, python3_sitedir)  # without suffix
        filename = PurePath(filename).stem
        #        pycache.extend(pattern_filter(f"{re.escape(python3_sitedir)}/__pycache__/{filename}.*\\.pyc", parsed_record_content))
        pycache.extend(glob_filter(f"{python3_sitedir}/__pycache__/{filename}*.pyc",
                                   parsed_record_content))

    return scripts, scripts + pycache


def find_package(python3_sitelib: PurePath, python3_sitearch: PurePath, parsed_record_content: List[PurePath]) -> Tuple[Set[str], List[str]]:
    """return tuple([package dirs], [all package files])"""

    packages = set()
    for sitedir in (python3_sitelib, python3_sitearch):
        #python_files = glob_filter(f"{sitedir}/**/*/*.py", parsed_record_content)
        python_files = pattern_filter(f"{re.escape(str(sitedir))}/.*/.*\\.py$", parsed_record_content)

        sitedir_len = len(sitedir.parts)
        for path in parsed_record_content:
            if len(path.parts) > (sitedir_len + 1) and is_subpath(sitedir, path):
                package = PurePath(*path.parts[:(sitedir_len + 1)])
                if not ".dist-info" in package.name and not "__pycache__" == package.name:
                    packages.add(f"{package}/")
    files: List[str] = []
    for package in packages:
        #files += glob_filter(f"{package}**/*", parsed_record_content)
        files += pattern_filter(f"{re.escape(package)}.*", parsed_record_content)

    return packages, files


def find_executable(bindir: PurePath, parsed_record_content: List[PurePath]) -> Tuple[List[str], List[str]]:
    """return all files in bindir"""

    executables = []
    #    bindir_content = glob_filter(f"{bindir}/**/*", parsed_record_content)
    bindir_content = pattern_filter(f"{re.escape(str(bindir))}.*", parsed_record_content)
    for file in bindir_content:
        # do not list .pyc files, because pyproject-rpm-macro deletes them in bindir
        if not file.endswith(".pyc"):
            executables.append(file)
    return executables, bindir_content


def get_modules(packages: Tuple[List[set], List[str]], extension_files: Tuple[List[str], List[str]],
                scripts: Tuple[List[str], List[str]]) -> Dict[str, Any]:
    """helper function"""

    modules: Dict[str, Any] = {}

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


def get_modules_directory(record_path: PurePath, python3_sitelib: PurePath, python3_sitearch: PurePath):
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


def classify_paths(record_path: PurePath, parsed_record_content: List[PurePath], python3_sitelib: PurePath, python3_sitearch: PurePath, bindir: PurePath) -> Dict:
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


def generate_file_list(record_path: PurePath, python3_sitelib: PurePath, python3_sitearch: PurePath,
                       paths_dict: Dict[str, Any], modules_glob: List[str],
                       include_executables: bool = False) -> List[str]:
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


def pyproject_save_files_parse(module_globs: List[str]) -> Tuple[List[str], bool]:
    """parse input from %pyproject_save_files macro"""
    include_bindir = False

    if "+bindir" in module_globs:
        include_bindir = True
        module_globs.remove("+bindir")

    return module_globs, include_bindir


def pyproject_save_files(root: Path, python3_sitelib: PurePath, python3_sitearch: PurePath,
                         bindir: PurePath, args: List[str]) -> List[str]:
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
parser.add_argument("path_to_save", help="Path to save list of paths for file secton", type=lambda x: Path(x))
parser.add_argument('buildroot', type=lambda x: Path(x))
parser.add_argument('python3_sitelib', type=lambda x: PurePath(x))
parser.add_argument('python3_sitearch', type=lambda x: PurePath(x))
parser.add_argument('bindir', type=lambda x: PurePath)
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
