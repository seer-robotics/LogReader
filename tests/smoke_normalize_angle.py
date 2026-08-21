# -*- coding: utf-8 -*-
"""NormalizeAngle 功能的 GUI 冒烟脚本（非单元测试，需手动运行）。

在 offscreen 模式下加载真实日志，对 LocationEachFrame.theta 调用
ApplicationWindow.normalizeAngle，校验：
1. 展开后的角度曲线连续（相邻采样点差值 < 180 度）
2. self.mid_line_t 时刻对应的角度值与原始值保持一致
3. mid_line_t 为 None 时保持首个采样点不变

用法（需装有 PyQt5 的环境，如 miniforge py39）:
    python tests/smoke_normalize_angle.py [log_file]
"""
import os
import sys
import time

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
os.chdir(PROJECT_ROOT)  # ReadThread 以相对路径读取 log_config.json

DEFAULT_LOG = os.path.join(PROJECT_ROOT, 'robokit_2026-08-21_14-02-58.61.d.log.zst')
KEY = 'LocationEachFrame.theta'
TIMEOUT_S = 180


def plotted_data(ax):
    """取 normalizeAngle 经 drawdata 绘制、label 为 'data' 的曲线。"""
    for line in ax.get_lines():
        if line.get_label() == 'data':
            return list(line.get_ydata())
    return None


def main():
    import numpy as np

    log_file = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_LOG
    assert os.path.exists(log_file), 'log file not found: ' + log_file

    from PyQt5 import QtWidgets
    from loggui import ApplicationWindow
    from ReadThread import ReadThread

    app = QtWidgets.QApplication([])
    win = ApplicationWindow()
    win.show()

    win.filenames = [log_file]
    win.map_widget.hide()
    win.finishReadFlag = False
    win.read_thread = ReadThread()
    done = []
    win.read_thread.signal.connect(lambda result: done.append(result))
    win.read_thread.signal.connect(win.readFinished)
    win.read_thread.filenames = win.filenames

    t0 = time.time()
    win.read_thread.start()
    while not done and time.time() - t0 < TIMEOUT_S:
        app.processEvents()
        time.sleep(0.05)
    if not done:
        print('SMOKE FAIL: read timeout after %ds' % TIMEOUT_S)
        return 1
    print('load finished in %.1fs' % (time.time() - t0))

    rt = win.read_thread
    if KEY not in rt.data:
        print('SMOKE FAIL: %s not in parsed data keys' % KEY)
        return 1
    data, ts = rt.getData(KEY)
    pairs = sorted((t, d) for t, d in zip(ts, data)
                   if isinstance(d, (int, float)))
    if len(pairs) < 2:
        print('SMOKE FAIL: %s has too few numeric samples' % KEY)
        return 1
    org = np.array([d for _, d in pairs], dtype=float)
    org_ts = [t for t, _ in pairs]
    org_jump = float(np.max(np.abs(np.diff(org))))
    print('%s: %d samples, range [%.3f, %.3f], max raw jump %.3f'
          % (KEY, len(org), org.min(), org.max(), org_jump))

    ax = win.axs[0]
    win.xys[0].y_combo.setCurrentText(KEY)
    assert win.xys[0].y_combo.currentText() == KEY, 'y_combo not set to ' + KEY

    failures = []

    # 用例1：mid_line_t 取数据中间时刻，展开后连续且该时刻角度不变
    win.mid_line_t = org_ts[len(org_ts)//2]
    win.normalizeAngle(ax)
    app.processEvents()
    y = plotted_data(ax)
    if y is None or len(y) != len(org):
        failures.append('normalized curve missing or length mismatch')
    else:
        y = np.array(y, dtype=float)
        jump = float(np.max(np.abs(np.diff(y))))
        idx = int(np.abs(np.array(
            [(t - win.mid_line_t).total_seconds() for t in org_ts])).argmin())
        print('case mid_line_t: max jump %.6f, anchor idx %d, '
              'org %.6f -> norm %.6f' % (jump, idx, org[idx], y[idx]))
        if jump >= 180.0:
            failures.append('normalized curve still jumps: %.3f' % jump)
        if abs(y[idx] - org[idx]) > 1e-6:
            failures.append('mid_line_t value changed: %r -> %r'
                            % (org[idx], y[idx]))

    # 用例2：mid_line_t 为 None 时保持首个点不变
    win.mid_line_t = None
    win.normalizeAngle(ax)
    app.processEvents()
    y = plotted_data(ax)
    if y is None or len(y) != len(org):
        failures.append('case None: normalized curve missing')
    else:
        y = np.array(y, dtype=float)
        jump = float(np.max(np.abs(np.diff(y))))
        print('case mid_line_t=None: max jump %.6f, first %.6f -> %.6f'
              % (jump, org[0], y[0]))
        if jump >= 180.0:
            failures.append('case None: normalized curve still jumps')
        if abs(y[0] - org[0]) > 1e-6:
            failures.append('case None: first value changed')

    if failures:
        for f in failures:
            print('SMOKE FAIL:', f)
        return 1
    print('SMOKE PASS')
    return 0


if __name__ == '__main__':
    sys.exit(main())
