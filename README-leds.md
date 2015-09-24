
# Enhancement: Use a multicolor led for network monitoring

We use [Ledborg](https://www.piborg.org/ledborg) to display different colors based on the network status

* No IP or link in eth0     => Blink RED
* Autoconfiguration IP      => Blink Magenta
* IP set but not access     => Fix YELLOW
* Direct access to Internet => Alternate GREEN/YELLOW
* OpenVPN stablished        => Fix GREEN

## Environment preparation
* Install the following
```bash
sudo easy_install wiringpi2
sudo easy_install netaddr
```
## netmon2led Service

* Add /usr/local/bin/netmon2led.py with the content below:
```python
#!/usr/bin/env python
########################################
# Monitor:
#  - OpenVPN
#  - Interface status
#  - IPs
# and set the LED colors acordingly
# We use a LedBorg:
#  https://www.piborg.org/ledborg/
########################################

import logging
import logging.handlers
import argparse
import sys
import time
import RPi.GPIO as GPIO
import os
import netifaces
import re
import urllib2
import wiringpi2 as wiringpi
import socket
wiringpi.wiringPiSetup()

# Setup the LedBorg GPIO pins
PIN_RED   = 0
PIN_GREEN = 2
PIN_BLUE  = 3
wiringpi.pinMode(PIN_RED,   wiringpi.GPIO.OUTPUT)
wiringpi.pinMode(PIN_GREEN, wiringpi.GPIO.OUTPUT)
wiringpi.pinMode(PIN_BLUE,  wiringpi.GPIO.OUTPUT)

 
# A function to set the LedBorg colours
def SetLedBorg(red, green, blue):
    wiringpi.digitalWrite(PIN_RED,   red)
    wiringpi.digitalWrite(PIN_GREEN, green)
    wiringpi.digitalWrite(PIN_BLUE,  blue)
 
# A function to turn the LedBorg off
def LedBorgOff():
    SetLedBorg(0, 0, 0)

# A function to check if we have direct access to internet
def internetacess():
    url = "http://clients3.google.com/generate_204"
    try:
        connection = urllib2.urlopen(url,timeout = 1)
        code =  connection.getcode()
        connection.close()
    except urllib2.HTTPError, e:
        code = e.getcode()
    except Exception as e:
        logger.error("internetacess exception:" + e)
        
    if code == 204:
        return True
    else:
        logger.info("internetacess Code is " + str(code))
        return False
    
# Deafults
LOG_FILENAME = "/var/log/netmon2led.log"
LOG_LEVEL = logging.INFO  # Could be e.g. "DEBUG" or "WARNING"

# Define and parse command line arguments
parser = argparse.ArgumentParser(description="Monitor network status and set RPi LEDS acordingly")
parser.add_argument("-l", "--log", help="file to write log to (default '" + LOG_FILENAME + "')")

# If the log file is specified on the command line then override the default
args = parser.parse_args()
if args.log:
        LOG_FILENAME = args.log

# Configure logging to log to a file, making a new file at midnight and keeping the last 3 day's data
# Give the logger a unique name (good practice)
logger = logging.getLogger(__name__)
# Set the log level to LOG_LEVEL
logger.setLevel(LOG_LEVEL)
# Make a handler that writes to a file, making a new file at midnight and keeping 3 backups
handler = logging.handlers.TimedRotatingFileHandler(LOG_FILENAME, when="midnight", backupCount=3)
# Format each log message like this
formatter = logging.Formatter('%(asctime)s %(levelname)-8s %(message)s')
# Attach the formatter to the handler
handler.setFormatter(formatter)
# Attach the handler to the logger
logger.addHandler(handler)

# Make a class we can use to capture stdout and sterr in the log
class MyLogger(object):
    def __init__(self, logger, level):
        """Needs a logger and a logger level."""
        self.logger = logger
        self.level = level

    def write(self, message):
        # Only log if there is a message (not just a new line)
        if message.rstrip() != "":
            self.logger.log(self.level, message.rstrip())

# Replace stdout with logging to file at INFO level
sys.stdout = MyLogger(logger, logging.INFO)
# Replace stderr with logging to file at ERROR level
sys.stderr = MyLogger(logger, logging.ERROR)

# LedBorg basic colors
# SetLedBorg(1, 0, 0) Red
# SetLedBorg(0, 1, 0) Green
# SetLedBorg(0, 0, 1) Blue
# SetLedBorg(1, 1, 0) Yellow
# SetLedBorg(0, 1, 1) Cyan
# SetLedBorg(1, 0, 1) Magenta
# SetLedBorg(1, 1, 1) White

SHORT_SLOT  = 0.25
LONG_SLOT   = 1
REPETITIONS = 2  # To keep parity, LONG_SLOT = 2 X REPETITIONS X SHORT_SLOT

# At the moment we are not able to distinguish NOIP from NOLINK
# Perhaps this could help https://stackoverflow.com/questions/808560/how-to-detect-the-physical-connected-state-of-a-network-cable-connector

ST_NOLINK  = 0  # Blink RED
ST_NOIP    = 1  # Blink RED
ST_AUTOIP  = 2  # Blink MAGENTA
ST_IP      = 3  # Fix YELLOW
ST_DIRECT  = 4  # Alternate GREEN - YELLOW
ST_OPENVPN = 5  # Fix GREEN
ethip      = "not set"
vpndomain = 'vpn.palaurecha.com'

try:
    while True:
        eth0on  = ST_NOLINK
        dnsok = False
        try:            
            socket.gethostbyname_ex(vpndomain)
            dnsok = True
        except Exception as e:
            pass
        
        f=os.popen("sudo service openvpn status")
        if dnsok and "is running" in f.readlines()[0]:
            eth0on  = ST_OPENVPN
        else:
            # Check interface status
            try:
                addrs = netifaces.ifaddresses('eth0')
                ethif = addrs[netifaces.AF_INET]
                ethip = ethif[0]['addr']
                #logger.info("eth0 has IP: " + ethip)

                # We should check that the IP is not autoconfiguration
                pat = re.compile("169\.254\.*\.*")
                autoconf = pat.match(ethip)
   
                if autoconf:
                    eth0on = ST_AUTOIP
                elif internetacess():
                    eth0on  = ST_DIRECT
                else:
                    eth0on  = ST_IP
            
            except Exception as e:
                logger.error(e)    
                
        # If openvpn is up, set to GREEN
        if eth0on == ST_OPENVPN:
            logger.info("Set GREEN: OpenVPN is running. IP is " + ethip)
            SetLedBorg(0, 1, 0)
            time.sleep(LONG_SLOT)
            
        # If direct access to internet, alternate GREEN and YELLOW
        elif eth0on == ST_DIRECT:
            logger.info("Set GREEN/YELLOW: Direct access to the Internet. IP is " + ethip)
            for x in range(REPETITIONS):
                SetLedBorg(0, 1, 0)
                time.sleep(SHORT_SLOT)
                SetLedBorg(1, 1, 0)
                time.sleep(SHORT_SLOT)

        # If IP only (captive portal ??) set to YELLOW
        elif (eth0on == ST_IP):
            logger.info("Set YELLOW: We have an IP but not access. IP is " + ethip)
            SetLedBorg(1, 1, 0)
            time.sleep(LONG_SLOT)
            
        # If we have autoconfiguration IP, blink MAGENTA
        elif (eth0on == ST_AUTOIP):
            logger.info("Set blinking MAGENTA: Autoconfiguration IP. IP is " + ethip)            
            for x in range(REPETITIONS):
                SetLedBorg(1, 0, 1)
                time.sleep(SHORT_SLOT)
                LedBorgOff()
                time.sleep(SHORT_SLOT)

        # else, set flashing RED
        else:                
            logger.info("Set FLASHING RED: No IP in eth0")
            for x in range(REPETITIONS):
                SetLedBorg(1, 0, 0)
                time.sleep(SHORT_SLOT)
                LedBorgOff()
                time.sleep(SHORT_SLOT)
                    
except KeyboardInterrupt:
        GPIO.cleanup()  # clean up GPIO on CTRL+C exit
GPIO.cleanup()          # clean up GPIO on normal exit
```

* Make it executable
```bash
sudo chmod 755 /usr/local/bin/netmon2led.py
```

* Create service handler /etc/init.d/netmon2led.sh
```bash
#!/bin/sh

### BEGIN INIT INFO
# Provides:          netmon2led
# Required-Start:    $remote_fs $syslog
# Required-Stop:     $remote_fs $syslog
# Default-Start:     2 3 4 5
# Default-Stop:      0 1 6
# Short-Description: Monitors network interfaces and sets the LED color acordingly
# Description:       Monitors network interfaces and sets the LED color acordingly
### END INIT INFO

# Change the next 3 lines to suit where you install your script and what you want to call it
DIR=/usr/local/bin/
DAEMON=$DIR/netmon2led.py 
DAEMON_NAME=netmon2led

# Add any command line options for your daemon here
DAEMON_OPTS=""

# This next line determines what user the script runs as.
# Root generally not recommended but necessary if you are using the Raspberry Pi GPIO from Python.
DAEMON_USER=root

# The process ID of the script when it runs is stored here:
PIDFILE=/var/run/$DAEMON_NAME.pid

. /lib/lsb/init-functions

do_start () {
    log_daemon_msg "Starting system $DAEMON_NAME daemon"
    start-stop-daemon --start --background --pidfile $PIDFILE --make-pidfile --user $DAEMON_USER --chuid $DAEMON_USER --startas $DAEMON -- $DAEMON_OPTS
    log_end_msg $?
}
do_stop () {
    log_daemon_msg "Stopping system $DAEMON_NAME daemon"
    start-stop-daemon --stop --pidfile $PIDFILE --retry 10
    log_end_msg $?
}

case "$1" in

    start|stop)
        do_${1}
        ;;

    restart|reload|force-reload)
        do_stop
        do_start
        ;;

    status)
        status_of_proc "$DAEMON_NAME" "$DAEMON" && exit 0 || exit $?
        ;;

    *)
        echo "Usage: /etc/init.d/$DAEMON_NAME {start|stop|restart|status}"
        exit 1
        ;;

esac
exit 0
```

* Make it executable
```bash
sudo chmod 755  /etc/init.d/netmon2led.sh
```
* Ensure it starts at boot
```bash
sudo update-rc.d netmon2led.sh defaults
```

## References
* [Set Python Script as a Service](http://blog.scphillips.com/posts/2013/07/getting-a-python-script-to-run-in-the-background-as-a-service-on-boot/)
* [Led Borg](https://www.piborg.org/ledborg/)