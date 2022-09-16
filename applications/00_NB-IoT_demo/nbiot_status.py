 #!/usr/bin/env python3

from datetime import datetime
import argparse
import os
import sys
import serial
import time

# Get the filename
filename = "node_" + str(sys.argv[1]) + ".txt"

try:
	APP_DURATION = int(os.environ['APP_DURATION_MIN'])
	APP_DURATION = APP_DURATION * 60
except:
	print("No app duration was defined...going with default 1min")
	APP_DURATION = 60

file = open(filename, mode="w", encoding = "ASCII")
file.write(str(datetime.now())+"\n")

s = serial.Serial('/dev/ttyS2', 115200, timeout=0)

try:
    s.open()
except:
    s.close()
    s.open()
a = b''

while not b'OK\r\n' in a:
    s.write(b'AT\r\n')
    time.sleep(1)
    a = s.read(12)
s.write(b'ATI\r\n')
time.sleep(1)
a = s.read(1000) #flush the whole buffer containing ATI info
print(a)

try: 
    a_str=a.decode("ascii")
    file.write(str(a_str))
except:
    print("Cannot decode recieved data")
print('OK' in a_str)

file.close()