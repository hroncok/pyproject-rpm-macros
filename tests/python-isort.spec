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
Building this tests that executables are not listed when +bindir is not used
with %%pyproject_save_files.

%package -n python3-%{modname}
Summary:            %{summary}

%description -n python3-%{modname}
%{summary}.


%prep
%autosetup -n %{modname}-%{version}-2


%generate_buildrequires
%pyproject_buildrequires -r


%build
%pyproject_wheel


%install
%pyproject_install
%pyproject_save_files isort


%check
# Internal check if the instalation outputs expected result
test -d %{buildroot}%{python3_sitelib}/%{modname}/
test -d %{buildroot}%{python3_sitelib}/%{modname}-%{version}.dist-info/

# Internal check that executables are not present when +bindir was not used with %%pyproject_save_files
grep -vF %{buildroot}%{_bindir}/%{modname} %{pyproject_files}


%files -n python3-%{modname} -f %{pyproject_files}
%doc README.rst *.md
%license LICENSE
%{_bindir}/%{modname}
