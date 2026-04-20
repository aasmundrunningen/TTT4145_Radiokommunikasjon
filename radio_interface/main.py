from hardware_process   import HARDWARE_COMMUNICATION
from transmitt_process  import TRANSMITT_PROCESS
from Monitor_process    import MONITOR
from recive_process     import RECIVE_PROCESS
from modules.sound      import SOUND

import numpy as np
import matplotlib.pyplot as plt
import sys

if __name__ == "__main__":
    ip = None
    master = True
    if len(sys.argv) > 1:
        if sys.argv[1] == "2":
            ip = "ip:192.168.2.1"
        elif sys.argv[1] == "3":
            ip = "ip:192.168.3.1"
        elif sys.argv[1] == "4":
            ip = "ip:192.168.4.1"
    if len(sys.argv) > 2:
        if sys.argv[2] == "s":
            master = False
        
    print(f"Master {master}")

    try:
        print("Starting hardware process")
        monitor             = MONITOR(ip=ip)
        hardware_process    = HARDWARE_COMMUNICATION(monitor_q=monitor.get_monitor_q(), ip=ip, master=master)
        transmitt_process   = TRANSMITT_PROCESS(tx_q=hardware_process.get_tx_queue()) #starts transmitt process and hook it up to transmitt queue on hardware communication
        recive_process      = RECIVE_PROCESS(rx_q=hardware_process.get_rx_queue(), 
                                             hardware_process_feedback_q=hardware_process.get_rx_feedback_queue(), 
                                             monitor_q=monitor.get_monitor_q())
        sound               = SOUND(transmitt_process.get_binary_q(), recive_process.get_binary_q())
        sound.stream()
        
        monitor.run() #runs the monitor process in the main branch

    except KeyboardInterrupt:
        pass
    except SystemExit:
        pass

    finally:
        transmitt_process.stop()
        recive_process.stop()
        hardware_process.stop()
        sound.stop_all()