#!/usr/bin/env bash


#baseurl=http://ftp.cuhk.edu.hk/pub/linux/fedora-archive/fedora/linux/releases/\$releasever/Everything/\$basearch/os/
#http://dl.fedoraproject.org/pub/archive/fedora/linux/releases/\$releasever/Everything/\$basearch/os/


# Mukodik: http://dl.fedoraproject.org/pub/archive/fedora/linux/releases/14/Everything/i386/os/repodata/repomd.xml



#baseurl=http://ftp.cuhk.edu.hk/pub/linux/fedora-archive/fedora/linux/releases/\$releasever/Everything/\$basearch/os/
#http://dl.fedoraproject.org/pub/archive/fedora/linux/releases/\$releasever/Everything/\$basearch/os/
#baseurl=http://archives.fedoraproject.org/pub/archive/fedora/linux/releases/\$releasever/Everything/\$basearch/os/
#baseurl=http://download.fedoraproject.org/pub/fedora/linux/releases/\$releasever/Everything/\$basearch/os/
#mirrorlist=https://mirrors.fedoraproject.org/metalink?repo=fedora-\$releasever&arch=\$basearch



#archive.fedoraproject.org/fedora/linux/updates/testing/14/x86_64/iperf-2.0.5-3.fc14.x86_64.rpm
#ftp://ftp.pbone.net/mirror/archive.fedoraproject.org/fedora/linux/updates/testing/14/x86_64/iperf-2.0.5-3.fc14.x86_64.rpm
#sudo rpm -Uvh package-name.rpm

#yum clean all
#yum info kernel

su

cp /etc/yum.repos.d/fedora.repo /etc/yum.repos.d/fedora.repo.bckp
cp /etc/yum.repos.d/fedora-updates.repo /etc/yum.repos.d/fedora-updates.repo.bckp


echo """[fedora]
name=Fedora \$releasever - \$basearch
failovermethod=priority
baseurl=http://dl.fedoraproject.org/pub/archive/fedora/linux/releases/\$releasever/Everything/\$basearch/os/
#mirrorlist=http://mirrors.fedoraproject.org/mirrorlist?repo=fedora-\$releasever&arch=\$basearch
enabled=1
metadata_expire=7d
gpgcheck=0
gpgkey=http://archives.fedoraproject.org/pub/archive/fedora/linux/releases/\$releasever/Everything/\$basearch/os/RPM-GPG-KEY-fedora-\$basearch

[fedora-debuginfo]
name=Fedora \$releasever - \$basearch - Debug
failovermethod=priority
baseurl=http://dl.fedoraproject.org/pub/archive/fedora/linux/releases/\$releasever/Everything/\$basearch/debug/
#baseurl=http://download.fedoraproject.org/pub/fedora/linux/releases/\$releasever/Everything/\$basearch/debug/
#mirrorlist=http://mirrors.fedoraproject.org/metalink?repo=fedora-debug-\$releasever&arch=\$basearch
enabled=0
metadata_expire=7d
gpgcheck=0
gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-fedora-\$basearch

[fedora-source]
name=Fedora \$releasever - Source
failovermethod=priority

baseurl=http://dl.fedoraproject.org/pub/archive/fedora/linux/releases/\$releasever/Everything/source/SRPMS/
#baseurl=http://download.fedoraproject.org/pub/fedora/linux/releases/\$releasever/Everything/source/SRPMS/
#mirrorlist=http://mirrors.fedoraproject.org/metalink?repo=fedora-source-\$releasever&arch=\$basearch
enabled=0
metadata_expire=7d
gpgcheck=0
gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-fedora-\$basearch
""" > fedora.repo


echo """
[updates]
name=Fedora $releasever - $basearch - Updates
failovermethod=priority
baseurl=http://dl.fedoraproject.org/pub/archive/fedora/linux/updates/\$releasever/\$basearch/
#baseurl=http://download.fedoraproject.org/pub/fedora/linux/updates/$releasever/$basearch/
#mirrorlist=https://mirrors.fedoraproject.org/metalink?repo=updates-released-f$releasever&arch=$basearch
enabled=1
gpgcheck=0
gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-fedora-$basearch

[updates-debuginfo]
name=Fedora $releasever - $basearch - Updates - Debug
failovermethod=priority
baseurl=http://dl.fedoraproject.org/pub/archive/fedora/linux/updates/\$releasever/\$basearch/debug/
#baseurl=http://download.fedoraproject.org/pub/fedora/linux/updates/$releasever/$basearch/debug/
#mirrorlist=https://mirrors.fedoraproject.org/metalink?repo=updates-released-debug-f$releasever&arch=$basearch
enabled=0
gpgcheck=0
gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-fedora-$basearch

[updates-source]
name=Fedora $releasever - Updates Source
failovermethod=priority
baseurl=http://dl.fedoraproject.org/pub/archive/fedora/linux/updates/\$releasever/SRPMS/
#baseurl=http://download.fedoraproject.org/pub/fedora/linux/updates/$releasever/SRPMS/
#mirrorlist=https://mirrors.fedoraproject.org/metalink?repo=updates-released-source-f$releasever&arch=$basearch
enabled=0
gpgcheck=0
gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-fedora-$basearch
""" > fedora-updates.repo

yum install iperf -y
