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
Building this tests:
- the flit build backend
- the %%{python3_sitelib}/__pycache__ directory is not listed in %%pyproject_files


%package -n python3-%{pypi_name}
Summary:        %{summary}
%{?python_provide:%python_provide python3-%{pypi_name}}

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

%files -n python3-%{pypi_name} -f %{pyproject_files}
%doc README.rst
%license LICENSE
