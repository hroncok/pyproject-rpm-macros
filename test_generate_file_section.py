import pytest
import os
from pathlib import Path
from pprint import pprint
from pprint import pformat
import generate_file_section
from generate_file_section import *
import tempfile
import warnings
from pathlib import PurePath
from pathlib import Path
import shutil
import sys

RECORDS_PATH = f"{Path(__file__).parent}"
SITELIB = PurePath("/usr/lib/python3.7/site-packages")
SITEARCH = PurePath("/usr/lib64/python3.7/site-packages")


def test_parse_record_kerberos():
    """test if RECORD file is parsed properly"""
    record_content = read_record(RECORDS_PATH, "test_RECORD_kerberos")
    output = parse_record("/usr/lib64/python3.7/site-packages/kerberos-1.3.0.dist-info/RECORD", record_content)
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
    output = parse_record(f"{dist_info_prefix}/{dist_info_dir}/RECORD", record_content)

    pprint(output)
    expected = [PurePath('/usr/bin/toco_from_protos'),
                PurePath('/usr/lib/python3.7/site-packages/tensorflow_core/include/tensorflow/core/common_runtime/base_collective_executor.h'),
                PurePath('/usr/lib64/python3.7/site-packages/tensorflow-2.1.0.dist-info/METADATA'),
                ]
    assert output == expected


def test_find_metadata():
    """test if function returns list with all metadata paths"""
    dist_info_dir = "kerberos-1.3.0.dist-info/"
    dist_info_prefix = "/usr/lib64/python3.7/site-packages"
    parsed_record_content = [PurePath("/usr/lib64/python3.7/site-packages/kerberos-1.3.0.dist-info/INSTALLER"),
                             PurePath("/usr/lib64/python3.7/site-packages/kerberos-1.3.0.dist-info/METADATA"),
                             PurePath("/usr/lib64/python3.7/site-packages/kerberos-1.3.0.dist-info/RECORD"),
                             PurePath("/usr/lib64/python3.7/site-packages/kerberos-1.3.0.dist-info/WHEEL"),
                             PurePath("/usr/lib64/python3.7/site-packages/kerberos-1.3.0.dist-info/top_level.txt"),
                             PurePath("/usr/lib64/python3.7/site-packages/kerberos.cpython-37m-x86_64-linux-gnu.so")]
    expected = ("/usr/lib64/python3.7/site-packages/kerberos-1.3.0.dist-info/",
                ["/usr/lib64/python3.7/site-packages/kerberos-1.3.0.dist-info/INSTALLER",
                 "/usr/lib64/python3.7/site-packages/kerberos-1.3.0.dist-info/METADATA",
                 "/usr/lib64/python3.7/site-packages/kerberos-1.3.0.dist-info/RECORD",
                 "/usr/lib64/python3.7/site-packages/kerberos-1.3.0.dist-info/WHEEL",
                 "/usr/lib64/python3.7/site-packages/kerberos-1.3.0.dist-info/top_level.txt", ])

    record_path = os.path.join(dist_info_prefix, dist_info_dir, "RECORD")

    tested = find_metadata(parsed_record_content, PurePath(dist_info_prefix), PurePath(record_path))
    assert tested == expected


def test_find_extension():
    """test list of extension"""
    parsed_record_content = [PurePath("/usr/lib64/python3.7/site-packages/kerberos-1.3.0.dist-info/INSTALLER"),
                             PurePath("/usr/lib64/python3.7/site-packages/kerberos-1.3.0.dist-info/METADATA"),
                             PurePath("/usr/lib64/python3.7/site-packages/kerberos-1.3.0.dist-info/RECORD"),
                             PurePath("/usr/lib64/python3.7/site-packages/kerberos-1.3.0.dist-info/WHEEL"),
                             PurePath("/usr/lib64/python3.7/site-packages/kerberos-1.3.0.dist-info/top_level.txt"),
                             PurePath("/usr/lib64/python3.7/site-packages/tensorflow_core/python/ops/__pycache__/gen_state_ops.cpython-37.pyc"),
                             PurePath("/usr/lib64/python3.7/site-packages/kerberos.cpython-37m-x86_64-linux-gnu.so")]

    assert find_extension(SITEARCH, parsed_record_content) == ([
        "/usr/lib64/python3.7/site-packages/kerberos.cpython-37m-x86_64-linux-gnu.so"])


def test_find_script():
    dist_info_dir = Path("tldr-0.5.dist-info/")
    python3_sitedir = PurePath("/usr/lib64/python3.7/site-packages")
    record_content = read_record(Path(RECORDS_PATH), Path("test_RECORD_tldr"))
    record_path = python3_sitedir / dist_info_dir / "RECORD"
    parsed_record_content = parse_record(record_path, record_content)
    expected = (["/usr/lib64/python3.7/site-packages/tldr.py"],
                ["/usr/lib64/python3.7/site-packages/tldr.py",
                 "/usr/lib64/python3.7/site-packages/__pycache__/tldr.cpython-37.pyc"])

    tested = find_script(python3_sitedir, parsed_record_content)
    assert tested == expected


def test_find_package():
    dist_info_dir = PurePath("requests-2.22.0.dist-info/")
    python3_sitedir = PurePath("/usr/lib/python3.7/site-packages")
    python3_sitearch = PurePath("/usr/lib64/python3.7/site-packages")
    record_content = read_record(RECORDS_PATH, "test_RECORD_requests")
    record_path = python3_sitedir / dist_info_dir / "RECORD"
    parsed_record_content = parse_record(record_path, record_content)

    tested = find_package(python3_sitedir, python3_sitearch, parsed_record_content)
    expected = ({"/usr/lib/python3.7/site-packages/requests/"},
                ["/usr/lib/python3.7/site-packages/requests/__init__.py",
                 "/usr/lib/python3.7/site-packages/requests/__pycache__/__init__.cpython-37.pyc",
                 "/usr/lib/python3.7/site-packages/requests/__pycache__/__version__.cpython-37.pyc",
                 "/usr/lib/python3.7/site-packages/requests/__pycache__/_internal_utils.cpython-37.pyc",
                 "/usr/lib/python3.7/site-packages/requests/__pycache__/adapters.cpython-37.pyc",
                 "/usr/lib/python3.7/site-packages/requests/__pycache__/api.cpython-37.pyc",
                 "/usr/lib/python3.7/site-packages/requests/__pycache__/auth.cpython-37.pyc",
                 "/usr/lib/python3.7/site-packages/requests/__pycache__/certs.cpython-37.pyc",
                 "/usr/lib/python3.7/site-packages/requests/__pycache__/compat.cpython-37.pyc",
                 "/usr/lib/python3.7/site-packages/requests/__pycache__/cookies.cpython-37.pyc",
                 "/usr/lib/python3.7/site-packages/requests/__pycache__/exceptions.cpython-37.pyc",
                 "/usr/lib/python3.7/site-packages/requests/__pycache__/help.cpython-37.pyc",
                 "/usr/lib/python3.7/site-packages/requests/__pycache__/hooks.cpython-37.pyc",
                 "/usr/lib/python3.7/site-packages/requests/__pycache__/models.cpython-37.pyc",
                 "/usr/lib/python3.7/site-packages/requests/__pycache__/packages.cpython-37.pyc",
                 "/usr/lib/python3.7/site-packages/requests/__pycache__/sessions.cpython-37.pyc",
                 "/usr/lib/python3.7/site-packages/requests/__pycache__/status_codes.cpython-37.pyc",
                 "/usr/lib/python3.7/site-packages/requests/__pycache__/structures.cpython-37.pyc",
                 "/usr/lib/python3.7/site-packages/requests/__pycache__/utils.cpython-37.pyc",
                 "/usr/lib/python3.7/site-packages/requests/__version__.py",
                 "/usr/lib/python3.7/site-packages/requests/_internal_utils.py",
                 "/usr/lib/python3.7/site-packages/requests/adapters.py",
                 "/usr/lib/python3.7/site-packages/requests/api.py",
                 "/usr/lib/python3.7/site-packages/requests/auth.py",
                 "/usr/lib/python3.7/site-packages/requests/certs.py",
                 "/usr/lib/python3.7/site-packages/requests/compat.py",
                 "/usr/lib/python3.7/site-packages/requests/cookies.py",
                 "/usr/lib/python3.7/site-packages/requests/exceptions.py",
                 "/usr/lib/python3.7/site-packages/requests/help.py",
                 "/usr/lib/python3.7/site-packages/requests/hooks.py",
                 "/usr/lib/python3.7/site-packages/requests/models.py",
                 "/usr/lib/python3.7/site-packages/requests/packages.py",
                 "/usr/lib/python3.7/site-packages/requests/sessions.py",
                 "/usr/lib/python3.7/site-packages/requests/status_codes.py",
                 "/usr/lib/python3.7/site-packages/requests/structures.py",
                 "/usr/lib/python3.7/site-packages/requests/utils.py"])

    pprint(tested)
    assert tested == expected

# [packagename: (expected path in buildroot, relative path to test RECORD file)]
TEST_RECORDS = {
    "kerberos": ("/usr/lib64/python3.7/site-packages/kerberos-1.3.0.dist-info/RECORD", "test_RECORD_kerberos"),
    "requests": ("/usr/lib/python3.7/site-packages/requests-2.22.0.dist-info/RECORD", "test_RECORD_requests"),
    "tensorflow": ("/usr/lib64/python3.7/site-packages/tensorflow-2.1.0.dist-info/RECORD", "test_RECORD_tensorflow"),
    "tldr": ("/usr/lib/python3.7/site-packages/tldr-0.5.dist-info/RECORD", "test_RECORD_tldr"),
    "mistune": ("/usr/lib64/python3.7/site-packages/mistune-0.8.3.dist-info/RECORD", "test_RECORD_mistune")
}

test_data = []
from classify_paths_output import PARAMETRIZED_EXPECTED_OUTPUT

for package in TEST_RECORDS:
    test_data.append((*TEST_RECORDS[package], PARAMETRIZED_EXPECTED_OUTPUT[package]))

del package


# @pytest.mark.filterwarnings('ignore::UserWarning')  # to ignore warning for uncathegorized files
# @pytest.mark.parametrize("supposed_record_path, rel_record_path, expected", test_data)
# def test_classify_paths(supposed_record_path, rel_record_path, expected):
#     """test categorization of files"""
#     root = str(Path(RECORDS_PATH).parent)
#     python3_sitelib = PurePath("/usr/lib/python3.7/site-packages")
#     python3_sitearch = PurePath("/usr/lib64/python3.7/site-packages")
#     bindir = PurePath("/usr/bin")
#
#     record_contents = read_record(RECORDS_PATH, rel_record_path)
#     record_contents = parse_record(supposed_record_path,
#                                    record_contents)
#
#     output = classify_paths(supposed_record_path, record_contents, python3_sitelib, python3_sitearch, bindir)
#     assert output == expected

# right now there is no package which would have warning
# def test_warning_classify_paths():
#     """test categorization of files"""
#     supposed_record_path, rel_record_path = TEST_RECORDS["tensorflow"]
#     warned_files = PARAMETRIZED_EXPECTED_OUTPUT["tensorflow"]["other"]["files"]
#     root = str(Path(RECORDS_PATH).parent)
#     python3_sitelib = PurePath("/usr/lib/python3.7/site-packages")
#     python3_sitearch = PurePath("/usr/lib64/python3.7/site-packages")
#     bindir = PurePath("/usr/bin")
#
#     record_contents = read_record(RECORDS_PATH, rel_record_path)
#     record_contents = parse_record(supposed_record_path,
#                                    record_contents)
#
#     with pytest.warns(UserWarning) as record:
#         output = classify_paths(PurePath(supposed_record_path), record_contents, python3_sitelib, python3_sitearch, bindir)
#
#     assert pformat(warned_files) in record[0].message.args[0]


file_section = (
    ("tensorflow", "tensorflow*", sorted([
        '/usr/lib/python3.7/site-packages/tensorflow_core/',
        "/usr/lib64/python3.7/site-packages/tensorflow/", "/usr/lib64/python3.7/site-packages/tensorflow_core/",
        "/usr/lib64/python3.7/site-packages/tensorflow-2.1.0.dist-info/INSTALLER",
        "/usr/lib64/python3.7/site-packages/tensorflow-2.1.0.dist-info/METADATA",
        "/usr/lib64/python3.7/site-packages/tensorflow-2.1.0.dist-info/RECORD",
        "/usr/lib64/python3.7/site-packages/tensorflow-2.1.0.dist-info/WHEEL",
        "/usr/lib64/python3.7/site-packages/tensorflow-2.1.0.dist-info/entry_points.txt",
        "/usr/lib64/python3.7/site-packages/tensorflow-2.1.0.dist-info/top_level.txt",
    ])),
    ("kerberos", "ke?ber*", sorted(["/usr/lib64/python3.7/site-packages/kerberos.cpython-37m-x86_64-linux-gnu.so",
                             "/usr/lib64/python3.7/site-packages/kerberos-1.3.0.dist-info/INSTALLER",
                             "/usr/lib64/python3.7/site-packages/kerberos-1.3.0.dist-info/METADATA",
                             "/usr/lib64/python3.7/site-packages/kerberos-1.3.0.dist-info/RECORD",
                             "/usr/lib64/python3.7/site-packages/kerberos-1.3.0.dist-info/WHEEL",
                             "/usr/lib64/python3.7/site-packages/kerberos-1.3.0.dist-info/top_level.txt",
                             ])),
    ("requests", "requests", sorted(["/usr/lib/python3.7/site-packages/requests/",
                              "/usr/lib/python3.7/site-packages/requests-2.22.0.dist-info/INSTALLER",
                              "/usr/lib/python3.7/site-packages/requests-2.22.0.dist-info/LICENSE",
                              "/usr/lib/python3.7/site-packages/requests-2.22.0.dist-info/METADATA",
                              "/usr/lib/python3.7/site-packages/requests-2.22.0.dist-info/RECORD",
                              "/usr/lib/python3.7/site-packages/requests-2.22.0.dist-info/WHEEL",
                              "/usr/lib/python3.7/site-packages/requests-2.22.0.dist-info/top_level.txt",
                              ])),
    ("tldr", "tldr", sorted(["/usr/lib/python3.7/site-packages/__pycache__/tldr.cpython-3" + str(sys.version_info[1]) + "{,.opt-?}.pyc",
                              "/usr/lib/python3.7/site-packages/tldr.py",
                              "/usr/lib/python3.7/site-packages/tldr-0.5.dist-info/INSTALLER",
                              "/usr/lib/python3.7/site-packages/tldr-0.5.dist-info/LICENSE",
                              "/usr/lib/python3.7/site-packages/tldr-0.5.dist-info/METADATA",
                              "/usr/lib/python3.7/site-packages/tldr-0.5.dist-info/RECORD",
                              "/usr/lib/python3.7/site-packages/tldr-0.5.dist-info/WHEEL",
                              "/usr/lib/python3.7/site-packages/tldr-0.5.dist-info/top_level.txt",
                              ])),

    ("mistune", "mistune", sorted([
        "/usr/lib64/python3.7/site-packages/__pycache__/mistune.cpython-3" + str(sys.version_info[1]) + "{,.opt-?}.pyc",
        "/usr/lib64/python3.7/site-packages/mistune-0.8.3.dist-info/INSTALLER",
        "/usr/lib64/python3.7/site-packages/mistune-0.8.3.dist-info/LICENSE",
        "/usr/lib64/python3.7/site-packages/mistune-0.8.3.dist-info/METADATA",
        "/usr/lib64/python3.7/site-packages/mistune-0.8.3.dist-info/RECORD",
        "/usr/lib64/python3.7/site-packages/mistune-0.8.3.dist-info/WHEEL",
        "/usr/lib64/python3.7/site-packages/mistune-0.8.3.dist-info/top_level.txt",
        "/usr/lib64/python3.7/site-packages/mistune.py",
        "/usr/lib64/python3.7/site-packages/mistune.cpython-38-x86_64-linux-gnu.so"
    ]))
)


@pytest.mark.parametrize("package, glob, expected", file_section)
def test_generate_file_list(package, glob, expected):
    """test glob at output of classify_paths"""
    paths_dict = PARAMETRIZED_EXPECTED_OUTPUT[package]
    modules_glob = (glob,)
    record_path = TEST_RECORDS[package][0]
    tested = generate_file_list(PurePath(record_path), PurePath("/usr/lib/python3.7/site-packages"),
                                PurePath("/usr/lib64/python3.7/site-packages"), paths_dict, modules_glob, False)

    assert tested == expected


@pytest.mark.parametrize("package, glob, expected", file_section)
def test_generate_file_list_with_executables(package, glob, expected):
    """test glob at output of classify_paths"""
    paths_dict = PARAMETRIZED_EXPECTED_OUTPUT[package]
    executables = PARAMETRIZED_EXPECTED_OUTPUT[package]["executables"]["files"]
    modules_glob = (glob,)
    files = sorted(expected + executables)
    record_path = PurePath(TEST_RECORDS[package][0])
    tested = generate_file_list(record_path, SITELIB,
                                SITEARCH, paths_dict, modules_glob,
                                include_executables=True)
    assert tested == files


def test_pyproject_save_files_parse():
    tested = [pyproject_save_files_parse(["requests*", "kerberos", "+bindir"]),
              pyproject_save_files_parse(["tldr", "tensorf*"])]

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
    cli_args = parser.parse_args([str(pyproject_files_path),
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
    cli_args = parser.parse_args([str(pyproject_files_path),
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
    cli_args = parser.parse_args([str(pyproject_files_path),
                                  mock_root,
                                  "/usr/lib/python3.7/site-packages",
                                  "/usr/lib64/python3.7/site-packages", "/usr/bin", "tldr*"])

    with pytest.raises(FileExistsError):
        main(cli_args)


def test_glob_filter_simple():
    test_list = [PurePath('/usr/lib/python3.7/site-packages/requests-2.22.0.dist-info/RECORD')]
    assert glob_filter("*dist-info/RECORD", test_list) == ['/usr/lib/python3.7/site-packages/requests-2.22.0.dist-info/RECORD']


def test_glob_filter_recursive_glob_simple():
    test_list = [PurePath('/usr/lib/python3.7/site-packages/requests-2.22.0.dist-info/RECORD')]
    assert glob_filter("/**/*dist-info/RECORD", test_list) == [
        '/usr/lib/python3.7/site-packages/requests-2.22.0.dist-info/RECORD']


def test_glob_filter_recursive_glob():
    test_list = [PurePath('/usr/lib/python3.7/site-packages/requests/requests_main/main.py')]
    assert glob_filter('/usr/lib/python3.7/site-packages/requests/**/*.py', test_list) == [
        '/usr/lib/python3.7/site-packages/requests/requests_main/main.py']


def test_glob_filter_recursive_glob_not_match():
    test_list = [PurePath('/usr/lib/python3.7/site-packages/requests/main.py')]
    tested = glob_filter('/usr/lib/python3.7/site-packages/requests/**/*/*.py', test_list)
    assert tested == []


def test_glob_filter_recursive_match():
    test_list = [PurePath('/usr/lib/python3.8/site-packages/isort/utils.py')]
    tested = glob_filter('/usr/lib/python3.8/site-packages/**/*/*.py', test_list)
    assert tested == ['/usr/lib/python3.8/site-packages/isort/utils.py']
