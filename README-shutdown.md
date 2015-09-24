
## Enhancement: Shutdown button

We use a soft button to send a shutdown signal to the RPi
We connect GPIO 21/PIN 40 to a softbutton connected also to GROUND (i.e. PIN 39)



## Environment preparation
* In not yet done, install the following
```bash
sudo easy_install wiringpi2
sudo easy_install netaddr
```
## Shutdown Service

* Add /usr/local/bin/shutdown-service.py with the content below:
```python
#!/usr/bin/env python
# Shutdow Service
# Wait for a signal to shutdown the RPi
# Button connected to GPIO 21 and Ground.
# GPIO 21 / PIN 40 set up as input will go to GND when button pressed
# GROUND  / PIN 39

import RPi.GPIO as GPIO
import os
GPIO.setmode(GPIO.BCM)

GPIO.setup(21, GPIO.IN, pull_up_down=GPIO.PUD_UP)

try:
    print "Waitting for shutdown signal"
    GPIO.wait_for_edge(21, GPIO.FALLING)
    print "Signal detected, shutting down!"
    f=os.popen("sudo halt")

except KeyboardInterrupt:
    GPIO.cleanup()       # clean up GPIO on CTRL+C exit
GPIO.cleanup()           # clean up GPIO on normal exit
```

* Make it executable
```bash
sudo chmod 755 /usr/local/bin/shutdown-service.py
```

* Create service handler /etc/init.d/shutdown-service.sh
```bash
#!/bin/sh

### BEGIN INIT INFO
# Provides:          shutdown-service
# Required-Start:    $remote_fs $syslog
# Required-Stop:     $remote_fs $syslog
# Default-Start:     2 3 4 5
# Default-Stop:      0 1 6
# Short-Description: Uses an external button to shutdown the Raspberry Pi
# Description:       Uses an external button to shutdown the Raspberry Pi
### END INIT INFO

# Change the next 3 lines to suit where you install your script and what you want to call it
DIR=/usr/local/bin/
DAEMON=$DIR/shutdown-service.py 
DAEMON_NAME=shutdown-service

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
sudo chmod 755  /etc/init.d/shutdown-service.sh
```
* Ensure it starts at boot
```bash
sudo update-rc.d shutdown-service.sh defaults
```

## References
* [Set Python Script as a Service](http://blog.scphillips.com/posts/2013/07/getting-a-python-script-to-run-in-the-background-as-a-service-on-boot/)














