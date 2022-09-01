# ---------------------------------------------------------------------
# A script to put start/restart NB-IoT module
# ---------------------------------------------------------------------

import sys
import os
import time

class nbiot_reset():

    def __init__(self):
        # Export GPIO0_4 or linuxPin-4 to user space 
        try:
            os.system('echo 4 > /sys/class/gpio/export')
        except:
            print("Pin 4 already exported")

        # Export GPIO0_5 or linuxPin-5 to user space 
        try:
            os.system('echo 5 > /sys/class/gpio/export')
        except:
            print("Pin 5 already exported")
        
        # Set the direction of the pin to output
        os.system('echo out > /sys/class/gpio/gpio4/direction')
        os.system('echo out > /sys/class/gpio/gpio5/direction')

        #Set pins to default state -> HIGH
        os.system('echo 1 > /sys/class/gpio/gpio4/value')
        os.system('echo 1 > /sys/class/gpio/gpio5/value')
        return

    def reset(self):
        # Set the value to 0 - reset nb-iot
        os.system('echo 0 > /sys/class/gpio/gpio5/value')
        time.sleep(0.5)
        os.system('echo 1 > /sys/class/gpio/gpio5/value')
        return

    def wakeup(self):
        # Set the value to 0 - wake nb-iot
        os.system('echo 0 > /sys/class/gpio/gpio4/value')
        time.sleep(0.5)
        os.system('echo 1 > /sys/class/gpio/gpio4/value')
        return


if __name__ == '__main__':

    vesna = nbiot_reset()
    
    if (int(sys.argv[1]) == 0):
        vesna.reset()
    else:
        vesna.wakeup()
        

