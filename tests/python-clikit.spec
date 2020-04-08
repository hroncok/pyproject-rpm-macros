%global pypi_name clikit
Name:           python-%{pypi_name}
Version:        0.3.1
Release:        1%{?dist}
Summary:        Builds beautiful and testable command line interfaces

License:        MIT
URL:            https://github.com/sdispater/clikit
Source0:        %{pypi_source}

BuildArch:      noarch
BuildRequires:  pyproject-rpm-macros

%description
Tests building with the poetry build backend.


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
%pyproject_save_files clikit


%files -n python3-%{pypi_name} -f %{pyproject_files}
%doc README.md
%license LICENSE
