%global modname isort

Name:               python-%{modname}
Version:            4.3.21
Release:            7%{?dist}
Summary:            Python utility / library to sort Python imports

License:            MIT
URL:                https://github.com/timothycrosley/%{modname}
Source0:            %{url}/archive/%{version}-2/%{modname}-%{version}-2.tar.gz
BuildArch:          noarch
BuildRequires:      pyproject-rpm-macros

%description
This package contains executables.
Building this tests that executables are not listed when +bindir is not used with %%pyproject_save_files.

%package -n python3-%{modname}
Summary:            %{summary}
%{?python_provide:%python_provide python%{python3_pkgversion}-%{modname}}


%description -n python3-%{modname}
%{summary}.

%prep
%autosetup -n %{modname}-%{version}-2
%generate_buildrequires
%pyproject_buildrequires -r

# Drop shebang
sed -i -e '1{\@^#!.*@d}' %{modname}/main.py

%build
%pyproject_wheel

%install
%pyproject_install
%pyproject_save_files isort

# check if the instalation outputs expected result
test -d "%{buildroot}%{python3_sitelib}/%{modname}/"
test -d "%{buildroot}%{python3_sitelib}/%{modname}-%{version}.dist-info/"

# testing not using +bindir in %%pyproject_save_files, make sure if the files get listed build will fail
# This line must come after %pyproject_save_files so the test is effective
rm -r %{buildroot}%{_bindir}/%{modname}


%files -n python3-%{modname} -f %{pyproject_files}
%doc README.rst *.md
%license LICENSE

