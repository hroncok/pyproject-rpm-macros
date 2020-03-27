import pytest
import os
from pathlib import Path
from pprint import pprint
from pprint import pformat
import pyproject_save_files
from pyproject_save_files import *
import tempfile
import warnings
from pathlib import PurePath
from pathlib import Path
import shutil
import sys

RECORDS_PATH = Path(__file__).parent
SITELIB = PurePath("/usr/lib/python3.7/site-packages")
SITEARCH = PurePath("/usr/lib64/python3.7/site-packages")


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
    """test if RECORD file is parsed properly"""
    record_content = read_record(RECORDS_PATH / "test_RECORD_kerberos")
    output = parse_record(PurePath("/usr/lib64/python3.7/site-packages/kerberos-1.3.0.dist-info/RECORD"), record_content)
    expected = [PurePath("/usr/lib64/python3.7/site-packages/kerberos-1.3.0.dist-info/INSTALLER"),
                PurePath("/usr/lib64/python3.7/site-packages/kerberos-1.3.0.dist-info/METADATA"),
                PurePath("/usr/lib64/python3.7/site-packages/kerberos-1.3.0.dist-info/RECORD"),
                PurePath("/usr/lib64/python3.7/site-packages/kerberos-1.3.0.dist-info/WHEEL"),
                PurePath("/usr/lib64/python3.7/site-packages/kerberos-1.3.0.dist-info/top_level.txt"),
                PurePath("/usr/lib64/python3.7/site-packages/kerberos.cpython-37m-x86_64-linux-gnu.so")]
    assert output == expected


def test_parse_record_tensorflow():
    """test if RECORD file is parsed properly"""
    dist_info_dir = "tensorflow-2.1.0.dist-info"
    dist_info_prefix = "/usr/lib64/python3.7/site-packages"

    record_content = [
        ["../../../bin/toco_from_protos", "sha256=W1RBTgnD8F2jVoq2RiIfW_Ph6HNm7Kw0Jz-1_4MANDU", "289"],
        [
            "../../../lib/python3.7/site-packages/tensorflow_core/include/tensorflow/core/common_runtime/base_collective_executor.h",
            "sha256=7RAlc1tDVIXyRwVp3YaGHzQb9xzSXwUh89XYdN2JE-c", "1024"],
        ["tensorflow-2.1.0.dist-info/METADATA", "sha256=g5W3QfLBbDHaqVmDvLXQIV2KfDFQe9zssq4fKz-Rah4", "2859"],
    ]
    output = parse_record(PurePath(f"{dist_info_prefix}/{dist_info_dir}/RECORD"), record_content)

    pprint(output)
    expected = [PurePath('/usr/bin/toco_from_protos'),
                PurePath('/usr/lib/python3.7/site-packages/tensorflow_core/include/tensorflow/core/common_runtime/base_collective_executor.h'),
                PurePath('/usr/lib64/python3.7/site-packages/tensorflow-2.1.0.dist-info/METADATA'),
                ]
    assert output == expected


# [packagename: (expected path in buildroot, relative path to test RECORD file)]
TEST_RECORDS = {
    "kerberos": ("/usr/lib64/python3.7/site-packages/kerberos-1.3.0.dist-info/RECORD", "test_RECORD_kerberos"),
    "requests": ("/usr/lib/python3.7/site-packages/requests-2.22.0.dist-info/RECORD", "test_RECORD_requests"),
    "tensorflow": ("/usr/lib64/python3.7/site-packages/tensorflow-2.1.0.dist-info/RECORD", "test_RECORD_tensorflow"),
    "tldr": ("/usr/lib/python3.7/site-packages/tldr-0.5.dist-info/RECORD", "test_RECORD_tldr"),
    "mistune": ("/usr/lib64/python3.7/site-packages/mistune-0.8.3.dist-info/RECORD", "test_RECORD_mistune")
}

test_data = []
import json
with open(f"{RECORDS_PATH}/pyproject_save_files_test_data.json", "r", encoding='utf-8') as file:
    PARAMETRIZED_EXPECTED_OUTPUT = json.loads(file.read())


for package in TEST_RECORDS:
    test_data.append((*TEST_RECORDS[package], PARAMETRIZED_EXPECTED_OUTPUT[package]))

del package

file_section = (
    ("tensorflow", "tensorflow*", sorted([
        '/usr/lib/python3.7/site-packages/tensorflow_core/',
        "/usr/lib64/python3.7/site-packages/tensorflow/", "/usr/lib64/python3.7/site-packages/tensorflow_core/",
        "%dir /usr/lib64/python3.7/site-packages/tensorflow-2.1.0.dist-info",
        "/usr/lib64/python3.7/site-packages/tensorflow-2.1.0.dist-info/INSTALLER",
        "/usr/lib64/python3.7/site-packages/tensorflow-2.1.0.dist-info/METADATA",
        "/usr/lib64/python3.7/site-packages/tensorflow-2.1.0.dist-info/RECORD",
        "/usr/lib64/python3.7/site-packages/tensorflow-2.1.0.dist-info/WHEEL",
        "/usr/lib64/python3.7/site-packages/tensorflow-2.1.0.dist-info/entry_points.txt",
        "/usr/lib64/python3.7/site-packages/tensorflow-2.1.0.dist-info/top_level.txt",
    ])),
    ("kerberos", "ke?ber*", sorted(["/usr/lib64/python3.7/site-packages/kerberos.cpython-37m-x86_64-linux-gnu.so",
                             "%dir /usr/lib64/python3.7/site-packages/kerberos-1.3.0.dist-info",
                             "/usr/lib64/python3.7/site-packages/kerberos-1.3.0.dist-info/INSTALLER",
                             "/usr/lib64/python3.7/site-packages/kerberos-1.3.0.dist-info/METADATA",
                             "/usr/lib64/python3.7/site-packages/kerberos-1.3.0.dist-info/RECORD",
                             "/usr/lib64/python3.7/site-packages/kerberos-1.3.0.dist-info/WHEEL",
                             "/usr/lib64/python3.7/site-packages/kerberos-1.3.0.dist-info/top_level.txt",
                             ])),
    ("requests", "requests", sorted(["/usr/lib/python3.7/site-packages/requests/",
                              "%dir /usr/lib/python3.7/site-packages/requests-2.22.0.dist-info",
                              "/usr/lib/python3.7/site-packages/requests-2.22.0.dist-info/INSTALLER",
                              "/usr/lib/python3.7/site-packages/requests-2.22.0.dist-info/LICENSE",
                              "/usr/lib/python3.7/site-packages/requests-2.22.0.dist-info/METADATA",
                              "/usr/lib/python3.7/site-packages/requests-2.22.0.dist-info/RECORD",
                              "/usr/lib/python3.7/site-packages/requests-2.22.0.dist-info/WHEEL",
                              "/usr/lib/python3.7/site-packages/requests-2.22.0.dist-info/top_level.txt",
                              ])),
    ("tldr", "tldr", sorted(["/usr/lib/python3.7/site-packages/__pycache__/tldr.cpython-37{,.opt-?}.pyc",
                              "/usr/lib/python3.7/site-packages/tldr.py",
                              "%dir /usr/lib/python3.7/site-packages/tldr-0.5.dist-info",
                              "/usr/lib/python3.7/site-packages/tldr-0.5.dist-info/INSTALLER",
                              "/usr/lib/python3.7/site-packages/tldr-0.5.dist-info/LICENSE",
                              "/usr/lib/python3.7/site-packages/tldr-0.5.dist-info/METADATA",
                              "/usr/lib/python3.7/site-packages/tldr-0.5.dist-info/RECORD",
                              "/usr/lib/python3.7/site-packages/tldr-0.5.dist-info/WHEEL",
                              "/usr/lib/python3.7/site-packages/tldr-0.5.dist-info/top_level.txt",
                              ])),

    ("mistune", "mistune", sorted([
        "/usr/lib64/python3.7/site-packages/__pycache__/mistune.cpython-37{,.opt-?}.pyc",
        "%dir /usr/lib64/python3.7/site-packages/mistune-0.8.3.dist-info",
        "/usr/lib64/python3.7/site-packages/mistune-0.8.3.dist-info/INSTALLER",
        "/usr/lib64/python3.7/site-packages/mistune-0.8.3.dist-info/LICENSE",
        "/usr/lib64/python3.7/site-packages/mistune-0.8.3.dist-info/METADATA",
        "/usr/lib64/python3.7/site-packages/mistune-0.8.3.dist-info/RECORD",
        "/usr/lib64/python3.7/site-packages/mistune-0.8.3.dist-info/WHEEL",
        "/usr/lib64/python3.7/site-packages/mistune-0.8.3.dist-info/top_level.txt",
        "/usr/lib64/python3.7/site-packages/mistune.py",
        "/usr/lib64/python3.7/site-packages/mistune.cpython-37m-x86_64-linux-gnu.so"
    ]))
)


@pytest.mark.parametrize("package, glob, expected", file_section)
def test_generate_file_list(package, glob, expected):
    """test glob at output of classify_paths"""
    paths_dict = PARAMETRIZED_EXPECTED_OUTPUT[package]
    modules_glob = (glob,)
    record_path = TEST_RECORDS[package][0]
    tested = generate_file_list(paths_dict, modules_glob, False)

    assert tested == expected


@pytest.mark.parametrize("package, glob, expected", file_section)
def test_generate_file_list_with_executables(package, glob, expected):
    """test glob at output of classify_paths"""
    paths_dict = PARAMETRIZED_EXPECTED_OUTPUT[package]
    executables = PARAMETRIZED_EXPECTED_OUTPUT[package]["executables"]["files"]
    modules_glob = (glob,)
    files = sorted(expected + executables)
    record_path = PurePath(TEST_RECORDS[package][0])
    tested = generate_file_list(paths_dict, modules_glob,
                                include_executables=True)
    assert tested == files


def test_parse_globs():
    tested = [parse_globs(["requests*", "kerberos", "+bindir"]),
              parse_globs(["tldr", "tensorf*"])]

    expected = [(["requests*", "kerberos"], True), (["tldr", "tensorf*"], False)]
    assert tested == expected


def create_root(tmp_path, record_path, rel_path_record):
    """create mock buildroot in tmp_path

    parameters:
    tmp_path: path where buildroot should be created
    record_path: expected path found in buildroot
    rel_path_record: relative path to test RECORD file

    example:
    create_root(tmp_path, '/usr/lib/python/tldr-0.5.dist-info/RECORD', 'test_RECORD_tldr')
    -> copy RECORD file and creates subdirectories tmp/buildroot/usr/lib/python/tldr-0.5.dist-info/RECORD'
    """

    dist_info_path =  "/".join(record_path.split("/")[:-1])
    src = os.path.join(RECORDS_PATH, rel_path_record)
    dest = f"{tmp_path}/buildroot/{record_path}"
    os.makedirs(f"{tmp_path}/buildroot/{dist_info_path}")
    shutil.copy(src, dest)
    return f"{tmp_path}/buildroot/"


@pytest.mark.parametrize("package, glob, expected", file_section)
def test_cli(tmp_path, package, glob, expected):
    """test cli"""

    mock_root = create_root(tmp_path, *TEST_RECORDS[package])
    buildir = tmp_path / "builddir"
    buildir.mkdir()
    pyproject_files_path = buildir / "files"
    cli_args = argparser().parse_args([str(pyproject_files_path),
                                  mock_root,
                                  "/usr/lib/python3.7/site-packages",
                                  "/usr/lib64/python3.7/site-packages", "/usr/bin", glob])

    main(cli_args)
    with open(pyproject_files_path, "r") as file:
        tested = file.readlines()
        expected = [path + "\n" for path in expected]
        assert tested == expected


def test_not_find_RECORD(tmp_path):
    """test if program raises error on not finding RECORD file"""

    mock_root = create_root(tmp_path, "/usr/lib/RECORD", TEST_RECORDS["tldr"][1])

    buildir = tmp_path / "builddir"
    buildir.mkdir()
    pyproject_files_path = buildir / "files"
    cli_args = argparser().parse_args([str(pyproject_files_path),
                                  mock_root,
                                  "/usr/lib/python3.7/site-packages",
                                  "/usr/lib64/python3.7/site-packages", "/usr/bin", "tldr*"])

    with pytest.raises(FileNotFoundError):
        main(cli_args)


def test_find_too_many_RECORDS(tmp_path):
    """test if program raises error on finding multiple RECORD files"""

    mock_root = create_root(tmp_path, *TEST_RECORDS["tldr"])
    create_root(tmp_path, *TEST_RECORDS["tensorflow"])

    buildir = tmp_path / "builddir"
    buildir.mkdir()
    pyproject_files_path = buildir / "files"
    cli_args = argparser().parse_args([str(pyproject_files_path),
                                  mock_root,
                                  "/usr/lib/python3.7/site-packages",
                                  "/usr/lib64/python3.7/site-packages", "/usr/bin", "tldr*"])

    with pytest.raises(FileExistsError):
        main(cli_args)

