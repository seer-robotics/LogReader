import sys
import re
import json
from collections import defaultdict

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QTextEdit, QPushButton, QFileDialog)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

# 导入 matplotlib 嵌合 PyQt5 的模块
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


class MplCanvas(FigureCanvas):
    """用于在 PyQt5 中嵌入 Matplotlib 图像的画布类"""
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = self.fig.add_subplot(111)
        super(MplCanvas, self).__init__(self.fig)


class LogAnalyzerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Log 资源释放分析工具")
        self.resize(1200, 800)

        # 核心数据存储
        self.id_data = {}
        self.unconfirmed_ids = []
        self.show_unconfirmed_only = False # 切换状态标识

        self.initUI()

    def initUI(self):
        # 主控组件
        main_widget = QWidget(self)
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)

        # 左侧面板：拖拽提示、文本输出、控制按钮
        left_panel = QVBoxLayout()
        
        self.drop_label = QLabel("将 log 文件拖拽到此处\n(支持多个文件)")
        self.drop_label.setAlignment(Qt.AlignCenter)
        self.drop_label.setStyleSheet("QLabel { border: 2px dashed #aaa; border-radius: 5px; background-color: #f0f0f0; padding: 20px; font-size: 14px; }")
        self.drop_label.setMinimumHeight(100)
        
        self.text_output = QTextEdit()
        self.text_output.setReadOnly(True)
        self.text_output.setFont(QFont("Consolas", 10))
        self.text_output.setPlaceholderText("解析结果将显示在这里...")

        self.toggle_btn = QPushButton("当前视图: 🌍 显示所有资源")
        self.toggle_btn.setMinimumHeight(40)
        self.toggle_btn.setStyleSheet("font-weight: bold; font-size: 14px;")
        self.toggle_btn.clicked.connect(self.toggle_view)
        self.toggle_btn.setEnabled(False) # 解析前禁用

        left_panel.addWidget(self.drop_label)
        left_panel.addWidget(self.text_output)
        left_panel.addWidget(self.toggle_btn)

        # 右侧面板：绘图区
        right_panel = QVBoxLayout()
        self.canvas = MplCanvas(self, width=6, height=6, dpi=100)
        right_panel.addWidget(self.canvas)

        # 设置布局比例 (左边4，右边6)
        main_layout.addLayout(left_panel, 4)
        main_layout.addLayout(right_panel, 6)

        # 启用拖拽功能
        self.setAcceptDrops(True)

    # ================= 拖拽事件处理 =================
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        file_paths = []
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path.endswith('.log'):
                file_paths.append(path)
        
        if file_paths:
            self.text_output.append(f"<b>接收到 {len(file_paths)} 个 log 文件，开始解析...</b>")
            self.parse_logs(file_paths)
            self.update_ui_after_parse()
        else:
            self.text_output.append("<font color='red'>未检测到有效的 .log 文件！</font>")

    # ================= 核心日志解析逻辑 =================
    def parse_logs(self, file_paths):
        self.id_data = {}
        self.unconfirmed_ids = []
        uuid_to_req_ids = defaultdict(set)

        # 第一遍：PostRes
        for file in file_paths:
            with open(file, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    if '[PostRes]' in line:
                        match = re.search(r'\[PostRes\]\[(\d+)', line)
                        if match:
                            req_id = match.group(1)
                            if req_id not in self.id_data:
                                self.id_data[req_id] = {
                                    'postres_lines': [], 'dopostrelease_lines': [],
                                    'poll_lines': [], 'uuids': set(),
                                    'confirmed': False, 'points_list': []
                                }
                            self.id_data[req_id]['postres_lines'].append(line.strip())
                            
                            json_start = line.find('[{')
                            json_end = line.rfind('}]')
                            if json_start != -1 and json_end != -1:
                                json_str = line[json_start:json_end+2]
                                try:
                                    parsed_json = json.loads(json_str)
                                    for item in parsed_json:
                                        for zone in item.get('spatialZones', []):
                                            pts = zone.get('points', [])
                                            if pts:
                                                self.id_data[req_id]['points_list'].append(pts)
                                except:
                                    pass

        # 第二遍：doPostRelease
        for file in file_paths:
            with open(file, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    if 'doPostRelease' in line:
                        uuid_match = re.search(r'\[doPostRelease\]\[uuid\|(\d+)', line)
                        if uuid_match:
                            uuid = uuid_match.group(1)
                            for req_id in self.id_data:
                                if req_id in line:
                                    self.id_data[req_id]['dopostrelease_lines'].append(line.strip())
                                    self.id_data[req_id]['uuids'].add(uuid)
                                    uuid_to_req_ids[uuid].add(req_id)

        # 第三遍：pollPendingReleases
        for file in file_paths:
            with open(file, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    if 'pollPendingReleases' in line:
                        for uuid, req_ids in uuid_to_req_ids.items():
                            if uuid in line:
                                for req_id in req_ids:
                                    self.id_data[req_id]['poll_lines'].append(line.strip())
                                    if 'release confirmed' in line:
                                        self.id_data[req_id]['confirmed'] = True

        # 分类未确认的 ID
        for req_id, info in self.id_data.items():
            if not info['confirmed']:
                self.unconfirmed_ids.append(req_id)

    # ================= 界面与绘图更新 =================
    def update_ui_after_parse(self):
        # 1. 输出文本报告
        self.text_output.clear()
        self.text_output.append("<b>解析完成！结果如下：</b><br>")
        
        for req_id, info in self.id_data.items():
            color = "green" if info['confirmed'] else "red"
            status = "已释放" if info['confirmed'] else "未释放"
            self.text_output.append(f"<font color='{color}'><b>【ID】: {req_id} ({status})</b></font>")
            
            for line in info['postres_lines']:
                self.text_output.append(f"  - {line}")
            for line in info['dopostrelease_lines']:
                self.text_output.append(f"  - {line}")
            for line in info['poll_lines']:
                self.text_output.append(f"  - {line}")
            self.text_output.append("<br>")
            
        if self.unconfirmed_ids:
            self.text_output.append(f"<font color='red'><b>总结：以下 ID 没有释放: {', '.join(self.unconfirmed_ids)}</b></font>")
        else:
            self.text_output.append("<font color='green'><b>总结：所有 ID 均已成功释放。</b></font>")

        # 2. 启用按钮并绘制图形
        self.toggle_btn.setEnabled(True)
        self.show_unconfirmed_only = False
        self.draw_plot()

    def toggle_view(self):
        """切换显示状态并重绘"""
        self.show_unconfirmed_only = not self.show_unconfirmed_only
        if self.show_unconfirmed_only:
            self.toggle_btn.setText("当前视图: 🚨 仅显示未释放的资源 (点击切换全部)")
            self.toggle_btn.setStyleSheet("font-weight: bold; font-size: 14px; color: red;")
        else:
            self.toggle_btn.setText("当前视图: 🌍 显示所有资源 (点击切换未释放)")
            self.toggle_btn.setStyleSheet("font-weight: bold; font-size: 14px; color: black;")
        self.draw_plot()

    def draw_plot(self):
        """根据当前状态在画布上绘图"""
        ax = self.canvas.axes
        ax.clear() # 清空旧图

        has_points = False
        
        # 决定要遍历的 ID 集合
        target_ids = self.unconfirmed_ids if self.show_unconfirmed_only else self.id_data.keys()

        for req_id in target_ids:
            info = self.id_data[req_id]
            is_unconfirmed = req_id in self.unconfirmed_ids

            for pts in info['points_list']:
                if not pts: continue
                has_points = True
                xs = [p['x'] for p in pts]
                ys = [p['y'] for p in pts]
                
                # 闭合多边形
                if xs[0] != xs[-1] or ys[0] != ys[-1]:
                    xs.append(xs[0])
                    ys.append(ys[0])
                
                # 设置样式：未释放为红色加粗X，正常释放为蓝色圆点
                if is_unconfirmed:
                    ax.plot(xs, ys, marker='x', markersize=6, color='red', linestyle='-', linewidth=2)
                    ax.text(xs[0], ys[0], str(req_id), color='darkred', fontsize=10, 
                            ha='right', va='bottom', weight='bold', 
                            bbox=dict(facecolor='white', alpha=0.8, edgecolor='red', pad=2))
                else:
                    ax.plot(xs, ys, marker='o', markersize=4, color='tab:blue', linestyle='-', linewidth=1.5, alpha=0.6)
                    ax.text(xs[0], ys[0], str(req_id), color='black', fontsize=9, 
                            ha='right', va='bottom', alpha=0.8,
                            bbox=dict(facecolor='white', alpha=0.6, edgecolor='none', pad=1))

        if has_points:
            title = 'Unconfirmed Spatial Zones' if self.show_unconfirmed_only else 'All Requested Spatial Zones'
            ax.set_title(title)
            ax.set_xlabel('X Coordinate')
            ax.set_ylabel('Y Coordinate')
            ax.grid(True, linestyle='--', alpha=0.6)
        else:
            ax.text(0.5, 0.5, '当前视图无有效的空间坐标数据', horizontalalignment='center', verticalalignment='center', transform=ax.transAxes)

        # 触发画布刷新
        self.canvas.draw()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = LogAnalyzerApp()
    window.show()
    sys.exit(app.exec_())