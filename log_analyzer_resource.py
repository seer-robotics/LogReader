import sys
import re
import json
import math
from collections import defaultdict

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QTextEdit, QPushButton, QFileDialog)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

# 导入 matplotlib 嵌合 PyQt5 的模块
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure


class MplCanvas(FigureCanvas):
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = self.fig.add_subplot(111)
        super(MplCanvas, self).__init__(self.fig)


class LogAnalyzerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Log 资源释放分析工具 (支持平移/缩放/测量/点击下钻)")
        self.resize(1400, 900)

        # 核心数据存储
        self.id_data = {}
        self.unconfirmed_ids = []
        
        # 交互状态
        self.show_unconfirmed_only = False
        self.selected_id = None  # 当前被点击选中的 ID
        self.artist_to_id = {}   # 用于记录图形对象 (线条/文本) 对应的 ID

        # 测量工具的状态
        self.measure_mode = False
        self.measure_points = []
        self.measure_line = None
        self.measure_text = None

        self.initUI()

    def initUI(self):
        main_widget = QWidget(self)
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)

        # ---------------- 左侧面板 ----------------
        left_panel = QVBoxLayout()
        
        self.drop_label = QLabel("将 log 文件拖拽到此处\n(支持多个文件)")
        self.drop_label.setAlignment(Qt.AlignCenter)
        self.drop_label.setStyleSheet("QLabel { border: 2px dashed #aaa; border-radius: 5px; background-color: #f0f0f0; padding: 20px; font-size: 14px; }")
        self.drop_label.setMinimumHeight(100)
        
        self.text_output = QTextEdit()
        self.text_output.setReadOnly(True)
        self.text_output.setFont(QFont("Consolas", 10))
        self.text_output.setPlaceholderText("解析结果将显示在这里...\n(点击右侧图中的形状可查看该资源的详细日志)")

        # 按钮区
        self.toggle_btn = QPushButton("当前视图: 🌍 显示所有资源")
        self.toggle_btn.setMinimumHeight(40)
        self.toggle_btn.setStyleSheet("font-weight: bold; font-size: 14px;")
        self.toggle_btn.clicked.connect(self.toggle_view)
        self.toggle_btn.setEnabled(False)

        self.clear_sel_btn = QPushButton("🧹 取消选中 (恢复汇总信息)")
        self.clear_sel_btn.setMinimumHeight(40)
        self.clear_sel_btn.setStyleSheet("font-size: 14px;")
        self.clear_sel_btn.clicked.connect(self.clear_selection)
        self.clear_sel_btn.setEnabled(False)

        self.measure_btn = QPushButton("📏 测量距离: 关")
        self.measure_btn.setMinimumHeight(40)
        self.measure_btn.setCheckable(True)
        self.measure_btn.clicked.connect(self.toggle_measure)
        self.measure_btn.setStyleSheet("font-size: 14px;")

        left_panel.addWidget(self.drop_label)
        left_panel.addWidget(self.text_output)
        left_panel.addWidget(self.toggle_btn)
        left_panel.addWidget(self.clear_sel_btn)
        left_panel.addWidget(self.measure_btn)

        # ---------------- 右侧面板 ----------------
        right_panel = QVBoxLayout()
        self.canvas = MplCanvas(self, width=6, height=6, dpi=100)
        self.toolbar = NavigationToolbar(self.canvas, self)
        
        right_panel.addWidget(self.toolbar)
        right_panel.addWidget(self.canvas)

        main_layout.addLayout(left_panel, 3)
        main_layout.addLayout(right_panel, 7)

        self.setAcceptDrops(True)

        # 绑定事件
        self.canvas.mpl_connect('button_press_event', self.on_canvas_click)
        self.canvas.mpl_connect('pick_event', self.on_pick)

    # ================= 解析逻辑 =================
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        file_paths = [url.toLocalFile() for url in event.mimeData().urls() if url.toLocalFile().endswith('.log')]
        if file_paths:
            self.selected_id = None  # 重置选中状态
            self.text_output.append(f"<b>接收到 {len(file_paths)} 个 log 文件，开始解析...</b>")
            self.parse_logs(file_paths)
            self.update_summary_ui()
        else:
            self.text_output.append("<font color='red'>未检测到有效的 .log 文件！</font>")

    def parse_logs(self, file_paths):
        self.id_data = {}
        self.unconfirmed_ids = []
        uuid_to_req_ids = defaultdict(set)

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

        for req_id, info in self.id_data.items():
            if not info['confirmed']:
                self.unconfirmed_ids.append(req_id)

    # ================= 视图与 UI 更新 =================
    def update_summary_ui(self):
        """显示全局汇总信息"""
        self.text_output.clear()
        self.text_output.append("<b>解析完成！结果如下 (点击右侧形状可查看明细)：</b><br>")
        
        for req_id, info in self.id_data.items():
            color = "green" if info['confirmed'] else "red"
            status = "已释放" if info['confirmed'] else "未释放"
            self.text_output.append(f"<font color='{color}'><b>【ID】: {req_id} ({status})</b></font>")
            
        if self.unconfirmed_ids:
            self.text_output.append(f"<br><font color='red'><b>总结：以下 ID 没有释放: {', '.join(self.unconfirmed_ids)}</b></font>")
        else:
            self.text_output.append("<br><font color='green'><b>总结：所有 ID 均已成功释放。</b></font>")

        self.toggle_btn.setEnabled(True)
        self.clear_sel_btn.setEnabled(False)
        self.draw_plot()

    def show_detail_logs(self, req_id):
        """显示被选中 ID 的详细日志"""
        self.text_output.clear()
        info = self.id_data[req_id]
        status = "✅ 已释放 (release confirmed)" if info['confirmed'] else "❌ 未释放 (Missing confirmed)"
        color = "green" if info['confirmed'] else "red"

        self.text_output.append(f"<h3 style='color: {color};'>当前选中资源: {req_id}</h3>")
        self.text_output.append(f"<b>状态:</b> <span style='color: {color}; font-weight: bold;'>{status}</span><br><hr>")

        self.text_output.append("<b>[1] 申请资源日志 (PostRes):</b>")
        for line in info['postres_lines']:
            self.text_output.append(f"<div style='background-color: #f5f5f5; padding: 5px; margin-bottom: 5px;'><pre style='white-space: pre-wrap; font-size: 12px; margin: 0;'>{line}</pre></div>")

        self.text_output.append("<br><b>[2] 释放资源请求日志 (doPostRelease):</b>")
        if info['dopostrelease_lines']:
            for line in info['dopostrelease_lines']:
                self.text_output.append(f"<div style='background-color: #e6f7ff; padding: 5px; margin-bottom: 5px;'><pre style='white-space: pre-wrap; font-size: 12px; margin: 0;'>{line}</pre></div>")
        else:
            self.text_output.append("<i style='color: gray;'>暂无匹配记录</i><br>")

        self.text_output.append("<br><b>[3] 释放确认日志 (pollPendingReleases):</b>")
        if info['poll_lines']:
            for line in info['poll_lines']:
                self.text_output.append(f"<div style='background-color: #f6ffed; padding: 5px; margin-bottom: 5px;'><pre style='white-space: pre-wrap; font-size: 12px; margin: 0;'>{line}</pre></div>")
        else:
            self.text_output.append("<i style='color: gray;'>暂无匹配记录</i><br>")

        # 滚动到顶部
        self.text_output.verticalScrollBar().setValue(0)

    def toggle_view(self):
        self.show_unconfirmed_only = not self.show_unconfirmed_only
        if self.show_unconfirmed_only:
            self.toggle_btn.setText("当前视图: 🚨 仅显示未释放的资源 (点击切换)")
            self.toggle_btn.setStyleSheet("font-weight: bold; font-size: 14px; color: red;")
        else:
            self.toggle_btn.setText("当前视图: 🌍 显示所有资源 (点击切换)")
            self.toggle_btn.setStyleSheet("font-weight: bold; font-size: 14px; color: black;")
        
        self.clear_measurements() 
        self.clear_selection()

    def clear_selection(self):
        """取消选中状态并恢复全局视图"""
        self.selected_id = None
        self.update_summary_ui()

    # ================= 交互事件处理 =================
    def on_pick(self, event):
        """处理点击选中线条或文本的事件"""
        if self.measure_mode: return # 如果正在测量，忽略选中事件

        artist = event.artist
        if artist in self.artist_to_id:
            req_id = self.artist_to_id[artist]
            self.selected_id = req_id
            
            self.clear_sel_btn.setEnabled(True)
            self.show_detail_logs(req_id)
            self.draw_plot() # 触发重绘以高亮当前选中项

    # ================= 测量功能 =================
    def toggle_measure(self, checked):
        self.measure_mode = checked
        if checked:
            self.measure_btn.setText("📏 测量距离: 开 (请在图上点击两点)")
            self.measure_btn.setStyleSheet("font-size: 14px; color: blue; font-weight: bold;")
            self.canvas.setCursor(Qt.CrossCursor)
        else:
            self.measure_btn.setText("📏 测量距离: 关")
            self.measure_btn.setStyleSheet("font-size: 14px;")
            self.canvas.setCursor(Qt.ArrowCursor)
            self.clear_measurements()

    def clear_measurements(self):
        self.measure_points = []
        if self.measure_line:
            self.measure_line.remove()
            self.measure_line = None
        if self.measure_text:
            self.measure_text.remove()
            self.measure_text = None
        self.canvas.draw()

    def on_canvas_click(self, event):
        # 仅测量模式下生效
        if not self.measure_mode or event.inaxes is None or event.button != 1:
            return

        self.measure_points.append((event.xdata, event.ydata))

        if len(self.measure_points) == 2:
            x1, y1 = self.measure_points[0]
            x2, y2 = self.measure_points[1]
            distance = math.hypot(x2 - x1, y2 - y1)

            if self.measure_line: self.measure_line.remove()
            if self.measure_text: self.measure_text.remove()

            self.measure_line, = event.inaxes.plot([x1, x2], [y1, y2], color='purple', linestyle='--', linewidth=2)
            self.measure_text = event.inaxes.text((x1+x2)/2, (y1+y2)/2, f" Dist: {distance:.3f} ",
                                                  color='white', weight='bold', fontsize=10,
                                                  bbox=dict(facecolor='purple', alpha=0.8, edgecolor='none', pad=2),
                                                  ha='center', va='center')
            self.canvas.draw()
            self.measure_points = []

    # ================= 核心绘图 =================
    def draw_plot(self):
        ax = self.canvas.axes
        ax.clear()
        self.artist_to_id.clear() # 清空映射字典

        has_points = False
        target_ids = self.unconfirmed_ids if self.show_unconfirmed_only else self.id_data.keys()

        for req_id in target_ids:
            info = self.id_data[req_id]
            is_unconfirmed = req_id in self.unconfirmed_ids
            is_selected = (self.selected_id == req_id)

            for pts in info['points_list']:
                if not pts: continue
                has_points = True
                xs = [p['x'] for p in pts]
                ys = [p['y'] for p in pts]
                
                if xs[0] != xs[-1] or ys[0] != ys[-1]:
                    xs.append(xs[0])
                    ys.append(ys[0])
                
                # 样式控制：根据是否被选中设置颜色、透明度、层级
                if is_selected:
                    # 选中的形状：亮橙色、最粗、不透明、画在最上层
                    line_color = '#FF8C00' # 深橙色
                    alpha_val = 1.0
                    line_width = 4.0
                    z_order = 10
                    marker_style = 'D' # 钻石形状标记
                else:
                    # 未选中的形状
                    line_color = 'red' if is_unconfirmed else 'tab:blue'
                    line_width = 2.0 if is_unconfirmed else 1.5
                    # 如果当前有选中的项目，非选中项目全部变半透明(0.2)；如果没有选中项目，保持原始透明度
                    alpha_val = 0.2 if self.selected_id else (1.0 if is_unconfirmed else 0.6)
                    z_order = 2 if is_unconfirmed else 1
                    marker_style = 'x' if is_unconfirmed else 'o'

                # 绘制折线，开启 picker=5 (点击范围5像素内容差)
                line, = ax.plot(xs, ys, marker=marker_style, markersize=5, color=line_color, 
                                linestyle='-', linewidth=line_width, alpha=alpha_val, zorder=z_order, picker=5)
                self.artist_to_id[line] = req_id # 记录线与 ID 的映射

                # 绘制文本标签
                text = ax.text(xs[0], ys[0], str(req_id), color='black' if not is_selected else 'white', 
                               fontsize=10 if is_selected else 9, 
                               ha='right', va='bottom', weight='bold', alpha=alpha_val,
                               bbox=dict(facecolor=line_color if is_selected else 'white', 
                                         alpha=alpha_val if is_selected else alpha_val*0.8, 
                                         edgecolor='none', pad=2),
                               zorder=z_order, picker=5)
                self.artist_to_id[text] = req_id # 记录文本与 ID 的映射

        if has_points:
            title = 'Unconfirmed Spatial Zones' if self.show_unconfirmed_only else 'All Requested Spatial Zones'
            if self.selected_id:
                title += f" [Highlighing ID: {self.selected_id}]"
            ax.set_title(title)
            ax.set_xlabel('X Coordinate')
            ax.set_ylabel('Y Coordinate')
            ax.grid(True, linestyle='--', alpha=0.6)
        else:
            ax.text(0.5, 0.5, '当前视图无有效的空间坐标数据', ha='center', va='center', transform=ax.transAxes)

        self.canvas.draw()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = LogAnalyzerApp()
    window.show()
    sys.exit(app.exec_())