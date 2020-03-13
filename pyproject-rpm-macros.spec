Name:           pyproject-rpm-macros
Summary:        RPM macros for PEP 517 Python packages
License:        MIT

%bcond_without tests

# Keep the version at zero and increment only release
Version:        0
Release:        13%{?dist}
Source0:        macros.pyproject
Source1:        pyproject_buildrequires.py
Source2:        generate_file_section.py
Source3:        test_generate_file_section.py
Source4:        classify_paths_output.py


Source8:        README.md
Source9:        LICENSE

Source10:       test_pyproject_buildrequires.py
Source11:       testcases.yaml

Source12:       test_RECORD_kerberos
Source13:       test_RECORD_requests
Source14:       test_RECORD_tensorflow
Source15:       test_RECORD_tldr
Source16:       test_RECORD_mistune


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
install -m 644 generate_file_section.py  %{buildroot}%{_rpmconfigdir}/redhat/
%if %{with tests}
%check
%{__python3} -m pytest -vv
%endif


%files
%{_rpmmacrodir}/macros.pyproject
%{_rpmconfigdir}/redhat/pyproject_buildrequires.py
%{_rpmconfigdir}/redhat/generate_file_section.py
%doc README.md
%license LICENSE

%changelog
* Mon Feb 17 2020 Patrik Kopkan <pkopkan@redhat.com> - 0-13
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
