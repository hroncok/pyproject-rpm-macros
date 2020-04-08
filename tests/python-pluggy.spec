%global pypi_name pluggy
Name:           python-%{pypi_name}
Version:        0.13.0
Release:        1%{?dist}
Summary:        The plugin manager stripped of pytest specific details

License:        MIT
URL:            https://github.com/pytest-dev/pluggy
Source0:        %{pypi_source}

BuildArch:      noarch
BuildRequires:  pyproject-rpm-macros

%description
A pure Python library. The package contains tox.ini. Does not contain executables.
Building this tests:
- generating runtime and testing dependencies
- running tests with %%tox
- the %%pyproject_save_files +bindir option works without actual executables
- pyproject.toml with the setuptools backend and setuptools-scm


%package -n python3-%{pypi_name}
Summary:        %{summary}

%description -n python3-%{pypi_name}
%{summary}.


%prep
%autosetup -p1 -n %{pypi_name}-%{version}


%generate_buildrequires
%pyproject_buildrequires -t


%build
%pyproject_wheel


%install
%pyproject_install
# There are no executables, but we are allowed to pass +bindir anyway
%pyproject_save_files pluggy +bindir


%check
%tox


%files -n python3-%{pypi_name} -f %{pyproject_files}
%doc README.rst
%license LICENSE
