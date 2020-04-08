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
This is a pure Python package with executables. It has a test suite in tox.ini
and test dependencies specified via the [test] extra.
Building this tests:
- generating runtime and test dependencies by both tox.ini and extras
- pyproject.toml with the setuptools backend and setuptools-scm
- passing arguments into %%tox

%package -n python3-%{pypi_name}
Summary:        %{summary}

%description -n python3-%{pypi_name}
%{summary}.


%prep
%autosetup -p1 -n %{pypi_name}-%{version}


%generate_buildrequires
%pyproject_buildrequires -x testing -t

%build
%pyproject_wheel


%install
%pyproject_install
%pyproject_save_files *pytest +bindir

%check
# Only run one test (which uses a test-only dependency, hypothesis)
# See how to pass options trough the macro to tox, trough tox to pytest
%tox -- -- -k metafunc


%files -n python3-%{pypi_name} -f %{pyproject_files}
%doc README.rst
%doc CHANGELOG.rst
%license LICENSE
