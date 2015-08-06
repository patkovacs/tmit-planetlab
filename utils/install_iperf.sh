#!/usr/bin/env bash
#baseurl=http://ftp.cuhk.edu.hk/pub/linux/fedora-archive/fedora/linux/releases/\$releasever/Everything/\$basearch/os/
#http://dl.fedoraproject.org/pub/archive/fedora/linux/releases/\$releasever/Everything/\$basearch/os/


#archive.fedoraproject.org/fedora/linux/updates/testing/14/x86_64/iperf-2.0.5-3.fc14.x86_64.rpm
#ftp://ftp.pbone.net/mirror/archive.fedoraproject.org/fedora/linux/updates/testing/14/x86_64/iperf-2.0.5-3.fc14.x86_64.rpm
#sudo rpm -Uvh package-name.rpm






su

cp /etc/yum.repos.d/fedora.repo /etc/yum.repos.d/fedora.repo.bckp

echo """[fedora]
name=Fedora \$releasever - \$basearch
failovermethod=priority
#baseurl=http://archives.fedoraproject.org/pub/archive/fedora/linux/releases/\$releasever/Everything/\$basearch/os/
#baseurl=http://download.fedoraproject.org/pub/fedora/linux/releases/\$releasever/Everything/\$basearch/os/
#mirrorlist=https://mirrors.fedoraproject.org/metalink?repo=fedora-\$releasever&arch=\$basearch
mirrorlist=http://mirrors.fedoraproject.org/mirrorlist?repo=fedora-\$releasever&arch=\$basearch
enabled=1
metadata_expire=7d
gpgcheck=0
gpgkey=http://archives.fedoraproject.org/pub/archive/fedora/linux/releases/\$releasever/Everything/\$basearch/os/RPM-GPG-KEY-fedora-\$basearch

[fedora-debuginfo]
name=Fedora \$releasever - \$basearch - Debug
failovermethod=priority
#baseurl=http://download.fedoraproject.org/pub/fedora/linux/releases/\$releasever/Everything/\$basearch/debug/
mirrorlist=http://mirrors.fedoraproject.org/metalink?repo=fedora-debug-\$releasever&arch=\$basearch
enabled=0
metadata_expire=7d
gpgcheck=1
gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-fedora-\$basearch

[fedora-source]
name=Fedora \$releasever - Source
failovermethod=priority
#baseurl=http://download.fedoraproject.org/pub/fedora/linux/releases/\$releasever/Everything/source/SRPMS/
mirrorlist=http://mirrors.fedoraproject.org/metalink?repo=fedora-source-\$releasever&arch=\$basearch
enabled=0
metadata_expire=7d
gpgcheck=1
gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-fedora-\$basearch
""" > fedora.repo

yum clean all
yum info kernel
