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

def GetGlobalPos(p2b, b2g):
    x = p2b[0] * np.cos(b2g[2]) - p2b[1] * np.sin(b2g[2])
    y = p2b[0] * np.sin(b2g[2]) + p2b[1] * np.cos(b2g[2])
    x = x + b2g[0]
    y = y + b2g[1]
    return np.array([x, y])

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
        fid = open(self.map_name)
        self.js = js.load(fid)
        fid.close()
        self.head = float(self.js['chassis']['head'])
        self.tail = float(self.js['chassis']['tail'])
        self.width = float(self.js['chassis']['width'])
        laser0 = self.js['laser']['index'][0]
        self.laser = [float(laser0['x']),float(laser0['y']),np.deg2rad(float(laser0['r']))]
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
        self.points = []
        self.codes = [ 
            Path.MOVETO,
            Path.CURVE4,
            Path.CURVE4,
            Path.CURVE4,
            ]
    # run method gets called when we start the thread
    def run(self):
        fid = open(self.map_name)
        self.js = js.load(fid)
        fid.close()
        self.map_x = []
        self.map_y = []
        self.verts = []
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
                x0,y0 = line['startPos']['pos']['x'], line['startPos']['pos']['y']
                x1,y1 = line['controlPos1']['x'], line['controlPos1']['y']
                x2,y2 = line['controlPos2']['x'], line['controlPos2']['y']
                x3,y3 = line['endPos']['pos']['x'], line['endPos']['pos']['y']
                self.verts.append([(x0,y0),(x1,y1),(x2,y2),(x3,y3)])
        if 'advancedPointList' in self.js:
            for pt in self.js['advancedPointList']:
                x0 = None
                y0 = None 
                theta = None
                if 'dir' in pt:
                    x0,y0,theta = pt['pos']['x'], pt['pos']['y'], pt['dir']
                else:
                    x0,y0 = pt['pos']['x'], pt['pos']['y']
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
        self.draw_size = [] #xmin xmax ymin ymax
        self.map_data = lines.Line2D([],[], marker = '.', linestyle = '', markersize = 1.0)
        self.laser_data = lines.Line2D([],[], marker = 'o', markersize = 2.0, 
                                        linestyle = '-', linewidth = 0.1, 
                                        color='r', alpha = 0.5)
        self.robot_data = lines.Line2D([],[], linestyle = '-', color='k')
        self.robot_pos = []
        self.laser_org_data = np.array([])
        self.check_draw_flag = False
        self.fig_ratio = 1.0
        self.setAcceptDrops(True)
        self.dropped.connect(self.dragFiles)
        self.read_map = Readmap()
        self.read_map.signal.connect(self.readMapFinished)
        self.read_model = Readmodel()
        self.read_model.signal.connect(self.readModelFinished)
        self.setupUI()

    def setupUI(self):
        self.static_canvas = FigureCanvas(Figure(figsize=(5,5)))
        self.static_canvas.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
        # self.static_canvas.figure.subplots_adjust(left = 0.0, right = 1.0, bottom = 0.0, top = 1.0)
        self.static_canvas.figure.tight_layout()
        self.ax= self.static_canvas.figure.subplots(1, 1)
        self.ax.add_line(self.map_data)
        self.ax.add_line(self.robot_data)
        self.ax.add_line(self.laser_data)
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
        self.timestamp_lable = QtWidgets.QLabel(self)
        self.timestamp_lable.setText('当前时间戳(TimeStamp)')
        self.timestamp_lable.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        self.timestamp_lable.setFixedHeight(16.0)
        self.logt_lable = QtWidgets.QLabel(self)
        self.logt_lable.setText('当前Log记录时间(t)')
        self.logt_lable.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        self.logt_lable.setFixedHeight(16.0)
        self.fig_layout.addWidget(self.toolbar)
        self.fig_layout.addWidget(self.file_lable)
        self.fig_layout.addWidget(self.robot_lable)
        self.fig_layout.addWidget(self.timestamp_lable)
        self.fig_layout.addWidget(self.logt_lable)
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
        for file in files:
            if os.path.exists(file):
                if os.path.splitext(file)[1] == ".smap":
                    self.map_names.append(file)
                if os.path.splitext(file)[1] == ".model":
                    self.model_names.append(file)
        if self.map_names:
            self.read_map.map_name = self.map_names[0]
            self.setWindowTitle('MapViewer: ' + self.read_map.map_name.split('/')[-1])
            self.file_lable.hide()
            self.read_map.start()
        if self.model_names:
            self.read_model.map_name = self.model_names[0]
            self.robot_lable.setText('2. 机器人: ' + self.read_model.map_name)
            self.robot_lable.hide()
            self.read_model.start()


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
                path = Path(vert, self.read_map.codes)
                patch = patches.PathPatch(path, facecolor='none', edgecolor='orange', lw=1)
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
            laser_data = [self.read_model.laser[0], self.read_model.laser[1]]
            if not self.robot_pos:
                if len(self.draw_size) == 4:
                    xmid = (self.draw_size[0] + self.draw_size[1])/2
                    ymid = (self.draw_size[2] + self.draw_size[3])/2
                else:
                    xmid = 0.5
                    ymid = 0.5
                xdata = [tmp + xmid for tmp in xdata]
                ydata = [tmp + ymid for tmp in ydata]
                self.robot_pos = [xmid, ymid, 0.0]
            robot_shape = GetGlobalPos(robot_shape,self.robot_pos)
            xdata = robot_shape[0]
            ydata = robot_shape[1]
            self.robot_data.set_xdata(xdata)
            self.robot_data.set_ydata(ydata)
            if self.laser_org_data.any():
                laser_data = GetGlobalPos(self.laser_org_data, self.read_model.laser)
            laser_data = GetGlobalPos(laser_data, self.robot_pos)
            self.laser_data.set_xdata(laser_data[0])
            self.laser_data.set_ydata(laser_data[1])
            if len(self.draw_size) != 4:
                xmax = self.robot_pos[0] + 10
                xmin = self.robot_pos[0] - 10
                ymax = self.robot_pos[1] + 10
                ymin = self.robot_pos[1] - 10
                self.draw_size = [xmin,xmax, ymin, ymax]
                self.ax.set_xlim(xmin, xmax)
                self.ax.set_ylim(ymin, ymax)
            self.static_canvas.figure.canvas.draw()
    
    def updateRobotLaser(self, laser_org_data, robot_pos, timestamp, logt):
        self.timestamp_lable.setText('当前时间戳(timestamp): '+str(timestamp))
        self.logt_lable.setText('当前Log记录时间(t):'+str(logt))
        self.robot_pos = robot_pos
        self.laser_org_data = laser_org_data
        if self.read_model.tail and self.read_model.head and self.read_model.width:
            xdata = [-self.read_model.tail, -self.read_model.tail, self.read_model.head, self.read_model.head, -self.read_model.tail]
            ydata = [self.read_model.width/2, -self.read_model.width/2, -self.read_model.width/2, self.read_model.width/2, self.read_model.width/2]
            robot_shape = np.array([xdata, ydata])
            robot_shape = GetGlobalPos(robot_shape,robot_pos)
            self.robot_data.set_xdata(robot_shape[0])
            self.robot_data.set_ydata(robot_shape[1])
            laser_data = GetGlobalPos(laser_org_data, self.read_model.laser)
            laser_data = GetGlobalPos(laser_data,robot_pos)
            self.laser_data.set_xdata(laser_data[0])
            self.laser_data.set_ydata(laser_data[1])
            self.static_canvas.figure.canvas.draw()


if __name__ == '__main__':
    import sys
    import os
    app = QtWidgets.QApplication(sys.argv)
    form = MapWidget()
    form.show()
    app.exec_()
