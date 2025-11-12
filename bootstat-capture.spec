%define name bootstat-capture
%define version 1.0
%define release 1%{?dist}
%define summary Boot status checker and shutdown trace capture tools
%define license GPLv2+

Name:           %{name}
Version:        %{version}
Release:        %{release}
Summary:        %{summary}
License:        %{license}
Group:          System Environment/Base
Source0:        %{name}-%{version}.tar.gz
BuildArch:      noarch
BuildRequires:  bash
Requires:      bash systemd
Requires(pre):  shadow-utils
Requires(post): systemd
Requires(preun): systemd
Requires(postun): systemd

%description
Boot status checker and shutdown trace capture tools for detecting kernel
panics, oops, and BUG traces across reboots.

This package includes:
- bootstat: Check boot status and detect shutdown errors
- capture-shutdown: Captures dmesg during shutdown
- capture-boot: Captures dmesg immediately on boot

These tools work together to preserve kernel traces that occur during
shutdown, which would otherwise be lost when the system reboots.

%prep
%setup -q

%build
# No build step needed for shell scripts

%install
# Install scripts to standard Fedora binary directory
install -d %{buildroot}%{_bindir}
install -m 755 bootstat %{buildroot}%{_bindir}/
install -m 755 capture-boot %{buildroot}%{_bindir}/
install -m 755 capture-shutdown %{buildroot}%{_bindir}/
# Verify scripts are executable and have correct shebang
test -x %{buildroot}%{_bindir}/capture-boot || exit 1
test -x %{buildroot}%{_bindir}/capture-shutdown || exit 1
grep -q '^#!/bin/bash' %{buildroot}%{_bindir}/capture-boot || exit 1
grep -q '^#!/bin/bash' %{buildroot}%{_bindir}/capture-shutdown || exit 1

# Install systemd service files (paths are already correct in source files)
install -d %{buildroot}%{_unitdir}
install -m 644 capture-boot.service %{buildroot}%{_unitdir}/
install -m 644 capture-shutdown.service %{buildroot}%{_unitdir}/
# Verify the paths are correct (safety check)
grep -q 'ExecStart=/usr/bin/' %{buildroot}%{_unitdir}/capture-boot.service || {
    echo "ERROR: capture-boot.service does not have /usr/bin/ path!" >&2
    grep ExecStart %{buildroot}%{_unitdir}/capture-boot.service >&2
    exit 1
}
grep -q 'ExecStart=/usr/bin/' %{buildroot}%{_unitdir}/capture-shutdown.service || {
    echo "ERROR: capture-shutdown.service does not have /usr/bin/ path!" >&2
    grep ExecStart %{buildroot}%{_unitdir}/capture-shutdown.service >&2
    exit 1
}

# Install documentation
install -d %{buildroot}%{_docdir}/%{name}
install -m 644 CAPTURE-SHUTDOWN-README %{buildroot}%{_docdir}/%{name}/

# Create log directory structure
install -d %{buildroot}/var/log/shutdown-traces

%pre
# Create log directory with proper permissions if it doesn't exist
# This ensures the directory exists before services try to use it
getent group root >/dev/null 2>&1 || exit 1
if [ ! -d /var/log/shutdown-traces ]; then
    mkdir -p /var/log/shutdown-traces
    chmod 755 /var/log/shutdown-traces
    chown root:root /var/log/shutdown-traces
fi

%post
# Remove any override files in /etc/systemd/system/ that might have old paths
# These override files take precedence over /usr/lib/systemd/system/ files
# We want to use the RPM-managed files from /usr/lib/systemd/system/
if [ -f /etc/systemd/system/capture-boot.service ] && [ ! -L /etc/systemd/system/capture-boot.service ]; then
    echo "Removing override file /etc/systemd/system/capture-boot.service (not a symlink)"
    rm -f /etc/systemd/system/capture-boot.service
fi
if [ -f /etc/systemd/system/capture-shutdown.service ] && [ ! -L /etc/systemd/system/capture-shutdown.service ]; then
    echo "Removing override file /etc/systemd/system/capture-shutdown.service (not a symlink)"
    rm -f /etc/systemd/system/capture-shutdown.service
fi

# Disable services first to remove any old symlinks
systemctl disable capture-shutdown.service capture-boot.service >/dev/null 2>&1 || :

# Reload systemd daemon to recognize new service files
systemctl daemon-reload >/dev/null 2>&1 || :

# Enable services (capture-shutdown runs on shutdown, capture-boot runs on boot)
# This will create proper symlinks pointing to /usr/lib/systemd/system/
systemctl enable capture-shutdown.service capture-boot.service >/dev/null 2>&1 || :

# Start capture-boot service immediately (capture-shutdown only runs on shutdown)
systemctl start capture-boot.service >/dev/null 2>&1 || :

%preun
# Stop and disable services before removal
if [ $1 -eq 0 ]; then
    # Package is being removed (not upgraded)
    # Reload daemon first to ensure we have latest service definitions
    systemctl daemon-reload >/dev/null 2>&1 || :
    # Stop services
    systemctl stop capture-shutdown.service capture-boot.service >/dev/null 2>&1 || :
    # Disable services (removes symlinks from /etc/systemd/system/)
    systemctl disable capture-shutdown.service capture-boot.service >/dev/null 2>&1 || :
fi

%postun
# Clean up systemd after removal or upgrade
if [ $1 -eq 0 ]; then
    # Package was removed (not upgraded)
    systemctl daemon-reload >/dev/null 2>&1 || :
else
    # Package was upgraded - reload systemd and restart services
    systemctl daemon-reload >/dev/null 2>&1 || :
    systemctl try-restart capture-boot.service >/dev/null 2>&1 || :
fi

%files
%defattr(-,root,root,-)
%{_bindir}/bootstat
%{_bindir}/capture-boot
%{_bindir}/capture-shutdown
%{_unitdir}/capture-boot.service
%{_unitdir}/capture-shutdown.service
%{_docdir}/%{name}/CAPTURE-SHUTDOWN-README
%dir %attr(755,root,root) /var/log/shutdown-traces

%changelog
* %(date "+%a %b %d %Y") Your Name <your.email@example.com> - %{version}-%{release}
- Initial package release
- Includes bootstat, capture-shutdown, and capture-boot
- Scripts installed to standard Fedora directories (%{_bindir})
- Includes systemd service files for automatic capture during shutdown and boot
- Proper scriptlets for service management and log directory creation

