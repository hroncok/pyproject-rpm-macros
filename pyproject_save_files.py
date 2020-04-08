import argparse
import csv
import fnmatch
import os
import warnings
import sys

from collections import defaultdict
from pathlib import PosixPath, PurePosixPath


class BuildrootPath(PurePosixPath):
    """
    This path represents a path in a buildroot.
    When absolute, it is "relative" to a buildroot.

    E.g. /usr/lib means %{buildroot}/usr/lib
    The object carries no buildroot information.
    """

    @staticmethod
    def from_real(realpath, *, root):
        """
        For a given real disk path, return a BuildrootPath in the given root.

        For example::

            >>> BuildrootPath.from_real(PosixPath('/tmp/buildroot/foo'), root=PosixPath('/tmp/buildroot'))
            BuildrootPath('/foo')
        """
        return BuildrootPath("/") / realpath.relative_to(root)

    def to_real(self, root):
        """
        Return a real PosixPath in the given root

        For example::

            >>> BuildrootPath('/foo').to_real(PosixPath('/tmp/buildroot'))
            PosixPath('/tmp/buildroot/foo')
        """
        return root / self.relative_to("/")

    def normpath(self):
        """
        Normalize all the potential /../ parts of the path without touching real files.

        PurePaths don't have .resolve().
        Paths have .resolve() but it touches real files.
        This is an alternative. It assumes there are no symbolic links.

        Example:

            >>> BuildrootPath('/usr/lib/python/../pypy').normpath()
            BuildrootPath('/usr/lib/pypy')
        """
        return type(self)(os.path.normpath(self))


def locate_record(root, sitedirs):
    """
    Find a RECORD file in the given root.
    sitedirs are BuildrootPaths.
    Only RECORDs in dist-info dirs inside sitedirs are considered.
    There can only be one RECORD file.

    Returns a PosixPath of the RECORD file.
    """
    records = []
    for sitedir in sitedirs:
        records.extend(sitedir.to_real(root).glob("*.dist-info/RECORD"))

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

    The triplet is str-path, hash, size -- the last two optional.
    We will later care only for the paths anyway.
    """
    with open(record_path, newline="", encoding="utf-8") as f:
        yield from csv.reader(
            f, delimiter=",", quotechar='"', lineterminator=os.linesep
        )


def parse_record(record_path, record_content):
    """
    Returns a generator with BuildrootPaths parsed from record_content

    params:
    record_path: RECORD BuildrootPath
    record_content: list of RECORD triplets
                    first item is a str-path relative to directory where dist-info directory is
                    (it can also be absolute according to the standard, but not from pip)

    Examples:

        >>> next(parse_record(BuildrootPath("/usr/lib/python3.7/site-packages/requests-2.22.0.dist-info/RECORD"),
        ...                   [("requests/sessions.py", "sha256=xxx", "666"), ...]))
        BuildrootPath("/usr/lib/python3.7/site-packages/requests/sessions.py")

        >>> next(parse_record(BuildrootPath("/usr/lib/python3.7/site-packages/tldr-0.5.dist-info/RECORD"),
        ...                   [("../../../bin/tldr", "sha256=yyy", "777"), ...]))
        BuildrootPath("/usr/bin/tldr")
    """
    sitedir = record_path.parent.parent  # trough the dist-info directory
    # / with absolute right operand will remove the left operand
    # any .. parts are resolved via normpath
    return ((sitedir / row[0]).normpath() for row in record_content)


def pycached(script):
    """
    For a script BuildrootPath, return a list with that path and its bytecode glob.
    Like the %pycached macro.

    The glob is represented as a BuildrootPath.
    """
    assert script.suffix == ".py"
    ver = sys.version_info
    pycname = f"{script.stem}.cpython-{ver.major}{ver.minor}{{,.opt-?}}.pyc"
    pyc = script.parent / "__pycache__" / pycname
    return [script, pyc]


def add_file_to_module(paths, module_name, module_type, *files):
    """
    Helper procedure, adds given files to the module_name of a given module_type
    """
    for module in paths["modules"][module_name]:
        if module["type"] == module_type:
            if files[0] not in module["files"]:
                module["files"].extend(files)
            break
    else:
        paths["modules"][module_name].append(
            {"type": module_type, "files": list(files)}
        )


def classify_paths(record_path, parsed_record_content, sitedirs, bindir):
    """
    For each BuildrootPath in parsed_record_content classify it to a dict structure
    that allows to filter the files for the %files section easier.

    For the dict structure, look at the beginning of this function's code.

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

    # In RECORDs generated by pip, there are no directories, only files.
    # The example RECORD from PEP 376 does not contain directories either.
    # Hence, we'll only assume files, but TODO get it officially documented.
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
                        name = BuildrootPath(path.stem).stem
                        add_file_to_module(paths, name, "extension", path)
                    elif path.suffix == ".py":
                        name = path.stem
                        add_file_to_module(paths, name, "script", *pycached(path))
                    else:
                        # TODO classify .pth files
                        warnings.warn(f"Unrecognized file: {path}")
                        paths["other"]["files"].append(path)
                else:
                    # this file is inside a dir, we classify that dir
                    index = path.parents.index(sitedir)
                    module_dir = path.parents[index - 1]
                    add_file_to_module(paths, module_dir.name, "package", module_dir)
                break
        else:
            warnings.warn(f"Unrecognized file: {path}")
            paths["other"]["files"].append(path)

    return paths


def generate_file_list(paths_dict, module_globs, include_executables=False):
    """
    This function takes the classified paths_dict and turns it into lines
    for the %files section. Returns list with text lines, no Path objects.

    Only includes files from modules that match module_globs, metadata and
    optional executables.

    It asserts that all globs match at least one module, raises ValueError otherwise.
    Multiple globs matching identical module(s) are OK.
    """
    files = set()

    if include_executables:
        files.update(f"{p}" for p in paths_dict["executables"]["files"])

    files.update(f"{p}" for p in paths_dict["metadata"]["files"])
    for macro in "dir", "doc", "license":
        files.update(f"%{macro} {p}" for p in paths_dict["metadata"][f"{macro}s"])

    modules = paths_dict["modules"]
    done_modules = set()
    done_globs = set()

    for glob in module_globs:
        for name in modules:
            if fnmatch.fnmatchcase(name, glob):
                if name not in done_modules:
                    for module in modules[name]:
                        if module["type"] == "package":
                            files.update(f"{p}/" for p in module["files"])
                        else:
                            files.update(f"{p}" for p in module["files"])
                    done_modules.add(name)
                done_globs.add(glob)

    missed = module_globs - done_globs
    if missed:
        missed_text = ", ".join(sorted(missed))
        raise ValueError(f"Globs did not match any module: {missed_text}")

    return sorted(files)


def parse_varargs(varargs):
    """
    Parse varargs from the %pyproject_save_files macro

    Arguments starting with + are treated as a flags, everything else is a glob

    Returns as set of globs, boolean flag whether to include executables from bindir

    Raises ValueError for unknown flags
    """
    include_bindir = False
    globs = set()

    for arg in varargs:
        if arg.startswith("+"):
            if arg == "+bindir":
                include_bindir = True
            else:
                raise ValueError(f"Invalid argument: {arg}")
        elif "." in arg:
            top, *_ = arg.partition(".")
            msg = (
                f"Attempted to use a namespaced package with dot in the glob: {arg}. "
                f"That is not (yet) supported. Use {top} instead and/or file a Bugzilla explaining your use case."
            )
            raise ValueError(msg)
        else:
            globs.add(arg)

    return globs, include_bindir


def pyproject_save_files(buildroot, sitelib, sitearch, bindir, varargs):
    """
    Takes arguments from the %{pyproject_save_files} macro

    Returns list of paths for the %files section
    """
    # On 32 bit architectures, sitelib equals to sitearch
    # This saves us browsing one directory twice
    sitedirs = sorted({sitelib, sitearch})

    globs, include_bindir = parse_varargs(varargs)
    record_path_real = locate_record(buildroot, sitedirs)
    record_path = BuildrootPath.from_real(record_path_real, root=buildroot)
    parsed_record = parse_record(record_path, read_record(record_path_real))

    paths_dict = classify_paths(record_path, parsed_record, sitedirs, bindir)
    return generate_file_list(paths_dict, globs, include_bindir)


def main(cli_args):
    file_section = pyproject_save_files(
        cli_args.buildroot,
        cli_args.sitelib,
        cli_args.sitearch,
        cli_args.bindir,
        cli_args.varargs,
    )

    cli_args.output.write_text("\n".join(file_section) + "\n", encoding="utf-8")


def argparser():
    parser = argparse.ArgumentParser()
    r = parser.add_argument_group("required arguments")
    r.add_argument("--output", type=PosixPath, required=True)
    r.add_argument("--buildroot", type=PosixPath, required=True)
    r.add_argument("--sitelib", type=BuildrootPath, required=True)
    r.add_argument("--sitearch", type=BuildrootPath, required=True)
    r.add_argument("--bindir", type=BuildrootPath, required=True)
    parser.add_argument("varargs", nargs="+")
    return parser


if __name__ == "__main__":
    cli_args = argparser().parse_args()
    main(cli_args)
