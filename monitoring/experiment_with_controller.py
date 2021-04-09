#!/usr/bin/python3

# ----------------------------------------------------------------------------------------
# Serial monitor application with client thread to communicate with controller server.
#
# ----------------------------------------------------------------------------------------

from queue import Queue
import threading
import sys
import os
import logging
import time
from timeit import default_timer as timer

from lib import serial_monitor
from lib import file_logger

import controller_client


# ----------------------------------------------------------------------------------------
# EXPERIMENT DEFINITIONS AND CONFIGURATION
# ----------------------------------------------------------------------------------------

# DEFINITIONS
LOG_LEVEL = logging.DEBUG

ROUTER_HOSTNAME = "tcp://localhost:5562"
SUBSCR_HOSTNAME = "tcp://localhost:5561"

SERIAL_TIMEOUT = 2  # In seconds

RESULTS_FILENAME = "node_results"
LOGGING_FILENAME = "logger"

# ENVIRONMENTAL VARIABLES
# Device id should be given as argument at start of the script
try:
    LGTC_ID = sys.argv[1]
    LGTC_ID = LGTC_ID.replace(" ", "")
except:
    logging.warning("No device name was given...going with default")
    LGTC_ID = "xy"

LGTC_NAME = "LGTC" + LGTC_ID
RESULTS_FILENAME += ("_" + LGTC_ID + ".txt")
LOGGING_FILENAME += ("_" + LGTC_ID + ".log")

# Application name and duration should be defined as variable while running container
try:
    APP_DURATION = int(os.environ['APP_DURATION_MIN'])
except:
    logging.warning("No app duration was defined...going with default 60min")
    APP_DURATION = 60

try:
    APP_DIR = int(os.environ['APP_DIR'])
except:
    logging.error("No application was given...aborting!")
    #sys.exit(1) TODO
    APP_DIR = "00_test"

# TODO: change when in container
# APP_PATH = "/root/logatec-experiment/application" + APP_DIR
APP_PATH = "/home/logatec/magistrska/logatec-experiment/applications/" + APP_DIR
APP_NAME = APP_DIR[3:]

logging.info("Testing application " + APP_NAME + " for " + str(APP_DURATION) + " minutes on device " + LGTC_NAME)






# ----------------------------------------------------------------------------------------
# MAIN THREAD - SERIAL MONITOR
# ----------------------------------------------------------------------------------------
def main_thread(input_q, output_q, filename, lgtcname):

    # ------------------------------------------------------------------------------------
    monitor = serial_monitor.serial_monitor(2)
    txt = file_logger.file_logger()

    # Link multithread input output queue
    in_q = input_q
    out_q = output_q

    # Var for serial monitor
    _is_app_running = False
    _command_waiting = None
    _command_timeout = False
    _lines_stored = 0



    # ----------------------------------------------------------------------------------------
    logging.info("Starting main Serial monitor thread")

    # Open file to store measurements
    txt.prepare_file(filename, lgtcname)
    txt.open_file()  

    # Connect to VESNA serial port
    if not monitor.connect_to("ttyS2"):
        logging.error("Couldn't connect to VESNA.")
        out_q.put(["-1", "VESNA_ERR"])
        return
    
    logging.info("Successfully connected to VESNA serial port!")

    elapsed_sec = 0
    timeout_cnt = 0
    loop_time = timer()

    try:
        while(True):

            # -------------------------------------------------------------------------------
            # Failsafe - Check if serial was available in last 10 seconds
            # Failsafe - Check if we got respond on a command in last 3 sec
            # Failsafe enabled only while some application is running 
            if _is_app_running:

                # Every second
                if ((timer() - loop_time) > 1):
                    elapsed_sec += (timer() - loop_time)
                    loop_time = timer()
                    #logging.debug("Elapsed seconds: " + str(elapsed_sec))

                    # Every 10 seconds
                    if elapsed_sec % 10 == 0:

                        if not monitor.serial_avaliable:
                            txt.store_lgtc_line("Timeout detected.")
                            timeout_cnt += 1
                            logging.warning("No lines read for more than 10 seconds..")

                        if timeout_cnt > 5:
                            txt.warning("VESNA did not respond for more than a minute")
                            out_q.put(["-1", "VESNA_TIMEOUT"])
                            timeout_cnt = 0
                            logging.error("VESNA did not respond for more than a minute")
                            _is_app_running = False
                            # We don't do anything here - let the user interfeer

                        # Set to False, so when monitor reads something, it goes back to True
                        monitor.serial_avaliable = False

                    # Every 3 seconds
                    if elapsed_sec % 3 == 0:
                        if _command_waiting != None:
                            # If _command_timeout allready occurred - response on command was
                            # not captured for more than 3 seconds. Something went wrong, 
                            # so stop waiting for it
                            if _command_timeout:
                                txt.warning("Command timeout occurred!")
                                out_q.put([_command_waiting, "Failed to get response ..."])
                                logging.warning("No response on command for more than 3 seconds!")
                                _command_timeout = False
                                _command_waiting = None
                            
                            _command_timeout = True

            # -------------------------------------------------------------------------------
            # Read line from VESNA
            if monitor.input_waiting():
                data = monitor.read_line()

                # Store the line into file
                txt.store_line(data)
                _lines_stored += 1

                # If we got response on the command
                if data[0] == "*":
                    out_q.put([_command_waiting, data[1:]])
                    _command_waiting = None
                    _command_timeout = False
                    logging.debug("Got response on cmd " + data[1:])
                
                # If we got stop command
                elif data[0] == "=":
                    out_q.put(["-1","END_OF_APP"])
                    _command_waiting = None
                    _command_timeout = False
                    _is_app_running = False
                    logging.info("Got end-of-app response!")
                
                

            # -------------------------------------------------------------------------------
            # If we are not witing for any response
            # and there is new command in queue, send it to VESNA
            elif (not in_q.empty() and _command_waiting == None):
                cmd = in_q.get()

                # SYSTEM COMMANDS
                if cmd[0] == "-1":

                    # @ Sync with VESNA - start the serial_monitor but not the app 
                    # #TODO add while(1) to VESNA main loop
                    if cmd[1] == "SYNC_WITH_VESNA":
                        if not monitor.sync_with_vesna():
                            out_q.put(["-1", "VESNA_ERR"])
                            txt.warning("Couldn't sync with VESNA.")
                            logging.error("Couldn't sync with VESNA.")
                            break
                        
                        out_q.put(["-1", "SYNCED_WITH_VESNA"])
                        txt.store_lgtc_line("Synced with VESNA ...")
                        logging.info("Synced with VESNA over serial ...")
                    
                    # > Start the app (with app running time as an argument)
                    elif cmd[1] == "START_APP":
                        if _is_app_running == True:
                            logging.warning("Application already running..")
                            out_q.put(["0", "Application is already running!"])

                        if not monitor.start_app(str(APP_DURATION * 60)):
                            out_q.put(["-1", "VESNA_ERR"])
                            txt.warning("Couldn't start the APP.")
                            logging.error("Couldn't start the APP.")
                            break
                        
                        # In case we restarted experiment, start from 0
                        elapsed_sec = 0
                        _lines_stored = 0
                        _is_app_running = True
                        out_q.put(["-1", "START_APP"])
                        txt.store_lgtc_line("Application started!")
                        logging.info("Application started!")

                    # = Stop the app
                    elif cmd[1] == "STOP_APP":
                        if not monitor.stop_app():
                            out_q.put(["-1", "VESNA_TIMEOUT"])
                            txt.warning("Couldn't stop the APP.")
                            logging.error("Couldn't stop the APP.")
                        
                        _is_app_running = False
                        out_q.put(["-1", "STOP_APP"])
                        txt.store_lgtc_line("Application stopped!")
                        logging.info("Application stopped!")

                    elif cmd[1] == "EXIT":
                        monitor.stop_app()
                        txt.store_lgtc_line("Application exit!")
                        logging.info("Received exit command!")
                        break

                # EXPERIMENT COMMANDS
                else:
                    # Return number of lines read
                    if cmd[1] == "LINES":
                        out_q.put([cmd[0], ("LINES " + str(_lines_stored))])

                    # Return number of seconds since the beginning of app
                    elif cmd[1] == "SEC":
                        out_q.put([cmd[0], ("SEC " + str(elapsed_sec))])

                    # Forward command to VESNA
                    else:
                        monitor.send_command(cmd[1])
                        _command_waiting = cmd[0]

                    # Log it to file as well
                    txt.store_lgtc_line("Received command [" + cmd[0] + "]: " + cmd[1])
                    logging.debug("Received command [" + cmd[0] + "]: " + cmd[1])



    except KeyboardInterrupt:
        logging.info("\n Keyboard interrupt!.. Stopping the monitor")
        # TODO: inform Vesna and controller
        # TODO LGTC_exit()"OFFLINE"
    
    except serial.SerialException:
        logging.error("Serial error!.. Stopping the monitor")

    except IOError:
        logging.error("Serial port disconnected!.. Stopping the monitor")

    finally:
    # ------------------------------------------------------------------------------------
        # Clear resources
        monitor.close()
        txt.close()
        return





# ----------------------------------------------------------------------------------------
# MAIN
# ----------------------------------------------------------------------------------------
if __name__ == "__main__":

    # LGTC -> VESNA
    L_V_QUEUE = Queue()
    # VESNA -> LGTC
    V_L_QUEUE = Queue()

    # Use this logging setup for testbed usage
    #logging.basicConfig(format="%(asctime)s [%(levelname)7s]:[%(module)26s > %(funcName)16s() > %(lineno)3s] - %(message)s", level=logging.DEBUG, filename=LOGGING_FILENAME)
    # Use this logging setup for testing 
    logging.basicConfig(format="[%(levelname)5s:%(funcName)16s()] %(message)s", level=LOG_LEVEL, filename=LOGGING_FILENAME)

    # Start client thread (ZMQ)
    client_thread = controller_client.zmq_client_thread(V_L_QUEUE, L_V_QUEUE, LGTC_NAME, SUBSCR_HOSTNAME, ROUTER_HOSTNAME)
    client_thread.start()
    
    # Start main thread (Serial Monitor)
    main_thread(L_V_QUEUE, V_L_QUEUE, RESULTS_FILENAME, LGTC_NAME)

    logging.info("Main thread stopped, trying to stop client thread.")

    # Notify serial monitor thread to exit its operation and join until quit
    client_thread.stop()
    client_thread.join()

    logging.info("Exit!")








# ----------------------------------------------------------------------------------------
# POSSIBLE LGTC STATES
# ----------------------------------------------------------------------------------------
# --> ONLINE        - LGTC is online and ready
# --> COMPILING     - LGTC is compiling the experiment application
# --> RUNNING       - Experiment application is running
# --> STOPPED       - User successfully stopped the experiment app
# --> FINISHED      - Experiment application came to the end
#
# --> TIMEOUT       - VESNA is not responding for more than a minute
# --> LGTC_WARNING  - Warning sign that something was not as expected
# --> COMPILE_ERROR - Experiment application could not be compiled
# --> VESNA_ERROR   - Problems with UART communication
#
#
# ----------------------------------------------------------------------------------------
# SUPPORTED COMMANDS
# ----------------------------------------------------------------------------------------
# Incoming commands must be formated as a list with 2 string arguments: message number 
# and command itself (example: ["66", "STATE"]). Message number is used as a sequence
# number, but if it is set to "-1", command represents SYSTEM COMMAND:
#
# --> SYSTEM COMMANDS - used for controll over the LGTC monitoring application
#
#       * START_APP       - start the experiment application
#       * STOP_APP        -
#       * RESTART_APP     - 
#       * FLASH           - flash VESNA with experiment application
#       * SYNC_WITH_VESNA - start the serial monitor
#       * EXIT            - exit monitoring application
#       * STATE           - return the current state of monitoring application
#       * SYNC            - used to synchronize LGTC with broker/server
#       * ACK             - acknowledge packet sent as a response on every message
#       
# --> EXPERIMENT COMMANDS - used for controll over the VESNA experiment application
#
#       * LINES           - return the number of lines stored in measurement file
#       * SEC             - return the number of elapsed seconds since the beginning of exp.
#       TODO:
#       They should start with the char "*" so VESNA will know?
#       Depend on Contiki-NG application
#




# TODO: Prestavi Reset Vesna in Flash funkcije iz controller_client sem v serial monitor...
# Zato da je tisti del (client) univerzalen (tudi za BT) in odgovoren sam za komunikcaijo 
# sz strežnikom
