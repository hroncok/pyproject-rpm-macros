# workaround for https://bugzilla.redhat.com/show_bug.cgi?id=1806625
%global debug_package %{nil}

Name:           python-mistune
Version:        0.8.3
Release:        11%{?dist}
Summary:        Markdown parser for Python

License:        BSD
URL:            https://github.com/lepture/mistune
Source0:        %{url}/archive/v%{version}.tar.gz

BuildRequires:  gcc
BuildRequires:  pyproject-rpm-macros

# optional dependency, listed explicitly to have the extension module:
BuildRequires:  python3-Cython

%description
This package contains an extension module. Does not contain pyproject.toml.
Has a script (.py) and extension (.so) with identical name.
Building this tests:
- installing both a script and an extension with the same name
- default build backend without pyproject.toml


%package -n python3-mistune
Summary:        %summary

%description -n python3-mistune
%{summary}


%prep
%autosetup -n mistune-%{version}


%generate_buildrequires
%pyproject_buildrequires


%build
%pyproject_wheel


%install
%pyproject_install
%pyproject_save_files mistune


%check
# Internal check for our macros
# making sure that pyproject_install outputs these files so that we can test behaviour of %%pyproject_save_files
# when a package has multiple files with the same name (here script and extension)
test -f %{buildroot}%{python3_sitearch}/mistune.py
test -f %{buildroot}%{python3_sitearch}/mistune.cpython-*.so


%files -n python3-mistune -f %{pyproject_files}
%doc README.rst
%license LICENSE
