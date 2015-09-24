# Raspberry Pi VPN Client router
*Route all incoming traffic through an OpenVPN SSL VPN*

The Pi-hush is a Raspberry Pi router that will send all incoming traffic received through a WLAN or LAN interface through an OpenVPN tunnel stablished trough another LAN interface
It uses different led colours to indicate status, link on, acquired IP, access to internet, VPN established...

## Hardware used 

- Raspberry Pi 2
- WLAN USB Dongle Edimax EW-7811Un [Realtek RTL8188CUS]
- Apple USB - Ethernet Adapter
- LED board: https://www.piborg.org/ledborg/ (OPTIONAL)
- Soft buttton (OPTIONAL)
(components from other vendors might also work)

## Target
**eth0** (the embedded ethernet port)
  - WAN port to connect to upstream router
  - Gets IP, DNS from DHCP
  - After 30 seconds, all traffic is sent through OpenVPN  (time needed to go through potential captive portals)
  - All incoming connections are rejected
  
**eth1** (USB to Ethernet adapter)
	- Local LAN
  - Fixed IP 172.16.0.1
  - Offers DHCP IPS from 172.16.0.3 to 172.16.0.199
  - Offers DNS service

**wlan0** (USB WLAN dongle)
	- Creates WLAN network
	- WPA2
  - Fixed IP 172.16.1.1
  - Offers DHCP IPS from 172.16.1.2 to 172.16.1.199
  - Offers DNS service

## Table of Contents

* [Raspberry Pi first boot](#raspberry-pi-first-boot)
* [Clean up, update and install necessary modules](#clean-up,-update-and-install-necessary-modules)
* [Configure dnsmasq](#configure-dnsmasq)
* [Network configuration](#network-configuration)
* [wlan0 as an access point](#wlan0-as-an-access-point)
* [OpenVPN client configuration](#openvpn-client-configuration)
* [Iptables configuration](#iptables-configuration)
* [Enhancement: Use a muticolor led for network monitoring](README-leds.md)
* [Enhancement: Shutdown button](README-shutdown.md)
* [References](#references)

## Raspberry Pi first boot

* Plug screen and keyboard
* Expand FileSystem
* Update password
* Update keyboard layout (if necessary)

## Clean up, update and install necessary modules

* Remove GUI packages (*Warning* this will take some time). I remove all GUI packages as I don´t use them and it saves more than 2GB. This is not necessary and you can skip this step if you are unsure or want to keep them.
```bash
sudo apt-get -y install deborphan
sudo apt-get -y autoremove --purge libx11-.* lxde-.* raspberrypi-artwork xkb-data omxplayer penguinspuzzle sgml-base xml-core alsa-.* cifs-.* samba-.* fonts-.* desktop-* gnome-.*
sudo apt-get -y autoremove --purge $(deborphan)
sudo apt-get -y autoremove --purge
sudo apt-get autoclean
```
* Update firmware (boot partition)
```bash
sudo rpi-update 
sudo reboot
```
* Remove packages that might conflict with the new ones, install required packages and update the rest.
```bash
sudo apt-get -y remove bind9 isc-dhcp-server 
sudo apt-get -y update
sudo apt-get -y upgrade 
sudo apt-get -y autoremove --purge
sudo apt-get -y install dnsmasq openvpn tcpdump iw bridge-utils dos2unix python-netifaces python-dev python-setuptools
```

## Configure dnsmasq

* Edit the file /etc/dnsmasq.d/dnsmasq.custom.conf  and replace it's content with:
```bash
# Interfaces
interface=eth1
interface=wlan0
listen-address=127.0.0.1

# DNS Configuration
domain-needed
bogus-priv
no-resolv
server=8.8.4.4
server=8.8.8.8
cache-size=10000
local-ttl=300

# DHCP Configuration
dhcp-range=eth1,172.16.0.2,172.16.0.199,12h
dhcp-range=wlan0,172.16.1.2,172.16.1.199,12h

dhcp-option=eth1,3,172.16.0.1 # router ethernet interface
dhcp-option=wlan0,3,172.16.1.1 # router wlan interface

dhcp-option=eth1,6,172.16.0.1 # our local DNS Server
dhcp-option=wlan0,6,172.16.1.1 # our local DNS Server
dhcp-authoritative # force clients to grab a new IP
```

If you plan to use [pi-hole](http://jacobsalmela.com/block-millions-ads-network-wide-with-a-raspberry-pi-hole-2-0/), a highly recommended DNS and Malware blocker, add also the entry below. 
```bash
addn-hosts=/etc/pihole/gravity.list
```
Have in mind that the current gravity.sh script from [pi-hole](http://jacobsalmela.com/block-millions-ads-network-wide-with-a-raspberry-pi-hole-2-0/) creates a host file with all IPs of all network interfaces. I recommend you use my own version of the gravity.sh scripts that allows you to define the IP where to redirect all requests: (https://raw.githubusercontent.com/jofrep/pi-hole/IP-as-input-parameter/gravity.sh). Just execute ./gravity 123.123.123.123  (but using your target IP)
   
## Network configuration

* Edit /etc/network/interfaces and replace it with the content below:
```bash
auto lo
iface lo inet loopback

auto eth0
iface eth0 inet dhcp

auto eth1
allow-hotplug eth1
iface eth1 inet static
        address 172.16.0.1
        netmask 255.255.255.0

#auto wlan0
allow-hotplug wlan0
iface wlan0 inet static
        address 172.16.1.1
        netmask 255.255.255.0
```
* Set routing
```bash
echo 1 | sudo tee /proc/sys/net/ipv4/ip_forward
```
* Ensure persistency eddting /etc/sysctl.conf and seeting forwarding on:
```bash
net.ipv4.ip_forward=1
```
* Reboot the RPi
```bash
sudo reboot
```

## wlan0 as an access point

* Follow instructions below to build hostapd. Instructions taken from (http://www.jenssegers.be/blog/43/Realtek-RTL8188-based-access-point-on-Raspberry-Pi)

*WARNING:* if you use a different WLAN dongle skip this and finds the right way to configure it as an Access Point. Perhaps the default hostpad is good enough for you
```bash
sudo apt-get autoremove hostapd
wget https://github.com/jenssegers/RTL8188-hostapd/archive/v2.0.tar.gz
tar -zxvf v2.0.tar.gz
cd RTL8188-hostapd-2.0/hostapd
sudo make
sudo make install
```
* Edit the file /etc/init.d/hostapd and add to (DAEMON_CONF=) the following line:
```bash
DAEMON_CONF=/etc/hostapd/hostapd.conf
```

* Edit the file hostapd.conf /etc/hostapd/hostapd.confand update the following values 
```bash
ssid=CHOOSE-SOME-NAME
wpa_passphrase=longrandompasswordb4a1d29d5eaa92a26270e8acfc4
```bash
* restart service
```bash
sudo service hostapd restart
```
* in case of errors execute
```bash
sudo hostapd /etc/hostapd/hostapd.conf
```

## OpenVPN client configuration

The assumption is that you already have an OpenVPN server to connect to. The Raspberry Pi will act as a client only.
* Copy all configuration files (certs, key, ta, config) to /etc/openvpn
* Rename configuration file to openvpn.conf
* Start OpenVPN and ensure it's working fine
```bash
sudo service openvpn start   
```
* Remove openvpn from start
```bash
sudo update-rc.d openvpn remove
```
* Set script to delay OpenVPN start for 30 segons  (/home/pi/start-openvpn-delay.sh)
```bash
#!/bin/sh

# Script used at boot to start openvpn with a 30 seconds delay to allow end user to go through login pages
sleep 30
sudo service openvpn start
```
* Make file executable
```bash
chmod +x /home/pi/start-openvpn-delay.sh
```

## Iptables configuration
 Create file /usr/local/bin/iptables.onlynat.sh with contents below
```bash 
# Set default policies for INPUT, FORWARD and OUTPUT chains
sudo iptables -P INPUT DROP
sudo iptables -P FORWARD DROP
sudo iptables -P OUTPUT ACCEPT

# Allow all traffic from local address and local LANs
sudo iptables -A INPUT -i lo    -j ACCEPT
sudo iptables -A INPUT -i eth1  -j ACCEPT
sudo iptables -A INPUT -i wlan0 -j ACCEPT

# NAT forwarded traffic exiting eth0 or wlan1
sudo iptables -t nat -A POSTROUTING -o eth0  -j MASQUERADE
sudo iptables -t nat -A POSTROUTING -o tun0  -j MASQUERADE

# Accept established traffic being forwared
sudo iptables -A FORWARD -i eth0  -o eth1  -m state --state RELATED,ESTABLISHED -j ACCEPT
sudo iptables -A FORWARD -i eth0  -o wlan0 -m state --state RELATED,ESTABLISHED -j ACCEPT

# Accept exit traffic from LANs to WAN(s)
sudo iptables -A FORWARD -i eth1  -o eth0  -j ACCEPT
sudo iptables -A FORWARD -i wlan0 -o eth0  -j ACCEPT

# Accept exit traffic from LANs to VPN
sudo iptables -A FORWARD -i eth1  -o tun0  -j ACCEPT
sudo iptables -A FORWARD -i wlan0 -o tun0  -j ACCEPT
sudo iptables -A FORWARD -i tun0  -o eth1  -m state --state RELATED,ESTABLISHED -j ACCEPT
sudo iptables -A FORWARD -i tun0  -o wlan0 -m state --state RELATED,ESTABLISHED -j ACCEPT

# OPTIONAL: Logging dropped packets to syslog
sudo iptables -N LOGGING
sudo iptables -A INPUT -j LOGGING
sudo iptables -A FORWARD -j LOGGING
sudo iptables -A LOGGING -m limit --limit 2/min -j LOG --log-prefix "IPT-Drop: " --log-level 4
sudo iptables -A LOGGING -j DROP
```
* Make file executable
```bash
sudo chmod +x /usr/local/bin/iptables.onlynat.sh
```
* Add the following in /etc/rc.local
```bash
echo "Loading iptables for IP masquerading"
/usr/local/bin/iptables.onlynat.sh

echo "Delayed OpenVPN start"
nohup /home/pi/admin/start-openvpn-delay.sh &
```

## References
* (http://makezine.com/projects/browse-anonymously-with-a-diy-raspberry-pi-vpntor-router/)
* (http://alphaloop.blogspot.de/2014/01/raspberry-pi-as-vpn-wireless-access.html)
* [Pi-Hole, Block Ads and Malware using a Raspberry Pi](http://jacobsalmela.com/block-millions-ads-network-wide-with-a-raspberry-pi-hole-2-0/)
* [Set Python Script as a Service](http://blog.scphillips.com/posts/2013/07/getting-a-python-script-to-run-in-the-background-as-a-service-on-boot/)
* [Wlan as an access point using a Realtek RTL8188 dongle](http://www.jenssegers.be/blog/43/Realtek-RTL8188-based-access-point-on-Raspberry-Pi)
* [Led Borg](https://www.piborg.org/ledborg/)