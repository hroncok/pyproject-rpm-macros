from pathlib import Path
import io

import pytest
import yaml

from pyproject_buildrequires import generate_requires

try:
    import importlib.metadata as importlib_metadata
except ImportError:
    import importlib_metadata

testcases = {}
with Path(__file__).parent.joinpath('pyproject_buildrequires_testcases.yaml').open() as f:
    testcases = yaml.safe_load(f)


@pytest.mark.parametrize('case_name', testcases)
def test_data(case_name, capsys, tmp_path, monkeypatch):
    case = testcases[case_name]

    cwd = tmp_path.joinpath('cwd')
    cwd.mkdir()
    monkeypatch.chdir(cwd)

    if case.get('xfail'):
        pytest.xfail(case.get('xfail'))

    for filename in 'pyproject.toml', 'setup.py', 'tox.ini':
        if filename in case:
            cwd.joinpath(filename).write_text(case[filename])

    def get_installed_version(dist_name):
        try:
            return str(case['installed'][dist_name])
        except (KeyError, TypeError):
            raise importlib_metadata.PackageNotFoundError(
                f'info not found for {dist_name}'
            )

    try:
        generate_requires(
            get_installed_version=get_installed_version,
            include_runtime=case.get('include_runtime', False),
            extras=case.get('extras', ''),
            toxenv=case.get('toxenv', None),
        )
    except SystemExit as e:
        assert e.code == case['result']
    except Exception as e:
        if 'except' not in case:
            raise
        assert type(e).__name__ == case['except']
    else:
        assert 0 == case['result']

        captured = capsys.readouterr()
        assert captured.out == case['expected']
