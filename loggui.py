print("LOGGUI START...")
import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import (
    FigureCanvas, NavigationToolbar2QT as NavigationToolbar)
from PyQt5 import QtCore, QtWidgets,QtGui
from PyQt5.QtCore import QThread, pyqtSignal
from matplotlib.figure import Figure
from loglib import MCLoc, IMU, Odometer, Battery, Controller, Send, Get, Laser, Manual 
from loglib import StopPoints, SlowDownPoints, SensorFuser
from loglib import ErrorLine, WarningLine, ReadLog, FatalLine, NoticeLine, LaserOdometer, TaskStart, TaskFinish
from loglib import findrange
from datetime import datetime, timedelta
import os, sys
from numpy import searchsorted
from ExtendedComboBox import ExtendedComboBox
from Widget import Widget



def decide_old_imu(gx,gy,gz):
    for v in gx:
        if abs(round(v) - v) > 1e-5:
            return True
    for v in gy:
        if abs(round(v) - v) > 1e-5:
            return True
    for v in gz:
        if abs(round(v) - v) > 1e-5:
            return True
    return False

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
        self.battery = Battery()
        self.controller = Controller()
        self.odo = Odometer()
        self.laserOdo = LaserOdometer()
        self.send = Send()
        self.get = Get()
        self.manual = Manual()
        self.stop = StopPoints()
        self.slowdown = SlowDownPoints()
        self.sensorfuser = SensorFuser()
        self.laser = Laser(1000.0)
        self.err = ErrorLine()
        self.war = WarningLine()
        self.fatal = FatalLine()
        self.notice = NoticeLine()
        self.taskstart = TaskStart()
        self.taskfinish = TaskFinish()
        self.tlist = []
        if self.filenames:
            log = ReadLog(self.filenames)
            log.parse(self.mcl, self.imu, self.odo, self.battery, self.controller, self.laserOdo, self.stop, self.slowdown, self.sensorfuser,
            self.send, self.get, self.manual, self.laser, self.err, self.war, self.fatal, self.notice, self.taskstart, self.taskfinish)
            #analyze data
            old_imu_flag = decide_old_imu(self.imu.gx()[0], self.imu.gy()[0], self.imu.gz()[0])
            if old_imu_flag:
                self.imu.old2newGyro()
                print('The unit of gx, gy, gz in file is rad/s.')
            else:
                print('The org unit of gx, gy, gz in IMU is LSB/s.')
            tmax = max(self.mcl.t() + self.odo.t() + self.send.t() + self.get.t() + self.manual.t() + self.sensorfuser.t() + self.laser.t() + self.err.t() + self.fatal.t() + self.notice.t())
            tmin = min(self.mcl.t() + self.odo.t() + self.send.t() + self.get.t() + self.manual.t() + self.sensorfuser.t() + self.laser.t() + self.err.t() + self.fatal.t() + self.notice.t())
            dt = tmax - tmin
            self.tlist = [tmin + timedelta(microseconds=x) for x in range(0, int(dt.total_seconds()*1e6+1000),1000)]
            #save Error
            fid = open("Report.txt", "w") 
            print("="*20, file = fid)
            print("Files: ", self.filenames, file = fid)
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
        #creat dic
        self.data = {"mcl.x":self.mcl.x(),"mcl.y":self.mcl.y(),"mcl.theta":self.mcl.theta(), "mcl.confidence":self.mcl.confidence(),
                     "imu.yaw":self.imu.yaw(),"imu.pitch": self.imu.pitch(), "imu.roll": self.imu.roll(), "imu.ts":self.imu.ts(),
                     "imu.ax":self.imu.ax(),"imu.ay":self.imu.ay(),"imu.az":self.imu.az(),
                     "imu.gx":self.imu.gx(),"imu.gy":self.imu.gy(),"imu.gz":self.imu.gz(),
                     "imu.offx":self.imu.offx(),"imu.offy":self.imu.offy(),"imu.offz":self.imu.offz(),
                     "imu.org_gx":([i+j for (i,j) in zip(self.imu.gx()[0],self.imu.offx()[0])], self.imu.gx()[1]),
                     "imu.org_gy":([i+j for (i,j) in zip(self.imu.gy()[0],self.imu.offy()[0])], self.imu.gy()[1]),
                     "imu.org_gz":([i+j for (i,j) in zip(self.imu.gz()[0],self.imu.offz()[0])], self.imu.gz()[1]),
                     "odo.ts": self.odo.ts(),"odo.x":self.odo.x(),"odo.y":self.odo.y(),"odo.theta":self.odo.theta(),"odo.stop":self.odo.stop(),
                     "odo.vx":self.odo.vx(),"odo.vy":self.odo.vy(),"odo.vw":self.odo.vw(),"odo.steer_angle":self.odo.steer_angle(),
                     "odo.encode0":self.odo.encode0(),"odo.encode1":self.odo.encode1(),"odo.encode2":self.odo.encode2(),"odo.encode3":self.odo.encode3(),
                     "laserOdo.ts":self.laserOdo.ts(),"laserOdo.x":self.laserOdo.x(),"laserOdo.y":self.laserOdo.y(),"laserOdo.angle":self.laserOdo.angle(),
                     "laser.ts":self.laser.ts(),
                     "sensorfuser.local":self.sensorfuser.localnum(),"sensorfuser.global":self.sensorfuser.globalnum(),
                     "stop.x":self.stop.x(),"stop.y":self.stop.y(),"stop.type":self.stop.type(), "stop.id":self.stop.id(), "stop.dist": self.stop.dist(),
                     "slowdown.x":self.slowdown.x(),"slowdown.y":self.slowdown.y(),"slowdown.type":self.slowdown.type(), "slowdown.id":self.slowdown.id(), "slowdown.dist": self.slowdown.dist(),
                     "send.vx":self.send.vx(),"send.vy":self.send.vy(),"send.vw":self.send.vw(),"send.steer_angle":self.send.steer_angle(),
                     "send.max_vx":self.send.max_vx(),"send.max_vw":self.send.max_vw(),
                     "manual.vx": self.manual.vx(), "manual.vy": self.manual.vy(), "manual.vw":self.manual.vw(), "manual.steer_angle": self.manual.steer_angle(),
                     "get.vx":self.get.vx(),"get.vy":self.get.vy(),"get.vw":self.get.vw(), "get.steer_angle":self.get.steer_angle(),
                     "get.max_vx":self.get.max_vx(),"get.max_vw":self.get.max_vw(),
                     "battery.percentage": self.battery.percentage(), "battery.current": self.battery.current(), "battery.voltage": self.battery.voltage(),
                     "battery.ischarging": self.battery.ischarging(), "battery.temperature": self.battery.temperature(), "battery.cycle": self.battery.cycle(),
                     "controller.temp": self.controller.temp(), "controller.humi": self.controller.humi(), "controller.voltage":self.controller.voltage(),
                     "controller.emc": self.controller.emc(),"controller.brake":self.controller.brake(),"controller.driveremc":self.controller.driveremc(),
                     "controller.manualcharge": self.controller.manualcharge(),"controller.autocharge": self.controller.autocharge(), "controller.electric": self.controller.electric()}
        self.signal.emit(self.filenames)

class ApplicationWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.finishReadFlag = False
        self.filenames = []
        self.lines_dict = {"fatal":[],"error":[],"warning":[],"notice":[], "taskstart":[], "taskfinish":[]} 
        self.setWindowTitle('Log分析器')
        self.read_thread = ReadThread()
        self.read_thread.signal.connect(self.readFinished)
        self.setupUI()

    def setupUI(self):
        """初始化窗口结构""" 
        self.setGeometry(50,50,800,800)
        self.max_fig_num = 6 
        self.file_menu = QtWidgets.QMenu('&File', self)
        self.file_menu.addAction('&Open', self.openLogFilesDialog,
                                 QtCore.Qt.CTRL + QtCore.Qt.Key_O)
        self.file_menu.addAction('&Quit', self.fileQuit,
                                 QtCore.Qt.CTRL + QtCore.Qt.Key_Q)
        self.menuBar().addMenu(self.file_menu)

        self.fig_menu = QtWidgets.QMenu('&Numer', self)
        group = QtWidgets.QActionGroup(self.fig_menu)
        texts = [str(i) for i in range(2,self.max_fig_num+1)]
        cur_id = 1
        cur_fig_num = int(texts[cur_id])
        for text in texts:
            action = QtWidgets.QAction(text, self.fig_menu, checkable=True, checked=text==texts[cur_id])
            self.fig_menu.addAction(action)
            group.addAction(action)
        group.setExclusive(True)
        group.triggered.connect(self.fignum_changed)
        self.menuBar().addMenu(self.fig_menu)

        self.help_menu = QtWidgets.QMenu('&Help', self)
        self.help_menu.addAction('&About', self.about)
        self.menuBar().addMenu(self.help_menu)

        self._main = Widget()
        self._main.dropped.connect(self.dragFiles)
        self.setCentralWidget(self._main)
        self.layout = QtWidgets.QVBoxLayout(self._main)
        #Add ComboBox
        self.grid = QtWidgets.QGridLayout()
        for i in range(0, cur_fig_num):
            self.grid.setColumnMinimumWidth(i*2,40)
            self.grid.setColumnStretch(i*2+1,1)
        self.labels = []
        self.combos = []
        for i in range(0,cur_fig_num):
            label = QtWidgets.QLabel("图片"+str(i+1),self)
            label.adjustSize()
            combo = ExtendedComboBox(self)
            combo.resize(10,10)
            combo.activated.connect(self.combo_onActivated)
            self.labels.append(label)
            self.combos.append(combo)
            self.grid.addWidget(label,1,i*2)
            self.grid.addWidget(combo,1,i*2+1)
        self.layout.addLayout(self.grid)

        #消息框
        # self.label_info = QtWidgets.QLabel("",self)
        # self.label_info.setStyleSheet("background-color: white;")
        # self.label_info.setWordWrap(True)
        self.info = QtWidgets.QTextBrowser(self)
        self.info.setReadOnly(True)
        self.info.setFixedHeight(50)
        self.grid.addWidget(self.info,2,0,1,50)

        #图形化结构
        self.static_canvas = FigureCanvas(Figure(figsize=(100,100)))
        self.layout.addWidget(self.static_canvas)
        self.old_home = NavigationToolbar.home
        self.old_forward = NavigationToolbar.forward
        self.old_back = NavigationToolbar.back
        NavigationToolbar.home = self.new_home
        NavigationToolbar.forward = self.new_forward
        NavigationToolbar.back = self.new_back
        self.addToolBar(NavigationToolbar(self.static_canvas, self))
        self.axs= self.static_canvas.figure.subplots(cur_fig_num, 1, sharex = True)
        #鼠标移动消息
        self.static_canvas.mpl_connect('motion_notify_event', self.mouse_move)

        #选择消息框
        self.hbox = QtWidgets.QHBoxLayout()
        self.check_all = QtWidgets.QCheckBox('ALL',self)
        self.check_fatal = QtWidgets.QCheckBox('FATAL',self)
        self.check_err = QtWidgets.QCheckBox('ERROR',self)
        self.check_war = QtWidgets.QCheckBox('WARNING',self)
        self.check_notice = QtWidgets.QCheckBox('NOTICE',self)
        self.check_tstart = QtWidgets.QCheckBox('TASK START',self)
        self.check_tfinish = QtWidgets.QCheckBox('TASK FINISHED',self)
        self.hbox.addWidget(self.check_all)
        self.hbox.addWidget(self.check_fatal)
        self.hbox.addWidget(self.check_err)
        self.hbox.addWidget(self.check_war)
        self.hbox.addWidget(self.check_notice)
        self.hbox.addWidget(self.check_tstart)
        self.hbox.addWidget(self.check_tfinish)
        self.hbox.setAlignment(QtCore.Qt.AlignLeft)
        self.layout.addLayout(self.hbox)
        self.check_fatal.stateChanged.connect(self.changeCheckBox)
        self.check_err.stateChanged.connect(self.changeCheckBox)
        self.check_war.stateChanged.connect(self.changeCheckBox)
        self.check_notice.stateChanged.connect(self.changeCheckBox)
        self.check_tstart.stateChanged.connect(self.changeCheckBox)
        self.check_tfinish.stateChanged.connect(self.changeCheckBox)
        self.check_all.stateChanged.connect(self.changeCheckBoxAll)
        self.check_all.setChecked(True)

    def mouse_move(self, event):
        if event.inaxes and self.finishReadFlag:
            mouse_time = event.xdata * 86400 - 62135712000
            if mouse_time > 1e6:
                mouse_time = datetime.fromtimestamp(mouse_time)
                content = []
                dt_min = 1e10
                if self.read_thread.fatal.t() and self.check_fatal.isChecked():
                    vdt = [abs((tmpt - mouse_time).total_seconds()) for tmpt in self.read_thread.fatal.t()]
                    dt_min = min(vdt)
                    contents = [self.read_thread.fatal.content()[0][i] for i,val in enumerate(vdt) if abs(val - dt_min) < 1e-3]
                    content = '\n'.join(contents)
                if self.read_thread.err.t() and self.check_err.isChecked(): 
                    vdt = [abs((tmpt - mouse_time).total_seconds()) for tmpt in self.read_thread.err.t()]
                    tmp_dt = min(vdt)
                    if tmp_dt < dt_min:
                        dt_min = tmp_dt
                        contents = [self.read_thread.err.content()[0][i] for i,val in enumerate(vdt) if abs(val - dt_min) < 1e-3]
                        content = '\n'.join(contents)
                if self.read_thread.war.t() and self.check_war.isChecked(): 
                    vdt = [abs((tmpt - mouse_time).total_seconds()) for tmpt in self.read_thread.war.t()]
                    tmp_dt = min(vdt)
                    if tmp_dt < dt_min:
                        dt_min = tmp_dt
                        contents = [self.read_thread.war.content()[0][i] for i,val in enumerate(vdt) if abs(val - dt_min) < 1e-3]
                        content = '\n'.join(contents)
                if self.read_thread.notice.t() and self.check_notice.isChecked(): 
                    vdt = [abs((tmpt - mouse_time).total_seconds()) for tmpt in self.read_thread.notice.t()]
                    tmp_dt = min(vdt)
                    if tmp_dt < dt_min:
                        dt_min = tmp_dt
                        contents = [self.read_thread.notice.content()[0][i] for i,val in enumerate(vdt) if abs(val - dt_min) < 1e-3]
                        content = '\n'.join(contents)
                if self.read_thread.taskstart.t() and self.check_tstart.isChecked(): 
                    vdt = [abs((tmpt - mouse_time).total_seconds()) for tmpt in self.read_thread.taskstart.t()]
                    tmp_dt = min(vdt)
                    if tmp_dt < dt_min:
                        dt_min = tmp_dt
                        contents = [self.read_thread.taskstart.content()[0][i] for i,val in enumerate(vdt) if abs(val - dt_min) < 1e-3]
                        content = '\n'.join(contents)
                if self.read_thread.taskfinish.t() and self.check_tfinish.isChecked(): 
                    vdt = [abs((tmpt - mouse_time).total_seconds()) for tmpt in self.read_thread.taskfinish.t()]
                    tmp_dt = min(vdt)
                    if tmp_dt < dt_min:
                        dt_min = tmp_dt
                        contents = [self.read_thread.taskfinish.content()[0][i] for i,val in enumerate(vdt) if abs(val - dt_min) < 1e-3]
                        content = '\n'.join(contents)
                if dt_min < 10:
                    self.info.setText(content)
                else:
                    self.info.setText("")
            else:
                self.info.setText("")
        elif not self.finishReadFlag:
            self.info.setText("")


    def new_home(self, *args, **kwargs):
        for ax, combo in zip(self.axs, self.combos):
            text = combo.currentText()
            data = self.read_thread.data[text][0]
            if data:
                max_range = max(max(data) - min(data), 1e-6)
                ax.set_ylim(min(data) - 0.05 * max_range, max(data)  + 0.05 * max_range)
                ax.set_xlim(self.read_thread.tlist[0], self.read_thread.tlist[-1])
        self.static_canvas.figure.canvas.draw()

    def new_forward(self, *args, **kwargs):
        xmin,xmax =  self.axs[0].get_xlim()
        range = xmax - xmin
        xmin = xmin + range /10.0
        xmax = xmax + range /10.0
        for ax in self.axs:
            ax.set_xlim(xmin,xmax)
        self.static_canvas.figure.canvas.draw()

    def new_back(self, *args, **kwargs):
        xmin,xmax =  self.axs[0].get_xlim()
        range = xmax - xmin
        xmin = xmin - range /10.0
        xmax = xmax - range /10.0
        for ax in self.axs:
            ax.set_xlim(xmin,xmax)
        self.static_canvas.figure.canvas.draw()

    def openLogFilesDialog(self):
        # self.setGeometry(50,50,640,480)
        options = QtWidgets.QFileDialog.Options()
        options |= QtWidgets.QFileDialog.DontUseNativeDialog
        options |= QtCore.Qt.WindowStaysOnTopHint
        self.filenames, _ = QtWidgets.QFileDialog.getOpenFileNames(self,"选取log文件", "","Log Files (*.log);;All Files (*)", options=options)
        if self.filenames:
            self.read_thread.filenames = self.filenames
            self.read_thread.start()
            print('Loading', len(self.filenames), 'Files:')
            for (ind, f) in enumerate(self.filenames):
                print(ind+1, ':', f)
            tmpstr = 'Loading......: {0}'.format([f.split('/')[-1] for f in self.filenames])
            self.statusBar().showMessage(tmpstr)

    def dragFiles(self, files):
        self.filenames = []
        for file in files:
            if os.path.exists(file):
                if os.path.splitext(file)[1] == ".log":
                    self.filenames.append(file)
        if self.filenames:
            self.read_thread.filenames = self.filenames
            self.read_thread.start()
            print('Loading', len(self.filenames), 'Files:')
            for (ind, f) in enumerate(self.filenames):
                print(ind+1, ':', f)
            tmpstr = 'Loading......: {0}'.format([f.split('/')[-1] for f in self.filenames])
            self.statusBar().showMessage(tmpstr)

    def readFinished(self, result):
        print('Finished')
        self.statusBar().showMessage('Finished')
        max_line = 1000
        if len(self.read_thread.fatal.t()) > max_line:
            print("FATALs are too much to be ploted. Max Number is ", max_line, ". Current Number is ", len(self.read_thread.fatal.t()))
            self.read_thread.fatal = FatalLine()
        if len(self.read_thread.err.t()) > max_line:
            print("ERRORs are too much to be ploted. Max Number is ", max_line, ". Current Number is ", len(self.read_thread.err.t()))
            self.read_thread.err = ErrorLine()
        if len(self.read_thread.war.t()) > max_line:
            print("WARNINGs are too much to be ploted. Max Number is ", max_line, ". Current Number is ", len(self.read_thread.war.t()))
            self.read_thread.war = WarningLine()
        if len(self.read_thread.notice.t()) > max_line:
            print("NOTICEs are too much to be ploted. Max Number is ", max_line, ". Current Number is ", len(self.read_thread.notice.t()))
            self.read_thread.notice = NoticeLine()
        if len(self.read_thread.taskstart.t()) > max_line:
            print("TASKSTART are too much to be ploted. Max Number is ", max_line, ". Current Number is ", len(self.read_thread.taskstart.t()))
            self.read_thread.taskstart = TaskStart()
        if len(self.read_thread.taskfinish.t()) > max_line:
            print("TASKFINISH are too much to be ploted. Max Number is ", max_line, ". Current Number is ", len(self.read_thread.taskfinish.t()))
            self.read_thread.taskfinish = TaskFinish()
        self.finishReadFlag = True
        self.setWindowTitle('Log分析器: {0}'.format([f.split('/')[-1] for f in self.filenames]))
        if self.read_thread.filenames:
            #画图 mcl.t, mcl.x
            keys = list(self.read_thread.data.keys())
            for ax, combo in zip(self.axs, self.combos):
                if combo.count() == 0:
                    combo.addItems(keys)
                self.drawdata(ax, self.read_thread.data[combo.currentText()],combo.currentText(), True)

    def fileQuit(self):
        self.close()

    def about(self):
        QtWidgets.QMessageBox.about(self, "关于", """Log Viewer V1.1.2""")

    def combo_onActivated(self):
        # print("combo1: ",text)
        curcombo = self.sender()
        index = self.combos.index(curcombo)
        text = curcombo.currentText()
        # print("index:", index, "sender:", self.sender()," text:", text)
        ax = self.axs[index]
        self.drawdata(ax, self.read_thread.data[text], text, False)

    def fignum_changed(self,action):
        new_fig_num = int(action.text())
        xmin, xmax = self.axs[0].get_xlim()
        for ax in self.axs:
            self.static_canvas.figure.delaxes(ax)
        self.axs= self.static_canvas.figure.subplots(new_fig_num, 1, sharex = True)
        self.static_canvas.figure.canvas.draw()
        for i in reversed(range(2, self.grid.count())): 
            self.grid.itemAt(i).widget().deleteLater()
        for i in range(0, new_fig_num):
            self.grid.setColumnMinimumWidth(i*2,40)
            self.grid.setColumnStretch(i*2+1,1)
        combo_ind = [] 
        for combo in self.combos:
            combo_ind.append(combo.currentIndex())
        self.labels = []
        self.combos = []
        for i in range(0,new_fig_num):
            label = QtWidgets.QLabel("图片"+str(i+1),self)
            label.adjustSize()
            combo = ExtendedComboBox(self)
            combo.resize(10,10)
            combo.activated.connect(self.combo_onActivated)
            self.labels.append(label)
            self.combos.append(combo)
            self.grid.addWidget(label,1,i*2)
            self.grid.addWidget(combo,1,i*2+1)
        self.info = QtWidgets.QTextBrowser(self)
        self.info.setReadOnly(True)
        self.info.setFixedHeight(50)
        self.grid.addWidget(self.info,2,0,1,50)
        if self.finishReadFlag:
            if self.read_thread.filenames:
                keys = list(self.read_thread.data.keys())
                count = 0
                for ax, combo in zip(self.axs, self.combos):
                    combo.addItems(keys)
                    if count < len(combo_ind):
                        combo.setCurrentIndex(combo_ind[count])
                    count = count + 1
                    ax.set_xlim(xmin, xmax)
                    self.drawdata(ax, self.read_thread.data[combo.currentText()],combo.currentText(), False)

    def drawdata(self, ax, data, ylabel, resize = False):
        xmin,xmax =  ax.get_xlim()
        ax.cla()
        self.drawFEWN(ax)
        if data[1] and data[0]:
            ax.plot(data[1], data[0], '.')
            max_range = max(max(data[0]) - min(data[0]), 1.0)
            ax.set_ylim(min(data[0]) - 0.05 * max_range, max(data[0]) + 0.05 * max_range)
        if resize:
            ax.set_xlim(self.read_thread.tlist[0], self.read_thread.tlist[-1])
        else:
            ax.set_xlim(xmin, xmax)
        ax.set_ylabel(ylabel)
        ax.grid()
        self.static_canvas.figure.canvas.draw()

    def drawFEWN(self,ax):
        """ 绘制 Fatal, Error, Warning在坐标轴上"""
        fl, el, wl,nl = None, None, None, None
        self.lines_dict = dict()
        line_num = 0
        legend_info = []
        fnum, ernum, wnum, nnum = [], [], [], [] 
        tsnum, tfnum = [],[]
        tsl, tfl = None,None
        for tmp in self.read_thread.fatal.t():
            fl= ax.axvline(tmp, linestyle='-',color = 'm')
            # fl, = ax.plot((tmp,tmp),[-1e50, 1e50],'m-')
            fnum.append(line_num)
            line_num = line_num + 1
        if fl:
            legend_info.append(fl)
            legend_info.append('fatal')
        for tmp in self.read_thread.err.t():
            el= ax.axvline(tmp, linestyle = '-.', color='r')
            # el, = ax.plot((tmp,tmp),[-1e50, 1e50],'r-.')
            ernum.append(line_num)
            line_num = line_num + 1
        if el:
            legend_info.append(el)
            legend_info.append('error')
        for tmp in self.read_thread.war.t():
            wl = ax.axvline(tmp, linestyle = '--', color = 'y')
            # wl, = ax.plot((tmp,tmp),[-1e50, 1e50],'y--')
            wnum.append(line_num)
            line_num = line_num + 1
        if wl:
            legend_info.append(wl)
            legend_info.append('warning')
        for tmp in self.read_thread.notice.t():
            nl = ax.axvline(tmp, linestyle = ':', color = 'g')
            # nl, = ax.plot((tmp,tmp),[-1e50, 1e50],'g:')
            nnum.append(line_num)
            line_num = line_num + 1
        if nl:
            legend_info.append(nl)
            legend_info.append('notice')
        for tmp in self.read_thread.taskstart.t():
            tsl = ax.axvline(tmp, linestyle = '-', color = 'b')
            # tsl, = ax.plot((tmp,tmp),[-1e50, 1e50],'b')
            tsnum.append(line_num)
            line_num = line_num + 1
        if tsl:
            legend_info.append(tsl)
            legend_info.append('task start')
        for tmp in self.read_thread.taskfinish.t():
            tfl = ax.axvline(tmp, linestyle = '--', color = 'b')
            # tfl, = ax.plot((tmp,tmp),[-1e50, 1e50],'b--')
            tfnum.append(line_num)
            line_num = line_num + 1
        if tfl:
            legend_info.append(tfl)
            legend_info.append('task finish')
        if legend_info:
            ax.legend(legend_info[0::2], legend_info[1::2], loc='upper right')
        self.lines_dict['fatal'] = fnum
        self.lines_dict['error'] = ernum
        self.lines_dict['warning'] = wnum
        self.lines_dict['notice'] = nnum
        self.lines_dict['taskstart'] = tsnum
        self.lines_dict['taskfinish'] = tfnum
        lines = ax.get_lines()
        for n in fnum:
            lines[n].set_visible(self.check_fatal.isChecked())
        for n in ernum:
            lines[n].set_visible(self.check_err.isChecked())
        for n in wnum:
            lines[n].set_visible(self.check_war.isChecked())
        for n in nnum:
            lines[n].set_visible(self.check_notice.isChecked())
        for n in tsnum:
            lines[n].set_visible(self.check_tstart.isChecked())
        for n in tfnum:
            lines[n].set_visible(self.check_tfinish.isChecked())
        
    def updateCheckInfoLine(self,key):
        for ax in self.axs:
            lines = ax.get_lines()
            for num in self.lines_dict[key]:
                vis = not lines[num].get_visible()
                lines[num].set_visible(vis)
        # for ax, combo in zip(self.axs, self.combos):
        #     if combo.currentText():
        #         self.drawdata(ax, self.read_thread.data[combo.currentText()],combo.currentText(), False)
        self.static_canvas.figure.canvas.draw()


    def changeCheckBox(self):
        if self.check_err.isChecked() and self.check_fatal.isChecked() and self.check_notice.isChecked() and \
        self.check_war.isChecked() and self.check_tstart.isChecked() and self.check_tfinish.isChecked():
            self.check_all.setCheckState(QtCore.Qt.Checked)
        elif self.check_err.isChecked() or self.check_fatal.isChecked() or self.check_notice.isChecked() or \
        self.check_war.isChecked() or self.check_tstart.isChecked() and self.check_tfinish.isChecked():
            self.check_all.setTristate()
            self.check_all.setCheckState(QtCore.Qt.PartiallyChecked)
        else:
            self.check_all.setTristate(False)
            self.check_all.setCheckState(QtCore.Qt.Unchecked)

        cur_check = self.sender()
        if cur_check is self.check_fatal:
            self.updateCheckInfoLine('fatal')
        elif cur_check is self.check_err:
            self.updateCheckInfoLine('error')
        elif cur_check is self.check_war:
            self.updateCheckInfoLine('warning')
        elif cur_check is self.check_notice:
            self.updateCheckInfoLine('notice')
        elif cur_check is self.check_tstart:
            self.updateCheckInfoLine('taskstart')
        elif cur_check is self.check_tfinish:
            self.updateCheckInfoLine('taskfinish')

    def changeCheckBoxAll(self):
        if self.check_all.checkState() == QtCore.Qt.Checked:
            self.check_fatal.setChecked(True)
            self.check_err.setChecked(True)
            self.check_war.setChecked(True)
            self.check_notice.setChecked(True)
            self.check_tstart.setChecked(True)
            self.check_tfinish.setChecked(True)
        elif self.check_all.checkState() == QtCore.Qt.Unchecked:
            self.check_fatal.setChecked(False)
            self.check_err.setChecked(False)
            self.check_war.setChecked(False)
            self.check_notice.setChecked(False)
            self.check_tstart.setChecked(False)
            self.check_tfinish.setChecked(False)

if __name__ == "__main__":
    qapp = QtWidgets.QApplication(sys.argv)
    app = ApplicationWindow()
    app.show()
    qapp.exec_()
