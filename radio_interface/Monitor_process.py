import sys
import numpy as np
from PyQt6 import QtWidgets, QtCore
import pyqtgraph as pg
import time
import multiprocessing
import queue
import modules.config as config


def test_data_producer(m_q):
    while True:
        m_q.put(("rx_raw_data", np.random.rand(100)))
        time.sleep(0.1)

class MONITOR:
    def __init__(self):
        self.monitor_q = multiprocessing.Queue(maxsize=100) #recive data as touple ("header", data_np_array)

        # 1. Standard PyQt Setup
        pg.setConfigOption('background', 'w')
        pg.setConfigOption('foreground', 'k') # Sets axes/text to black
        self.app = QtWidgets.QApplication(sys.argv)
        self.view = pg.GraphicsLayoutWidget(show=True, title="Efficient Live Plotting")
        self.view.resize(800, 400)



        #RX power plot
        self.rx_power_plot = self.view.addPlot(row=0, col=0, title="Recived power")
        self.rx_power_plot.setLabel('bottom', "Time", color='#FFFFFF', size='12pt')
        self.rx_power_plot.setLabel('left', "Amplitude")
        self.rx_power_curve = self.rx_power_plot.plot(pen='b') #pen is collor
        self.rx_power_data = np.zeros(100)

        #eye diagram
        self.eye_plot = self.view.addPlot(row=0, col=1, title="Absolute Eye diagram")
        self.eye_curve = self.eye_plot.plot(pen=pg.mkPen(color=(0, 0, 0, 40), width=1)) #pen is collor
        self.eye_plot.setYRange(0,3)


        #Constalation plots
        self.constalation_item = pg.ScatterPlotItem(size=3, pen=pg.mkPen(None), brush=pg.mkBrush(0, 0, 0, 250))
        self.constalation_plot       = self.view.addPlot(row=1, col=0, title="Unsynced constalation diagram")
        self.constalation_plot.addItem(self.constalation_item)
        self.constalation_plot.setRange(xRange=[-3,3], yRange=[-3,3])


        self.sync_constalation_item = pg.ScatterPlotItem(size=3, pen=pg.mkPen(None), brush=pg.mkBrush(0, 0, 0, 250))
        self.sync_constalation_plot       = self.view.addPlot(row=1, col=1, title="Synced constalation diagram")
        self.sync_constalation_plot.addItem(self.sync_constalation_item)
        self.sync_constalation_plot.setRange(xRange=[-3,3], yRange=[-3,3])
        

        #recive rate plot
        self.recive_rate_plot = self.view.addPlot(row=0, col=3, title="Recive rate")
        self.recive_rate_plot.addLegend()
        self.recive_rate_curve = self.recive_rate_plot.plot(pen='b',name="Recive rate")
        self.wrong_preamble_rate_curve = self.recive_rate_plot.plot(pen="g", name="Wrong preamble rate")
        self.recive_rate = np.zeros(60)
        self.wrong_preamble_rate = np.zeros(60)
        self.num_recived_packages = 0
        self.num_wrong_preamble = 0
        self.time_last_recived_packages_update = time.time()
        self.time_last_wrong_preamble_update = time.time()
        self.recive_rate_plot.setLabel('left', "Rate [packages/s]")
        self.recive_rate_plot.setYRange(0, 100)

        # 4. Setup the Update Timer
        # We update the UI at 60Hz (approx 16ms), even if data comes in at 1000Hz.
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_plot)
        self.timer.start(16) 
        

    
    def get_monitor_q(self):
        return self.monitor_q


    def update_plot(self):
        while True:
            try:
                header, data = self.monitor_q.get_nowait()
                match header: 
                    case "rx_raw_data":
                        self.rx_power_data[:-1] = self.rx_power_data[1:]
                        self.rx_power_data[-1] = np.sum(np.pow(np.abs(data),2))
                        self.rx_power_curve.setData(self.rx_power_data)
                    case "rx data_package": #eye diagram
                        data = np.concatenate((np.full(np.floor(config.filter.sps_rx/2).astype(int), np.nan), np.abs(data), np.full(np.ceil(config.filter.sps_rx/2).astype(int), np.nan)))
                        data_split = data.reshape(-1, config.filter.sps_rx)
                        nans = np.full((data_split.shape[0], 1), np.nan)
                        stacked_data = np.hstack((data_split, nans)).flatten()
                        x_axis = np.tile(np.linspace(0,1,config.filter.sps_rx+1),data_split.shape[0])
                        self.eye_curve.setData(x_axis, stacked_data)
                        
                        pass
                    case "rx downsampled_data": #unsynced constalation diagram
                        self.constalation_item.setData(x=data.real, y=data.imag)
                    case "rx phase_synced_data": #synced constalation diagram
                        self.sync_constalation_item.setData(x=data.real, y=data.imag)
                    case "num_recived_packages":
                        if 1 < time.time() - self.time_last_recived_packages_update:
                            recive_rate = (data - self.num_recived_packages) / (time.time() - self.time_last_recived_packages_update)
                            self.num_recived_packages = data
                            self.time_last_recived_packages_update = time.time()
                            self.recive_rate[:-1] = self.recive_rate[1:]
                            self.recive_rate[-1] = recive_rate
                            self.recive_rate_curve.setData(self.recive_rate)
                    case "num_false_preamble":
                        if 1 < time.time() - self.time_last_wrong_preamble_update:
                            wrong_preamble_rate = (data - self.num_wrong_preamble) / (time.time() - self.time_last_wrong_preamble_update)
                            self.num_wrong_preamble = data
                            self.time_last_wrong_preamble_update = time.time()
                            self.wrong_preamble_rate[:-1] = self.wrong_preamble_rate[1:]
                            self.wrong_preamble_rate[-1] = wrong_preamble_rate
                            self.wrong_preamble_rate_curve.setData(self.wrong_preamble_rate)
                        pass


            except queue.Empty:
                break
    
    def run(self):
        sys.exit(self.app.exec())

if __name__ == '__main__':
    monitor = MONITOR()
    m_q = monitor.get_monitor_q()

    data_producer_thread = multiprocessing.Process(target=test_data_producer, args=(m_q,), daemon=True)
    data_producer_thread.start()
    monitor.run()