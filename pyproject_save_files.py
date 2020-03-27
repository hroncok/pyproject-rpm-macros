import argparse
import csv
import fnmatch
import os
import warnings
import sys

from collections import defaultdict
from pathlib import Path, PurePath


def real2buildroot(root, realpath):
    """
    For a given real disk path, return an "absolute" path relative to .

    For example::

        >>> real2buildroot(Path('/tmp/buildroot'), Path('/tmp/buildroot/foo'))
        PurePosixPath('/foo')
    """
    return PurePath("/") / realpath.relative_to(root)


def buildroot2real(root, buildrootpath):
    """
    For an "absolute" path relative to root, return a real absolute path

    For example::

        >>> buildroot2real(Path('/tmp/buildroot'), PurePath('/foo'))
        PosixPath('/tmp/buildroot/foo')
    """
    return root / buildrootpath.relative_to("/")


def _sitedires(sitelib, sitearch):
    """
    On 32 bit architectures, sitelib equals to sitearch.
    This helper function will return a list of possible values to save us
    browsing one directory twice.
    """
    return sorted({sitelib, sitearch})


def locate_record(root, sitedirs):
    """
    Find a RECORD path in the given root.
    sitedirs are relative to root (looking like absolute)
    Only RECORDs in dist-info dirs inside sitedirs are considered.
    There can only be one RECORD file.

    Returns real absolute path to the RECORD file.
    """

    records = []
    for sitedir in sitedirs:
        records.extend(buildroot2real(root, sitedir).glob("*.dist-info/RECORD"))

    sitedirs_text = ", ".join(str(p) for p in sitedirs)
    if len(records) == 0:
        raise FileNotFoundError(f"There is no *.dist-info/RECORD in {sitedirs_text}")
    if len(records) > 1:
        raise FileExistsError(f"Multiple *.dist-info directories in {sitedirs_text}")

    return records[0]


def read_record(record_path):
    """
    A generator yielding individual RECORD triplets.

    https://www.python.org/dev/peps/pep-0376/#record

    The triplet is path, hash, size, with the last two optional.
    We will later care only for the paths anyway.
    """

    with open(record_path, newline="", encoding="utf-8") as f:
        yield from csv.reader(
            f, delimiter=",", quotechar='"', lineterminator=os.linesep
        )


def parse_record(record_path, record_content):
    """
    Returns a list of absolute buildroot paths

    params:
    record_path: RECORD buildroot path
    record_content: list of RECORD triplets
                    first item is path relative to directory where dist-info directory is

    Example:

        >>> parse_record("/usr/lib/python3.7/site-packages/requests-2.22.0.dist-info/RECORD", [("requests/sessions.py", ...), ...])
        [PurePosixPath("/usr/lib/python3.7/site-packages/requests/sessions.py"), ...]

    TODO make this a generator once we only read this once
    """
    sitedir = record_path.parent.parent  # trough the dist-info directory
    # PurePaths don't have .resolve(), so we make a trip to str and back :(
    return [PurePath(os.path.normpath(sitedir / row[0])) for row in record_content]


def pycached(script):
    """
    For a script path, return a list with that path and its bytecode glob.
    Like the %pycached macro.
    """
    assert script.suffix == ".py"
    ver = sys.version_info
    pycname = f"{script.stem}.cpython-{ver.major}{ver.minor}{{,.opt-?}}.pyc"
    pyc = script.parent / "__pycache__" / pycname
    return [script, pyc]


def classify_paths(record_path, parsed_record_content, sitedirs, bindir):
    """
    For each file in parsed_record_content classify it to a dict structure
    that allows to filter the files for the %files section easier.

    For the dict structure, look at the beginning of the code.

    Each "module" is a dict with "type" ("package", "script", "extension") and "files".
    """
    distinfo = record_path.parent
    paths = {
        "metadata": {
            "files": [],  # regular %file entries with dist-info content
            "dirs": [distinfo],  # %dir %file entries with dist-info directory
            "docs": [],  # to be used once there is upstream way to recognize READMEs
            "licenses": [],  # to be used once there is upstream way to recognize LICENSEs
        },
        "modules": defaultdict(list),  # each importable module (directory, .py, .so)
        "executables": {"files": []},  # regular %file entries in %{_bindir}
        "other": {"files": []},  # regular %file entries we could not parse :(
    }

    # Note that there are no directories, only files !  # TODO find documentation
    for path in parsed_record_content:
        if path.suffix == ".pyc":
            # we handle bytecode separately
            continue

        if path.parent == distinfo:
            # TODO is this a license/documentation?
            paths["metadata"]["files"].append(path)
            continue

        if path.parent == bindir:
            paths["executables"]["files"].append(path)
            continue

        for sitedir in sitedirs:
            if sitedir in path.parents:
                if path.parent == sitedir:
                    if path.suffix == ".so":
                        # extension modules can have 2 suffixes
                        name = PurePath(path.stem).stem
                        # as far as we know, there can be only one
                        paths["modules"][name].append(
                            {"type": "extension", "files": [path]}
                        )
                    elif path.suffix == ".py":
                        name = path.stem
                        # theoretically, we can have 1 in lib and 1 in lib64
                        for module in paths["modules"][name]:
                            if module["type"] == "script":
                                if path not in module["files"]:
                                    module["files"].extend(pycached(path))
                                break
                        else:
                            paths["modules"][name].append(
                                {"type": "script", "files": pycached(path)}
                            )
                    else:
                        # TODO classify .pth files
                        warnings.warn(f"Unrecognized file: {path}")
                        paths["other"]["files"].append(path)
                else:
                    # this file is inside a dir, we classify that dir
                    index = path.parents.index(sitedir)
                    module_dir = path.parents[index - 1]
                    name = module_dir.name
                    for module in paths["modules"][name]:
                        if module["type"] == "package":
                            if module_dir not in module["files"]:
                                module["files"].append(module_dir)
                            break
                    else:
                        paths["modules"][name].append(
                            {"type": "package", "files": [module_dir]}
                        )
                break
        else:
            warnings.warn(f"Unrecognized file: {path}")
            paths["other"]["files"].append(path)

    return paths


def generate_file_list(paths_dict, module_globs, include_executables=False):
    """generated list of files to be added to specfile %file"""
    files = set()

    if include_executables:
        files.update(f"{p}" for p in paths_dict["executables"]["files"])

    files.update(f"{p}" for p in paths_dict["metadata"]["files"])
    for macro in "dir", "doc", "license":
        files.update(f"%{macro} {p}" for p in paths_dict["metadata"][f"{macro}s"])

    modules = paths_dict["modules"]

    for name in modules:
        for glob in module_globs:
            if fnmatch.fnmatch(name, glob):
                for module in modules[name]:
                    if module["type"] == "package":
                        files.update(f"{p}/" for p in module["files"])
                    else:
                        files.update(f"{p}" for p in module["files"])
                break

    return sorted(files)


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


def pyproject_save_files(buildroot, sitelib, sitearch, bindir, globs_to_save):
    """
    Takes arguments from the %{pyproject_save_files} macro

    Returns list of paths for the %file section
    """
    sitedirs = _sitedires(sitelib, sitearch)

    record_path_real = locate_record(buildroot, sitedirs)
    record_path = real2buildroot(buildroot, record_path_real)
    parsed_record = parse_record(record_path, read_record(record_path_real))

    paths_dict = classify_paths(record_path, parsed_record, sitedirs, bindir)
    return generate_file_list(paths_dict, *parse_globs(globs_to_save))


def main(cli_args):
    file_section = pyproject_save_files(
        cli_args.buildroot,
        cli_args.sitelib,
        cli_args.sitearch,
        cli_args.bindir,
        cli_args.globs_to_save,
    )

    cli_args.path_to_save.write_text("\n".join(file_section) + "\n", encoding="utf-8")


def argparser():
    p = argparse.ArgumentParser()
    p.add_argument(
        "path_to_save", help="Path to save list of paths for file section", type=Path
    )
    p.add_argument("buildroot", type=Path)
    p.add_argument("sitelib", type=PurePath)
    p.add_argument("sitearch", type=PurePath)
    p.add_argument("bindir", type=PurePath)
    p.add_argument("globs_to_save", nargs="+")
    return p


if __name__ == "__main__":
    cli_args = argparser().parse_args()
    main(cli_args)
