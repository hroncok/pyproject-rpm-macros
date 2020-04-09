Name:           pyproject-rpm-macros
Summary:        RPM macros for PEP 517 Python packages
License:        MIT

%bcond_without tests

# Keep the version at zero and increment only release
Version:        0
Release:        14%{?dist}

# Macro files
Source001:      macros.pyproject

# Implementation files
Source101:      pyproject_buildrequires.py
Source102:      pyproject_save_files.py

# Tests
Source201:      test_pyproject_buildrequires.py
Source202:      test_pyproject_save_files.py

# Test data
Source301:      pyproject_buildrequires_testcases.yaml
Source302:      pyproject_save_files_test_data.yaml
Source303:      test_RECORD

# Metadata
Source901:      README.md
Source902:      LICENSE

URL:            https://src.fedoraproject.org/rpms/pyproject-rpm-macros

BuildArch:      noarch

Requires: python3-pip >= 19
Requires: python3-devel

# We keep these here for now to avoid one loop of %%generate_buildrequires
# But those are also always in the output of %%generate_buildrequires
# in order to be removable in the future
Requires: python3dist(packaging)
Requires: python3dist(pytoml)

# This is not output from %%generate_buildrequires to work around:
#   https://github.com/rpm-software-management/mock/issues/336
Requires: (python3dist(importlib-metadata) if python3 < 3.8)

%if %{with tests}
BuildRequires: python3dist(pytest)
BuildRequires: python3dist(pyyaml)
BuildRequires: python3dist(packaging)
%if 0%{fedora} < 32
# The %%if should not be needed, it works around:
#   https://github.com/rpm-software-management/mock/issues/336
BuildRequires: (python3dist(importlib-metadata) if python3 < 3.8)
%endif
BuildRequires: python3dist(pytoml)
BuildRequires: python3dist(pip)
BuildRequires: python3dist(setuptools)
BuildRequires: python3dist(tox-current-env) >= 0.0.2
BuildRequires: python3dist(wheel)
%endif


%description
This is a provisional implementation of pyproject RPM macros for Fedora 30+.
These macros are useful for packaging Python projects that use the PEP 517
pyproject.toml file, which specifies the package's build dependencies
(including the build system, such as setuptools, flit or poetry).


%prep
# Not strictly necessary but allows working on file names instead
# of source numbers in install section
%setup -c -T
cp -p %{sources} .

%build
# nothing to do, sources are not buildable

%install
mkdir -p %{buildroot}%{_rpmmacrodir}
mkdir -p %{buildroot}%{_rpmconfigdir}/redhat
install -m 644 macros.pyproject %{buildroot}%{_rpmmacrodir}/
install -m 644 pyproject_buildrequires.py %{buildroot}%{_rpmconfigdir}/redhat/
install -m 644 pyproject_save_files.py  %{buildroot}%{_rpmconfigdir}/redhat/

%if %{with tests}
%check
%{python3} -m pytest -vv --doctest-modules
%endif


%files
%{_rpmmacrodir}/macros.pyproject
%{_rpmconfigdir}/redhat/pyproject_buildrequires.py
%{_rpmconfigdir}/redhat/pyproject_save_files.py

%doc README.md
%license LICENSE

%changelog
* Thu Apr 09 2020 Patrik Kopkan <pkopkan@redhat.com> - 0-14
- add %%pyproject_save_file macro for generating file section

* Mon Mar 02 2020 Miro Hrončok <mhroncok@redhat.com> - 0-13
- Tox dependency generator: Handle deps read in from a text file (#1808601)

* Wed Feb 05 2020 Miro Hrončok <mhroncok@redhat.com> - 0-12
- Fallback to setuptools.build_meta:__legacy__ backend instead of setuptools.build_meta
- Properly handle backends with colon
- Preserve existing flags in shebangs of Python files in /usr/bin

* Thu Jan 30 2020 Fedora Release Engineering <releng@fedoraproject.org> - 0-11
- Rebuilt for https://fedoraproject.org/wiki/Fedora_32_Mass_Rebuild

* Fri Nov 15 2019 Patrik Kopkan <pkopkan@redhat.com> - 0-10
- Install wheel in '$PWD/pyproject-macros-wheeldir' to have more explicit path from which we install.
- The path can be changed by redefining %%_pyproject_wheeldir.

* Wed Nov 13 2019 Anna Khaitovich <akhaitov@redhat.com> - 0-9
- Remove stray __pycache__ directory from /usr/bin when running %%pyproject_install

* Fri Oct 25 2019 Miro Hrončok <mhroncok@redhat.com> - 0-8
- When tox fails, print tox output before failing

* Tue Oct 08 2019 Miro Hrončok <mhroncok@redhat.com> - 0-7
- Move a verbose line of %%pyproject_buildrequires from stdout to stderr

* Fri Jul 26 2019 Petr Viktorin <pviktori@redhat.com> - 0-6
- Use importlib_metadata rather than pip freeze

* Fri Jul 26 2019 Miro Hrončok <mhroncok@redhat.com> - 0-5
- Allow to fetch test dependencies from tox
- Add %%tox macro to invoke tests

* Fri Jul 26 2019 Fedora Release Engineering <releng@fedoraproject.org> - 0-4
- Rebuilt for https://fedoraproject.org/wiki/Fedora_31_Mass_Rebuild

* Tue Jul 02 2019 Miro Hrončok <mhroncok@redhat.com> - 0-3
- Add %%pyproject_buildrequires

* Tue Jul 02 2019 Miro Hrončok <mhroncok@redhat.com> - 0-2
- Fix shell syntax errors in %%pyproject_install
- Drop PATH warning in %%pyproject_install

* Fri Jun 28 2019 Patrik Kopkan <pkopkan@redhat.com> - 0-1
- created package
