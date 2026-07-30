# -*- coding: utf-8 -*-
"""Smoke-test dynamic log config registration against a real log file."""
import json
import os
import shutil
import sys
import tempfile
from types import SimpleNamespace

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
os.chdir(PROJECT_ROOT)

DEFAULT_LOG = os.path.join(
    PROJECT_ROOT, 'robokit-Debug-20260728234453', 'log',
    'robokit_2026-07-28_15-34-05.3.d.log.zst')


def main():
    log_file = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_LOG
    assert os.path.exists(log_file), 'log file not found: ' + log_file

    from PyQt5 import QtWidgets
    from loggui import ApplicationWindow
    from loglibPlus import ReadLog, sort_log_lines_by_timestamp
    from ReadThread import ReadThread

    raw_reader = ReadLog([])
    from loglibPlus import open_log_file
    with open_log_file(log_file, 'rb') as stream:
        raw_reader._readData(stream, log_file)
    raw_reader.lines = sort_log_lines_by_timestamp(raw_reader.lines)

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    reader = ReadThread()
    reader.reader = raw_reader
    entries = {
        'periodRun': {
            'type': 'periodRun',
            'content': [
                {'name': 'active', 'type': 'bool'},
                {'name': 'script', 'type': 'str'},
            ],
        },
    }

    with tempfile.TemporaryDirectory() as temp_dir:
        config_path = os.path.join(temp_dir, 'log_config.json')
        shutil.copyfile('log_config.json', config_path)
        new_series = reader.add_log_configs(entries, config_path)

        curve_combo = QtWidgets.QComboBox()
        fake_window = SimpleNamespace(
            xys=[SimpleNamespace(y_combo=curve_combo)],
            dataSelection=SimpleNamespace(y_combo=QtWidgets.QComboBox()),
            dataViews=[],
            read_thread=reader,
        )
        ApplicationWindow._refreshDynamicConfigViews(
            fake_window, new_series)

        active_data, active_times = reader.getData('periodRun.active')
        with open(config_path, encoding='utf-8') as stream:
            persisted = json.load(stream)

    ok = (
        len(active_data) > 0
        and len(active_data) == len(active_times)
        and curve_combo.findText('periodRun.active') >= 0
        and 'periodRun' in persisted
    )
    print('dynamic series:', new_series)
    print('periodRun samples:', len(active_data))
    print('DYNAMIC CONFIG SMOKE PASS' if ok
          else 'DYNAMIC CONFIG SMOKE FAIL')
    app.processEvents()
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
