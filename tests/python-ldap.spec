# global prerelease b4

# workaround for https://bugzilla.redhat.com/show_bug.cgi?id=1806625
%global debug_package %{nil}

Name: python-ldap
Version: 3.1.0
Release: 9%{?dist}
License: Python
Summary: An object-oriented API to access LDAP directory servers
URL: http://python-ldap.org/
Source0: %{pypi_source}

BuildRequires: pyproject-rpm-macros

### Build Dependencies ###
BuildRequires: openldap-devel
BuildRequires: openssl-devel
BuildRequires: cyrus-sasl-devel
BuildRequires: gcc
BuildRequires: openldap-servers
BuildRequires: openldap-clients

%generate_buildrequires
%pyproject_buildrequires -t

%description
This package contains extension modules. Does not contain pyproject.toml. Has multiple files and directories.
Building this tests:
- the proper files are installed in the proper places
- module glob in %%pyproject_save_files (some modules are included, some not)


%package -n     python3-ldap
Summary:        %{summary}

Requires:  openldap
Requires:  python3-pyasn1 >= 0.3.7
Requires:  python3-pyasn1-modules >= 0.1.5
Requires:  python3-setuptools
%{?python_provide:%python_provide python3-ldap}

%description -n python3-ldap
%{summary}


%prep


%setup -q -n %{name}-%{version}%{?prerelease}

# Disable warnings in test to work around "'U' mode is deprecated"
# https://github.com/python-ldap/python-ldap/issues/96
sed -i 's,-Werror,-Wignore,g' tox.ini

%build
%pyproject_wheel

%install
%pyproject_install
%pyproject_save_files ldap* *ldap

%check
# don't download packages
#export PIP_INDEX_URL=http://host.invalid./
#export PIP_NO_DEPS=yes
LOGLEVEL=10 %tox -- --sitepackages

# check if the instalation outputs expected files
test -d "%{buildroot}%{python3_sitearch}/__pycache__/" 
test -d "%{buildroot}%{python3_sitearch}/python_ldap-%{version}.dist-info/" 
test -d "%{buildroot}%{python3_sitearch}/ldap/" 
test -f "%{buildroot}%{python3_sitearch}/ldapurl.py" 
test -f "%{buildroot}%{python3_sitearch}/ldif.py" 
test -d "%{buildroot}%{python3_sitearch}/slapdtest" 
test -n "$(find '%{buildroot}%{python3_sitearch}' -maxdepth 1 -name '_ldap.cpython-*.so' -print -quit)"

# Not supposed to be listed in %{pyproject_files}. Making sure build will fail if they got listed.
rm -rf %{buildroot}%{python3_sitearch}/ldif.py
rm -rf %{buildroot}%{python3_sitearch}/__pycache__/ldif.cpython*.pyc
rm -rf %{buildroot}%{python3_sitearch}/slapdtest/

%files -n python3-ldap -f %{pyproject_files}
%license LICENCE
%doc CHANGES README TODO Demo