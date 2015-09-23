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
