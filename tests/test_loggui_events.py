# -*- coding: utf-8 -*-
import os
import unittest
from datetime import datetime, timedelta
from types import SimpleNamespace

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

from eventutils import EventIndex, event_line_data
from loggui import ApplicationWindow, EVENT_LINE_STYLES


class FakeCheckBox:
    def __init__(self, checked=True):
        self.checked = checked

    def isChecked(self):
        return self.checked


class TestLogEventRendering(unittest.TestCase):
    def setUp(self):
        self.figure = Figure(figsize=(8, 3))
        FigureCanvasAgg(self.figure)
        self.ax = self.figure.add_subplot(111)
        self.fake = SimpleNamespace(
            event_artists={key: {} for key in EVENT_LINE_STYLES},
            event_plot_data={
                key: event_line_data([]) for key in EVENT_LINE_STYLES},
            event_checkboxes={
                key: FakeCheckBox() for key in EVENT_LINE_STYLES},
            static_canvas=SimpleNamespace(figure=self.figure),
        )

    def test_thousands_of_events_create_one_artist_per_category(self):
        start = datetime(2026, 7, 28, 15, 39, 5)
        times = [start + timedelta(milliseconds=i) for i in range(10000)]
        lane = EVENT_LINE_STYLES['service']['lane']
        self.fake.event_plot_data['service'] = event_line_data(times, *lane)

        ApplicationWindow.drawFEWN(self.fake, self.ax)

        self.assertEqual(1, len(self.ax.lines))
        self.assertEqual(1, len(self.fake.event_artists['service']))
        self.assertEqual(30000, len(self.ax.lines[0].get_xdata()))
        self.assertEqual(list(lane),
                         self.ax.lines[0].get_ydata()[:2].tolist())

    def test_visibility_updates_the_compound_artist(self):
        start = datetime(2026, 7, 28, 15, 39, 5)
        lane = EVENT_LINE_STYLES['service']['lane']
        self.fake.event_plot_data['service'] = event_line_data([start], *lane)
        ApplicationWindow.drawFEWN(self.fake, self.ax)
        self.fake.event_checkboxes['service'].checked = False

        ApplicationWindow.updateCheckInfoLine(self.fake, 'service')

        self.assertFalse(self.fake.event_artists['service'][self.ax].get_visible())


class TestLogEventHover(unittest.TestCase):
    def test_returns_nearest_enabled_event_content(self):
        start = datetime(2026, 7, 28, 15, 39, 5)
        fake = SimpleNamespace(
            event_indexes={
                'service': EventIndex(
                    [start, start + timedelta(seconds=2)],
                    ['first service', 'second service']),
                'notice': EventIndex(
                    [start + timedelta(seconds=1)], ['notice']),
            },
            event_checkboxes={
                'service': FakeCheckBox(True),
                'notice': FakeCheckBox(False),
            },
        )

        content = ApplicationWindow.get_content(
            fake, start + timedelta(seconds=1, milliseconds=900))

        self.assertEqual('second service', content)


if __name__ == '__main__':
    unittest.main()
