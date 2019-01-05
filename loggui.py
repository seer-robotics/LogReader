import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import (
    FigureCanvas, NavigationToolbar2QT as NavigationToolbar)
from PyQt5 import QtCore, QtWidgets,QtGui
from PyQt5.QtCore import QThread, pyqtSignal
from matplotlib.figure import Figure
from loglib import MCLoc, IMU, Odometer, Send, Get, Laser, ErrorLine, WarningLine, ReadLog, FatalLine, NoticeLine
from loglib import findrange
from datetime import datetime, timedelta
import sys


class ReadThread(QThread):
    signal = pyqtSignal('PyQt_PyObject')

    def __init__(self):
        QThread.__init__(self)
        self.filenames = []
        self.run()

    # run method gets called when we start the thread
    def run(self):
        """读取log"""
        #初始化log数据
        self.mcl = MCLoc()
        self.imu = IMU()
        self.odo = Odometer()
        self.send = Send()
        self.get = Get()
        self.laser = Laser(1000.0)
        self.err = ErrorLine()
        self.war = WarningLine()
        self.fatal = FatalLine()
        self.notice = NoticeLine()
        self.tlist = []
        if self.filenames:
            log = ReadLog(self.filenames)
            log.parse(self.mcl, self.imu, self.odo, self.send, self.get, self.laser, self.err, self.war, self.fatal, self.notice)
            tmax = max(self.mcl.t() + self.odo.t() + self.send.t() + self.get.t() + self.laser.t() + self.err.t() + self.fatal.t() + self.notice.t())
            tmin = min(self.mcl.t() + self.odo.t() + self.send.t() + self.get.t() + self.laser.t() + self.err.t() + self.fatal.t() + self.notice.t())
            dt = tmax - tmin
            self.tlist = [tmin + timedelta(microseconds=x) for x in range(0, int(dt.total_seconds()*1e6+1000),1000)]
            #save Error
            fid = open("Report.txt", "w", encoding='utf-8') 
            for filename in self.filenames:
                print("="*20, file = fid)
                print("Files: ", filename, file = fid)
                print(len(self.fatal.content()[0]), " FATALs, ", len(self.err.content()[0]), " ERRORs, ", 
                      len(self.war.content()[0]), " WARNINGs, ", len(self.notice.content()[0]), " NOTICEs", file = fid)
                print("FATALs:", file = fid)
                for data in self.fatal.content()[0]:
                    print(data, file = fid)
                print("ERRORs:", file = fid)
                for data in self.err.content()[0]:
                    print(data,file = fid)
                print("WARNINGs:", file = fid)
                for data in self.war.content()[0]:
                    print(data, file = fid)
                print("NOTICEs:", file = fid)
                for data in self.notice.content()[0]:
                    print(data, file = fid)
            fid.close()
        self.data = {"mcl.x":self.mcl.x(),"mcl.y":self.mcl.y(),"mcl.theta":self.mcl.theta(), "mcl.confidence":self.mcl.confidence(),
                     "imu.yaw":self.imu.yaw(),"imu.ax":self.imu.ax(),"imu.ay":self.imu.ay(),"imu.az":self.imu.az(),
                     "imu.gx":self.imu.gx(),"imu.gy":self.imu.gy(),"imu.gz":self.imu.gz(),
                     "imu.offx":self.imu.offx(),"imu.offy":self.imu.offy(),"imu.offz":self.imu.offz(),
                     "odo.x":self.odo.x(),"odo.y":self.odo.y(),"odo.theta":self.odo.theta(),"odo.stop":self.odo.stop(),
                     "odo.vx":self.odo.vx(),"odo.vy":self.odo.vy(),"odo.vw":self.odo.vw(),"odo.steer_angle":self.odo.steer_angle(),
                     "send.vx":self.send.vx(),"send.vy":self.send.vy(),"send.vw":self.send.vw(),"send.steer_angle":self.send.steer_angle(),
                     "send.max_vx":self.send.max_vx(),"send.max_vw":self.send.max_vw(),
                     "get.vx":self.get.vx(),"get.vy":self.get.vy(),"get.vw":self.get.vw(),
                     "get.max_vx":self.get.max_vx(),"get.max_vw":self.get.max_vw()}
        self.signal.emit(self.filenames)

class ApplicationWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Log分析器')
        self.read_thread = ReadThread()
        self.openLogFilesDialog()
        self.setupUI()

    def setupUI(self):
        """初始化窗口结构""" 
        self.setGeometry(50,50,800,800)
        self.file_menu = QtWidgets.QMenu('&File', self)
        self.file_menu.addAction('&Open', self.openLogFilesDialog,
                                 QtCore.Qt.CTRL + QtCore.Qt.Key_O)
        self.file_menu.addAction('&Quit', self.fileQuit,
                                 QtCore.Qt.CTRL + QtCore.Qt.Key_Q)
        self.menuBar().addMenu(self.file_menu)
        self.help_menu = QtWidgets.QMenu('&Help', self)
        self.menuBar().addSeparator()
        self.help_menu.addAction('&About', self.about)
        self.menuBar().addMenu(self.help_menu)
        self._main = QtWidgets.QWidget()
        self.setCentralWidget(self._main)
        #Add ComboBox
        layout = QtWidgets.QVBoxLayout(self._main)
        grid = QtWidgets.QGridLayout()
        self.label1 = QtWidgets.QLabel("图片1",self)
        self.label1.adjustSize()
        self.combo1 = QtWidgets.QComboBox(self)
        self.combo1.activated[str].connect(self.combo_onActivated1)
        grid.addWidget(self.label1,1,0)
        grid.addWidget(self.combo1,1,1,1,14)
        self.label2 = QtWidgets.QLabel("图片2",self)
        self.label2.adjustSize()
        self.combo2 = QtWidgets.QComboBox(self)
        self.combo2.activated[str].connect(self.combo_onActivated2)
        grid.addWidget(self.label2,2,0)
        grid.addWidget(self.combo2,2,1,2,14)
        layout.addLayout(grid)

        #图形化结构
        self.static_canvas = FigureCanvas(Figure(figsize=(10,10)))
        layout.addWidget(self.static_canvas)
        self.old_home = NavigationToolbar.home
        self.old_forward = NavigationToolbar.forward
        self.old_back = NavigationToolbar.back
        NavigationToolbar.home = self.new_home
        NavigationToolbar.forward = self.new_forward
        NavigationToolbar.back = self.new_back
        self.addToolBar(NavigationToolbar(self.static_canvas, self))
        self.ax1, self.ax2 = self.static_canvas.figure.subplots(2, 1, sharex = True)
        self.ax2.set_xlabel("t")

    def new_home(self, *args, **kwargs):
        text1 = self.combo1.currentText()
        data = self.read_thread.data[text1][0]
        if data:
            max_range = max(max(data) - min(data), 1e-6)
            self.ax1.set_ylim(min(data) - 0.05 * max_range, max(data)  + 0.05 * max_range)
            self.ax1.set_xlim(self.read_thread.tlist[0], self.read_thread.tlist[-1])

        text2 = self.combo2.currentText()
        data = self.read_thread.data[text2][0]
        if data:
            max_range = max(max(data) - min(data), 1e-6)
            self.ax2.set_ylim(min(data) - 0.05 * max_range, max(data)  + 0.05 * max_range)
            self.ax2.set_xlim(self.read_thread.tlist[0], self.read_thread.tlist[-1])
        self.static_canvas.figure.canvas.draw()

    def new_forward(self, *args, **kwargs):
        xmin,xmax =  self.ax1.get_xlim()
        range = xmax - xmin
        xmin = xmin + range /10.0
        xmax = xmax + range /10.0
        self.ax1.set_xlim(xmin,xmax)
        self.ax2.set_xlim(xmin,xmax)
        self.static_canvas.figure.canvas.draw()

    def new_back(self, *args, **kwargs):
        xmin,xmax =  self.ax1.get_xlim()
        range = xmax - xmin
        xmin = xmin - range /10.0
        xmax = xmax - range /10.0
        self.ax1.set_xlim(xmin,xmax)
        self.ax2.set_xlim(xmin,xmax)
        self.static_canvas.figure.canvas.draw()

    def openLogFilesDialog(self):
        self.setGeometry(50,50,640,480)
        self.read_thread.signal.connect(self.readFinished)
        options = QtWidgets.QFileDialog.Options()
        options |= QtWidgets.QFileDialog.DontUseNativeDialog
        self.filenames, _ = QtWidgets.QFileDialog.getOpenFileNames(self,"选取log文件", "","Log Files (*.log);;All Files (*)", options=options)
        if self.filenames:
            self.read_thread.filenames = self.filenames
            self.read_thread.start()
            self.statusBar().showMessage('Loading......: {0}'.format(self.filenames))

    def readFinished(self, result):
        print("Current: {0}.".format(result))  # Show the output to the user
        self.statusBar().showMessage('Current: {0}'.format(self.filenames))
        if self.read_thread.filenames:
            #画图 mcl.t, mcl.x
            keys = list(self.read_thread.data.keys())
            self.combo1.addItems(keys)
            self.drawdata(self.ax1, self.read_thread.data[keys[0]], keys[0])
            self.combo2.addItems(keys)
            self.drawdata(self.ax2, self.read_thread.data[keys[0]], keys[0])

    def fileQuit(self):
        self.close()

    def about(self):
        QtWidgets.QMessageBox.about(self, "关于", """Log Viewer""")

    def combo_onActivated1(self,text):
        # print("combo1: ",text)
        self.drawdata(self.ax1, self.read_thread.data[text], text)

    def combo_onActivated2(self,text):
        # print("combo2: ",text)
        self.drawdata(self.ax2, self.read_thread.data[text], text)

    

    def drawdata(self, ax, data, ylabel):
        ax.cla()
        self.drawFEWN(ax)
        ax.set_xlim(self.read_thread.tlist[0], self.read_thread.tlist[-1])
        if data[1]:
            ax.plot(data[1], data[0], '.')
            max_range = max(max(data[0]) - min(data[0]), 1e-6)
            ax.set_ylim(min(data[0]) - 0.05 * max_range, max(data[0]) + 0.05 * max_range)
        ax.set_ylabel(ylabel)
        ax.grid()
        self.static_canvas.figure.canvas.draw()

    def drawFEWN(self,ax):
        """ 绘制 Fatal, Error, Warning在坐标轴上"""
        fl, el, wl,nl = None, None, None, None
        legend_info = []
        for tmp in self.read_thread.fatal.t():
            fl, = ax.plot((tmp,tmp),[-1e10, 1e10],'m-')
        if fl:
            legend_info.append(fl)
            legend_info.append('fatal')
        for tmp in self.read_thread.err.t():
            el, = ax.plot((tmp,tmp),[-1e10, 1e10],'r-.')
        if el:
            legend_info.append(el)
            legend_info.append('error')
        for tmp in self.read_thread.war.t():
            wl, = ax.plot((tmp,tmp),[-1e10, 1e10],'y--')
        if wl:
            legend_info.append(wl)
            legend_info.append('warning')
        for tmp in self.read_thread.notice.t():
            nl, = ax.plot((tmp,tmp),[-1e10, 1e10],'g:')
        if nl:
            legend_info.append(nl)
            legend_info.append('notice')
        if legend_info:
            ax.legend(legend_info[0::2], legend_info[1::2], loc='upper right')


if __name__ == "__main__":
    qapp = QtWidgets.QApplication(sys.argv)
    app = ApplicationWindow()
    app.show()
    qapp.exec_()
