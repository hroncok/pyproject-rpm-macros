import json
import pytest
import shutil
import sys

from pathlib import Path
from pprint import pprint

from pyproject_save_files import argparser, generate_file_list, main
from pyproject_save_files import parse_varargs, parse_record, read_record
from pyproject_save_files import BuildrootPath


RECORDS = Path(__file__).parent
BINDIR = BuildrootPath("/usr/bin")
SITELIB = BuildrootPath("/usr/lib/python3.7/site-packages")
SITEARCH = BuildrootPath("/usr/lib64/python3.7/site-packages")

json_file = RECORDS / "pyproject_save_files_test_data.json"
json_data = json.loads(json_file.read_text())
EXPECTED_DICT = json_data["classified"]
EXPECTED_FILES = json_data["dumped"]


@pytest.fixture(autouse=True)
def _fake_version(monkeypatch):
    """
    The test data are for Python 3.7.
    We only support running this for 3.7 packages on 3.7 etc.
    Hence in tests, we fake our version.
    """

    class version_info(tuple):
        major = 3
        minor = 7
        patch = 100

        def __new__(cls):
            return super().__new__(cls, (3, 7, 100))

    monkeypatch.setattr(sys, "version_info", version_info(), raising=True)


def test_parse_record_kerberos():
    record_path = SITEARCH / "kerberos-1.3.0.dist-info/RECORD"
    record_content = read_record(RECORDS / "test_RECORD_kerberos")
    output = list(parse_record(record_path, record_content))
    pprint(output)
    expected = [
        SITEARCH / "kerberos-1.3.0.dist-info/INSTALLER",
        SITEARCH / "kerberos-1.3.0.dist-info/METADATA",
        SITEARCH / "kerberos-1.3.0.dist-info/RECORD",
        SITEARCH / "kerberos-1.3.0.dist-info/WHEEL",
        SITEARCH / "kerberos-1.3.0.dist-info/top_level.txt",
        SITEARCH / "kerberos.cpython-37m-x86_64-linux-gnu.so",
    ]
    assert output == expected


def test_parse_record_tensorflow():
    long = "tensorflow_core/include/tensorflow/core/common_runtime/base_collective_executor.h"
    record_path = SITEARCH / "tensorflow-2.1.0.dist-info/RECORD"
    record_content = [
        ["../../../bin/toco_from_protos", "sha256=hello", "289"],
        [f"../../../lib/python3.7/site-packages/{long}", "sha256=darkness", "1024"],
        ["tensorflow-2.1.0.dist-info/METADATA", "sha256=friend", "2859"],
    ]
    output = list(parse_record(record_path, record_content))
    pprint(output)
    expected = [
        BINDIR / "toco_from_protos",
        SITELIB / long,
        SITEARCH / "tensorflow-2.1.0.dist-info/METADATA",
    ]
    assert output == expected


# packagename: expected path in buildroot
TEST_RECORDS = {
    "kerberos": SITEARCH / "kerberos-1.3.0.dist-info/RECORD",
    "requests": SITELIB / "requests-2.22.0.dist-info/RECORD",
    "tensorflow": SITEARCH / "tensorflow-2.1.0.dist-info/RECORD",
    "tldr": SITELIB / "tldr-0.5.dist-info/RECORD",
    "mistune": SITEARCH / "mistune-0.8.3.dist-info/RECORD",
}


def remove_executables(expected):
    return [p for p in expected if not p.startswith(str(BINDIR))]


@pytest.mark.parametrize("include_executables", (True, False))
@pytest.mark.parametrize("package, glob, expected", EXPECTED_FILES)
def test_generate_file_list(package, glob, expected, include_executables):
    paths_dict = EXPECTED_DICT[package]
    modules_glob = {glob}
    if not include_executables:
        expected = remove_executables(expected)
    tested = generate_file_list(paths_dict, modules_glob, include_executables)

    assert tested == expected


def test_generate_file_list_unused_glob():
    paths_dict = EXPECTED_DICT["kerberos"]
    modules_glob = {"kerberos", "unused_glob1", "unused_glob2", "kerb*"}
    with pytest.raises(ValueError) as excinfo:
        generate_file_list(paths_dict, modules_glob, True)

    assert "unused_glob1, unused_glob2" in str(excinfo.value)
    assert "kerb" not in str(excinfo.value)


@pytest.mark.parametrize(
    "arguments, output",
    [
        (["requests*", "kerberos", "+bindir"], ({"requests*", "kerberos"}, True)),
        (["tldr", "tensorf*"], ({"tldr", "tensorf*"}, False)),
        (["+bindir"], (set(), True)),
    ],
)
def test_parse_varargs_good(arguments, output):
    assert parse_varargs(arguments) == output


@pytest.mark.parametrize(
    "arguments, wrong",
    [
        (["+kinkdir"], 0),
        (["good", "+bad", "*ugly*"], 1),
        (["+bad", "my.bad"], 0),
        (["mod", "mod.*"], "mod"),
        (["my.bad", "+bad"], "my"),
    ],
)
def test_parse_varargs_bad(arguments, wrong):
    with pytest.raises(ValueError) as excinfo:
        parse_varargs(arguments)
    if isinstance(wrong, int):
        assert str(excinfo.value) == f"Invalid argument: {arguments[wrong]}"
    else:
        assert str(excinfo.value).startswith("Attempted to use a namespaced package")
        assert f" {wrong} " in str(excinfo.value)


def create_root(tmp_path, record_path, rel_path_record):
    """create mock buildroot in tmp_path

    parameters:
    tmp_path: path where buildroot should be created
    record_path: expected path found in buildroot
    rel_path_record: relative path to test RECORD file

    example:
    create_root(Path('tmp'), '/usr/lib/python/tldr-0.5.dist-info/RECORD', 'test_RECORD_tldr')
    -> copy RECORD file and creates subdirectories in 'tmp/buildroot/usr/lib/python/tldr-0.5.dist-info/RECORD'
    """

    src = RECORDS / rel_path_record
    buildroot = tmp_path / "buildroot"
    dest = buildroot / record_path.relative_to("/")
    dest.parent.mkdir(parents=True)
    shutil.copy(src, dest)
    return tmp_path / buildroot


def default_options(pyproject_files_path, mock_root):
    return [
        "--output",
        str(pyproject_files_path),
        "--buildroot",
        str(mock_root),
        "--sitelib",
        str(SITELIB),
        "--sitearch",
        str(SITEARCH),
        "--bindir",
        str(BINDIR),
    ]


@pytest.mark.parametrize("include_executables", (True, False))
@pytest.mark.parametrize("package, glob, expected", EXPECTED_FILES)
def test_cli(tmp_path, package, glob, expected, include_executables):
    mock_root = create_root(tmp_path, TEST_RECORDS[package], f"test_RECORD_{package}")
    pyproject_files_path = tmp_path / "files"
    globs = [glob, "+bindir"] if include_executables else [glob]
    cli_args = argparser().parse_args(
        [*default_options(pyproject_files_path, mock_root), *globs]
    )
    main(cli_args)

    if not include_executables:
        expected = remove_executables(expected)
    tested = pyproject_files_path.read_text()
    assert tested == "\n".join(expected) + "\n"


def test_cli_not_find_RECORD(tmp_path):
    mock_root = create_root(
        tmp_path, BuildrootPath("/usr/lib/RECORD"), "test_RECORD_tldr"
    )
    pyproject_files_path = tmp_path / "files"
    cli_args = argparser().parse_args(
        [*default_options(pyproject_files_path, mock_root), "tldr*"]
    )

    with pytest.raises(FileNotFoundError):
        main(cli_args)


def test_cli_find_too_many_RECORDS(tmp_path):
    mock_root = create_root(tmp_path, TEST_RECORDS["tldr"], "test_RECORD_tldr")
    create_root(tmp_path, TEST_RECORDS["tensorflow"], "test_RECORD_tensorflow")
    pyproject_files_path = tmp_path / "files"
    cli_args = argparser().parse_args(
        [*default_options(pyproject_files_path, mock_root), "tldr*"]
    )

    with pytest.raises(FileExistsError):
        main(cli_args)


def test_cli_bad_argument(tmp_path):
    mock_root = create_root(tmp_path, TEST_RECORDS["tldr"], "test_RECORD_tldr")
    pyproject_files_path = tmp_path / "files"
    cli_args = argparser().parse_args(
        [*default_options(pyproject_files_path, mock_root), "tldr*", "+foodir"]
    )

    with pytest.raises(ValueError):
        main(cli_args)


def test_cli_bad_option(tmp_path):
    mock_root = create_root(tmp_path, TEST_RECORDS["tldr"], "test_RECORD_tldr")
    pyproject_files_path = tmp_path / "files"
    cli_args = argparser().parse_args(
        [
            *default_options(pyproject_files_path, mock_root),
            "tldr*",
            "you_cannot_have_this",
        ]
    )

    with pytest.raises(ValueError):
        main(cli_args)


def test_cli_bad_namespace(tmp_path):
    mock_root = create_root(tmp_path, TEST_RECORDS["tldr"], "test_RECORD_tldr")
    pyproject_files_path = tmp_path / "files"
    cli_args = argparser().parse_args(
        [*default_options(pyproject_files_path, mock_root), "tldr.didntread"]
    )

    with pytest.raises(ValueError):
        main(cli_args)
