# workaround for https://bugzilla.redhat.com/show_bug.cgi?id=1806625
%global debug_package %{nil}

Name:           python-ldap
Version:        3.1.0
Release:        9%{?dist}
License:        Python
Summary:        An object-oriented API to access LDAP directory servers
Source0:        %{pypi_source}

BuildRequires:  pyproject-rpm-macros

BuildRequires:  cyrus-sasl-devel
BuildRequires:  gcc
BuildRequires:  openldap-clients
BuildRequires:  openldap-devel
BuildRequires:  openldap-servers
BuildRequires:  openssl-devel


%description
This package contains extension modules. Does not contain pyproject.toml.
Has multiple files and directories.
Building this tests:
- the proper files are installed in the proper places
- module glob in %%pyproject_save_files (some modules are included, some not)
- combined manual and generated Buildrequires


%package -n     python3-ldap
Summary:        %{summary}

%description -n python3-ldap
%{summary}


%prep
%autosetup


%generate_buildrequires
%pyproject_buildrequires -t


%build
%pyproject_wheel


%install
%pyproject_install
# We can pass multiple globs
%pyproject_save_files ldap* *ldap


%check
# TODO: Upstream tox configuration calls setup.py test and rebuilds the extension module
# But we want to test the installed one instead
# This works but we are not testing what we ship
# https://github.com/python-ldap/python-ldap/issues/326
%tox

# Internal check if the instalation outputs expected files
test -d %{buildroot}%{python3_sitearch}/__pycache__/
test -d %{buildroot}%{python3_sitearch}/python_ldap-%{version}.dist-info/
test -d %{buildroot}%{python3_sitearch}/ldap/
test -f %{buildroot}%{python3_sitearch}/ldapurl.py
test -f %{buildroot}%{python3_sitearch}/ldif.py
test -d %{buildroot}%{python3_sitearch}/slapdtest/
test -f %{buildroot}%{python3_sitearch}/_ldap.cpython-*.so

# Internal check: Unmatched modules are not supposed to be listed in %%{pyproject_files}
# We'll list them explicitly
grep -vF %{python3_sitearch}/ldif.py %{pyproject_files}
grep -vF %{python3_sitearch}/__pycache__/ldif.cpython-%{python3_version_nodots}.pyc %{pyproject_files}
grep -vF %{python3_sitearch}/__pycache__/ldif.cpython-%{python3_version_nodots}.opt-1.pyc %{pyproject_files}
grep -vF %{python3_sitearch}/slapdtest/ %{pyproject_files}

# Internal check: Top level __pycache__ is never owned
grep -vE '/__pycache__$' %{pyproject_files}
grep -vE '/__pycache__/$' %{pyproject_files}


%files -n python3-ldap -f %{pyproject_files}
%license LICENCE
%doc CHANGES README TODO Demo
# Explicitly listed files can be combined with automation
%pycached %{python3_sitearch}/ldif.py
%{python3_sitearch}/slapdtest/
