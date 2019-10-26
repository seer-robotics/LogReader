import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import (
    FigureCanvas, NavigationToolbar2QT as NavigationToolbar)
from matplotlib.figure import Figure
import matplotlib.lines as lines
from matplotlib.patches import Circle, Polygon
from PyQt5 import QtGui, QtCore,QtWidgets
from PyQt5.QtCore import QThread, pyqtSignal, pyqtSlot
import numpy as np
import json as js
import os
from MyToolBar import MyToolBar, keepRatio
from matplotlib.path import Path
import matplotlib.patches as patches
from matplotlib.textpath import TextPath
import math
import logging

def GetGlobalPos(p2b, b2g):
    x = p2b[0] * np.cos(b2g[2]) - p2b[1] * np.sin(b2g[2])
    y = p2b[0] * np.sin(b2g[2]) + p2b[1] * np.cos(b2g[2])
    x = x + b2g[0]
    y = y + b2g[1]
    return np.array([x, y])

class Readcp (QThread):
    signal = pyqtSignal('PyQt_PyObject')
    def __init__(self):
        QThread.__init__(self)
        self.cp_name = ''
        self.js = dict()
        self.laser = []
    # run method gets called when we start the thread
    def run(self):
        fid = open(self.cp_name)
        self.js = js.load(fid)
        fid.close()
        self.laser = []
        self.laser = [ float(self.js['laser']['index'][0]['x']),
                       float(self.js['laser']['index'][0]['y']),
                       np.deg2rad(float(self.js['laser']['index'][0]['r']))]
        self.signal.emit(self.cp_name)

class Readmodel(QThread):
    signal = pyqtSignal('PyQt_PyObject')
    def __init__(self):
        QThread.__init__(self)
        self.model_name = ''
        self.js = dict()
        self.head = None
        self.tail = None 
        self.width = None
        self.laser = [] #x,y,r
    # run method gets called when we start the thread
    def run(self):
        fid = open(self.model_name)
        self.js = js.load(fid)
        fid.close()
        self.head = None
        self.tail = None 
        self.width = None
        self.laser = [] #x,y,r
        if 'chassis' in self.js:
            self.head = float(self.js['chassis']['head'])
            self.tail = float(self.js['chassis']['tail'])
            self.width = float(self.js['chassis']['width'])
            laser0 = self.js['laser']['index'][0]
            self.laser = [float(laser0['x']),float(laser0['y']),np.deg2rad(float(laser0['r']))]
        elif 'deviceTypes' in self.js:
            for device in self.js['deviceTypes']:
                if device['name'] == 'chassis':
                    for param in device['devices'][0]['deviceParams']:
                        if param['key'] == 'shape':
                            for childparam in param['comboParam']['childParams']:
                                if childparam['key'] == 'rectangle':
                                    if param['comboParam']['childKey'] == childparam['key']:
                                        for p in childparam['params']:
                                            if p['key'] == 'width':
                                                self.width = p['doubleValue']
                                            elif p['key'] == 'head':
                                                self.head = p['doubleValue']
                                            elif p['key'] == 'tail':
                                                self.tail = p['doubleValue']
                                elif childparam['key'] == 'circle':
                                    if param['comboParam']['childKey'] == childparam['key']:
                                        for p in childparam['params']:
                                            if p['key'] == 'radius':
                                                self.width = p['doubleValue']
                                                self.head = self.width
                                                self.tail = self.width
                elif device['name'] == 'laser':
                    x, y, r = 0, 0, 0
                    for param in device['devices'][0]['deviceParams']:
                        if param['key'] == 'basic':
                            for p in param['arrayParam']['params']:
                                if p['key'] == 'x':
                                    x = p['doubleValue']
                                elif p['key'] == 'y':
                                    y = p['doubleValue']
                                elif p['key'] == 'yaw':
                                    r = p['doubleValue']
                    self.laser = [float(x),float(y),np.deg2rad(r)]
        else:
            logging.error('Cannot Open robot.model: ' + self.model_name)
        self.signal.emit(self.model_name)

class Readmap(QThread):
    signal = pyqtSignal('PyQt_PyObject')
    def __init__(self):
        QThread.__init__(self)
        self.map_name = ''
        self.js = dict()
        self.map_x = []
        self.map_y = []
        self.verts = []
        self.circles = []
        self.points = []
        self.straights = []
        self.bezier_codes = [ 
            Path.MOVETO,
            Path.CURVE4,
            Path.CURVE4,
            Path.CURVE4,
            ]
        self.straight_codes = [
            Path.MOVETO,
            Path.LINETO ,
        ]
    # run method gets called when we start the thread
    def run(self):
        fid = open(self.map_name)
        self.js = js.load(fid)
        fid.close()
        self.map_x = []
        self.map_y = []
        self.verts = []
        self.circles = []
        self.straights = []
        self.points = []
        self.p_names = []
        # print(self.js.keys())
        for pos in self.js['normalPosList']:
            if 'x' in pos:
                self.map_x.append(float(pos['x']))
            else:
                self.map_x.append(0.0)
            if 'y' in pos:
                self.map_y.append(float(pos['y']))
            else:
                self.map_y.append(0.0)
        if 'advancedCurveList' in self.js:
            for line in self.js['advancedCurveList']:
                if line['className'] == 'BezierPath':
                    x0 = 0
                    y0 = 0
                    x1 = 0
                    y1 = 0
                    x2 = 0
                    y2 = 0
                    x3 = 0
                    y3 = 0
                    if 'x' in line['startPos']['pos']:
                        x0 = line['startPos']['pos']['x']
                    if 'y' in line['startPos']['pos']:
                        y0 = line['startPos']['pos']['y']
                    if 'x' in line['controlPos1']:
                        x1 = line['controlPos1']['x']
                    if 'y' in line['controlPos1']:
                        y1 = line['controlPos1']['y']
                    if 'x' in line['controlPos2']:
                        x2 = line['controlPos2']['x']
                    if 'y' in line['controlPos2']:
                        y2 = line['controlPos2']['y']
                    if 'x' in line['endPos']['pos']:
                        x3 = line['endPos']['pos']['x']
                    if 'y' in line['endPos']['pos']:
                        y3 = line['endPos']['pos']['y']
                    self.verts.append([(x0,y0),(x1,y1),(x2,y2),(x3,y3)])
                elif line['className'] == 'ArcPath':
                    x1 = 0
                    y1 = 0
                    x2 = 0
                    y2 = 0
                    x3 = 0
                    y3 = 0
                    if 'x' in line['startPos']['pos']:
                        x1 = line['startPos']['pos']['x']
                    if 'y' in line['startPos']['pos']:
                        y1 = line['startPos']['pos']['y']
                    if 'x' in line['controlPos1']:
                        x2 = line['controlPos1']['x']
                    if 'y' in line['controlPos1']:
                        y2 = line['controlPos1']['y']
                    if 'x' in line['endPos']['pos']:
                        x3 = line['endPos']['pos']['x']
                    if 'y' in line['endPos']['pos']:
                        y3 = line['endPos']['pos']['y']
                    A = x1*(y2-y3) - y1*(x2-x3)+x2*y3-x3*y2
                    B = (x1*x1 + y1*y1)*(y3-y2)+(x2*x2+y2*y2)*(y1-y3)+(x3*x3+y3*y3)*(y2-y1)
                    C = (x1*x1 + y1*y1)*(x2-x3)+(x2*x2+y2*y2)*(x3-x1)+(x3*x3+y3*y3)*(x1-x2)
                    D = (x1*x1 + y1*y1)*(x3*y2-x2*y3)+(x2*x2+y2*y2)*(x1*y3-x3*y1)+(x3*x3+y3*y3)*(x2*y1-x1*y2)
                    if abs(A) > 1e-12:
                        x = -B/2/A
                        y = -C/2/A
                        r = math.sqrt((B*B+C*C-4*A*D)/(4*A*A))
                        theta1 = math.atan2(y1-y,x1-x)
                        theta3 = math.atan2(y3-y,x3-x)
                        v1 = np.array([x2-x1,y2-y1])
                        v2 = np.array([x3-x2,y3-y2])
                        flag = float(np.cross(v1,v2))
                        if flag >= 0:
                            self.circles.append([x, y, r, np.rad2deg(theta1), np.rad2deg(theta3)])
                        else:
                            self.circles.append([x, y, r, np.rad2deg(theta3), np.rad2deg(theta1)])
                    else:
                        self.straights.append([(x1,y1),(x3,y3)])
                elif line['className'] == 'StraightPath':
                    x1 = 0
                    y1 = 0
                    x2 = 0
                    y2 = 0
                    if 'x' in line['startPos']['pos']:
                        x1 = line['startPos']['pos']['x']
                    if 'y' in line['startPos']['pos']:
                        y1 = line['startPos']['pos']['y']
                    if 'x' in line['endPos']['pos']:
                        x2 = line['endPos']['pos']['x']
                    if 'y' in line['endPos']['pos']:
                        y2 = line['endPos']['pos']['y']
                    self.straights.append([(x1,y1),(x2,y2)])
        if 'advancedPointList' in self.js:
            for pt in self.js['advancedPointList']:
                x0 = 0
                y0 = 0 
                theta = 0
                if 'x' in pt['pos']:
                    x0 = pt['pos']['x']
                if 'y' in pt['pos']:
                    y0 = pt['pos']['y']
                if 'dir' in pt:
                    theta = pt['dir']
                if  'ignoreDir' in pt:
                    if pt['ignoreDir'] == True:
                        theta = None
                self.points.append([x0,y0,theta])
                self.p_names.append([pt['instanceName']])
        self.signal.emit(self.map_name)


class MapWidget(QtWidgets.QWidget):
    dropped = pyqtSignal('PyQt_PyObject')
    hiddened = pyqtSignal('PyQt_PyObject')
    def __init__(self):
        super(QtWidgets.QWidget, self).__init__()
        self.setWindowTitle('MapViewer')
        self.map_names = []
        self.model_names = []
        self.cp_names = []
        self.draw_size = [] #xmin xmax ymin ymax
        self.map_data = lines.Line2D([],[], marker = '.', linestyle = '', markersize = 1.0)
        self.laser_data = lines.Line2D([],[], marker = 'o', markersize = 2.0, 
                                        linestyle = '-', linewidth = 0.1, 
                                        color='r', alpha = 0.5)
        self.robot_data = lines.Line2D([],[], linestyle = '-', color='k')
        self.robot_data_c0 = lines.Line2D([],[], linestyle = '-', linewidth = 2, color='k')
        self.robot_loc_data = lines.Line2D([],[], linestyle = '--', color='gray')
        self.robot_loc_data_c0 = lines.Line2D([],[], linestyle = '--', linewidth = 2, color='gray')
        self.obs_points = lines.Line2D([],[], linestyle = '', marker = '*', markersize = 8.0, color='k')
        self.trajectory = lines.Line2D([],[], linestyle = '', marker = 'o', markersize = 2.0, color='m')
        self.trajectory_next = lines.Line2D([],[], linestyle = '', marker = 'o', markersize = 2.0, color='mediumpurple')
        self.cur_arrow = patches.FancyArrow(0, 0, 0.2, 0,
                                            length_includes_head=True,# 增加的长度包含箭头部分
                                            head_width=0.05, head_length=0.08, fc='r', ec='b')
        self.org_arrow_xy = self.cur_arrow.get_xy().copy()

        self.robot_pos = []
        self.robot_loc_pos = []
        self.laser_pos = []
        self.laser_org_data = np.array([])
        self.check_draw_flag = False
        self.fig_ratio = 1.0
        self.setAcceptDrops(True)
        self.dropped.connect(self.dragFiles)
        self.read_map = Readmap()
        self.read_map.signal.connect(self.readMapFinished)
        self.read_model = Readmodel()
        self.read_model.signal.connect(self.readModelFinished)
        self.read_cp = Readcp()
        self.read_cp.signal.connect(self.readCPFinished)
        self.setupUI()

    def setupUI(self):
        self.static_canvas = FigureCanvas(Figure(figsize=(5,5)))
        self.static_canvas.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
        # self.static_canvas.figure.subplots_adjust(left = 0.0, right = 1.0, bottom = 0.0, top = 1.0)
        self.static_canvas.figure.tight_layout()
        self.ax= self.static_canvas.figure.subplots(1, 1)
        self.ax.add_line(self.map_data)
        self.ax.add_line(self.robot_data)
        self.ax.add_line(self.robot_data_c0)
        self.ax.add_line(self.robot_loc_data)
        self.ax.add_line(self.robot_loc_data_c0)
        self.ax.add_line(self.laser_data)
        self.ax.add_line(self.obs_points)
        self.ax.add_line(self.trajectory)
        self.ax.add_line(self.trajectory_next)
        self.ax.add_patch(self.cur_arrow)
        MyToolBar.home = self.toolbarHome
        self.toolbar = MyToolBar(self.static_canvas, self)
        self.toolbar.fig_ratio = 1
        self.fig_layout = QtWidgets.QVBoxLayout(self)
        self.file_lable = QtWidgets.QLabel(self)
        self.file_lable.setText('1. 将地图(*.smap)文件拖入窗口')
        self.file_lable.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        self.file_lable.setFixedHeight(16.0)
        self.robot_lable = QtWidgets.QLabel(self)
        self.robot_lable.setText('2. 机器人模型(*.model)文件拖入窗口')
        self.robot_lable.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        self.robot_lable.setFixedHeight(16.0)
        self.cp_lable = QtWidgets.QLabel(self)
        self.cp_lable.setText('3. (可选)机器人标定(*.cp)文件拖入窗口')
        self.cp_lable.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        self.cp_lable.setFixedHeight(16.0)
        self.timestamp_lable = QtWidgets.QLabel(self)
        self.timestamp_lable.setText('实框定位: ')
        self.timestamp_lable.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        self.timestamp_lable.setFixedHeight(16.0)
        self.logt_lable = QtWidgets.QLabel(self)
        self.logt_lable.setText('虚框定位: ')
        self.logt_lable.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        self.logt_lable.setFixedHeight(16.0)
        self.obs_lable = QtWidgets.QLabel(self)
        self.obs_lable.setText('')
        self.obs_lable.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        self.obs_lable.setFixedHeight(16.0)
        self.fig_layout.addWidget(self.toolbar)
        self.fig_layout.addWidget(self.file_lable)
        self.fig_layout.addWidget(self.robot_lable)
        self.fig_layout.addWidget(self.cp_lable)
        self.fig_layout.addWidget(self.timestamp_lable)
        self.fig_layout.addWidget(self.logt_lable)
        self.fig_layout.addWidget(self.obs_lable)
        self.fig_layout.addWidget(self.static_canvas)
        self.static_canvas.mpl_connect('resize_event', self.resize_fig)


    def closeEvent(self,event):
        self.hide()
        self.hiddened.emit(True)

    def toolbarHome(self, *args, **kwargs):
        xmin, xmax, ymin ,ymax = keepRatio(self.draw_size[0], self.draw_size[1], self.draw_size[2], self.draw_size[3], self.fig_ratio)
        self.ax.set_xlim(xmin,xmax)
        self.ax.set_ylim(ymin,ymax)
        self.static_canvas.figure.canvas.draw()

    def resize_fig(self, event):
        ratio = event.width/event.height
        self.fig_ratio = ratio
        self.toolbar.fig_ratio = ratio
        (xmin, xmax) = self.ax.get_xlim()
        (ymin, ymax) = self.ax.get_ylim()
        bigger = True
        if len(self.draw_size) == 4:
            factor = 1.5
            if not(xmin > self.draw_size[0]*factor or xmax < self.draw_size[1]*factor or ymin > self.draw_size[2]*factor or ymax < self.draw_size[3]*factor):
                bigger = False
        xmin, xmax, ymin ,ymax = keepRatio(xmin, xmax, ymin, ymax, ratio, bigger)
        self.ax.set_xlim(xmin,xmax)
        self.ax.set_ylim(ymin,ymax)
        self.static_canvas.figure.canvas.draw()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls:
            event.accept()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls:
            event.setDropAction(QtCore.Qt.CopyAction)
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        if event.mimeData().hasUrls:
            event.setDropAction(QtCore.Qt.CopyAction)
            event.accept()
            links = []
            for url in event.mimeData().urls():
                links.append(str(url.toLocalFile()))
            self.dropped.emit(links)
        else:
            event.ignore()

    def dragFiles(self,files):
        self.map_names = []
        self.model_names = []
        self.cp_names = []
        for file in files:
            if os.path.exists(file):
                if os.path.splitext(file)[1] == ".smap":
                    self.map_names.append(file)
                elif os.path.splitext(file)[1] == ".model":
                    self.model_names.append(file)
                elif os.path.splitext(file)[1] == ".cp":
                    self.cp_names.append(file)
        if self.map_names:
            self.read_map.map_name = self.map_names[0]
            self.file_lable.hide()
            self.read_map.start()
        if self.model_names:
            self.read_model.model_name = self.model_names[0]
            self.robot_lable.hide()
            self.read_model.start()
        if self.cp_names:
            self.read_cp.cp_name = self.cp_names[0]
            self.cp_lable.hide()
            self.read_cp.start()


    def readMapFinished(self, result):
        if len(self.read_map.map_x) > 0:
            self.map_data.set_xdata(self.read_map.map_x)
            self.map_data.set_ydata(self.read_map.map_y)
            self.ax.grid()
            self.ax.axis('auto')
            xmin = min(self.read_map.map_x)
            xmax = max(self.read_map.map_x)
            ymin = min(self.read_map.map_y)
            ymax = max(self.read_map.map_y)
            if xmax - xmin > ymax - ymin:
                ymax = ymin + xmax - xmin
            else:
                xmax = xmin + ymax - ymin
            self.draw_size = [xmin, xmax, ymin ,ymax]
            self.ax.set_xlim(xmin, xmax)
            self.ax.set_ylim(ymin, ymax)
            [p.remove() for p in reversed(self.ax.patches)]
            [p.remove() for p in reversed(self.ax.texts)]
            for vert in self.read_map.verts:
                path = Path(vert, self.read_map.bezier_codes)
                patch = patches.PathPatch(path, facecolor='none', edgecolor='orange', lw=1)
                self.ax.add_patch(patch)
            for circle in self.read_map.circles:
                wedge = patches.Arc([circle[0], circle[1]], circle[2]*2, circle[2]*2, 0, circle[3], circle[4], facecolor = 'none', ec="orange", lw = 1)
                self.ax.add_patch(wedge)
            for vert in self.read_map.straights:
                path = Path(vert, self.read_map.straight_codes)
                patch = patches.PathPatch(path, facecolor='none', edgecolor='orange', lw=2)
                self.ax.add_patch(patch)
            pr = 0.25
            for (pt,name) in zip(self.read_map.points, self.read_map.p_names):
                circle = patches.Circle((pt[0], pt[1]), pr, facecolor='orange',
                edgecolor=(0, 0.8, 0.8), linewidth=3, alpha=0.5)
                self.ax.add_patch(circle)
                text_path = TextPath((pt[0],pt[1]), name[0], size = 0.2)
                text_path = patches.PathPatch(text_path, ec="none", lw=3, fc="k")
                self.ax.add_patch(text_path)
                if pt[2] != None:
                    arrow = patches.Arrow(pt[0],pt[1], pr * np.cos(pt[2]), pr*np.sin(pt[2]), pr)
                    self.ax.add_patch(arrow)

            self.static_canvas.figure.canvas.draw()

    def readModelFinished(self, result):
        if self.read_model.head and self.read_model.tail and self.read_model.width:
            xdata = [-self.read_model.tail, -self.read_model.tail, self.read_model.head, self.read_model.head, -self.read_model.tail]
            ydata = [self.read_model.width/2, -self.read_model.width/2, -self.read_model.width/2, self.read_model.width/2, self.read_model.width/2]
            robot_shape = np.array([xdata, ydata])
            xxdata = [-0.05, 0.05, 0.0, 0.0, 0.0]
            xydata = [0.0, 0.0, 0.0, 0.05, -0.05]
            cross_shape = np.array([xxdata,xydata])
            self.laser_pos = self.read_model.laser
            laser_data = [self.laser_pos[0], self.laser_pos[1]]
            if not self.robot_pos:
                if len(self.draw_size) == 4:
                    xmid = (self.draw_size[0] + self.draw_size[1])/2
                    ymid = (self.draw_size[2] + self.draw_size[3])/2
                else:
                    xmid = 0.5
                    ymid = 0.5
                self.robot_pos = [xmid, ymid, 0.0]
                self.robot_loc_pos = [xmid, ymid, 0.0]
            robot_shape = GetGlobalPos(robot_shape,self.robot_pos)
            self.robot_data.set_xdata(robot_shape[0])
            self.robot_data.set_ydata(robot_shape[1])
            cross_shape = GetGlobalPos(cross_shape,self.robot_pos)
            self.robot_data_c0.set_xdata(cross_shape[0])
            self.robot_data_c0.set_ydata(cross_shape[1])
            if self.laser_org_data.any():
                laser_data = GetGlobalPos(self.laser_org_data, self.laser_pos)
            laser_data = GetGlobalPos(laser_data, self.robot_pos)
            self.laser_data.set_xdata(laser_data[0])
            self.laser_data.set_ydata(laser_data[1])

            cross_shape = np.array([xxdata,xydata])
            cross_shape = GetGlobalPos(cross_shape,self.robot_pos)
            self.robot_loc_data_c0.set_xdata(cross_shape[0])
            self.robot_loc_data_c0.set_ydata(cross_shape[1])
            robot_shape = np.array([xdata, ydata])
            robot_shape = GetGlobalPos(robot_shape,self.robot_loc_pos)
            self.robot_loc_data_c0.set_xdata([self.robot_pos[0]])
            self.robot_loc_data_c0.set_ydata([self.robot_pos[1]])

            if len(self.draw_size) != 4:
                xmax = self.robot_pos[0] + 10
                xmin = self.robot_pos[0] - 10
                ymax = self.robot_pos[1] + 10
                ymin = self.robot_pos[1] - 10
                self.draw_size = [xmin,xmax, ymin, ymax]
                self.ax.set_xlim(xmin, xmax)
                self.ax.set_ylim(ymin, ymax)
            self.static_canvas.figure.canvas.draw()
    

    

    def readCPFinished(self, result):
        if self.read_model.laser:
            if self.read_cp.laser:
                self.laser_pos[0] = self.read_model.laser[0] + self.read_cp.laser[0]
                self.laser_pos[1] = self.read_model.laser[1] + self.read_cp.laser[1]
                self.laser_pos[2] = self.read_model.laser[2] + self.read_cp.laser[2]
                laser_data = [self.laser_pos[0], self.laser_pos[1]]
                if self.laser_org_data.any():
                    laser_data = GetGlobalPos(self.laser_org_data, self.laser_pos)
                laser_data = GetGlobalPos(laser_data, self.robot_pos)
                self.laser_data.set_xdata(laser_data[0])
                self.laser_data.set_ydata(laser_data[1])
                self.static_canvas.figure.canvas.draw()

    def readtrajectory(self, x, y, xn, yn, x0, y0, r0):
        self.trajectory.set_xdata(x)
        self.trajectory.set_ydata(y)
        self.trajectory_next.set_xdata(xn)
        self.trajectory_next.set_ydata(yn)
        data = self.org_arrow_xy.copy()
        tmp_data = data.copy()
        data[:,0]= tmp_data[:,0] * np.cos(r0) - tmp_data[:,1] * np.sin(r0)
        data[:,1] = tmp_data[:,0] * np.sin(r0) + tmp_data[:,1] * np.cos(r0)
        data = data + [x0, y0]
        self.cur_arrow.set_xy(data)
        if len(self.draw_size) != 4:
                xmax = max(x) + 10 
                xmin = min(x) - 10
                ymax = max(y) + 10
                ymin = min(y) - 10
                self.draw_size = [xmin,xmax, ymin, ymax]
                self.ax.set_xlim(xmin, xmax)
                self.ax.set_ylim(ymin, ymax)

    def updateRobotLaser(self, laser_org_data, robot_pos, robot_loc_pos, laser_info, loc_info, obs_pos, obs_info):
        self.timestamp_lable.setText('实框定位: '+ laser_info)
        self.logt_lable.setText('虚框定位: '+ loc_info)
        if obs_info != '':
            self.obs_lable.setText('障碍物信息: ' + obs_info)
            self.obs_lable.show()
        else:
            self.obs_lable.setText('')
        self.robot_pos = robot_pos
        self.robot_loc_pos = robot_loc_pos
        self.laser_org_data = laser_org_data
        if self.read_model.tail and self.read_model.head and self.read_model.width:
            xdata = [-self.read_model.tail, -self.read_model.tail, self.read_model.head, self.read_model.head, -self.read_model.tail]
            ydata = [self.read_model.width/2, -self.read_model.width/2, -self.read_model.width/2, self.read_model.width/2, self.read_model.width/2]
            robot_shape = np.array([xdata, ydata])
            xxdata = [-0.05, 0.05, 0.0, 0.0, 0.0]
            xydata = [0.0, 0.0, 0.0, 0.05, -0.05]
            cross_shape = np.array([xxdata,xydata])
            robot_shape = GetGlobalPos(robot_shape,robot_pos)
            self.robot_data.set_xdata(robot_shape[0])
            self.robot_data.set_ydata(robot_shape[1])
            cross_shape = GetGlobalPos(cross_shape,self.robot_pos)
            self.robot_data_c0.set_xdata(cross_shape[0])
            self.robot_data_c0.set_ydata(cross_shape[1])

            laser_data = GetGlobalPos(laser_org_data, self.laser_pos)
            laser_data = GetGlobalPos(laser_data,robot_pos)
            self.laser_data.set_xdata(laser_data[0])
            self.laser_data.set_ydata(laser_data[1])

            cross_shape = np.array([xxdata,xydata])
            cross_shape = GetGlobalPos(cross_shape,robot_loc_pos)
            self.robot_loc_data_c0.set_xdata(cross_shape[0])
            self.robot_loc_data_c0.set_ydata(cross_shape[1])
            robot_shape = np.array([xdata, ydata])
            robot_shape = GetGlobalPos(robot_shape,robot_loc_pos)
            self.robot_loc_data.set_xdata(robot_shape[0])
            self.robot_loc_data.set_ydata(robot_shape[1])

            if obs_pos:
                self.obs_points.set_xdata([obs_pos[0]])
                self.obs_points.set_ydata([obs_pos[1]])
            else:
                self.obs_points.set_xdata([])
                self.obs_points.set_ydata([])
    def redraw(self):
        self.static_canvas.figure.canvas.draw()


if __name__ == '__main__':
    import sys
    import os
    app = QtWidgets.QApplication(sys.argv)
    form = MapWidget()
    form.show()
    app.exec_()
