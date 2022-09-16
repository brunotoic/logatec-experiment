#!/bin/sh
# A demo script to run the demo NB-IoT application

#Reset the NB-IoT device
cd ../../deployment/tasks/
python3 nbiot_reset.py 1
python3 nbiot_reset.py 0
cd ../../applications/00_NB-IoT_demo

#Run the python script
python3 nbiot_status.py
