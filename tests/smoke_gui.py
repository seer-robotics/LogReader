# -*- coding: utf-8 -*-
"""GUI 自动化冒烟脚本（非单元测试，需手动运行）。

在 offscreen 模式下完整走一遍主程序加载流程：
创建 ApplicationWindow -> 用 ReadThread 加载真实日志 -> 等待 readFinished
-> 校验解析数据 -> 退出。

用法（需装有 PyQt5 的环境，如 miniforge py39）:
    python tests/smoke_gui.py [log_file]
"""
import os
import sys
import time

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
os.chdir(PROJECT_ROOT)  # ReadThread 以相对路径读取 log_config.json

DEFAULT_LOG = os.path.join(
    PROJECT_ROOT, 'robokit-Debug-20260721171819', 'log',
    'robokit_2026-07-21_17-02-49.9.log')
TIMEOUT_S = 180


def main():
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
    elapsed = time.time() - t0
    if not done:
        print('SMOKE FAIL: read timeout after %ds' % TIMEOUT_S)
        return 1

    rt = win.read_thread
    n_fatal = len(rt.fatal.content()[0])
    n_err = len(rt.err.content()[0])
    n_war = len(rt.war.content()[0])
    n_notice = len(rt.notice.content()[0])
    n_series = len(rt.data)
    nonempty = sum(1 for v in rt.data.values()
                   if isinstance(v, tuple) and len(v) == 2 and len(v[1]) > 0)
    print('load finished in %.1fs' % elapsed)
    print('FATAL=%d ERROR=%d WARNING=%d NOTICE=%d'
          % (n_fatal, n_err, n_war, n_notice))
    print('data series: %d total, %d non-empty' % (n_series, nonempty))
    print('tlist:', rt.tlist)
    print('report file:', rt.getReportFileAddr())

    ok = (n_series > 0 and nonempty > 0
          and len(rt.tlist) == 2 and rt.tlist[0] is not None
          and win.finishReadFlag)
    print('SMOKE PASS' if ok else 'SMOKE FAIL: empty parse result')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
