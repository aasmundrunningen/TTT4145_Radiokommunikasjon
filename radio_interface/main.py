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
    transmitt = True
    recive = True
    if len(sys.argv) > 1:
        if sys.argv[1] == "2":
            ip = "ip:192.168.2.1"
        elif sys.argv[1] == "3":
            ip = "ip:192.168.3.1"
    if len(sys.argv) > 2:
        match sys.argv[2]:
            case "r":
                transmitt = False
            case "t":
                recive = False

    print(f"Transmitting {transmitt}, Reciving {recive}")

    try:
        monitor             = MONITOR(ip=ip)
        hardware_process    = HARDWARE_COMMUNICATION(monitor_q=monitor.get_monitor_q(), ip=ip)
        transmitt_process   = TRANSMITT_PROCESS(tx_q=hardware_process.get_tx_queue()) #starts transmitt process and hook it up to transmitt queue on hardware communication
        recive_process      = RECIVE_PROCESS(rx_q=hardware_process.get_rx_queue(), monitor_q=monitor.get_monitor_q())
        sound               = SOUND(transmitt_process.get_binary_q(), recive_process.get_binary_q())
        
        if transmitt and recive:
            sound.stream()
        elif transmitt:
            sound.record()
        elif recive:
            sound.play()

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