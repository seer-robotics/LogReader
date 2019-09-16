import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import (
    FigureCanvas, NavigationToolbar2QT as NavigationToolbar)
from PyQt5 import QtCore, QtWidgets,QtGui
from matplotlib.figure import Figure
from datetime import datetime
from datetime import timedelta
import os, sys
from numpy import searchsorted
from ExtendedComboBox import ExtendedComboBox
from Widget import Widget
from ReadThread import ReadThread, Fdir2Flink
from loglib import ErrorLine, WarningLine, ReadLog, FatalLine, NoticeLine, TaskStart, TaskFinish, Service
from MapWidget import MapWidget, Readmap
import logging
import numpy as np
import traceback

class XYSelection:
    def __init__(self, num = 1):
        self.num = num 
        self.groupBox = QtWidgets.QGroupBox('图片'+str(self.num))
        self.x_label = QtWidgets.QLabel('Time')
        self.y_label = QtWidgets.QLabel('Data')
        self.x_combo = ExtendedComboBox()
        self.y_combo = ExtendedComboBox()
        x_form = QtWidgets.QFormLayout()
        x_form.addRow(self.x_label,self.x_combo)
        y_form = QtWidgets.QFormLayout()
        y_form.addRow(self.y_label,self.y_combo)
        vbox = QtWidgets.QVBoxLayout()
        vbox.addLayout(y_form)
        vbox.addLayout(x_form)
        self.groupBox.setLayout(vbox)

class ApplicationWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.finishReadFlag = False
        self.filenames = []
        self.lines_dict = {"fatal":[],"error":[],"warning":[],"notice":[], "taskstart":[], "taskfinish":[], "service":[]} 
        self.setWindowTitle('Log分析器')
        self.read_thread = ReadThread()
        self.read_thread.signal.connect(self.readFinished)
        self.setupUI()
        self.map_select_flag = False
        self.map_select_lines = []
        self.mouse_pressed = False
        self.map_widget = None

    def setupUI(self):
        """初始化窗口结构""" 
        self.setGeometry(50,50,800,900)
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

        self.map_menu = QtWidgets.QMenu('&Map', self)
        self.menuBar().addMenu(self.map_menu)
        self.map_action = QtWidgets.QAction('&Open Map', self.map_menu, checkable = True)
        self.map_action.setShortcut(QtCore.Qt.CTRL + QtCore.Qt.Key_M)
        self.map_action.triggered.connect(self.openMap)
        self.map_menu.addAction(self.map_action)

        self.help_menu = QtWidgets.QMenu('&Help', self)
        self.help_menu.addAction('&About', self.about)
        self.menuBar().addMenu(self.help_menu)

        self._main = Widget()
        self._main.dropped.connect(self.dragFiles)
        self.setCentralWidget(self._main)
        self.layout = QtWidgets.QVBoxLayout(self._main)
        #Add ComboBox
        self.xys = []
        self.xy_hbox = QtWidgets.QHBoxLayout()
        for i in range(0,cur_fig_num):
            selection = XYSelection(i+1)
            selection.y_combo.activated.connect(self.ycombo_onActivated)
            selection.x_combo.activated.connect(self.xcombo_onActivated)
            self.xys.append(selection)
            self.xy_hbox.addWidget(selection.groupBox)
        self.layout.addLayout(self.xy_hbox)

        #消息框
        # self.label_info = QtWidgets.QLabel("",self)
        # self.label_info.setStyleSheet("background-color: white;")
        # self.label_info.setWordWrap(True)
        self.info = QtWidgets.QTextBrowser(self)
        self.info.setReadOnly(True)
        self.info.setMinimumHeight(5)
        # self.layout.addWidget(self.info)

        #图形化结构
        self.fig_height = 2.0
        self.static_canvas = FigureCanvas(Figure(figsize=(14,self.fig_height*cur_fig_num)))
        self.static_canvas.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.fig_widget = Widget()
        self.fig_layout = QtWidgets.QVBoxLayout(self.fig_widget)
        self.fig_layout.addWidget(self.static_canvas)
        self.scroll = QtWidgets.QScrollArea(self.fig_widget)
        self.scroll.setWidget(self.static_canvas)
        self.scroll.setWidgetResizable(True)
        self.scroll.keyPressEvent = self.keyPressEvent
        # self.layout.addWidget(self.scroll)
        self.old_home = NavigationToolbar.home
        self.old_forward = NavigationToolbar.forward
        self.old_back = NavigationToolbar.back
        NavigationToolbar.home = self.new_home
        NavigationToolbar.forward = self.new_forward
        NavigationToolbar.back = self.new_back
        self.addToolBar(NavigationToolbar(self.static_canvas, self._main))
        self.static_canvas.figure.subplots_adjust(left = 0.2/cur_fig_num, right = 0.99, bottom = 0.05, top = 0.99, hspace = 0.1)
        self.axs= self.static_canvas.figure.subplots(cur_fig_num, 1, sharex = True)
        #鼠标移动消息
        self.static_canvas.mpl_connect('motion_notify_event', self.mouse_move)
        self.static_canvas.mpl_connect('button_press_event', self.mouse_press)
        self.static_canvas.mpl_connect('button_release_event', self.mouse_release)
        self.static_canvas.mpl_connect('pick_event', self.onpick)

        #Log
        self.log_info = QtWidgets.QTextBrowser(self)
        self.log_info.setReadOnly(True)
        self.log_info.setMinimumHeight(10)
        self.log_info.setOpenLinks(False)
        self.log_info.anchorClicked.connect(self.openFileUrl)
        # self.layout.addWidget(self.log_info)

        #消息框，绘图，Log窗口尺寸可变
        splitter1 = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        splitter1.addWidget(self.info)
        splitter1.addWidget(self.scroll)
        splitter1.setSizes([1,100])

        splitter2 = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        splitter2.addWidget(splitter1)
        splitter2.addWidget(self.log_info)
        splitter2.setSizes([100,1])
        self.layout.addWidget(splitter2)

        #选择消息框
        self.hbox = QtWidgets.QHBoxLayout()
        self.check_all = QtWidgets.QCheckBox('ALL',self)
        self.check_fatal = QtWidgets.QCheckBox('FATAL',self)
        self.check_err = QtWidgets.QCheckBox('ERROR',self)
        self.check_war = QtWidgets.QCheckBox('WARNING',self)
        self.check_notice = QtWidgets.QCheckBox('NOTICE',self)
        self.check_tstart = QtWidgets.QCheckBox('TASK START',self)
        self.check_tfinish = QtWidgets.QCheckBox('TASK FINISHED',self)
        self.check_service = QtWidgets.QCheckBox('SERVICE',self)
        self.hbox.addWidget(self.check_all)
        self.hbox.addWidget(self.check_fatal)
        self.hbox.addWidget(self.check_err)
        self.hbox.addWidget(self.check_war)
        self.hbox.addWidget(self.check_notice)
        self.hbox.addWidget(self.check_tstart)
        self.hbox.addWidget(self.check_tfinish)
        self.hbox.addWidget(self.check_service)
        self.hbox.setAlignment(QtCore.Qt.AlignLeft)
        self.layout.addLayout(self.hbox)
        self.check_fatal.stateChanged.connect(self.changeCheckBox)
        self.check_err.stateChanged.connect(self.changeCheckBox)
        self.check_war.stateChanged.connect(self.changeCheckBox)
        self.check_notice.stateChanged.connect(self.changeCheckBox)
        self.check_tstart.stateChanged.connect(self.changeCheckBox)
        self.check_tfinish.stateChanged.connect(self.changeCheckBox)
        self.check_service.stateChanged.connect(self.changeCheckBox)
        self.check_all.stateChanged.connect(self.changeCheckBoxAll)
        self.check_all.setChecked(True)
    
    def get_content(self, mouse_time):
        content = ""
        dt_min = 1e10
        if self.read_thread.fatal.t() and self.check_fatal.isChecked():
            vdt = [abs((tmpt - mouse_time).total_seconds()) for tmpt in self.read_thread.fatal.t()]
            dt_min = min(vdt)
        if self.read_thread.err.t() and self.check_err.isChecked(): 
            vdt = [abs((tmpt - mouse_time).total_seconds()) for tmpt in self.read_thread.err.t()]
            tmp_dt = min(vdt)
            if tmp_dt < dt_min:
                dt_min = tmp_dt
        if self.read_thread.war.t() and self.check_war.isChecked(): 
            vdt = [abs((tmpt - mouse_time).total_seconds()) for tmpt in self.read_thread.war.t()]
            tmp_dt = min(vdt)
            if tmp_dt < dt_min:
                dt_min = tmp_dt
        if self.read_thread.notice.t() and self.check_notice.isChecked(): 
            vdt = [abs((tmpt - mouse_time).total_seconds()) for tmpt in self.read_thread.notice.t()]
            tmp_dt = min(vdt)
            if tmp_dt < dt_min:
                dt_min = tmp_dt
        if self.read_thread.taskstart.t() and self.check_tstart.isChecked(): 
            vdt = [abs((tmpt - mouse_time).total_seconds()) for tmpt in self.read_thread.taskstart.t()]
            tmp_dt = min(vdt)
            if tmp_dt < dt_min:
                dt_min = tmp_dt
        if self.read_thread.taskfinish.t() and self.check_tfinish.isChecked(): 
            vdt = [abs((tmpt - mouse_time).total_seconds()) for tmpt in self.read_thread.taskfinish.t()]
            tmp_dt = min(vdt)
            if tmp_dt < dt_min:
                dt_min = tmp_dt
        if self.read_thread.service.t() and self.check_service.isChecked(): 
            vdt = [abs((tmpt - mouse_time).total_seconds()) for tmpt in self.read_thread.service.t()]
            tmp_dt = min(vdt)
            if tmp_dt < dt_min:
                dt_min = tmp_dt

        if dt_min < 10:
            contents = []
            if self.read_thread.fatal.t() and self.check_fatal.isChecked():
                vdt = [abs((tmpt - mouse_time).total_seconds()) for tmpt in self.read_thread.fatal.t()]
                tmp_dt = min(vdt)
                if abs(tmp_dt - dt_min) < 2e-2:
                    contents = contents + [self.read_thread.fatal.content()[0][i] for i,val in enumerate(vdt) if abs(val - dt_min) < 1e-3]
            if self.read_thread.err.t() and self.check_err.isChecked(): 
                vdt = [abs((tmpt - mouse_time).total_seconds()) for tmpt in self.read_thread.err.t()]
                tmp_dt = min(vdt)
                if abs(tmp_dt - dt_min) < 2e-2:
                    contents = contents + [self.read_thread.err.content()[0][i] for i,val in enumerate(vdt) if abs(val - dt_min) < 1e-3]
            if self.read_thread.war.t() and self.check_war.isChecked(): 
                vdt = [abs((tmpt - mouse_time).total_seconds()) for tmpt in self.read_thread.war.t()]
                tmp_dt = min(vdt)
                if abs(tmp_dt - dt_min) < 2e-2:
                    contents = contents + [self.read_thread.war.content()[0][i] for i,val in enumerate(vdt) if abs(val - dt_min) < 1e-3]
            if self.read_thread.notice.t() and self.check_notice.isChecked(): 
                vdt = [abs((tmpt - mouse_time).total_seconds()) for tmpt in self.read_thread.notice.t()]
                tmp_dt = min(vdt)
                if abs(tmp_dt - dt_min) < 2e-2:
                    contents = contents + [self.read_thread.notice.content()[0][i] for i,val in enumerate(vdt) if abs(val - dt_min) < 1e-3]
            if self.read_thread.taskstart.t() and self.check_tstart.isChecked(): 
                vdt = [abs((tmpt - mouse_time).total_seconds()) for tmpt in self.read_thread.taskstart.t()]
                tmp_dt = min(vdt)
                if abs(tmp_dt - dt_min) < 2e-2:
                    contents = contents + [self.read_thread.taskstart.content()[0][i] for i,val in enumerate(vdt) if abs(val - dt_min) < 1e-3]
            if self.read_thread.taskfinish.t() and self.check_tfinish.isChecked(): 
                vdt = [abs((tmpt - mouse_time).total_seconds()) for tmpt in self.read_thread.taskfinish.t()]
                tmp_dt = min(vdt)
                if abs(tmp_dt - dt_min) < 2e-2:
                    contents = contents + [self.read_thread.taskfinish.content()[0][i] for i,val in enumerate(vdt) if abs(val - dt_min) < 1e-3]
            if self.read_thread.service.t() and self.check_service.isChecked(): 
                vdt = [abs((tmpt - mouse_time).total_seconds()) for tmpt in self.read_thread.service.t()]
                tmp_dt = min(vdt)
                if abs(tmp_dt - dt_min) < 2e-2:
                    contents = contents + [self.read_thread.service.content()[0][i] for i,val in enumerate(vdt) if abs(val - dt_min) < 1e-3]
            content = '\n'.join(contents)
        return content

    def updateMap(self, mouse_time):
        try:
            for ln in self.map_select_lines:
                ln.set_xdata([mouse_time,mouse_time])
            self.static_canvas.figure.canvas.draw()
            if 'LocationEachFrame' in self.read_thread.content:
                if self.read_thread.content['LocationEachFrame']['timestamp']:
                    if self.read_thread.laser.t:
                        #最近的定位时间
                        loc_ts = np.array(self.read_thread.content['LocationEachFrame']['t'])
                        loc_idx = (np.abs(loc_ts - mouse_time)).argmin()
                        robot_loc_pos = [self.read_thread.content['LocationEachFrame']['x'][loc_idx],
                                    self.read_thread.content['LocationEachFrame']['y'][loc_idx],
                                    np.deg2rad(self.read_thread.content['LocationEachFrame']['theta'][loc_idx])]

                        #最近的激光时间
                        t = np.array(self.read_thread.laser.t())
                        if len(t) < 1:
                            return
                        laser_idx = (np.abs(t-mouse_time)).argmin()
                        org_point = [0 for _ in range(len(self.read_thread.laser.x()[0][laser_idx]))]
                        laser_x = [None] * len(org_point) * 2
                        laser_x[::2] = self.read_thread.laser.x()[0][laser_idx]
                        laser_x[1::2] = org_point
                        laser_y = [None] * len(org_point) * 2
                        laser_y[::2] = self.read_thread.laser.y()[0][laser_idx]
                        laser_y[1::2] = org_point
                        laser_poitns = np.array([laser_x, laser_y])
                        ts = self.read_thread.laser.ts()[0][laser_idx]
                        pos_ts = np.array(self.read_thread.content['LocationEachFrame']['timestamp'])
                        pos_idx = (np.abs(pos_ts - ts)).argmin()
                        robot_pos = [self.read_thread.content['LocationEachFrame']['x'][pos_idx],
                                    self.read_thread.content['LocationEachFrame']['y'][pos_idx],
                                    np.deg2rad(self.read_thread.content['LocationEachFrame']['theta'][pos_idx])]
                        laser_info = (str(self.read_thread.content['LocationEachFrame']['t'][pos_idx]) 
                                            + ' , ' + str((int)(self.read_thread.content['LocationEachFrame']['timestamp'][pos_idx]))
                                            + ' , ' + str(self.read_thread.content['LocationEachFrame']['x'][pos_idx])
                                            + ' , ' + str(self.read_thread.content['LocationEachFrame']['y'][pos_idx])
                                            + ' , ' + str(self.read_thread.content['LocationEachFrame']['theta'][pos_idx]))
                        loc_info = (str(self.read_thread.content['LocationEachFrame']['t'][loc_idx]) 
                                            + ' , ' + str((int)(self.read_thread.content['LocationEachFrame']['timestamp'][loc_idx]))
                                            + ' , ' + str(self.read_thread.content['LocationEachFrame']['x'][loc_idx])
                                            + ' , ' + str(self.read_thread.content['LocationEachFrame']['y'][loc_idx])
                                            + ' , ' + str(self.read_thread.content['LocationEachFrame']['theta'][loc_idx]))
                        
                        obs_pos = []
                        obs_info = ''
                        stop_ts = np.array(self.read_thread.content['StopPoints']['t'])
                        if len(stop_ts) > 0:
                            stop_idx = (np.abs(stop_ts - mouse_time)).argmin()
                            dt = (stop_ts[stop_idx] - mouse_time).total_seconds()
                            if abs(dt) < 0.5:
                                obs_pos = [self.read_thread.content['StopPoints']['x'][stop_idx], self.read_thread.content['StopPoints']['y'][stop_idx]]
                                obs_info = (str(self.read_thread.content['StopPoints']['t'][stop_idx])
                                            + ' , ' + str(self.read_thread.content['StopPoints']['x'][stop_idx])
                                            + ' , ' + str(self.read_thread.content['StopPoints']['y'][stop_idx])
                                            + ' , ' + str((int)(self.read_thread.content['StopPoints']['category'][stop_idx]))
                                            + ' , ' + str((int)(self.read_thread.content['StopPoints']['ultra_id'][stop_idx]))
                                            + ' , ' + str(self.read_thread.content['StopPoints']['dist'][stop_idx]))

                        self.map_widget.updateRobotLaser(laser_poitns,robot_pos,robot_loc_pos, laser_info, loc_info, obs_pos, obs_info)
        except:
            logging.error(traceback.format_exc())

    def mouse_press(self, event):
        self.mouse_pressed = True
        if event.inaxes and self.finishReadFlag:
            mouse_time = event.xdata * 86400 - 62135712000
            if mouse_time > 1e6:
                mouse_time = datetime.fromtimestamp(mouse_time)
                if event.button == 1:
                    content = 't, '  + event.inaxes.get_ylabel() + ' : ' + str(mouse_time) + ',' +str(event.ydata)
                    self.log_info.append(content)
                else:
                    content = self.get_content(mouse_time)
                    self.log_info.append(content[:-1])
                if self.map_select_flag:
                    self.updateMap(mouse_time)

    def mouse_move(self, event):
        if event.inaxes and self.finishReadFlag:
            mouse_time = event.xdata * 86400 - 62135712000
            if mouse_time > 1e6:
                mouse_time = datetime.fromtimestamp(mouse_time)
                content = self.get_content(mouse_time)
                self.info.setText(content)
                if self.map_select_flag:
                    self.updateMap(mouse_time)
            else:
                self.info.setText("")
        elif not self.finishReadFlag:
            self.info.setText("")

    def mouse_release(self, event):
        self.mouse_pressed = False
        self.map_select_flag = False

    def onpick(self, event):
        if self.map_action.isChecked():
            self.map_select_flag = True
        else:
            self.map_select_flag = False

    def keyPressEvent(self,event):
        if self.map_action.isChecked():
            if len(self.map_select_lines) > 1:
                if (event.key() == QtCore.Qt.Key_A or event.key() == QtCore.Qt.Key_D
                    or event.key() == QtCore.Qt.Key_Left or event.key() == QtCore.Qt.Key_Right):
                    cur_t = self.map_select_lines[0].get_xdata()[0]
                    t = []
                    if event.key() == QtCore.Qt.Key_A or event.key() == QtCore.Qt.Key_D:
                        t = np.array(self.read_thread.content['LocationEachFrame']['t'])
                    else:
                        t = np.array(self.read_thread.laser.t())
                    loc_idx = (np.abs(t-cur_t)).argmin()
                    if event.key() == QtCore.Qt.Key_Left or event.key() == QtCore.Qt.Key_A:
                        if loc_idx > 0:
                            loc_idx = loc_idx - 1
                    elif event.key() == QtCore.Qt.Key_Right or  event.key() == QtCore.Qt.Key_D:
                        if loc_idx < (len(t)-1):
                            loc_idx = loc_idx + 1
                    self.updateMap(t[loc_idx])
                # for ln in self.map_select_lines:

    def new_home(self, *args, **kwargs):
        for ax, xy in zip(self.axs, self.xys):
            text = xy.y_combo.currentText()
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

    def openFileUrl(self, flink):
        QtGui.QDesktopServices.openUrl(flink)

    def openLogFilesDialog(self):
        # self.setGeometry(50,50,640,480)
        options = QtWidgets.QFileDialog.Options()
        options |= QtWidgets.QFileDialog.DontUseNativeDialog
        options |= QtCore.Qt.WindowStaysOnTopHint
        self.filenames, _ = QtWidgets.QFileDialog.getOpenFileNames(self,"选取log文件", "","Log Files (*.log);;All Files (*)", options=options)
        if self.filenames:
            self.finishReadFlag = False
            self.read_thread.filenames = self.filenames
            self.read_thread.start()
            logging.debug('Loading ' + str(len(self.filenames)) + ' Files:')
            self.log_info.append('Loading '+str(len(self.filenames)) + ' Files:')
            for (ind, f) in enumerate(self.filenames):
                logging.debug(str(ind+1)+':'+f)
                flink = Fdir2Flink(f)
                self.log_info.append(str(ind+1)+':'+flink)
            self.setWindowTitle('Loading')

    def dragFiles(self, files):
        try:
            flag_first_in = True
            for file in files:
                if os.path.exists(file):
                    if os.path.splitext(file)[1] == ".log":
                        if flag_first_in:
                            self.filenames = []
                            flag_first_in = False
                        self.filenames.append(file)
                    elif os.path.split(file)[1] == ".json":
                        logging.debug('Update log_config.json')
            if self.filenames:
                self.finishReadFlag = False
                self.read_thread.filenames = self.filenames
                self.read_thread.start()
                logging.debug('Loading' + str(len(self.filenames)) + 'Files:')
                self.log_info.append('Loading '+str(len(self.filenames)) + ' Files:')
                for (ind, f) in enumerate(self.filenames):
                    logging.debug(str(ind+1) + ':' + f)
                    flink = Fdir2Flink(f)
                    self.log_info.append(str(ind+1)+':'+flink)
                self.setWindowTitle('Loading')
        except:
            logging.error(traceback.format_exc())

    def readFinished(self, result):
        for tmps in self.read_thread.log:
            self.log_info.append(tmps)
        logging.debug('read Finished')
        self.log_info.append('Finished')
        max_line = 1000
        if len(self.read_thread.fatal.t()) > max_line:
            logging.warning("FATALs are too much to be ploted. Max Number is " + str(max_line) + ". Current Number is " + str(len(self.read_thread.fatal.t())))
            self.log_info.append("FATALs are too much to be ploted. Max Number is "+ str(max_line) + ". Current Number is " + str(len(self.read_thread.fatal.t())))
            self.read_thread.fatal = FatalLine()
        if len(self.read_thread.err.t()) > max_line:
            logging.warning("ERRORs are too much to be ploted. Max Number is " + str(max_line) + ". Current Number is " + str(len(self.read_thread.err.t())))
            self.log_info.append("ERRORs are too much to be ploted. Max Number is " + str(max_line)+". Current Number is "+str(len(self.read_thread.err.t())))
            self.read_thread.err = ErrorLine()
        if len(self.read_thread.war.t()) > max_line:
            logging.warning("WARNINGs are too much to be ploted. Max Number is " + str(max_line) + ". Current Number is " + str(len(self.read_thread.war.t())))
            self.log_info.append("WARNINGs are too much to be ploted. Max Number is " + str(max_line) +  ". Current Number is " + str(len(self.read_thread.war.t())))
            self.read_thread.war = WarningLine()
        if len(self.read_thread.notice.t()) > max_line:
            logging.warning("NOTICEs are too much to be ploted. Max Number is " + str(max_line) + ". Current Number is " + str(len(self.read_thread.notice.t())))
            self.log_info.append("NOTICEs are too much to be ploted. Max Number is " + str(max_line) + ". Current Number is " + str(len(self.read_thread.notice.t())))
            self.read_thread.notice = NoticeLine()
        if len(self.read_thread.taskstart.t()) > max_line:
            logging.warning("TASKSTART are too much to be ploted. Max Number is " + str(max_line) + ". Current Number is " + str(len(self.read_thread.taskstart.t())))
            self.log_info.append("TASKSTART are too much to be ploted. Max Number is " + str(max_line) + ". Current Number is " + str(len(self.read_thread.taskstart.t())))
            self.read_thread.taskstart = TaskStart()
        if len(self.read_thread.taskfinish.t()) > max_line:
            logging.warning("TASKFINISH are too much to be ploted. Max Number is " + str(max_line) + ". Current Number is " + str(len(self.read_thread.taskfinish.t())))
            self.log_info.append("TASKFINISH are too much to be ploted. Max Number is " + str(max_line) + ". Current Number is " + str(len(self.read_thread.taskfinish.t())))
            self.read_thread.taskfinish = TaskFinish()
        if len(self.read_thread.service.t()) > max_line:
            logging.warning("SERVICE are too much to be ploted. Max Number is " + str(max_line) +". Current Number is " + str(len(self.read_thread.service.t())))
            self.log_info.append("SERVICE are too much to be ploted. Max Number is " + str(max_line) + ". Current Number is " + str(len(self.read_thread.service.t())))
            self.read_thread.service = Service()
        self.finishReadFlag = True
        self.setWindowTitle('Log分析器: {0}'.format([f.split('/')[-1] for f in self.filenames]))
        if self.read_thread.filenames:
            #画图 mcl.t, mcl.x
            self.map_select_lines = []
            keys = list(self.read_thread.data.keys())
            for ax, xy in zip(self.axs, self.xys):
                xy.y_combo.clear()
                xy.y_combo.addItems(keys) 
                xy.x_combo.clear()
                xy.x_combo.addItems(['t'])
                group_name = xy.y_combo.currentText().split('.')[0]
                if group_name in self.read_thread.content:
                    if 'timestamp' in self.read_thread.content[group_name].data:
                        xy.x_combo.addItems(['timestamp'])
                self.drawdata(ax, self.read_thread.data[xy.y_combo.currentText()],
                                str(self.xys.index(xy) + 1) + ' : ' + xy.y_combo.currentText(), True)
            self.updateMapSelectLine()
            self.openMap(self.map_action.isChecked())


    def fileQuit(self):
        self.close()

    def about(self):
        QtWidgets.QMessageBox.about(self, "关于", """Log Viewer V2.0.3""")

    def ycombo_onActivated(self):
        curcombo = self.sender()
        index = 0
        for (ind, xy) in enumerate(self.xys):
            if xy.y_combo == curcombo:
                index = ind
                break; 
        text = curcombo.currentText()
        current_x_index = self.xys[index].x_combo.currentIndex()
        self.xys[index].x_combo.clear()
        self.xys[index].x_combo.addItems(['t'])
        group_name = text.split('.')[0]
        if group_name in self.read_thread.content:
            if 'timestamp' in self.read_thread.content[group_name].data:
                self.xys[index].x_combo.addItems(['timestamp'])

        ax = self.axs[index]
        if self.xys[index].x_combo.count() == 1 or current_x_index == 0:
            logging.info('Fig.' + str(index+1) + ' : ' + text + ' ' + 't')
            self.drawdata(ax, self.read_thread.data[text], str(index + 1) + ' : ' + text, False)
        else:
            logging.info('Fig.' + str(index+1) + ' : ' + text + ' ' + 'timestamp')
            org_t = self.read_thread.data[group_name + '.timestamp'][0]
            t = []
            dt = [timedelta(seconds = (tmp_t/1e9 - org_t[0]/1e9)) for tmp_t in org_t]
            t = [self.read_thread.data[text][1][0] + tmp for tmp in dt]
            self.drawdata(ax, (self.read_thread.data[text][0], t), str(index + 1) + ' : ' + text, False)


    def xcombo_onActivated(self):
        curcombo = self.sender()
        index = 0
        for (ind, xy) in enumerate(self.xys):
            if xy.x_combo == curcombo:
                index = ind
                break; 
        text = curcombo.currentText()
        ax = self.axs[index]
        y_label = self.xys[index].y_combo.currentText()
        logging.info('Fig.' + str(index+1) + ' : ' + y_label + ' ' + text)
        if text == 't':
            self.drawdata(ax, self.read_thread.data[y_label], str(index + 1) + ' : ' + y_label, False)
        elif text == 'timestamp':
            group_name = y_label.split('.')[0]
            org_t = self.read_thread.data[group_name + '.timestamp'][0]
            t = []
            dt = [timedelta(seconds = (tmp_t/1e9 - org_t[0]/1e9)) for tmp_t in org_t]
            t = [self.read_thread.data[y_label][1][0] + tmp for tmp in dt]
            self.drawdata(ax, (self.read_thread.data[y_label][0], t), str(index + 1) + ' : ' + y_label, False)


    def fignum_changed(self,action):
        new_fig_num = int(action.text())
        logging.info('fignum_changed to '+str(new_fig_num))
        xmin, xmax = self.axs[0].get_xlim()
        for ax in self.axs:
            self.static_canvas.figure.delaxes(ax)

        self.static_canvas.figure.subplots_adjust(left = 0.2/new_fig_num, right = 0.99, bottom = 0.05, top = 0.99, hspace = 0.1)
        self.static_canvas.figure.set_figheight(new_fig_num*self.fig_height)
        self.axs= self.static_canvas.figure.subplots(new_fig_num, 1, sharex = True)
        self.static_canvas.figure.canvas.draw()
        self.scroll.setWidgetResizable(True)
        for i in range(0, self.xy_hbox.count()): 
            self.xy_hbox.itemAt(i).widget().deleteLater()
        combo_y_ind = [] 
        combo_x_ind = [] 
        for xy in self.xys:
            combo_y_ind.append(xy.y_combo.currentIndex())
            combo_x_ind.append(xy.x_combo.currentIndex())
        self.xys = []
        for i in range(0,new_fig_num):
            selection = XYSelection(i+1)
            selection.y_combo.activated.connect(self.ycombo_onActivated)
            selection.x_combo.activated.connect(self.xcombo_onActivated)
            self.xys.append(selection)
            self.xy_hbox.addWidget(selection.groupBox)
        if self.finishReadFlag:
            if self.read_thread.filenames:
                self.map_select_lines = []
                keys = list(self.read_thread.data.keys())
                count = 0
                for ax, xy in zip(self.axs, self.xys):
                    xy.y_combo.addItems(keys)
                    if count < len(combo_y_ind):
                        xy.y_combo.setCurrentIndex(combo_y_ind[count])
                    xy.x_combo.addItems(['t'])
                    group_name = xy.y_combo.currentText().split('.')[0]
                    if group_name in self.read_thread.content:
                        if 'timestamp' in self.read_thread.content[group_name].data:
                            xy.x_combo.addItems(['timestamp'])
                    if count < len(combo_x_ind):
                        xy.x_combo.setCurrentIndex(combo_x_ind[count])
                    count = count + 1
                    ax.set_xlim(xmin, xmax)
                    #TO DO
                    if xy.x_combo.currentText() == 't':
                        self.drawdata(ax, self.read_thread.data[xy.y_combo.currentText()],
                                    str(self.xys.index(xy) + 1) + ' : ' + xy.y_combo.currentText(), False)
                    elif xy.x_combo.currentText() == 'timestamp':
                        org_t = self.read_thread.data[group_name + '.timestamp'][0]
                        t = []
                        dt = [timedelta(seconds = (tmp_t/1e9 - org_t[0]/1e9))-org_t[0] for tmp_t in org_t]
                        t = [self.read_thread.data[xy.y_combo.currentText()][1][0] + tmp for tmp in dt]
                        data = (self.read_thread.data[xy.y_combo.currentText()][0], t)
                        self.drawdata(ax, data,
                                    str(self.xys.index(xy) + 1) + ' : ' + xy.y_combo.currentText(), False)
                self.updateMapSelectLine()


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
        ind = np.where(self.axs == ax)[0][0]
        if self.map_select_lines:
            ax.add_line(self.map_select_lines[ind])
        self.static_canvas.figure.canvas.draw()

    def drawFEWN(self,ax):
        """ 绘制 Fatal, Error, Warning在坐标轴上"""
        fl, el, wl,nl = None, None, None, None
        self.lines_dict = dict()
        line_num = 0
        legend_info = []
        fnum, ernum, wnum, nnum = [], [], [], [] 
        tsnum, tfnum, tsenum = [],[], []
        tsl, tfl, tse = None, None, None
        lw = 1.5
        ap = 0.8
        for tmp in self.read_thread.taskstart.t():
            tsl = ax.axvline(tmp, linestyle = '-', color = 'b', linewidth = lw, alpha = ap)
            tsnum.append(line_num)
            line_num = line_num + 1
        if tsl:
            legend_info.append(tsl)
            legend_info.append('task start')
        for tmp in self.read_thread.taskfinish.t():
            tfl = ax.axvline(tmp, linestyle = '--', color = 'b', linewidth = lw, alpha = ap)
            tfnum.append(line_num)
            line_num = line_num + 1
        if tfl:
            legend_info.append(tfl)
            legend_info.append('task finish')
        for tmp in self.read_thread.service.t():
            tse = ax.axvline(tmp, linestyle = '-', color = 'k', linewidth = lw, alpha = ap)
            tsenum.append(line_num)
            line_num = line_num + 1
        if tse:
            legend_info.append(tse)
            legend_info.append('service')
        for tmp in self.read_thread.fatal.t():
            fl= ax.axvline(tmp, linestyle='-',color = 'm', linewidth = lw, alpha = ap)
            fnum.append(line_num)
            line_num = line_num + 1
        if fl:
            legend_info.append(fl)
            legend_info.append('fatal')
        for tmp in self.read_thread.err.t():
            el= ax.axvline(tmp, linestyle = '-.', color='r', linewidth = lw, alpha = ap)
            ernum.append(line_num)
            line_num = line_num + 1
        if el:
            legend_info.append(el)
            legend_info.append('error')
        for tmp in self.read_thread.war.t():
            wl = ax.axvline(tmp, linestyle = '--', color = 'y', linewidth = lw, alpha = ap)
            wnum.append(line_num)
            line_num = line_num + 1
        if wl:
            legend_info.append(wl)
            legend_info.append('warning')
        for tmp in self.read_thread.notice.t():
            nl = ax.axvline(tmp, linestyle = ':', color = 'g', linewidth = lw, alpha = ap)
            nnum.append(line_num)
            line_num = line_num + 1
        if nl:
            legend_info.append(nl)
            legend_info.append('notice')
        if legend_info:
            ax.legend(legend_info[0::2], legend_info[1::2], loc='upper right')
        self.lines_dict['fatal'] = fnum
        self.lines_dict['error'] = ernum
        self.lines_dict['warning'] = wnum
        self.lines_dict['notice'] = nnum
        self.lines_dict['taskstart'] = tsnum
        self.lines_dict['taskfinish'] = tfnum
        self.lines_dict['service'] = tsenum
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
        for n in tsenum:
            lines[n].set_visible(self.check_service.isChecked())
        
    def updateCheckInfoLine(self,key):
        for ax in self.axs:
            lines = ax.get_lines()
            for num in self.lines_dict[key]:
                vis = not lines[num].get_visible()
                lines[num].set_visible(vis)
        self.static_canvas.figure.canvas.draw()


    def changeCheckBox(self):
        if self.check_err.isChecked() and self.check_fatal.isChecked() and self.check_notice.isChecked() and \
        self.check_war.isChecked() and self.check_tstart.isChecked() and self.check_tfinish.isChecked() and \
        self.check_service.isChecked():
            self.check_all.setCheckState(QtCore.Qt.Checked)
        elif self.check_err.isChecked() or self.check_fatal.isChecked() or self.check_notice.isChecked() or \
        self.check_war.isChecked() or self.check_tstart.isChecked() and self.check_tfinish.isChecked() or \
        self.check_service.isChecked():
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
        elif cur_check is self.check_service:
            self.updateCheckInfoLine('service')

    def changeCheckBoxAll(self):
        if self.check_all.checkState() == QtCore.Qt.Checked:
            self.check_fatal.setChecked(True)
            self.check_err.setChecked(True)
            self.check_war.setChecked(True)
            self.check_notice.setChecked(True)
            self.check_tstart.setChecked(True)
            self.check_tfinish.setChecked(True)
            self.check_service.setChecked(True)
        elif self.check_all.checkState() == QtCore.Qt.Unchecked:
            self.check_fatal.setChecked(False)
            self.check_err.setChecked(False)
            self.check_war.setChecked(False)
            self.check_notice.setChecked(False)
            self.check_tstart.setChecked(False)
            self.check_tfinish.setChecked(False)
            self.check_service.setChecked(False)

    def openMap(self, checked):
        if checked:
            if not self.map_widget:
                self.map_widget = MapWidget()
                self.map_widget.hiddened.connect(self.mapClosed)
                self.map_widget.keyPressEvent = self.keyPressEvent
            self.map_widget.show()
            (xmin,xmax) = self.axs[0].get_xlim()
            tmid = (xmin+xmax)/2.0 
            if len(self.map_select_lines) < 1:
                for ax in self.axs:
                    wl = ax.axvline(tmid, color = 'c', linewidth = 10, alpha = 0.5, picker = 10)
                    self.map_select_lines.append(wl) 
            else:
                for ln in self.map_select_lines:
                    ln.set_visible(True)
                    ln.set_xdata([tmid, tmid])
            mouse_time = tmid * 86400 - 62135712000
            if mouse_time > 1e6:
                mouse_time = datetime.fromtimestamp(mouse_time)
                self.updateMap(mouse_time)
            if 'LocationEachFrame' in self.read_thread.content:
                if len(self.read_thread.content['LocationEachFrame']['x']) > 0 :
                    self.map_widget.readtrajectory(self.read_thread.content['LocationEachFrame']['x'], self.read_thread.content['LocationEachFrame']['y'])
                else :
                    if 'Location' in self.read_thread.content:
                        self.map_widget.readtrajectory(self.read_thread.content['Location']['x'], self.read_thread.content['Location']['y'])

        else:
            if self.map_widget:
                self.map_widget.hide()
                for ln in self.map_select_lines:
                    ln.set_visible(False)
        self.static_canvas.figure.canvas.draw()

    def updateMapSelectLine(self):
        if self.map_action.isChecked():
            logging.debug('map_select_lines.size = ' + str(len(self.map_select_lines)))
            (xmin,xmax) = self.axs[0].get_xlim()
            if self.map_select_lines:
                self.map_select_lines = []
            tmid = (xmin+xmax)/2.0 
            for ax in self.axs:
                wl = ax.axvline(tmid, color = 'c', linewidth = 10, alpha = 0.5, picker = 10)
                self.map_select_lines.append(wl) 
            self.static_canvas.figure.canvas.draw()


    
    def mapClosed(self,info):
        self.map_widget.hide()
        for ln in self.map_select_lines:
            ln.set_visible(False)
        self.map_action.setChecked(False)
        self.openMap(False)
    
    def closeEvent(self, event):
        if self.map_widget:
            self.map_widget.close()
        self.close()


if __name__ == "__main__":
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    
    if not os.path.exists('log'):
        os.mkdir('log')
    log_name = "log\\loggui_" + str(ts).replace(':','-').replace(' ','_') + ".log"
    logging.basicConfig(filename = log_name,format='[%(asctime)s][%(levelname)s][%(filename)s:%(lineno)d][%(funcName)s] %(message)s', level=logging.DEBUG)

    def excepthook(type_, value, traceback_):
        # Print the error and traceback
        logging.error(traceback.format_exception(type_, value, traceback_))
        QtCore.qFatal('')
    sys.excepthook = excepthook

    try:
        qapp = QtWidgets.QApplication(sys.argv)
        app = ApplicationWindow()
        app.show()
        sys.exit(qapp.exec_())
    except:
        logging.error(traceback.format_exc())

