%global pypi_name pytest
Name:           python-%{pypi_name}
Version:        4.4.2
Release:        0%{?dist}
Summary:        Simple powerful testing with Python
License:        MIT
URL:            https://pytest.org
Source0:        %{pypi_source}

BuildArch:      noarch
BuildRequires:  pyproject-rpm-macros

%description
This is a pure Python package with executables. It has a test suite in tox.ini and test dependencies specified via the [test] extra.
Building this tests:
- generating runtime and test dependencies by both tox.ini and extras
- pyproject.toml with the setuptools backend and setuptools-scm
- passing arguments into %%tox

%package -n python3-%{pypi_name}
Summary:        %{summary}
%{?python_provide:%python_provide python3-%{pypi_name}}

%description -n python3-%{pypi_name}
py.test provides simple, yet powerful testing for Python.


%prep
%autosetup -p1 -n %{pypi_name}-%{version}


%generate_buildrequires
%pyproject_buildrequires -x testing -t
%pyproject_save_files *pytest +bindir

%build
%pyproject_wheel


%install
%pyproject_install

%check
# Only run one test (which uses a test-only dependency, hypothesis).
# (Unfortunately, some other tests still fail.)
%tox -- -- -k metafunc


%files -n python3-%{pypi_name} -f %{pyproject_files}
%doc README.rst
%doc CHANGELOG.rst
%license LICENSE
