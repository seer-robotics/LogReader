# -*- coding: utf-8 -*-
import os
import unittest
from datetime import datetime, timedelta

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PyQt5 import QtCore, QtWidgets

from EventViewer import (EVENT_CONTENT_ROLE, EVENT_TIME_ROLE,
                         EventTableModel, EventViewer)


class FakeEventSource:
    def __init__(self, times, contents):
        self._times = times
        self._contents = contents

    def t(self):
        return self._times

    def content(self):
        return self._contents, self._times


class TestEventTableModel(unittest.TestCase):
    def test_exposes_time_content_and_custom_roles(self):
        event_time = datetime(2026, 7, 28, 15, 39, 5, 123000)
        model = EventTableModel()
        model.setEvents([event_time], ['service event\n'])

        time_index = model.index(0, 0)
        event_index = model.index(0, 1)
        self.assertEqual('2026-07-28 15:39:05.123',
                         time_index.data(QtCore.Qt.DisplayRole))
        self.assertEqual('service event',
                         event_index.data(QtCore.Qt.DisplayRole))
        self.assertEqual(event_time, event_index.data(EVENT_TIME_ROLE))
        self.assertEqual('service event',
                         event_index.data(EVENT_CONTENT_ROLE))

    def test_uses_shorter_input_length(self):
        model = EventTableModel()
        model.setEvents([datetime.now(), datetime.now()], ['one'])

        self.assertEqual(1, model.rowCount())


class TestEventViewer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = (QtWidgets.QApplication.instance()
                   or QtWidgets.QApplication([]))

    def setUp(self):
        start = datetime(2026, 7, 28, 15, 39, 5)
        self.times = [start, start + timedelta(seconds=1)]
        self.viewer = EventViewer()
        self.viewer.setEvents({
            'service': FakeEventSource(
                self.times, ['first service', 'second service']),
            'fatal': FakeEventSource(
                [start + timedelta(seconds=2)], ['fatal event']),
        })

    def tearDown(self):
        self.viewer.hide()
        self.viewer.deleteLater()
        self.app.processEvents()

    def test_categories_show_counts(self):
        self.assertIn('FATAL (1)', [
            self.viewer.tabs.tabText(i)
            for i in range(self.viewer.tabs.count())])
        self.assertIn('SERVICE (2)', [
            self.viewer.tabs.tabText(i)
            for i in range(self.viewer.tabs.count())])

    def test_filter_applies_to_current_category(self):
        service_tab = self.viewer._tab_keys.index('service')
        self.viewer.tabs.setCurrentIndex(service_tab)
        self.viewer.filter_edit.setText('second')

        self.assertEqual(1, self.viewer.proxies['service'].rowCount())
        self.assertEqual('1 / 2 events', self.viewer.result_label.text())

    def test_move_here_emits_selected_event_time(self):
        service_tab = self.viewer._tab_keys.index('service')
        self.viewer.tabs.setCurrentIndex(service_tab)
        view = self.viewer.views['service']
        view.setCurrentIndex(self.viewer.proxies['service'].index(1, 0))
        emitted = []
        self.viewer.moveHereSignal.connect(emitted.append)

        self.viewer.moveCurrentEvent(view)

        self.assertEqual([self.times[1]], emitted)


if __name__ == '__main__':
    unittest.main()
