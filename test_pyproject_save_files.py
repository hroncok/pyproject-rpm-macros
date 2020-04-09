import pytest
import yaml

from pathlib import Path
from pprint import pprint

from pyproject_save_files import argparser, generate_file_list, main
from pyproject_save_files import locate_record, parse_record, read_record
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


def create_root(tmp_path, *records):
    r"""
    Create mock buildroot in tmp_path

    parameters:
    tmp_path: path where buildroot should be created
    records: dicts with:
      path: expected path found in buildroot
      content: string content of the file

    Example:

        >>> record = {'path': '/usr/lib/python/tldr-0.5.dist-info/RECORD', 'content': '__pycache__/tldr.cpython-37.pyc,,\n...'}
        >>> create_root(Path('tmp'), record)
        PosixPath('tmp/buildroot')

    The example creates ./tmp/buildroot/usr/lib/python/tldr-0.5.dist-info/RECORD with the content.

        >>> import shutil
        >>> shutil.rmtree(Path('./tmp'))
    """
    buildroot = tmp_path / "buildroot"
    for record in records:
        dest = buildroot / Path(record["path"]).relative_to("/")
        dest.parent.mkdir(parents=True)
        dest.write_text(record["content"])
    return buildroot


@pytest.fixture
def tldr_root(tmp_path):
    return create_root(tmp_path, TEST_RECORDS["tldr"])


@pytest.fixture
def output(tmp_path):
    return tmp_path / "pyproject_files"


def test_locate_record_good(tmp_path):
    sitedir = tmp_path / "ha/ha/ha/site-packages"
    distinfo = sitedir / "foo-0.6.dist-info"
    distinfo.mkdir(parents=True)
    record = distinfo / "RECORD"
    record.write_text("\n")
    sitedir = BuildrootPath.from_real(sitedir, root=tmp_path)
    assert locate_record(tmp_path, {sitedir}) == record


def test_locate_record_missing(tmp_path):
    sitedir = tmp_path / "ha/ha/ha/site-packages"
    distinfo = sitedir / "foo-0.6.dist-info"
    distinfo.mkdir(parents=True)
    sitedir = BuildrootPath.from_real(sitedir, root=tmp_path)
    with pytest.raises(FileNotFoundError):
        locate_record(tmp_path, {sitedir})


def test_locate_record_misplaced(tmp_path):
    sitedir = tmp_path / "ha/ha/ha/site-packages"
    fakedir = tmp_path / "no/no/no/site-packages"
    distinfo = fakedir / "foo-0.6.dist-info"
    distinfo.mkdir(parents=True)
    record = distinfo / "RECORD"
    record.write_text("\n")
    sitedir = BuildrootPath.from_real(sitedir, root=tmp_path)
    with pytest.raises(FileNotFoundError):
        locate_record(tmp_path, {sitedir})


def test_locate_record_two_packages(tmp_path):
    sitedir = tmp_path / "ha/ha/ha/site-packages"
    for name in "foo-0.6.dist-info", "bar-1.8.dist-info":
        distinfo = sitedir / name
        distinfo.mkdir(parents=True)
        record = distinfo / "RECORD"
        record.write_text("\n")
    sitedir = BuildrootPath.from_real(sitedir, root=tmp_path)
    with pytest.raises(FileExistsError):
        locate_record(tmp_path, {sitedir})


def test_locate_record_two_sitedirs(tmp_path):
    sitedirs = ["ha/ha/ha/site-packages", "ha/ha/ha64/site-packages"]
    for idx, sitedir in enumerate(sitedirs):
        sitedir = tmp_path / sitedir
        distinfo = sitedir / "foo-0.6.dist-info"
        distinfo.mkdir(parents=True)
        record = distinfo / "RECORD"
        record.write_text("\n")
        sitedirs[idx] = BuildrootPath.from_real(sitedir, root=tmp_path)
    with pytest.raises(FileExistsError):
        locate_record(tmp_path, set(sitedirs))


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


def default_options(output, mock_root):
    return [
        "--output",
        str(output),
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
    mock_root = create_root(tmp_path, TEST_RECORDS[package])
    output = tmp_path / "files"
    globs = [glob, "+bindir"] if include_executables else [glob]
    cli_args = argparser().parse_args([*default_options(output, mock_root), *globs])
    main(cli_args)

    if not include_executables:
        expected = remove_executables(expected)
    tested = output.read_text()
    assert tested == "\n".join(expected) + "\n"


def test_cli_no_RECORD(tmp_path):
    mock_root = create_root(tmp_path)
    output = tmp_path / "files"
    cli_args = argparser().parse_args([*default_options(output, mock_root), "tldr*"])

    with pytest.raises(FileNotFoundError):
        main(cli_args)


def test_cli_misplaced_RECORD(tmp_path, output):
    record = {"path": "/usr/lib/", "content": TEST_RECORDS["tldr"]["content"]}
    mock_root = create_root(tmp_path, record)
    cli_args = argparser().parse_args([*default_options(output, mock_root), "tldr*"])

    with pytest.raises(FileNotFoundError):
        main(cli_args)


def test_cli_find_too_many_RECORDS(tldr_root, output):
    mock_root = create_root(tldr_root.parent, TEST_RECORDS["tensorflow"])
    cli_args = argparser().parse_args([*default_options(output, mock_root), "tldr*"])

    with pytest.raises(FileExistsError):
        main(cli_args)


def test_cli_bad_argument(tldr_root, output):
    cli_args = argparser().parse_args(
        [*default_options(output, tldr_root), "tldr*", "+foodir"]
    )

    with pytest.raises(ValueError):
        main(cli_args)


def test_cli_bad_option(tldr_root, output):
    cli_args = argparser().parse_args(
        [*default_options(output, tldr_root), "tldr*", "you_cannot_have_this"]
    )

    with pytest.raises(ValueError):
        main(cli_args)


def test_cli_bad_namespace(tldr_root, output):
    cli_args = argparser().parse_args(
        [*default_options(output, tldr_root), "tldr.didntread"]
    )

    with pytest.raises(ValueError):
        main(cli_args)
