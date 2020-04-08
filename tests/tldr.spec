Name:           tldr
Version:        0.4.4
Release:        1%{?dist}
Summary:        Simplified and community-driven man pages

License:        MIT
URL:            https://github.com/tldr-pages/tldr-python-client
Source0:        %{pypi_source}

BuildArch:      noarch
BuildRequires:  pyproject-rpm-macros

%description
A Python package containing executables.
Building this tests:
- there are no bytecompiled files in %%{_bindir}
- the executable's shebang is adjusted properly

%prep
%autosetup -n %{name}-%{version}

%generate_buildrequires
%pyproject_buildrequires

%build
%pyproject_wheel

%install
%pyproject_install
%pyproject_save_files tldr +bindir

%check
# Internal check for our macros: tests we don't ship __pycache__ in bindir
test ! -d %{buildroot}%{_bindir}/__pycache__

# Internal check for our macros: tests we have a proper shebang line
head -n1 %{buildroot}%{_bindir}/%{name}.py | grep -E '#!\s*%{python3}\s+%{py3_shbang_opts}\s*$'

%files -f %pyproject_files
%license LICENSE
%doc README.md
