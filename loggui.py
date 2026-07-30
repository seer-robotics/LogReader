import matplotlib
from enum import Enum
from TargetPrecision import TargetPrecision
matplotlib.use('Qt5Agg')
matplotlib.rcParams['font.sans-serif']=['FangSong']
matplotlib.rcParams['axes.unicode_minus'] = False
from matplotlib.backends.backend_qt5agg import (
    FigureCanvas, NavigationToolbar2QT as NavigationToolbar)
from PyQt5 import QtCore, QtWidgets,QtGui
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib import pyplot as plt
from datetime import datetime
from datetime import timedelta
import os, sys
from ExtendedComboBox import ExtendedComboBox
from Widget import Widget
from ReadThread import ReadThread, Fdir2Flink
from loglibPlus import ErrorLine, WarningLine, FatalLine, NoticeLine, TaskStart, TaskFinish, Service
from loglibPlus import date2num, num2date
from MapWidget import MapWidget, Readmap, find_log_resource
from ParamWidget import ParameterWidget
from LogViewer import LogViewer
from EventViewer import EventViewer
from JsonView import JsonView, DataView
from MyToolBar import MyToolBar, RulerShapeMap
import logging
import numpy as np
import traceback
import json
from multiprocessing import freeze_support
from PyQt5.QtCore import pyqtSignal
import MotorRead as mr
from getMotorErr import MotorErrViewer 
from TargetPrecision import TargetPrecision
from eventutils import EventIndex, event_line_data
from logconfig import LogConfigError, parse_log_config_text
# from ArmPlot import Arm
import math


EVENT_LINE_STYLES = {
    'taskstart': {
        'label': 'task start', 'linestyle': '-', 'color': '#1976d2',
        'lane': (0.04, 0.065), 'alpha': 0.8, 'linewidth': 1.0},
    'taskfinish': {
        'label': 'task finish', 'linestyle': '-', 'color': '#42a5f5',
        'lane': (0.075, 0.10), 'alpha': 0.8, 'linewidth': 1.0},
    'service': {
        'label': 'service', 'linestyle': '-', 'color': '#607d8b',
        'lane': (0.01, 0.03), 'alpha': 0.35, 'linewidth': 0.8},
    'fatal': {
        'label': 'fatal', 'linestyle': '-', 'color': '#ad1457',
        'lane': (0.215, 0.245), 'alpha': 0.95, 'linewidth': 1.5},
    'error': {
        'label': 'error', 'linestyle': '-', 'color': '#d32f2f',
        'lane': (0.18, 0.205), 'alpha': 0.9, 'linewidth': 1.3},
    'warning': {
        'label': 'warning', 'linestyle': '-', 'color': '#f9a825',
        'lane': (0.145, 0.17), 'alpha': 0.9, 'linewidth': 1.2},
    'notice': {
        'label': 'notice', 'linestyle': '-', 'color': '#2e7d32',
        'lane': (0.11, 0.135), 'alpha': 0.8, 'linewidth': 1.0},
}

class MFTimeCostViewer(QtWidgets.QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("MF Time Cost Viewer")
        self.setGeometry(100, 100, 1200, 800)
        
        self.central_widget = QtWidgets.QWidget()
        self.setCentralWidget(self.central_widget)
        
        self.layout = QtWidgets.QVBoxLayout(self.central_widget)
        
        # Create figure and canvas
        self.figure = Figure(figsize=(12, 8))
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)
        
        self.layout.addWidget(self.toolbar)
        self.layout.addWidget(self.canvas)
        
    def plotMFTimeCost(self, tcost_data, time_range=None):
        """绘制MF Time Cost数据 - 堆叠条形图显示各字段时间成本
        time_range: (xmin, xmax) 时间范围，为None时显示所有数据
        """
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        
        # 检查数据有效性
        if not tcost_data or not hasattr(tcost_data, 'data'):
            ax.text(0.5, 0.5, 'No TCost data available', 
                   horizontalalignment='center', verticalalignment='center',
                   transform=ax.transAxes, fontsize=16)
            self.canvas.draw()
            return
        
        # 从loglibPlus.Data对象中提取数据字段，排除't', 'timestamp'和'total'
        data_fields = [key for key in tcost_data.data.keys() 
                      if key not in ['t', 'timestamp', 'total'] and 
                      isinstance(tcost_data.data[key], (list, np.ndarray))]
        
        if not data_fields:
            ax.text(0.5, 0.5, 'No time cost data fields found', 
                   horizontalalignment='center', verticalalignment='center',
                   transform=ax.transAxes, fontsize=16)
            self.canvas.draw()
            return
        
        # 获取时间戳数据
        timestamps = tcost_data.data.get('t', [])
        if not timestamps:
            ax.text(0.5, 0.5, 'No timestamp data available', 
                   horizontalalignment='center', verticalalignment='center',
                   transform=ax.transAxes, fontsize=16)
            self.canvas.draw()
            return
        # 处理时间范围过滤
        if time_range is not None:
            xmin, xmax = time_range
            # 将matplotlib数值时间转换为datetime
            time_min = num2date(xmin)
            time_max = num2date(xmax)
            print("time range", xmin, xmax, time_min, time_max, timestamps) 
            # 过滤时间戳范围内的数据
            valid_indices = []
            for i, ts in enumerate(timestamps):
                if time_min <= ts <= time_max:
                    valid_indices.append(i)
            print("choose_t", timestamps[valid_indices[0]])
            
            # 如果没有数据在时间范围内，显示提示
            if not valid_indices:
                ax.text(0.5, 0.5, 'No TCost data in current time range', 
                       horizontalalignment='center', verticalalignment='center',
                       transform=ax.transAxes, fontsize=16)
                self.canvas.draw()
                return
            
            # 更新为筛选后的时间戳和数据
            timestamps = [timestamps[i] for i in valid_indices]
            num_points = len(timestamps)
            
            # 准备堆叠条形图数据 - 使用筛选后的数据
            field_data = {}
            
            # 使用对比度更高的颜色映射
            high_contrast_colors = [
                '#FF0000', '#00FF00', '#0000FF', '#FFFF00', '#FF00FF', '#00FFFF',  # 红绿蓝黄品青
                '#FF8000', '#8000FF', '#00FF80', '#FF0080', '#80FF00', '#0080FF',  # 橙紫青绿粉黄青
                '#FF4000', '#4000FF', '#00FF40', '#FF0040', '#40FF00', '#0040FF',  # 更深的对比色
                '#FFC000', '#C000FF', '#00FFC0', '#FF00C0', '#C0FF00', '#00C0FF'   # 更亮的对比色
            ]
            
            # 循环使用高对比度颜色
            for i, field in enumerate(data_fields):
                values = tcost_data.data[field]
                # 处理None值，将其转换为0
                processed_values = []
                for val in values:
                    if val is None:
                        processed_values.append(0)
                    elif isinstance(val, (int, float)):
                        processed_values.append(val)
                    else:
                        processed_values.append(0)  # 处理其他非数值类型
                
                # 筛选时间范围内的数据
                filtered_values = [processed_values[i] for i in valid_indices]
                print("field", field, filtered_values)
                
                # 确保数据长度与时间戳一致
                if len(filtered_values) < num_points:
                    filtered_values = filtered_values + [0] * (num_points - len(filtered_values))
                elif len(filtered_values) > num_points:
                    filtered_values = filtered_values[:num_points]
                
                # 循环使用高对比度颜色
                color_index = i % len(high_contrast_colors)
                field_data[field] = {
                    'values': filtered_values,
                    'color': high_contrast_colors[color_index]
                }
        else:
            # 如果没有提供时间范围，使用所有数据
            num_points = len(timestamps)
            field_data = {}
            high_contrast_colors = [
                '#FF0000', '#00FF00', '#0000FF', '#FFFF00', '#FF00FF', '#00FFFF',
                '#FF8000', '#8000FF', '#00FF80', '#FF0080', '#80FF00', '#0080FF',
                '#FF4000', '#4000FF', '#00FF40', '#FF0040', '#40FF00', '#0040FF',
                '#FFC000', '#C000FF', '#00FFC0', '#FF00C0', '#C0FF00', '#00C0FF'
            ]
            
            for i, field in enumerate(data_fields):
                values = tcost_data.data[field]
                processed_values = []
                for val in values:
                    if val is None:
                        processed_values.append(0)
                    elif isinstance(val, (int, float)):
                        processed_values.append(val)
                    else:
                        processed_values.append(0)
                
                if len(processed_values) < num_points:
                    processed_values = processed_values + [0] * (num_points - len(processed_values))
                elif len(processed_values) > num_points:
                    processed_values = processed_values[:num_points]
                
                color_index = i % len(high_contrast_colors)
                field_data[field] = {
                    'values': processed_values,
                    'color': high_contrast_colors[color_index]
                }
        
        # 创建堆叠条形图
        x_positions = range(num_points)
        bottom = np.zeros(num_points)
        
        # 绘制每个字段的条形图并在色块上添加名字
        for field in data_fields:
            values = field_data[field]['values']
            bars = ax.bar(x_positions, values, 0.8, 
                        bottom=bottom, 
                        color=field_data[field]['color'], alpha=0.8)
            
            # 在每个色块上添加字段名称
            for i, bar in enumerate(bars):
                height = bar.get_height()
                if height > 0:  # 只在有高度的色块上显示名称
                    # 计算标签位置
                    x = bar.get_x() + bar.get_width() / 2
                    y = bar.get_y() + height / 2
                    
                    # 添加字段名称标签
                    ax.text(x, y, field, 
                          ha='center', va='center', 
                          fontsize=8, color='black', 
                          fontweight='bold', rotation=0)
            
            bottom += values
        
        # 设置坐标轴标签
        ax.set_xlabel('Time Index')
        ax.set_ylabel('Time Cost (ms)')
        ax.set_title('MF Time Cost Analysis by Components')
        
        # 处理时间戳显示
        if isinstance(timestamps[0], datetime):
            time_labels = [ts.strftime('%H:%M:%S') for ts in timestamps]
        else:
            time_labels = [str(i) for i in range(num_points)]
        
        # 设置x轴刻度
        if len(time_labels) > 20:
            step = max(1, len(time_labels) // 10)
            ax.set_xticks(x_positions[::step])
            ax.set_xticklabels(time_labels[::step], rotation=45, ha='right')
        else:
            ax.set_xticks(x_positions)
            ax.set_xticklabels(time_labels, rotation=45, ha='right')
        
        # 添加网格
        ax.grid(True, alpha=0.3)
        
        # 自动调整布局
        self.canvas.draw()

    # 已删除鼠标悬浮功能



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


class DataSelection(QtWidgets.QWidget):
    getdata = pyqtSignal('PyQt_PyObject')
    def __init__(self):
        super(QtWidgets.QWidget, self).__init__()
        self.groupBox = QtWidgets.QGroupBox('增加曲线')
        self.y_label = QtWidgets.QLabel('Data')
        self.y_combo = ExtendedComboBox()
        y_form = QtWidgets.QFormLayout()
        y_form.addRow(self.y_label,self.y_combo)
        self.groupBox.setLayout(y_form)

        vbox = QtWidgets.QVBoxLayout(self)
        self.btn = QtWidgets.QPushButton("Yes") 
        self.btn.clicked.connect(self.getData)
        vbox.addWidget(self.groupBox)
        vbox.addWidget(self.btn)
        self.setWindowTitle("Line Input")
        self.ax = None
    def initForm(self, ax, keys):
        self.ax = ax
        self.y_combo.clear()
        self.y_combo.addItems(keys)
    def getData(self):
        try:
            name = self.y_combo.currentText()
            self.hide()
            self.getdata.emit([self.ax, name])
        except:
            pass


class LogConfigDialog(QtWidgets.QDialog):
    def __init__(self, config_path, parent=None):
        super().__init__(parent)
        self._entries = None
        self.setWindowTitle('添加日志解释规则')
        self.resize(720, 560)

        layout = QtWidgets.QVBoxLayout(self)
        form = QtWidgets.QFormLayout()
        self.path_edit = QtWidgets.QLineEdit(os.path.abspath(config_path))
        self.path_edit.setReadOnly(True)
        self.name_edit = QtWidgets.QLineEdit()
        self.name_edit.setPlaceholderText('未填写时从 type 或 textKey 推断')
        form.addRow('目标文件', self.path_edit)
        form.addRow('配置名称', self.name_edit)
        layout.addLayout(form)

        self.json_edit = QtWidgets.QPlainTextEdit()
        self.json_edit.setLineWrapMode(QtWidgets.QPlainTextEdit.NoWrap)
        self.json_edit.setFont(QtGui.QFontDatabase.systemFont(
            QtGui.QFontDatabase.FixedFont))
        self.json_edit.setPlainText(json.dumps({
            'type': 'NewLogType',
            'content': [{
                'name': 'value',
                'type': 'double',
                'description': 'NewLogType.value',
                'unit': '',
            }],
        }, ensure_ascii=False, indent=2))
        layout.addWidget(self.json_edit, 1)

        tool_layout = QtWidgets.QHBoxLayout()
        self.load_button = QtWidgets.QPushButton('从文件载入')
        self.load_button.setIcon(self.style().standardIcon(
            QtWidgets.QStyle.SP_DialogOpenButton))
        self.load_button.clicked.connect(self.loadJsonFile)
        self.format_button = QtWidgets.QPushButton('格式化 JSON')
        self.format_button.clicked.connect(self.formatJson)
        tool_layout.addWidget(self.load_button)
        tool_layout.addWidget(self.format_button)
        tool_layout.addStretch(1)
        layout.addLayout(tool_layout)

        self.button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Save
            | QtWidgets.QDialogButtonBox.Cancel)
        self.button_box.button(
            QtWidgets.QDialogButtonBox.Save).setText('保存并添加')
        self.button_box.button(
            QtWidgets.QDialogButtonBox.Cancel).setText('取消')
        self.button_box.accepted.connect(self.validateAndAccept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

    def entries(self):
        return self._entries

    def _showJsonError(self, message):
        QtWidgets.QMessageBox.warning(self, '日志解释规则无效', message)

    def loadJsonFile(self):
        path, _selected_filter = QtWidgets.QFileDialog.getOpenFileName(
            self, '载入日志解释 JSON', '',
            'JSON Files (*.json);;All Files (*)')
        if not path:
            return
        try:
            with open(path, encoding='utf-8') as stream:
                self.json_edit.setPlainText(stream.read())
        except (OSError, UnicodeError) as exc:
            self._showJsonError(str(exc))

    def formatJson(self):
        try:
            payload = json.loads(self.json_edit.toPlainText())
        except json.JSONDecodeError as exc:
            self._showJsonError(
                '第 {} 行，第 {} 列：{}'.format(
                    exc.lineno, exc.colno, exc.msg))
            return
        self.json_edit.setPlainText(json.dumps(
            payload, ensure_ascii=False, indent=2))

    def validateAndAccept(self):
        try:
            self._entries = parse_log_config_text(
                self.json_edit.toPlainText(), self.name_edit.text())
        except LogConfigError as exc:
            self._showJsonError(str(exc))
            return
        self.accept()


class SelectEnum(Enum):
    NoSelect = 0
    Left = 1
    Right = 2
    Region = 3
    Mid = 4


# 支持的日志文件后缀
LOG_FILE_EXTS = ('.log', '.gz', '.zst')


def _collect_logs_from_dir(dir_path):
    """从目录中收集日志文件。
    优先级:
      1. 若目录下存在 d/ 子目录(新版 robokit Debug 日志),只从 d/ 中收集 *.zst/*.gz/*.log
      2. 否则若存在 log/d/ 子目录,只从 log/d/ 中收集 *.zst/*.gz/*.log
      3. 否则若存在 log/ 子目录,从 log/ 中收集 robokit_* 开头的日志(排除 kern/syslog 等)
      4. 否则直接在该目录中收集 *.log/*.gz/*.zst
    返回按文件名排序的绝对路径列表。
    """
    files = []
    if not os.path.isdir(dir_path):
        return files
    d_subdir = os.path.join(dir_path, 'd')
    log_subdir = os.path.join(dir_path, 'log')
    log_d_subdir = os.path.join(log_subdir, 'd')
    target_dir = None
    name_filter = None
    if os.path.isdir(d_subdir):
        target_dir = d_subdir
    elif os.path.isdir(log_d_subdir):
        target_dir = log_d_subdir
    elif os.path.isdir(log_subdir):
        target_dir = log_subdir
        # log/ 目录中含 kern.log/syslog 等系统日志,只挑 robokit_ 开头的
        name_filter = lambda n: n.lower().startswith('robokit_')
    else:
        target_dir = dir_path
    for name in os.listdir(target_dir):
        full = os.path.join(target_dir, name)
        if not os.path.isfile(full):
            continue
        if not name.lower().endswith(LOG_FILE_EXTS):
            continue
        if name_filter is not None and not name_filter(name):
            continue
        files.append(full.replace('\\', '/'))
    files.sort()
    return files


class SelectRegion:
    def __init__(self, ax, t0, t1, tmid) -> None:
        self.ax = ax
        self.select_region = ax.axvspan(t0, t1, facecolor='r', alpha = 0.3, picker = self.pickfunc) 
        self.select_region.set_zorder(0)
        self.left_line = ax.axvline(t0, linestyle = '--', color = 'y', linewidth = 1, picker = self.pickfunc)
        self.left_line.set_zorder(0)
        self.right_line = ax.axvline(t1, linestyle = '--', color = 'y', linewidth = 1, picker = self.pickfunc)
        self.right_line.set_zorder(0)
        self.mid_line = ax.axvline(tmid, color = 'c', linewidth = 10, alpha = 0.5, picker = self.pickfunc)
        self.mid_line.set_zorder(10)
        self.t0 = t0
        self.t1 = t1
        self.tmid = tmid
        self.select_type = SelectEnum.NoSelect
        print("init", type(self.tmid), type(self.t0), type(self.t1))

    def remove(self):
        self.select_region.remove()
        self.left_line.remove()
        self.right_line.remove()
        self.mid_line.remove()

    def getRightT(self, t):
        if isinstance(t, float):
            return t
        elif isinstance(t, datetime):
            return date2num(t)
        else:
            print("getRightT t type error: ", type(t), t)
            return t
    def setRegion(self, t0, t1):
        self.t0 = self.getRightT(t0)
        self.t1 = self.getRightT(t1)              
        self.left_line.set_xdata([self.t0])
        self.right_line.set_xdata([self.t1])
        self.select_region.remove()
        self.select_region = self.ax.axvspan(self.t0, self.t1, facecolor='r', alpha = 0.3, picker = self.pickfunc) 
        self.select_region.set_zorder(0)

    def setMidLine(self, tmid):
        self.tmid = self.getRightT(tmid)
        print("tmid", self.tmid)
        self.mid_line.set_xdata([self.tmid])

    def addAgain(self, ax):
        if ax is self.ax:
            self.ax.add_artist(self.left_line)
            self.ax.add_artist(self.right_line)
            self.ax.add_artist(self.select_region)
            self.ax.add_artist(self.mid_line)

    def getMidLineX(self):
        return self.mid_line.get_xdata()

    def pickfunc(self, artist, mouseevent):
        if artist is self.select_region or\
            artist is self.left_line or\
                artist is self.right_line or\
                    artist is self.mid_line:
            cur_t = mouseevent.xdata
            if not isinstance(cur_t, float):
                return False, dict()
            dt0 = abs(self.t0 - cur_t)
            dt1 = abs(self.t1 - cur_t)
            dtmid = abs(self.tmid -cur_t)
            ax = mouseevent.inaxes
            xmin,xmax = ax.get_xlim()
            min_step = (xmax - xmin)/40.0
            # print("pickfunc", self.t0, self.t1, self.tmid, cur_t, dt0, dt1, dtmid)
            if dtmid < min_step:
                self.select_type = SelectEnum.Mid
            elif dt0 < min_step:
                self.select_type = SelectEnum.Left
            elif dt1 < min_step:
                self.select_type = SelectEnum.Right
            elif cur_t > self.t0 and cur_t < self.t1:
                self.select_type = SelectEnum.Region
        return False, dict()

class ApplicationWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.finishReadFlag = False
        self.filenames = []
        self.event_artists = {key: {} for key in EVENT_LINE_STYLES}
        self.event_indexes = {key: EventIndex() for key in EVENT_LINE_STYLES}
        self.event_plot_data = {
            key: event_line_data([]) for key in EVENT_LINE_STYLES}
        self._updating_event_checks = False
        self.setWindowTitle('Log分析器')
        self.read_thread = ReadThread()
        self.read_thread.signal.connect(self.readFinished)
        self.mid_line_t = None #中间蓝线对应的时间 datetime
        self.select_type = SelectEnum.NoSelect #中间蓝线是否被选择上
        self.left_line_t = None #datetime
        self.right_line_t = None #datetime
        self.select_regions = []
        self.mouse_pressed = False
        self.log_widget = None
        self.event_widget = None
        self.sts_widget = None
        self.motor_view_widget = None
        self.dataViews = [] #显示特定数据框
        self.in_close = False
        self.setupUI()
        self.ts2log_t = None

    def setupUI(self):
        """初始化窗口结构""" 
        self.setGeometry(50,50,800,900)
        self.max_fig_num = 6 
        self.file_menu = QtWidgets.QMenu('&File', self)
        self.file_menu.addAction('&Open', self.openLogFilesDialog,
                                 QtCore.Qt.CTRL + QtCore.Qt.Key_O)
        self.file_menu.addAction('Open &Folder', self.openLogFolderDialog,
                                 QtCore.Qt.CTRL + QtCore.Qt.SHIFT + QtCore.Qt.Key_O)
        self.file_menu.addAction('&Quit', self.fileQuit,
                                 QtCore.Qt.CTRL + QtCore.Qt.Key_Q)
        self.menuBar().addMenu(self.file_menu)

        self.num_menu = QtWidgets.QMenu('&Num', self)
        self.menuBar().addMenu(self.num_menu)

        self.fig_menu = QtWidgets.QMenu('&Fig', self)
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
        self.num_menu.addMenu(self.fig_menu)

        self.cpu_menu = QtWidgets.QMenu('&CPU', self)
        group = QtWidgets.QActionGroup(self.cpu_menu)
        texts = [str(i) for i in range(1, 9)]
        cur_id = 3
        cur_cpu_num = int(texts[cur_id])
        self.read_thread.cpu_num = cur_cpu_num
        for text in texts:
            action = QtWidgets.QAction(text, self.cpu_menu, checkable=True, checked=text==texts[cur_id])
            self.cpu_menu.addAction(action)
            group.addAction(action)
        group.setExclusive(True)
        group.triggered.connect(self.cpunum_changed)
        self.num_menu.addMenu(self.cpu_menu)

        self.tools_menu = QtWidgets.QMenu('&Tools', self)
        self.menuBar().addMenu(self.tools_menu)
        self.map_action = QtWidgets.QAction('&Open Map', self.tools_menu, checkable = True)
        self.map_action.setShortcut(QtCore.Qt.CTRL + QtCore.Qt.Key_M)
        self.map_action.triggered.connect(self.openMap)
        self.tools_menu.addAction(self.map_action)

        self.view_action = QtWidgets.QAction('&Open Log', self.tools_menu, checkable = True)
        self.view_action.setShortcut(QtCore.Qt.CTRL + QtCore.Qt.Key_L)
        self.view_action.triggered.connect(self.openViewer)
        self.tools_menu.addAction(self.view_action)

        self.event_action = QtWidgets.QAction(
            '&Open Events', self.tools_menu, checkable=True)
        self.event_action.setShortcut(
            QtCore.Qt.CTRL + QtCore.Qt.SHIFT + QtCore.Qt.Key_E)
        self.event_action.triggered.connect(self.openEventViewer)
        self.tools_menu.addAction(self.event_action)

        self.json_action = QtWidgets.QAction('&Open Status', self.tools_menu, checkable = True)
        self.json_action.setShortcut(QtCore.Qt.CTRL + QtCore.Qt.Key_J)
        self.json_action.triggered.connect(self.openJsonView)
        self.tools_menu.addAction(self.json_action)

        self.param_action = QtWidgets.QAction('&Open Parameters', self.tools_menu,
                                               checkable=True)
        self.param_action.setShortcut(QtCore.Qt.CTRL + QtCore.Qt.Key_P)
        self.param_action.triggered.connect(self.openParameters)
        self.tools_menu.addAction(self.param_action)

        self.motor_err_action = QtWidgets.QAction('&View Motor Err', self.tools_menu, checkable = True)
        self.motor_err_action.setShortcut(QtCore.Qt.CTRL + QtCore.Qt.Key_R)
        self.motor_err_action.triggered.connect(self.viewMotorErr)
        self.tools_menu.addAction(self.motor_err_action)

        self.data_action = QtWidgets.QAction('&Open Data', self.tools_menu, checkable = True)
        self.data_action.setShortcut(QtCore.Qt.CTRL + QtCore.Qt.Key_D)
        self.data_action.setChecked(True)
        self.data_action.triggered.connect(self.openDataView)
        self.tools_menu.addAction(self.data_action)

        self.add_log_config_action = QtWidgets.QAction(
            '添加日志解释规则...', self.tools_menu)
        self.add_log_config_action.setShortcut(
            QtCore.Qt.CTRL + QtCore.Qt.SHIFT + QtCore.Qt.Key_C)
        self.add_log_config_action.setEnabled(False)
        self.add_log_config_action.triggered.connect(
            self.openLogConfigDialog)
        self.tools_menu.addAction(self.add_log_config_action)

        self.motor_follow_action = QtWidgets.QAction('&View Motor Follow Cure', self.tools_menu, checkable = True)
        self.motor_follow_action.setShortcut(QtCore.Qt.CTRL + QtCore.Qt.Key_K)
        self.motor_follow_action.triggered.connect(self.drawMotorFollow)
        self.tools_menu.addAction(self.motor_follow_action)

        self.precision = QtWidgets.QAction('&TargetPrecision', self.tools_menu, checkable = True)
        self.precision.triggered.connect(self.openPrecision)
        self.tools_menu.addAction(self.precision)


        self.arm_aciton = QtWidgets.QAction('&Arm', self.tools_menu, checkable = True)
        self.arm_aciton.triggered.connect(self.openArm)
        self.tools_menu.addAction(self.arm_aciton)

        self.mf_timecost_action = QtWidgets.QAction('&View MFTimeCost', self.tools_menu, checkable = True)
        self.mf_timecost_action.triggered.connect(self.openMFTimeCostView)
        self.tools_menu.addAction(self.mf_timecost_action)

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
        self.static_canvas_ORG_resizeEvent = self.static_canvas.resizeEvent
        self.static_canvas.resizeEvent = self.static_canvas_resizeEvent
        self.fig_widget = Widget()
        self.fig_layout = QtWidgets.QVBoxLayout(self.fig_widget)
        self.fig_layout.addWidget(self.static_canvas)
        self.scroll = QtWidgets.QScrollArea(self.fig_widget)
        self.scroll.setWidget(self.static_canvas)
        self.scroll.setWidgetResizable(True)
        self.scroll.keyPressEvent = self.keyPressEvent
        # self.scroll.keyReleaseEvent = self.keyReleaseEvent
        self.is_keypressed = False
        self.key_loc_idx = -1   # 按键盘更新mid_line时，用于记住当前定位的位置
        self.key_laser_idx = -1 # 按键盘更新时，用于记住当前激光的信息
        self.key_laser_channel = -1 # 按键盘更新时， 用于记住当前激光的信息
        # self.layout.addWidget(self.scroll)
        self.ruler = RulerShapeMap()
        self.toolBar = MyToolBar(self.static_canvas, self._main, self.ruler)
        self.toolBar.update_home_callBack(self.new_home)
        self.addToolBar(self.toolBar)
        # self.static_canvas.figure.subplots_adjust(left = 0.2/cur_fig_num, right = 0.99, bottom = 0.05, top = 0.99, hspace = 0.1)
        self.axs= self.static_canvas.figure.subplots(cur_fig_num, 1, sharex = True)
        self.axs[0].tick_params(axis='x', labeltop=True, top = True)
        for ax in self.axs:
            self.ruler.add_ruler(ax)
        #鼠标移动消息
        self.static_canvas.mpl_connect('motion_notify_event', self.mouse_move)
        self.static_canvas.mpl_connect('button_press_event', self.mouse_press)
        self.static_canvas.mpl_connect('button_release_event', self.mouse_release)
        self.static_canvas.mpl_connect('axes_leave_event', self.leave_axes)

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
        splitter2.setSizes([100,0])
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
        self.event_checkboxes = {
            'fatal': self.check_fatal,
            'error': self.check_err,
            'warning': self.check_war,
            'notice': self.check_notice,
            'taskstart': self.check_tstart,
            'taskfinish': self.check_tfinish,
            'service': self.check_service,
        }
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

        self.dataSelection = DataSelection()
        self.dataSelection.getdata.connect(self.addNewData)
        self.dataSelection.hide()

        self.map_widget = MapWidget(self)
        self.map_widget.setWindowIcon(QtGui.QIcon('rds.ico'))
        self.map_widget.hiddened.connect(self.mapClosed)
        self.map_widget.keyPressEvent = self.keyPressEvent

        self.param_widget = ParameterWidget()
        self.param_widget.setWindowIcon(QtGui.QIcon('rbk.ico'))
        self.param_widget.hiddened.connect(self.parameterViewerClosed)

        self.targetPrecision = TargetPrecision(self)
        self.targetPrecision.hide()
        self.arm = None
        # dataView相关的初始化
        self.dataViewNewOne(None)


    def getTsFromT(self, datat):
        ts = datat[0]
        t = datat[1]
        if self.ts2log_t == None:
            ind = self.getTimeStampValidInd(ts)
            if ind >= 0:
                self.ts2log_t = t[ind].timestamp() - ts[ind]/1e9
        new_t= t
        if self.ts2log_t != None:
            new_t = [datetime.fromtimestamp(tmpt/1e9 + self.ts2log_t) for tmpt in ts]
        return new_t
    def static_canvas_resizeEvent(self, event):
        self.static_canvas_ORG_resizeEvent(event)
        w = event.size().width()
        font_width = 100.0
        self.static_canvas.figure.subplots_adjust(left = (font_width/(w*1.0)), right = 0.99, bottom = 0.05, top = 0.95, hspace = 0.1)

    def _event_sources(self):
        return {
            'fatal': self.read_thread.fatal,
            'error': self.read_thread.err,
            'warning': self.read_thread.war,
            'notice': self.read_thread.notice,
            'taskstart': self.read_thread.taskstart,
            'taskfinish': self.read_thread.taskfinish,
            'service': self.read_thread.service,
        }

    def _rebuild_event_indexes(self):
        self.event_indexes = {}
        self.event_plot_data = {}
        for key, source in self._event_sources().items():
            index = EventIndex(source.t(), source.content()[0])
            self.event_indexes[key] = index
            lane_bottom, lane_top = EVENT_LINE_STYLES[key]['lane']
            self.event_plot_data[key] = event_line_data(
                index.times, lane_bottom, lane_top)

    def get_content(self, mouse_time):
        nearest = []
        for key, index in self.event_indexes.items():
            checkbox = self.event_checkboxes.get(key)
            if checkbox is not None and checkbox.isChecked() and len(index):
                nearest.append((index.nearest_distance(mouse_time), index))

        if not nearest:
            return ''
        minimum_distance = min(distance for distance, _index in nearest)
        if minimum_distance >= 10:
            return ''

        contents = []
        for distance, index in nearest:
            if abs(distance - minimum_distance) < 2e-2:
                contents.extend(index.contents_at_distance(
                    mouse_time, minimum_distance))
        return '\n'.join(contents)

    def updateMap(self):
        self.updateMapSelectLine()
        self.updateLogView()
        self.updateJsonView()
        self.updateDataViews()
        self.updateArmViews()

    def updateJsonView(self):
        if len(self.read_thread.rstatus.chassis()[1]) > 0:
            ts = np.array(self.read_thread.rstatus.chassis()[1])
            idx = (np.abs(ts - self.mid_line_t)).argmin()
            if self.sts_widget:
                j = self.getRStatusJson(idx, self.read_thread.rstatus.chassis()[0][idx])
                self.sts_widget.loadJson(j)    

    def updateSelection(self):
        self.select_type = SelectEnum.NoSelect
        if self.toolBar.isActive():
            return
        for s in self.select_regions:
            if s.select_type is not SelectEnum.NoSelect:
                self.select_type = s.select_type
                break

    def mouse_press(self, event):
        if event.inaxes and self.finishReadFlag:
            mouse_time = num2date(event.xdata)
            if event.button == 1:
                self.updateSelection()
                print("select_type:", self.select_type)
                if self.select_type is not SelectEnum.NoSelect:
                    self.mouse_pressed = True
                content = 't, '  + event.inaxes.get_ylabel() + ' : ' + str(mouse_time) + ',' +str(event.ydata)
                self.log_info.append(content)
            elif event.button == 3:
                if not self.toolBar.isActive():
                    self.popMenu = QtWidgets.QMenu(self)
                    self.popMenu.addAction('&Save All Data',lambda:self.saveAllData(event.inaxes))
                    self.popMenu.addAction('&Save View Data',lambda:self.saveViewData(event.inaxes))
                    self.popMenu.addAction('&Save Region Data',lambda:self.saveSelectData(event.inaxes))
                    self.popMenu.addAction('&Move Here',lambda:self.moveHere(event.xdata))
                    self.popMenu.addAction('&resize Region',lambda:self.resizeRegion())
                    self.popMenu.addAction('&reset Data', lambda:self.resetData(event.inaxes))
                    self.popMenu.addAction('&dData/dt', lambda:self.diffData(event.inaxes))
                    self.popMenu.addAction('&data period', lambda:self.dataPeriod(event.inaxes))
                    self.popMenu.addAction('&- Data', lambda:self.negData(event.inaxes))
                    self.popMenu.addAction('&Rad2Deg', lambda:self.rad2Deg(event.inaxes))
                    self.popMenu.addAction('&Deg2Rad', lambda:self.deg2Rad(event.inaxes))
                    self.popMenu.addAction('&Add Data', lambda:self.addData(event.inaxes))
                    self.popMenu.addAction('&Statistic', lambda:self.statistic(event.inaxes))
                    cursor = QtGui.QCursor()
                    self.popMenu.exec_(cursor.pos())
                # show info
                content = self.get_content(mouse_time)
                if content != "":
                    self.log_info.append(content[:-1])

    def mouse_move(self, event):
        if event.inaxes and self.finishReadFlag:
            mouse_time = num2date(event.xdata)
            content = self.get_content(mouse_time)
            self.info.setText(content)
            if self.mouse_pressed:
                if self.select_type == SelectEnum.Mid:
                    self.resetMidLineProperty(mouse_time)
                    self.updateMap()
                elif self.select_type == SelectEnum.Left:
                    self.setSelectLeft(mouse_time)
                elif self.select_type == SelectEnum.Right:
                    self.setSelectRight(mouse_time)
                elif self.select_type == SelectEnum.Region:
                    self.setSelectRegion(event.xdata)
        elif not self.finishReadFlag:
            self.info.setText("")

    def mouse_release(self, event):
        self.mouse_pressed = False
        self.select_type = SelectEnum.NoSelect
        for s in self.select_regions:
            s.select_type = SelectEnum.NoSelect

    def leave_axes(self, event):
        self.mouse_pressed = False
        self.select_type = SelectEnum.NoSelect
        for s in self.select_regions:
            s.select_type = SelectEnum.NoSelect

    def moveHere(self, mtime):
        mouse_time = mtime
        if type(mouse_time) is not datetime:
            mouse_time = num2date(mtime)
        self.resetMidLineProperty(mouse_time)
        self.updateMap()

    def resizeRegion(self):
        (xmin,xmax) = self.axs[0].get_xlim()
        tmid = (xmin+xmax)/2.0
        dx = xmax - xmin
        self.setSelectionLR(num2date(xmin + dx * 0.1), num2date(xmax - dx * 0.1))

    def setSelectLeft(self, t):
        if t < self.right_line_t:
            self.left_line_t = t
            for s in self.select_regions:
                s.setRegion(self.left_line_t, self.right_line_t)
            self.static_canvas.figure.canvas.draw()

    def setSelectRight(self,t):
        if t > self.left_line_t:
            self.right_line_t = t
            for s in self.select_regions:
                s.setRegion(self.left_line_t, self.right_line_t)
            self.static_canvas.figure.canvas.draw()
    
    def setSelectionLR(self, tl, tr):
        if tl < tr:
            self.left_line_t = tl
            self.right_line_t = tr
            for s in self.select_regions:
                s.setRegion(self.left_line_t, self.right_line_t)
            self.static_canvas.figure.canvas.draw()            

    def setSelectRegion(self, midx):

        lt = date2num(self.left_line_t)
        rt = date2num(self.right_line_t)
        dt = midx - (lt + rt)/2.0
        lt += dt
        rt += dt
        self.left_line_t = num2date(lt)
        self.right_line_t = num2date(rt)
        for s in self.select_regions:
            s.setRegion(lt, rt)
        self.static_canvas.figure.canvas.draw()

    def getTimeStampValidInd(self, timestamp):
        if len(timestamp) <= 0:
            return -1
        ind = 0
        for t in timestamp:
            if t > 0:
                break
            ind += 1
        return ind
    def saveAllData(self, cur_ax):
        indx = self.axs.tolist().index(cur_ax)
        # print(xmin, xmax, time0, time1)
        xy = self.xys[indx]
        group_name = xy.y_combo.currentText().split('.')[0]
        tmpdata = []

        # 获取数据
        if xy.x_combo.currentText() == 't':
            tmpdata = self.read_thread.getData(xy.y_combo.currentText())
        elif xy.x_combo.currentText() == 'timestamp':
            org_t = self.getTsFromT(self.read_thread.getData(group_name + '.timestamp'))
            tmpdata = (self.read_thread.getData(xy.y_combo.currentText())[0], org_t)
        self.savePlotData(cur_ax, tmpdata[1][0], tmpdata[1][-1])

    def saveViewData(self, cur_ax):
        indx = self.axs.tolist().index(cur_ax)
        xmin,xmax = cur_ax.get_xlim()
        time0 = num2date(xmin)
        time1 = num2date(xmax)
        self.savePlotData(cur_ax, time0, time1)

    def saveSelectData(self, cur_ax):
        self.savePlotData(cur_ax, self.left_line_t, self.right_line_t)

    def savePlotData(self, cur_ax, time0, time1):
        indx = self.axs.tolist().index(cur_ax)
        # print(xmin, xmax, time0, time1)
        xy = self.xys[indx]
        fname, _ = QtWidgets.QFileDialog.getSaveFileName(self,"选取log文件", "","CSV Files (*.csv);;PY Files (*.py)")
        subffix = os.path.splitext(fname)[1]
        isPy = subffix == ".py"
        logging.debug('Save ' + xy.y_combo.currentText() + ' and ' + xy.x_combo.currentText() + ' in ' + fname)
        group_name = xy.y_combo.currentText().split('.')[0]
        tmpdata = []

        # 获取数据
        if xy.x_combo.currentText() == 't':
            tmpdata = self.read_thread.getData(xy.y_combo.currentText())
        elif xy.x_combo.currentText() == 'timestamp':
            org_t = self.getTsFromT(self.read_thread.getData(group_name + '.timestamp'))
            tmpdata = (self.read_thread.getData(xy.y_combo.currentText())[0], org_t)        

        outdata = []
        # 对数据存之前进行处理
        if isPy:
            ind1 = (np.abs(np.array(tmpdata[1])-time0)).argmin()
            ind2 = (np.abs(np.array(tmpdata[1][ind1::])-time1)).argmin() + ind1
            x,y = [],[]
            for i in range(len(tmpdata[1])):
                if i >= ind1 and i < ind2:
                    x.append(datetime.timestamp(tmpdata[1][i]))
                    y.append(tmpdata[0][i])
            xdata = 't='+str(x)
            ydata = 'x='+str(y)
            outdata.append(xdata)
            outdata.append(ydata)
        else:
            list_tmpdata = [(t,d) for t,d in zip(tmpdata[1], tmpdata[0])]
            tmpdata[1].sort()
            ind1 = (np.abs(np.array(tmpdata[1])-time0)).argmin()
            ind2 = (np.abs(np.array(tmpdata[1][ind1::])-time1)).argmin() + ind1
            list_tmpdata.sort(key=lambda d: d[0])
            for (ind, data) in enumerate(list_tmpdata):
                if ind >= ind1 and ind <= ind2:
                    outdata.append("{},{}".format(data[0].strftime('%Y-%m-%d %H:%M:%S.%f'), data[1]))
        # 写数据
        if fname:
            try:
                with open(fname, 'w') as fn:
                    for d in outdata:
                        fn.write(d+'\n')
            except:
                pass

    def resetData(self, cur_ax):
        indx = self.axs.tolist().index(cur_ax)
        xy = self.xys[indx]        
        group_name = xy.y_combo.currentText().split('.')[0]
        org_t = self.getTsFromT(self.read_thread.getData(group_name + '.timestamp'))
        if xy.x_combo.currentText() == 'timestamp':
            if len(org_t) > 0:
                tmpdata = [self.read_thread.getData(xy.y_combo.currentText())[0], org_t]
                self.drawdata(cur_ax, tmpdata, self.read_thread.ylabel[xy.y_combo.currentText()], False)
                return
        tmpdata = self.read_thread.getData(xy.y_combo.currentText())
        self.drawdata(cur_ax, tmpdata,  self.read_thread.ylabel[xy.y_combo.currentText()], False)

    def diffData(self, cur_ax):
        indx = self.axs.tolist().index(cur_ax)
        xy = self.xys[indx]        
        group_name = xy.y_combo.currentText().split('.')[0]
        list_tmpdata = []
        org_t = self.getTsFromT(self.read_thread.getData(group_name + '.timestamp'))
        if len(org_t) > 0:
            tmpdata = (self.read_thread.getData(xy.y_combo.currentText())[0], org_t)
            list_tmpdata = [(t,d) for t,d in zip(tmpdata[1], tmpdata[0])]
        else:
            tmpdata = self.read_thread.getData(xy.y_combo.currentText())
            list_tmpdata = [(t,d) for t,d in zip(tmpdata[1], tmpdata[0])]
        if len(list_tmpdata) < 2:
            return
        list_tmpdata.sort(key=lambda d: d[0])
        dts = [(a[0]-b[0]).total_seconds() for a, b in zip(list_tmpdata[1::], list_tmpdata[0:-1])]
        dvs = [a[1]-b[1] for a, b in zip(list_tmpdata[1::], list_tmpdata[0:-1])]
        try:
            dv_dt = [a/b if abs(b) > 1e-12 else np.nan for a, b in zip(dvs, dts)]
            self.drawdata(cur_ax, (dv_dt, list_tmpdata[1::]), 'diff_'+self.read_thread.ylabel[xy.y_combo.currentText()], False)
        except ZeroDivisionError:
            pass

    def dataPeriod(self, cur_ax):
        indx = self.axs.tolist().index(cur_ax)
        xy = self.xys[indx]        
        group_name = xy.y_combo.currentText().split('.')[0]
        list_tmpdata = []
        org_t = self.getTsFromT(self.read_thread.getData(group_name + '.timestamp'))
        if len(org_t) > 0:
            tmpdata = (self.read_thread.getData(xy.y_combo.currentText())[0], org_t)
            list_tmpdata = [(t,d) for t,d in zip(tmpdata[1], tmpdata[0])]
        else:
            tmpdata = self.read_thread.getData(xy.y_combo.currentText())
            list_tmpdata = [(t,d) for t,d in zip(tmpdata[1], tmpdata[0])]
        if len(list_tmpdata) < 2:
            return
        list_tmpdata.sort(key=lambda d: d[0])
        dts = [(a[0]-b[0]).total_seconds() for a, b in zip(list_tmpdata[1::], list_tmpdata[0:-1])]
        self.drawdata(cur_ax, (dts, list_tmpdata[1::]), 'dataPeriod_'+self.read_thread.ylabel[xy.y_combo.currentText()], False)       
    
    def negData(self, cur_ax):
        indx = self.axs.tolist().index(cur_ax)
        xy = self.xys[indx]        
        group_name = xy.y_combo.currentText().split('.')[0]
        if xy.x_combo.currentText() == 'timestamp':
            org_t = self.getTsFromT(self.read_thread.getData(group_name + '.timestamp'))
            if len(org_t) > 0:
                tmpdata = [self.read_thread.getData(xy.y_combo.currentText())[0], org_t]
                tmpdata[0] = [-a for a in tmpdata[0]]
                self.drawdata(cur_ax, (tmpdata[0], tmpdata[1]), '-'+self.read_thread.ylabel[xy.y_combo.currentText()], False)
                return
        tmpdata = self.read_thread.getData(xy.y_combo.currentText())
        data = []
        for a in tmpdata[0]:
            if isinstance(a, int) or isinstance(a, float):
                data.append(-a)
        self.drawdata(cur_ax, (data, tmpdata[1]), '-'+self.read_thread.ylabel[xy.y_combo.currentText()], False)

    def rad2Deg(self, cur_ax):
        indx = self.axs.tolist().index(cur_ax)
        xy = self.xys[indx]        
        group_name = xy.y_combo.currentText().split('.')[0]
        if xy.x_combo.currentText() == 'timestamp':
            org_t = self.getTsFromT(self.read_thread.getData(group_name + '.timestamp'))
            if len(org_t) > 0:
                tmpdata = [self.read_thread.getData(xy.y_combo.currentText())[0], org_t]
                tmpdata[0] = [a/np.pi*180.0 for a in tmpdata[0]]
                self.drawdata(cur_ax, (tmpdata[0], tmpdata[1]), self.read_thread.ylabel[xy.y_combo.currentText()]+" deg", False)
                return
        tmpdata = self.read_thread.getData(xy.y_combo.currentText())
        data = [a/np.pi*180.0 if a != None else None for a in tmpdata[0]]
        self.drawdata(cur_ax, (data, tmpdata[1]), self.read_thread.ylabel[xy.y_combo.currentText()]+" deg", False)

    def deg2Rad(self, cur_ax):
        indx = self.axs.tolist().index(cur_ax)
        xy = self.xys[indx]        
        group_name = xy.y_combo.currentText().split('.')[0]
        if xy.x_combo.currentText() == 'timestamp':
            org_t = self.getTsFromT(self.read_thread.getData(group_name + '.timestamp'))
            if len(org_t) > 0:
                tmpdata = [self.read_thread.getData(xy.y_combo.currentText())[0], org_t]
                tmpdata[0] = [a/180.0*np.pi for a in tmpdata[0]]
                self.drawdata(cur_ax, (tmpdata[0], tmpdata[1]), self.read_thread.ylabel[xy.y_combo.currentText()]+" rad", False)
                return
        tmpdata = self.read_thread.getData(xy.y_combo.currentText())
        data = []
        for a in tmpdata[0]:
            if isinstance(a, float) == True:
                data.append(a/180.0*np.pi)
            else:
                data.append(a)
        self.drawdata(cur_ax, (data, tmpdata[1]), self.read_thread.ylabel[xy.y_combo.currentText()]+" rad", False)

    def addData(self, cur_ax):
        keys = list(self.read_thread.data.keys())
        self.dataSelection.initForm(cur_ax, keys)
        self.dataSelection.show()
    
    def statistic(self, cur_ax):
        indx = self.axs.tolist().index(cur_ax)
        xy = self.xys[indx]        
        lines = cur_ax.get_lines()
        wanted_line = None
        for line in lines:
            if line.get_label() == "data":
                wanted_line = line
                break
        print("wanted_line", wanted_line)
        if wanted_line == None:
            tmpdata = self.read_thread.getData(xy.y_combo.currentText())
        else:
            tmpdata =(wanted_line.get_ydata(), wanted_line.get_xdata())
        l_indx = None
        r_indx = None
        if self.left_line_t != None:
            l_indx = (np.abs(np.array(tmpdata[1])-self.left_line_t)).argmin()
        if self.right_line_t != None:
            r_indx = (np.abs(np.array(tmpdata[1])-self.right_line_t)).argmin()
        datas = []
        for indx, d in enumerate(tmpdata[0]):
            if l_indx != None and indx < l_indx:
                continue
            if r_indx != None and indx > r_indx:
                continue
            if d != None:
                datas.append(d)
        max_data = max(datas)
        min_data = min(datas)
        average = 0.0
        if len(datas) > 0:
            average = sum(datas) / len(datas)
        content = "{3} average: {0:.4}, max: {1:.4}, min: {2:.4}, num: {4}".format(average, max_data, min_data, xy.y_combo.currentText(), len(datas))
        self.log_info.append(content)
        plt.figure()
        plt.hist(datas, 100, density=True)
        plt.title("Statistic from {} to {} \n {}".format(self.left_line_t, self.right_line_t, content))
        plt.show()
    
    def addNewData(self, event):
        cur_ax = event[0]
        current_text = event[1]
        current_text = current_text.replace(" ", "")
        tmpdata = None
        if current_text.count(".") == 2:
            if " + " in current_text or " - " in current_text or " * " in current_text:
                if "+" in current_text:
                    result = current_text.split("+")
                    if len(result) != 2:
                        return
                    data0 = self.read_thread.getData(result[0])
                    data1 = self.read_thread.getData(result[1])
                    if len(data0[0]) != len(data1[0]):
                        return
                    # 时间长度一样
                    tmpdata = [[],[]]
                    tmpdata[1] = data0[1] # 时间在 1 号元素中
                    for (d0, d1) in zip(data0[0], data1[0]):
                        if type(d0) is float and type(d1) is float:
                            tmpdata[0].append(d0 + d1)
                        else:
                            # print("error", type(d0),type(d1))
                            tmpdata[0].append(0)
                    print("-",len(tmpdata), len(tmpdata[0]), len(tmpdata[1]), len(data0[0]), len(data1[1]))
                elif " - " in current_text:
                    result = current_text.split("-")
                    if len(result) == 1:
                        data0 = self.read_thread.getData(result[0])
                        tmpdata = [[],[]]
                        tmpdata[1] = data0[1]
                        for d0 in data0[0]:
                            tmpdata[0].append(-d0)
                        print("-",len(tmpdata), len(tmpdata[0]), len(tmpdata[1]), len(data0[0]))
                    elif len(result) == 2:
                        data0 = self.read_thread.getData(result[0])
                        data1 = self.read_thread.getData(result[1])
                        print(len(data0[0]), len(data1[0]), result[0])
                        if result[0] == '':
                            tmpdata = [[],[]]
                            tmpdata[1] = data1[1]
                            for d0 in data1[0]:
                                tmpdata[0].append(-d0)
                        if len(data0[0]) != len(data1[0]):
                            return
                        # 时间长度一样
                        tmpdata = [[],[]]
                        tmpdata[1] = data0[1] # 时间在 1 号元素中
                        for (d0, d1) in zip(data0[0], data1[0]):
                            if type(d0) is float and type(d1) is float:
                                tmpdata[0].append(d0 - d1)
                            else:
                                # print("error", type(d0),type(d1))
                                tmpdata[0].append(0)
                        print("-",len(tmpdata), len(tmpdata[0]), len(tmpdata[1]), len(data0[0]), len(data1[1]))
                elif " * " in current_text:
                    result = current_text.split("*")
                    if len(result) != 2:
                        return
                    data0 = self.read_thread.getData(result[0])
                    data1 = self.read_thread.getData(result[1])
                    print(len(data0[0]), len(data1[0]), result[0])
                    if result[0] == '':
                        tmpdata = [[],[]]
                        tmpdata[1] = data1[1]
                        for d0 in data1[0]:
                            tmpdata[0].append(d0)
                    if len(data0[0]) != len(data1[0]):
                        return
                    # 时间长度一样
                    tmpdata = [[],[]]
                    tmpdata[1] = data0[1] # 时间在 1 号元素中
                    for (d0, d1) in zip(data0[0], data1[0]):
                        if type(d0) is float and type(d1) is float:
                            tmpdata[0].append(d0 * d1)
                        else:
                            # print("error", type(d0),type(d1))
                            tmpdata[0].append(0)
                    print("*",len(tmpdata), len(tmpdata[0]), len(tmpdata[1]), len(data0[0]), len(data1[1])) 
            else:
                tmpdata = self.read_thread.getData(current_text)       
        else :
            tmpdata = self.read_thread.getData(current_text)
        # print(len(tmpdata), len(tmpdata[0]), len(tmpdata[1]), current_text in self.read_thread.ylabel)
        if current_text in self.read_thread.ylabel:
            self.drawdata(cur_ax, tmpdata, self.read_thread.ylabel[current_text], False, False)
        else:
            self.drawdata(cur_ax, tmpdata, current_text, False, False)
        

    def keyPressEvent(self,event):
        if len(self.select_regions) < 1:
            return
        if (event.key() == QtCore.Qt.Key_A or event.key() == QtCore.Qt.Key_D
            or event.key() == QtCore.Qt.Key_Left or event.key() == QtCore.Qt.Key_Right):
            cur_t = self.select_regions[0].getMidLineX()
            if type(cur_t) is not datetime:
                cur_t = num2date(cur_t)
            if event.key() == QtCore.Qt.Key_A or event.key() == QtCore.Qt.Key_D:
                self.key_laser_idx = -1
                self.key_laser_channel = -1
                t = np.array(self.read_thread.content['LocationEachFrame']['t'])
                if self.key_loc_idx < 0:
                    self.key_loc_idx = (np.abs(t-cur_t)).argmin()
                if event.key() == QtCore.Qt.Key_A:
                    if self.key_loc_idx > 0:
                        self.key_loc_idx = self.key_loc_idx - 1
                if event.key() ==  QtCore.Qt.Key_D:
                    if self.key_loc_idx < (len(t) -1 ):
                        self.key_loc_idx = self.key_loc_idx + 1
                cur_t = t[self.key_loc_idx]
            else:
                self.key_loc_idx = -1
                if self.key_laser_idx < 0 \
                or self.key_laser_channel < 0:
                    min_laser_channel = -1
                    laser_idx = -1
                    min_dt = None
                    for index in self.read_thread.laser.datas.keys():
                        t = np.array(self.read_thread.laser.t(index))
                        if len(t) < 1:
                            continue
                        tmp_laser_idx = (np.abs(t-cur_t)).argmin()
                        tmp_dt = np.min(np.abs(t-cur_t))
                        if min_dt == None or tmp_dt < min_dt:
                            min_laser_channel = index
                            laser_idx = tmp_laser_idx
                            min_dt = tmp_dt
                    self.key_laser_idx = laser_idx
                    self.key_laser_channel = min_laser_channel
                    t = self.read_thread.laser.t(min_laser_channel)
                    cur_t = t[laser_idx]
                if event.key() == QtCore.Qt.Key_Left:
                    self.key_laser_idx = self.key_laser_idx -1
                    t = self.read_thread.laser.t(self.key_laser_channel)
                    if self.key_laser_idx < 0:
                        self.key_laser_idx = len(t) - 1
                    cur_t = t[self.key_laser_idx]
                if event.key() == QtCore.Qt.Key_Right:
                    self.key_laser_idx = self.key_laser_idx + 1
                    t = self.read_thread.laser.t(self.key_laser_channel)
                    if self.key_laser_idx >= len(t):
                        self.key_laser_idx = 0
                    cur_t = t[self.key_laser_idx]
            self.mid_line_t = cur_t
            self.updateMap()

    def openMFTimeCostView(self, checked):
        """打开MF Time Cost查看窗口"""
        if checked:
            if not hasattr(self, 'mf_timecost_widget'):
                self.mf_timecost_widget = MFTimeCostViewer(self)
                self.mf_timecost_widget.setWindowIcon(QtGui.QIcon('rbk.ico'))
            
            # 获取TCost数据和时间范围
            tcost_data = self.read_thread.content["TCost"]
            print(tcost_data)
            
            # 获取当前时间轴范围
            xmin, xmax = self.axs[0].get_xlim()
            time_range = (xmin, xmax)
            
            self.mf_timecost_widget.plotMFTimeCost(tcost_data, time_range)
            self.mf_timecost_widget.show()
        else:
            if hasattr(self, 'mf_timecost_widget') and self.mf_timecost_widget:
                self.mf_timecost_widget.hide()

    def new_home(self, *args, **kwargs):
        for ax, xy in zip(self.axs, self.xys):
            text = xy.y_combo.currentText()
            if text in self.read_thread.data:
                data = self.read_thread.getData(text)[0]
                if data:
                    if isinstance(data[0], str):
                        continue
                    tmpd = np.array(data)
                    tmpd = tmpd[~np.isnan(tmpd)]
                    if len(tmpd) > 0:
                        max_range = max(max(tmpd) - min(tmpd), 1e-6)
                        if not math.isnan(max_range) and not math.isinf(max_range):
                            ax.set_ylim(min(tmpd) - 0.05 * max_range, max(tmpd)  + 0.05 * max_range)
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
        self.filenames, _ = QtWidgets.QFileDialog.getOpenFileNames(self,"选取log文件", "","Log Files (*.log *.gz *.zst);;All Files (*)", options=options)
        if self.filenames:
            self.map_widget.hide()
            self._reloadParameterWidget()
            self.finishReadFlag = False
            self.add_log_config_action.setEnabled(False)
            self.read_thread = ReadThread()
            self.read_thread.signal.connect(self.readFinished)
            self.read_thread.filenames = self.filenames
            self.read_thread.start()
            logging.debug('Loading ' + str(len(self.filenames)) + ' Files:')
            self.log_info.append('Loading '+str(len(self.filenames)) + ' Files:')
            for (ind, f) in enumerate(self.filenames):
                logging.debug(str(ind+1)+':'+f)
                flink = Fdir2Flink(f)
                self.log_info.append(str(ind+1)+':'+flink)
            self.setWindowTitle('Loading')

    def openLogFolderDialog(self):
        """打开一个日志目录(支持从 d/ 或 log/d/ 子目录读取 robokit 调试日志)"""
        options = QtWidgets.QFileDialog.Options()
        options |= QtWidgets.QFileDialog.DontUseNativeDialog
        options |= QtCore.Qt.WindowStaysOnTopHint
        dir_path = QtWidgets.QFileDialog.getExistingDirectory(self, "选取log目录", "", options=options)
        if not dir_path:
            return
        files = _collect_logs_from_dir(dir_path)
        if not files:
            logging.warning('No log files found in {}'.format(dir_path))
            self.log_info.append('No log files (.log/.gz/.zst) found in: ' + dir_path)
            return
        self.filenames = files
        self.map_widget.hide()
        self._reloadParameterWidget()
        self.finishReadFlag = False
        self.add_log_config_action.setEnabled(False)
        self.read_thread = ReadThread()
        self.read_thread.signal.connect(self.readFinished)
        self.read_thread.filenames = self.filenames
        self.read_thread.start()
        logging.debug('Loading ' + str(len(self.filenames)) + ' Files from ' + dir_path)
        self.log_info.append('Loading ' + str(len(self.filenames)) + ' Files from: ' + dir_path)
        for (ind, f) in enumerate(self.filenames):
            logging.debug(str(ind+1)+':'+f)
            flink = Fdir2Flink(f)
            self.log_info.append(str(ind+1)+':'+flink)
        self.setWindowTitle('Loading')


    def openModelFilesDialog(self):
        options = QtWidgets.QFileDialog.Options()
        options |= QtWidgets.QFileDialog.DontUseNativeDialog
        options |= QtCore.Qt.WindowStaysOnTopHint
        self.model_name, _ = QtWidgets.QFileDialog.getOpenFileNames(self,"选取model文件", "","model Files (*.model);;All Files (*)", options=options)
        if self.model_name:
            return self.model_name[0]
        else:
            return None

    def dragFiles(self, files):
        flag_first_in = True
        for file in files:
            if os.path.exists(file):
                subffix = os.path.splitext(file)[1]
                if subffix == ".log" or subffix == ".gz" or subffix == ".zst":
                    if flag_first_in:
                        self.filenames = []
                        flag_first_in = False
                    self.filenames.append(file)
                elif os.path.splitext(file)[1] == ".json":
                    logging.debug('Update log_config.json')
                    self.read_thread.log_config = file
                elif os.path.isdir(file):
                    # 拖入目录: 自动收集其中以及 d/、log/d/ 子目录中的所有日志文件
                    if flag_first_in:
                        self.filenames = []
                        flag_first_in = False
                    self.filenames.extend(_collect_logs_from_dir(file))
                else:
                    logging.debug('fail to load {}'.format(file))
                    return
        if self.filenames:
            self.map_widget.hide()
            self._reloadParameterWidget()
            self.finishReadFlag = False
            self.add_log_config_action.setEnabled(False)
            self.read_thread = ReadThread()
            self.read_thread.signal.connect(self.readFinished)
            self.read_thread.filenames = self.filenames
            self.read_thread.start()
            logging.debug('Loading' + str(len(self.filenames)) + 'Files:')
            self.log_info.append('Loading '+str(len(self.filenames)) + ' Files:')
            for (ind, f) in enumerate(self.filenames):
                logging.debug(str(ind+1) + ':' + f)
                flink = Fdir2Flink(f)
                self.log_info.append(str(ind+1)+':'+flink)
            self.setWindowTitle('Loading')

    def readFinished(self, result):
        self.ts2log_t = None
        for tmps in self.read_thread.log:
            self.log_info.append(tmps)
        logging.debug('read Finished')
        self.log_info.append('Finished')
        self._rebuild_event_indexes()
        if self.event_widget is not None:
            self.event_widget.setEvents(self._event_sources())
        self.finishReadFlag = True
        self.add_log_config_action.setEnabled(
            self.read_thread.reader is not None)
        self.setWindowTitle('Log分析器: {0}'.format([f.split('/')[-1] for f in self.filenames]))
        if self.read_thread.filenames:
            #画图 mcl.t, mcl.x
            keys = list(self.read_thread.data.keys())
            for ax, xy in zip(self.axs, self.xys):
                last_combo_ind = xy.y_combo.currentIndex()
                xy.y_combo.clear()
                xy.y_combo.addItems(keys) 
                xy.x_combo.clear()
                xy.x_combo.addItems(['t']) 
                if last_combo_ind >= 0:
                    xy.y_combo.setCurrentIndex(last_combo_ind)
                group_name = xy.y_combo.currentText().split('.')[0]
                if group_name in self.read_thread.content:
                    if 'timestamp' in self.read_thread.content[group_name].data:
                        xy.x_combo.addItems(['timestamp'])
                self.drawdata(ax, self.read_thread.getData(xy.y_combo.currentText()),
                                self.read_thread.ylabel[xy.y_combo.currentText()], True)
            for d in self.dataViews:
                self.initDataView(d)
            self.key_laser_channel = -1
            self.key_laser_idx = -1
            self.key_loc_idx = -1
            self.resetSelect()
            self.openMap(self.map_action.isChecked())
            self.openViewer(self.view_action.isChecked())
            self.openJsonView(self.json_action.isChecked())
            self.openDataView(self.data_action.isChecked())
            self.updateMap()

    def _refreshDynamicConfigViews(self, new_series):
        for xy in self.xys:
            xy.y_combo.addItems(new_series)

        self.dataSelection.y_combo.addItems(new_series)
        group_names = list(self.read_thread.name2orgKey.keys())
        for data_view in self.dataViews:
            combo = data_view.selection.y_combo
            current_text = combo.currentText()
            combo.blockSignals(True)
            combo.clear()
            combo.addItems(group_names)
            current_index = combo.findText(current_text)
            if current_index >= 0:
                combo.setCurrentIndex(current_index)
            combo.blockSignals(False)

    def openLogConfigDialog(self):
        dialog = LogConfigDialog(self.read_thread.log_config, self)
        if dialog.exec_() != QtWidgets.QDialog.Accepted:
            return
        try:
            new_series = self.read_thread.add_log_configs(dialog.entries())
        except Exception as exc:
            logging.exception('Failed to add log config')
            QtWidgets.QMessageBox.critical(
                self, '添加日志解释规则失败', str(exc))
            return

        self._refreshDynamicConfigViews(new_series)
        message = 'Added {} config(s), {} curve field(s): {}'.format(
            len(dialog.entries()), len(new_series),
            ', '.join(dialog.entries().keys()))
        self.log_info.append(message)
        QtWidgets.QMessageBox.information(
            self, '日志解释规则已添加',
            '已添加 {} 条规则、{} 个曲线字段。'.format(
                len(dialog.entries()), len(new_series)))


    def fileQuit(self):
        self.close()

    def about(self):
        QtWidgets.QMessageBox.about(self, "关于", """Log Viewer V2.5.4.a""")

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
            self.drawdata(ax, self.read_thread.getData(text), self.read_thread.ylabel[text], False)
        else:
            logging.info('Fig.' + str(index+1) + ' : ' + text + ' ' + 'timestamp')
            org_t = self.getTsFromT(self.read_thread.getData(group_name + '.timestamp'))
            self.drawdata(ax, (self.read_thread.getData(text)[0], org_t), self.read_thread.ylabel[text], False)

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
            self.drawdata(ax, self.read_thread.getData(y_label), self.read_thread.ylabel[y_label], False)
        elif text == 'timestamp':
            group_name = y_label.split('.')[0]
            org_t = self.getTsFromT(self.read_thread.getData(group_name + '.timestamp'))
            self.drawdata(ax, (self.read_thread.getData(y_label)[0], org_t), self.read_thread.ylabel[y_label], False)

    def cpunum_changed(self, action):
        self.read_thread.cpu_num = int(action.text())

    def fignum_changed(self,action):
        new_fig_num = int(action.text())
        logging.info('fignum_changed to '+str(new_fig_num))
        xmin, xmax = self.axs[0].get_xlim()
        for ax in self.axs:
            self.static_canvas.figure.delaxes(ax)
        self.event_artists = {key: {} for key in EVENT_LINE_STYLES}

        # self.static_canvas.figure.subplots_adjust(left = 0.2/new_fig_num, right = 0.99, bottom = 0.05, top = 0.99, hspace = 0.1)
        self.static_canvas.figure.set_figheight(new_fig_num*self.fig_height)
        self.axs= self.static_canvas.figure.subplots(new_fig_num, 1, sharex = True)
        self.axs[0].tick_params(axis='x', labeltop=True, top = True)
        self.ruler.clear_rulers()
        for ax in self.axs:
            self.ruler.add_ruler(ax)
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
                        self.drawdata(ax, self.read_thread.getData(xy.y_combo.currentText()),
                                   self.read_thread.ylabel[xy.y_combo.currentText()], False)
                    elif xy.x_combo.currentText() == 'timestamp':
                        org_t = self.getTsFromT(self.read_thread.getData(group_name + '.timestamp'))
                        data = (self.read_thread.getData(xy.y_combo.currentText())[0], org_t)
                        self.drawdata(ax, data,
                                    self.read_thread.ylabel[xy.y_combo.currentText()], False)
                self.resetSelect()
        self.static_canvas.figure.canvas.draw()


    def drawdata(self, ax, data, ylabel, resize = False, replot = True):
        xmin,xmax =  ax.get_xlim()
        if replot:
            ax.cla()
            self.drawFEWN(ax)
            if data[1] and data[0]:
                ax.plot(data[1], data[0], '.', url = ylabel, label = "data")
                if isinstance(data[0][0], float) or isinstance(data[0][0], int):
                    tmpd = np.array(data[0], dtype=float)
                    tmpd = tmpd[~np.isnan(tmpd)]
                    print("len(tmpd)", len(tmpd))
                    if len(tmpd) > 0:
                        max_range = (max(tmpd) + min(tmpd))/2.0
                        if not math.isnan(max_range) and not math.isinf(max_range):
                            print("max_range:", max_range)
                            ax.set_ylim(min(tmpd) - 0.05 * max_range, max(tmpd) + 0.05 * max_range)
            if resize:
                ax.set_xlim(self.read_thread.tlist[0], self.read_thread.tlist[-1])
            else:
                ax.set_xlim(xmin, xmax)
            ax.set_ylabel(ylabel)
            ax.grid()
            ind = np.where(self.axs == ax)[0][0]
            for s in self.select_regions:
                s.addAgain(ax)
            self.ruler.add_ruler(ax)
        else:
            if data[1] and data[0]:
                lines = ax.get_lines()
                label_name = "data"
                for line in lines:
                    if line.get_label() == "data":
                        label_name = "data2"
                        break
                ax.plot(data[1], data[0], '.', url = ylabel, label = label_name)
                #用于遍历绘制的数据的特定artist
                art_list = [[],[]]
                for art in ax.get_children():
                    if art.get_url() is not None:
                        art_list[0].append(art)
                        art_list[1].append(art.get_url())
                ax.legend(art_list[0], art_list[1], loc='upper right')
        self.static_canvas.figure.canvas.draw_idle()

    def drawFEWN(self, ax):
        """Draw each event category as one compound Matplotlib artist."""
        for artists in self.event_artists.values():
            artists.pop(ax, None)

        legend_artists = []
        legend_labels = []
        for key, style in EVENT_LINE_STYLES.items():
            plot_data = self.event_plot_data.get(key)
            if plot_data is None:
                continue
            xdata, ydata = plot_data
            if len(xdata) == 0:
                continue
            artist = Line2D(
                xdata, ydata,
                transform=ax.get_xaxis_transform(),
                linestyle=style['linestyle'],
                color=style['color'],
                linewidth=style['linewidth'],
                alpha=style['alpha'],
                label=style['label'])
            artist.set_visible(self.event_checkboxes[key].isChecked())
            ax.add_line(artist)
            self.event_artists[key][ax] = artist
            legend_artists.append(artist)
            legend_labels.append(style['label'])

        if legend_artists:
            ax.legend(legend_artists, legend_labels, loc='upper right')
        
    def updateCheckInfoLine(self,key):
        visible = self.event_checkboxes[key].isChecked()
        for artist in self.event_artists[key].values():
            artist.set_visible(visible)
        self.static_canvas.figure.canvas.draw_idle()


    def changeCheckBox(self):
        if self._updating_event_checks:
            return

        checked_count = sum(
            checkbox.isChecked()
            for checkbox in self.event_checkboxes.values())
        blocker = QtCore.QSignalBlocker(self.check_all)
        if checked_count == len(self.event_checkboxes):
            self.check_all.setTristate(False)
            self.check_all.setCheckState(QtCore.Qt.Checked)
        elif checked_count:
            self.check_all.setTristate(True)
            self.check_all.setCheckState(QtCore.Qt.PartiallyChecked)
        else:
            self.check_all.setTristate(False)
            self.check_all.setCheckState(QtCore.Qt.Unchecked)
        del blocker

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
        if self._updating_event_checks:
            return
        state = self.check_all.checkState()
        if state == QtCore.Qt.PartiallyChecked:
            return

        checked = state == QtCore.Qt.Checked
        self._updating_event_checks = True
        try:
            for checkbox in self.event_checkboxes.values():
                checkbox.setChecked(checked)
        finally:
            self._updating_event_checks = False

        for key in self.event_checkboxes:
            visible = self.event_checkboxes[key].isChecked()
            for artist in self.event_artists[key].values():
                artist.set_visible(visible)
        self.static_canvas.figure.canvas.draw_idle()

    def openMap(self, checked):
        if checked:
            self.map_widget.show()
        else:
            self.map_widget.hide()
        self.static_canvas.figure.canvas.draw()

    def _reloadParameterWidget(self):
        if self.param_action.isChecked():
            self.param_widget.loadFromLogFiles(self.filenames)

    def openParameters(self, checked):
        if checked:
            self.param_widget.loadFromLogFiles(self.filenames)
            self.param_widget.show()
            self.param_widget.raise_()
            self.param_widget.activateWindow()
        else:
            self.param_widget.hide()
    
    def openArm(self, checked):
        if self.arm is None:
            return
        if checked :
            self.arm.show()
    
    def viewMotorErr(self, checked):
        if checked:
            if not self.motor_view_widget:
                self.motor_view_widget = MotorErrViewer()
                self.motor_view_widget.setWindowIcon(QtGui.QIcon('rbk.ico'))
                self.motor_view_widget.hiddened.connect(self.motorErrViewerClosed)
                self.motor_view_widget.moveHereSignal.connect(self.moveHere)
                model_name = find_log_resource(self.filenames[0], "models", "robot.model")
                if not model_name:
                    model_name = self.openModelFilesDialog()
                if model_name:
                    self.motor_view_widget.setModelPath(model_name)
            if self.read_thread.reader is not None:
                self.motor_view_widget.setLines(self.read_thread.reader.lines)
            self.motor_view_widget.listMotorErr()
            self.motor_view_widget.show()
            (xmin,xmax) = self.axs[0].get_xlim()
            tmid = (xmin+xmax)/2.0 
            # if len(self.mid_select_lines) > 1:
            #     for ln in self.mid_select_lines:
            #         ln.set_visible(True)
            #     cur_t = self.mid_select_lines[0].get_xdata()[0]
            #     if type(cur_t) is not datetime:
            #         cur_t = cur_t * 86400 - 62135712000
            #         cur_t = datetime.fromtimestamp(cur_t)
            #     self.updateMap(cur_t, self.key_loc_idx, self.key_laser_idx, self.key_laser_channel)
            # else:
            #     for ax in self.axs:
            #         wl = ax.axvline(tmid, color = 'c', linewidth = 10, alpha = 0.5, picker = 10)
            #         self.mid_select_lines.append(wl) 
            #         mouse_time = tmid * 86400 - 62135712000
            #         if mouse_time > 1e6:
            #             mouse_time = datetime.fromtimestamp(mouse_time)
            #             self.updateMap(mouse_time, -1, -1, -1)
        else:
            if self.motor_view_widget:
                self.motor_view_widget.clearPlainText()
                self.motor_view_widget.hide() 

    def openViewer(self, checked):
        if checked:
            if not self.log_widget:
                self.log_widget = LogViewer()
                self.log_widget.setWindowIcon(QtGui.QIcon('rbk.ico'))
                self.log_widget.hiddened.connect(self.viewerClosed)
                self.log_widget.moveHereSignal.connect(self.moveHere)
            if self.read_thread.reader:
                print("lines:", len(self.read_thread.reader.lines))
                self.log_widget.setLines(self.read_thread.reader.lines)
            self.log_widget.show()
            self.updateLogView()
        else:
            if self.log_widget:
                self.log_widget.hide()      

    def openEventViewer(self, checked):
        if checked:
            if self.event_widget is None:
                self.event_widget = EventViewer()
                self.event_widget.setWindowIcon(QtGui.QIcon('rbk.ico'))
                self.event_widget.hiddened.connect(self.eventViewerClosed)
                self.event_widget.moveHereSignal.connect(self.moveHere)
            self.event_widget.setEvents(self._event_sources())
            self.event_widget.show()
            self.event_widget.raise_()
            self.event_widget.activateWindow()
        elif self.event_widget is not None:
            self.event_widget.hide()
    
    def updateLogView(self):
        if self.log_widget is not None \
            and self.mid_line_t is not None \
                and self.read_thread.reader is not None:
            if self.key_loc_idx < 0 and 'LocationEachFrame' in self.read_thread.content:
                t = np.array(self.read_thread.content['LocationEachFrame']['t'])
                print("t", len(t), len(self.read_thread.content['LocationEachFrame']['t']), len(self.read_thread.content['LocationEachFrame'].data['t']))
                print(self.read_thread.content['LocationEachFrame'].data.keys())
                print(self.read_thread.getData('LocationEachFrame.t'))
                if len(t) > 0:
                    self.key_loc_idx = (np.abs(t-self.mid_line_t)).argmin()
                
            if len(self.read_thread.reader.t_and_num) > 0:
                org_t = [a[0] for a in self.read_thread.reader.t_and_num]
                t = np.array(org_t)
                idx = (np.abs(t-self.mid_line_t)).argmin()
                self.log_widget.setLineNum(self.read_thread.reader.t_and_num[idx][1])

    def openDataView(self, flag):
        if flag:
            if len(self.dataViews) < 1:
                self.dataViewNewOne(None)
        else:
            if len(self.dataViews) > 0:
                self.data_action.setChecked(True)

    def openJsonView(self, checked):
        if checked:
            if not self.sts_widget:
                self.sts_widget = JsonView()
                self.sts_widget.setWindowIcon(QtGui.QIcon('rbk.ico'))
                self.sts_widget.hiddened.connect(self.jsonViewerClosed)
                self.sts_widget.plotAction.connect(self.plotJsonAction)
            self.sts_widget.show()
            self.updateJsonView()
        else:
            if self.sts_widget:
                self.sts_widget.hide()           

    def openPrecision(self, checked):
        if checked:
            self.targetPrecision.show()
        else:
            self.targetPrecision.hide()
    # 画电机跟随曲线
    def drawMotorFollow(self, checked):
        model_name = find_log_resource(self.filenames[0], "models", "robot.model")
        if not model_name:
            model_name = self.openModelFilesDialog()
        if model_name:
            motor_name_list = mr.getMotorNames(model_name)
            motor_num = len(motor_name_list)
            num = QtWidgets.QLabel(str(motor_num))
            self.fignum_changed(num)
            name_motorinfo = mr.getNameMotorInfoDict(self.filenames[0], motor_name_list)
            name_motorcmd = mr.getNameMotorCmdDict(self.filenames[0], motor_name_list)
            name_type = mr.getMotorNameTypeDict(model_name)
            try:
                for i, name in enumerate(motor_name_list):
                    key1 = "MotorCmd." + name_motorcmd[name]
                    if name_type[name] == "steer":
                        key2 = name_motorinfo[name] + ".postion"
                    else:
                        key2 = name_motorinfo[name] + ".speed"
                    if i < self.max_fig_num:
                        self.drawdata(self.axs[i], self.read_thread.getData(key1),
                                        self.read_thread.ylabel[key1], True)
                        self.drawdata(self.axs[i], self.read_thread.getData(key2), 
                                        self.read_thread.ylabel[key2], False, False)
            except KeyError:
                self.log_info.append("Please choose the true model matched with log!!!")
            self.motor_follow_action.setChecked(False)
        else:
            self.log_info.append("Please choose the true model matched with log!!!")

    def resetMidLineProperty(self, t):
        self.mid_line_t = t
        self.key_laser_channel = -1
        self.key_laser_idx = -1
        self.key_loc_idx = -1

    def resetSelect(self):
        (xmin,xmax) = self.axs[0].get_xlim()
        tmid = (xmin+xmax)/2.0 
        for s in self.select_regions:
            s.remove()
        self.select_regions = []

        self.mid_line_t = num2date(tmid)
        for ax in self.axs:
            dx = xmax - xmin
            self.left_line_t = num2date(xmin + dx * 0.1)
            self.right_line_t = num2date(xmax - dx * 0.1)
            s = SelectRegion(ax, xmin + dx * 0.1, xmax - dx * 0.1, tmid)
            self.select_regions.append(s)

    def updateMapSelectLine(self):
        for s in self.select_regions:
            if self.mid_line_t is not None:
                s.setMidLine(self.mid_line_t)
        self.static_canvas.figure.canvas.draw()

    def mapClosed(self,info):
        self.map_widget.hide()
        self.map_action.setChecked(False)
        self.openMap(False)

    def viewerClosed(self):
        self.view_action.setChecked(False)
        self.openViewer(False)

    def eventViewerClosed(self, event):
        self.event_action.setChecked(False)
        if self.event_widget is not None:
            self.event_widget.hide()

    def jsonViewerClosed(self, event):
        self.json_action.setChecked(False)
        self.openJsonView(False)

    def parameterViewerClosed(self, event):
        self.param_action.setChecked(False)
        self.param_widget.hide()

    def motorErrViewerClosed(self):
        self.motor_err_action.setChecked(False)
        self.viewMotorErr(False)

    def closeEvent(self, event):
        self.in_close = True
        if self.map_widget:
            self.map_widget.close()
        if self.log_widget:
            self.log_widget.close()
        if self.event_widget:
            self.event_widget.close()
        if self.sts_widget:
            self.sts_widget.close()
        if self.param_widget:
            self.param_widget.close()
        if self.motor_view_widget:
            self.motor_view_widget.close()
        for d in self.dataViews:
            d.close()
        self.targetPrecision.close()
        self.close()

    def updateDataView(self, d:DataView):
        org_key = d.selection.y_combo.currentText()
        first_k = self.read_thread.name2orgKey.get(org_key, org_key)
        t = None
        print("DataView", "updateDataView",org_key, first_k)
        if first_k in self.read_thread.content:
            for name in self.read_thread.content[first_k].data.keys():
                if name != 't':
                    k = org_key+'.'+name
                    t = self.read_thread.getData(k)[1]
                    break
        if t is None or len(t) < 1:
            j = dict()
            j[first_k] = "No Valid Data"
            d.loadJson(j)
            return
        ts = np.array(t)
        idx = (np.abs(ts - self.mid_line_t)).argmin()
        j = dict()
        sum = 0
        for k in self.read_thread.content[first_k].data.keys():
            if k[0] == '_':
                continue
            data_name = k
            tmp_k = org_key+'.'+k
            if tmp_k in self.read_thread.ylabel:
                data_name = self.read_thread.ylabel[tmp_k]
                if tmp_k in data_name:
                    data_name = k
            print("data_name", data_name, first_k, k, idx, len(self.read_thread.content[first_k].data[k]), 
                                                               self.read_thread.content[first_k].data[k][idx])
            j[data_name] = self.read_thread.content[first_k].data[k][idx]
            if isinstance(j[data_name], float) and k != "total":
                sum += j[data_name]
        print("sum", sum)
        d.loadJson(j)

    def updateDataViews(self):
        for d in self.dataViews:
            self.updateDataView(d)

    def dataViewClosed(self, other):
        if not self.in_close:
            self.dataViews.remove(other)
            if len(self.dataViews) < 1:
                self.data_action.setChecked(False)
    
    def dataViewNewOne(self, other):
        dataView = DataView()
        dataView.setWindowIcon(QtGui.QIcon('rbk.ico'))
        dataView.closeMsg.connect(self.dataViewClosed)
        dataView.newOneMsg.connect(self.dataViewNewOne)
        dataView.dataViewMsg.connect(self.updateDataView)
        dataView.setGeometry(850,50,400,900)
        dataView.plotMsg.connect(self.plotDataView)
        dataView.show()
        self.initDataView(dataView)
        self.dataViews.append(dataView)  
        self.updateDataView(dataView) 

    def initDataView(self, d:DataView):
        d.setSelectionItems(list(self.read_thread.name2orgKey.keys())) 

    def plotDataView(self, event):
        print("plotDataView:", event[0], event[1], event[2])
        index = event[2]
        ax = self.axs[index]
        key1 = event[0]
        key2 = ""
        select_key = event[1][0]
        for k in self.read_thread.ylabel.keys():
            if key1 not in k:
                continue
            if self.read_thread.ylabel[k] == select_key:
                key2 = k.split(".")[1]
                break
        y_label = key1+"."+key2
        logging.info('Fig.' + str(index+1) + ' : ' + y_label)

        if self.read_thread.content[key1].isText():
            ts = []
            values = []
            datas = self.read_thread.getData(y_label)
            for k in event[1][1:]:
                y_label = y_label + "." +  k
            for (v, t) in zip (datas[0], datas[1]):
                cur_v = v
                for k in event[1][1:]:
                    if isinstance(cur_v, list) and isinstance(k, int):
                        cur_v = cur_v[k]
                    elif k in cur_v:
                        cur_v = cur_v[k]
                    else:
                        cur_v = None
                        break
                if cur_v != None:
                    ts.append(t)
                    values.append(cur_v)
            if len(values) > 0:
                print("values", values[0], len(values))
                self.drawdata(ax, (values, ts), y_label, False)
            else:
                print("no values", len(values), y_label, )
        else:
            self.xys[index].y_combo.setCurrentText(y_label)
            self.drawdata(ax, self.read_thread.getData(y_label), self.read_thread.ylabel[y_label], False)
    def getRStatusJson(self, idx, chassis):
        j = json.loads(chassis)   
        if idx < len(self.read_thread.rstatus.version()[0]) and  "ROBOKIT_VERSION_REDISTRIBUTE" in j:
            j["ROBOKIT_VERSION_REDISTRIBUTE"] = "{}.{}".format(self.read_thread.rstatus.version()[0][idx],
                                                                j["ROBOKIT_VERSION_REDISTRIBUTE"])
        if idx < len(self.read_thread.rstatus.fatalNum()[0]):
            j["fatalNums"] = self.read_thread.rstatus.fatalNum()[0][idx]
        if idx < len(self.read_thread.rstatus.fatals()[0]):
            try:
                j["fatals"] = json.loads(self.read_thread.rstatus.fatals()[0][idx])
            except:
                j["fatals"] = self.read_thread.rstatus.fatals()[0][idx]
        if idx < len(self.read_thread.rstatus.errorNum()[0]):
            j["errorNums"] = self.read_thread.rstatus.errorNum()[0][idx]
        if idx < len(self.read_thread.rstatus.errors()[0]):
            try:
                j["errors"] = json.loads(self.read_thread.rstatus.errors()[0][idx])
            except:
                j["errors"] = self.read_thread.rstatus.errors()[0][idx]
        if idx < len(self.read_thread.rstatus.warningNum()[0]):
            j["warningNum"] = self.read_thread.rstatus.warningNum()[0][idx]
        if idx < len(self.read_thread.rstatus.warnings()[0]):
            try:
                j["warnings"] = json.loads(self.read_thread.rstatus.warnings()[0][idx])
            except:
                j["warnings"] = self.read_thread.rstatus.warnings()[0][idx]
        if idx < len(self.read_thread.rstatus.noticeNum()[0]):
            j["noticeNum"] = self.read_thread.rstatus.noticeNum()[0][idx]
        if idx < len(self.read_thread.rstatus.notices()[0]):
            try:
                j["notices"] = json.loads(self.read_thread.rstatus.notices()[0][idx])
            except:
                j["notices"] = self.read_thread.rstatus.notices()[0][idx]
        return j
    
    def plotJsonAction(self, event):
        print("plotJsonAction:", event[0], event[1])
        if len(self.read_thread.rstatus.chassis()[1]) < 0:
            return
        index = event[1]
        ax = self.axs[index]
        keys = event[0]
        ts = []
        values = []
        y_label = '.'.join(k for k in keys)
        for (idx, chassis)  in enumerate(self.read_thread.rstatus.chassis()[0]):
            tmpj = self.getRStatusJson(idx, chassis)
            for key in keys:
                if tmpj != None and key in tmpj:
                    tmpj = tmpj[key]
                else:
                    tmpj = None
                    break
            if tmpj != None and \
                (isinstance(tmpj, str) or isinstance(tmpj, int) or isinstance(tmpj, float)):
                values.append(tmpj)
                ts.append(self.read_thread.rstatus.chassis()[1][idx])
        self.drawdata(ax, (values, ts), y_label, False)

    def updateArmViews(self):
        if self.arm is None:
            return
        if not self.arm.isShow():
            return
        left_q = []
        right_q = []
        def getq(key):
            cur_j0 = self.read_thread.getData(key+".cur_j0")
            ts = np.array(cur_j0[1])
            idx = (np.abs(ts - self.mid_line_t)).argmin()
            return [self.read_thread.getData(key+".cur_j0")[0][idx],
                    self.read_thread.getData(key+".cur_j1")[0][idx],
                    self.read_thread.getData(key+".cur_j2")[0][idx],
                    self.read_thread.getData(key+".cur_j3")[0][idx],
                    self.read_thread.getData(key+".cur_j4")[0][idx],
                    self.read_thread.getData(key+".cur_j5")[0][idx],
                    self.read_thread.getData(key+".cur_j6")[0][idx]]
        left_q = getq("left_hand_pose_ik_update")
        right_q = getq("right_hand_pose_ik_update")
        self.arm.plot(left_q = left_q, right_q= right_q)




if __name__ == "__main__":
    freeze_support()
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    if not os.path.exists('log'):
        os.mkdir('log')
    log_name = "log\\loggui_" + str(ts).replace(':','-').replace(' ','_') + ".log"
    logging.basicConfig(filename = log_name,format='[%(asctime)s][%(levelname)s][%(filename)s:%(lineno)d][%(funcName)s] %(message)s', level=logging.DEBUG)

    def excepthook(type_, value, traceback_):
        # Print the error and traceback
        traceback.print_exception(type_, value, traceback_) 
        logging.error(traceback.format_exception(type_, value, traceback_))
        QtCore.qFatal('')
    sys.excepthook = excepthook

    try:
        qapp = QtWidgets.QApplication(sys.argv)
        app = ApplicationWindow()
        app.setWindowIcon(QtGui.QIcon('rbk.ico'))
        app.show()
        sys.exit(qapp.exec_())
    except:
        logging.error(traceback.format_exc())


