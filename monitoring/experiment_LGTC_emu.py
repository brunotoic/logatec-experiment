# TODO:
# Put zmq_client.py in this file as well?
# V clienta bi lahko dal ukaz UPTIME - da odgovori kolko časa je že on

#!/usr/bin/python3
import threading
from queue import Queue

import sys
import os
import logging
import time

#from lib import zmq_client

import BLE_experiment


# DEFINITIONS
LOG_LEVEL = logging.DEBUG
RESULTS_FILENAME = "node_results"
LOGGING_FILENAME = "logger"

# ----------------------------------------------------------------------------------------
# MAIN
# ----------------------------------------------------------------------------------------
if __name__ == "__main__":


    # ------------------------------------------------------------------------------------
    # LOGGING CONFIG
    # ------------------------------------------------------------------------------------

    # Config logging module format for all scripts. Log level is defined in each submodule with var LOG_LEVEL.
    logging.basicConfig(format="%(asctime)s [%(levelname)7s]:[%(module)26s > %(funcName)16s() > %(lineno)3s] - %(message)s", level=LOG_LEVEL, filename="logger")
    #logging.basicConfig(format="[%(levelname)5s:%(funcName)16s() > %(module)17s] %(message)s", level=LOG_LEVEL)

    #logging.info("Testing application " + APP_NAME + " for " + str(APP_DURATION) + " minutes on device " + LGTC_NAME + "!")


    # Create 2 queue for communication between threads
    # Client -> Experiment
    C_E_QUEUE = Queue()
    # Experiment -> Clinet
    E_C_QUEUE = Queue()

    LGTC_NAME = "solata"
    RESULTS_FILENAME = "TEST.txt"
    
    print("Creating experiment thread")
    experiment_thread = BLE_experiment.BLE_experiment(C_E_QUEUE, E_C_QUEUE, RESULTS_FILENAME, LGTC_NAME)

    print("Starting thread...")
    experiment_thread.run()

    experiment_thread.join()
    print("Cleaned up...")
    logging.info("Dejanski konec")



