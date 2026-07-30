# -*- coding: utf-8 -*-
import json
import os
import unittest
from types import SimpleNamespace

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PyQt5 import QtWidgets

from loggui import ApplicationWindow, LogConfigDialog


class TestLogConfigDialog(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = (QtWidgets.QApplication.instance()
                   or QtWidgets.QApplication([]))

    def setUp(self):
        self.dialog = LogConfigDialog('log_config.json')

    def tearDown(self):
        self.dialog.close()
        self.dialog.deleteLater()
        self.app.processEvents()

    def test_accepts_single_rule_and_infers_name(self):
        self.dialog.name_edit.clear()
        self.dialog.json_edit.setPlainText(json.dumps({
            'type': 'DynamicState',
            'content': [{'name': 'value', 'type': 'double'}],
        }))

        self.dialog.validateAndAccept()

        self.assertEqual(QtWidgets.QDialog.Accepted,
                         self.dialog.result())
        self.assertEqual(['DynamicState'], list(self.dialog.entries()))

    def test_explicit_name_is_used_for_single_rule(self):
        self.dialog.name_edit.setText('DisplayName')
        self.dialog.json_edit.setPlainText(json.dumps({
            'type': 'DynamicState',
            'content': [{'name': 'value', 'type': 'double'}],
        }))

        self.dialog.validateAndAccept()

        self.assertEqual(['DisplayName'], list(self.dialog.entries()))


class TestDynamicConfigViewRefresh(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = (QtWidgets.QApplication.instance()
                   or QtWidgets.QApplication([]))

    def test_adds_curve_fields_and_refreshes_data_groups(self):
        curve_combo = QtWidgets.QComboBox()
        curve_combo.addItem('Existing.value')
        add_data_combo = QtWidgets.QComboBox()
        data_view_combo = QtWidgets.QComboBox()
        data_view_combo.addItem('Existing')
        fake = SimpleNamespace(
            xys=[SimpleNamespace(y_combo=curve_combo)],
            dataSelection=SimpleNamespace(y_combo=add_data_combo),
            dataViews=[SimpleNamespace(selection=SimpleNamespace(
                y_combo=data_view_combo))],
            read_thread=SimpleNamespace(name2orgKey={
                'Existing': 'Existing',
                'DynamicState': 'DynamicState',
            }),
        )

        ApplicationWindow._refreshDynamicConfigViews(
            fake, ['DynamicState.value'])

        self.assertEqual(1, curve_combo.findText('DynamicState.value'))
        self.assertEqual(0, add_data_combo.findText('DynamicState.value'))
        self.assertEqual(0, data_view_combo.findText('Existing'))
        self.assertEqual(1, data_view_combo.findText('DynamicState'))


if __name__ == '__main__':
    unittest.main()
