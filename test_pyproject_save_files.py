import pytest
import yaml

from pathlib import Path
from pprint import pprint

from pyproject_save_files import argparser, generate_file_list, main
from pyproject_save_files import parse_record, read_record
from pyproject_save_files import BuildrootPath


DIR = Path(__file__).parent
BINDIR = BuildrootPath("/usr/bin")
SITELIB = BuildrootPath("/usr/lib/python3.7/site-packages")
SITEARCH = BuildrootPath("/usr/lib64/python3.7/site-packages")

yaml_file = DIR / "pyproject_save_files_test_data.yaml"
yaml_data = yaml.safe_load(yaml_file.read_text())
EXPECTED_DICT = yaml_data["classified"]
EXPECTED_FILES = yaml_data["dumped"]
TEST_RECORDS = yaml_data["records"]


def test_parse_record_tldr():
    record_path = BuildrootPath(TEST_RECORDS["tldr"]["path"])
    record_content = read_record(DIR / "test_RECORD")
    output = list(parse_record(record_path, record_content))
    pprint(output)
    expected = [
        BINDIR / "__pycache__/tldr.cpython-37.pyc",
        BINDIR / "tldr",
        BINDIR / "tldr.py",
        SITELIB / "__pycache__/tldr.cpython-37.pyc",
        SITELIB / "tldr-0.5.dist-info/INSTALLER",
        SITELIB / "tldr-0.5.dist-info/LICENSE",
        SITELIB / "tldr-0.5.dist-info/METADATA",
        SITELIB / "tldr-0.5.dist-info/RECORD",
        SITELIB / "tldr-0.5.dist-info/WHEEL",
        SITELIB / "tldr-0.5.dist-info/top_level.txt",
        SITELIB / "tldr.py",
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


def create_root(tmp_path, record_path, record_content):
    """create mock buildroot in tmp_path

    parameters:
    tmp_path: path where buildroot should be created
    record_path: expected path found in buildroot
    rel_path_record: relative path to test RECORD file

    example:
    create_root(Path('tmp'), '/usr/lib/python/tldr-0.5.dist-info/RECORD', '../../../bin/__pycache__/tldr.cpython-37.pyc,,\n...')
    -> copy RECORD file and creates subdirectories in 'tmp/buildroot/usr/lib/python/tldr-0.5.dist-info/RECORD'
    """

    buildroot = tmp_path / "buildroot"
    dest = buildroot / Path(record_path).relative_to("/")
    dest.parent.mkdir(parents=True)
    dest.write_text(record_content)
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
        "--python-version",
        "3.7",  # test data are for 3.7
    ]


@pytest.mark.parametrize("include_executables", (True, False))
@pytest.mark.parametrize("package, glob, expected", EXPECTED_FILES)
def test_cli(tmp_path, package, glob, expected, include_executables):
    mock_root = create_root(
        tmp_path, TEST_RECORDS[package]["path"], TEST_RECORDS[package]["content"]
    )
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
        tmp_path, BuildrootPath("/usr/lib/RECORD"), TEST_RECORDS["tldr"]["content"]
    )
    pyproject_files_path = tmp_path / "files"
    cli_args = argparser().parse_args(
        [*default_options(pyproject_files_path, mock_root), "tldr*"]
    )

    with pytest.raises(FileNotFoundError):
        main(cli_args)


def test_cli_find_too_many_RECORDS(tmp_path):
    mock_root = create_root(
        tmp_path, TEST_RECORDS["tldr"]["path"], TEST_RECORDS["tldr"]["content"]
    )
    create_root(
        tmp_path,
        TEST_RECORDS["tensorflow"]["path"],
        TEST_RECORDS["tensorflow"]["content"],
    )
    pyproject_files_path = tmp_path / "files"
    cli_args = argparser().parse_args(
        [*default_options(pyproject_files_path, mock_root), "tldr*"]
    )

    with pytest.raises(FileExistsError):
        main(cli_args)


def test_cli_bad_argument(tmp_path):
    mock_root = create_root(
        tmp_path, TEST_RECORDS["tldr"]["path"], TEST_RECORDS["tldr"]["content"]
    )
    pyproject_files_path = tmp_path / "files"
    cli_args = argparser().parse_args(
        [*default_options(pyproject_files_path, mock_root), "tldr*", "+foodir"]
    )

    with pytest.raises(ValueError):
        main(cli_args)


def test_cli_bad_option(tmp_path):
    mock_root = create_root(
        tmp_path, TEST_RECORDS["tldr"]["path"], TEST_RECORDS["tldr"]["content"]
    )
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
    mock_root = create_root(
        tmp_path, TEST_RECORDS["tldr"]["path"], TEST_RECORDS["tldr"]["content"]
    )
    pyproject_files_path = tmp_path / "files"
    cli_args = argparser().parse_args(
        [*default_options(pyproject_files_path, mock_root), "tldr.didntread"]
    )

    with pytest.raises(ValueError):
        main(cli_args)
