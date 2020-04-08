%global pypi_name entrypoints
Name:           python-%{pypi_name}
Version:        0.3
Release:        0%{?dist}
Summary:        Discover and load entry points from installed packages
License:        MIT
URL:            https://entrypoints.readthedocs.io/
Source0:        %{pypi_source}

BuildArch:      noarch
BuildRequires:  pyproject-rpm-macros

%description
This package contains one .py module
Building this tests the flit build backend.


%package -n python3-%{pypi_name}
Summary:        %{summary}

%description -n python3-%{pypi_name}
%{summary}.


%prep
%autosetup -p1 -n %{pypi_name}-%{version}


%generate_buildrequires
%pyproject_buildrequires


%build
%pyproject_wheel


%install
%pyproject_install
%pyproject_save_files entrypoints


%check
# Internal check: Top level __pycache__ is never owned
grep -vE '/__pycache__$' %{pyproject_files}
grep -vE '/__pycache__/$' %{pyproject_files}
grep -F '/__pycache__/' %{pyproject_files}


%files -n python3-%{pypi_name} -f %{pyproject_files}
%doc README.rst
%license LICENSE
