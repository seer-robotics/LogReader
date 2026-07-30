# -*- coding: utf-8 -*-
import unittest
from datetime import datetime, timedelta

import numpy as np

from eventutils import EventIndex, event_line_data


class TestEventLineData(unittest.TestCase):
    def test_empty_events(self):
        xdata, ydata = event_line_data([])

        self.assertEqual(0, len(xdata))
        self.assertEqual(0, len(ydata))

    def test_multiple_events_share_one_nan_separated_polyline(self):
        start = datetime(2026, 7, 28, 15, 39, 5)
        xdata, ydata = event_line_data([
            start, start + timedelta(seconds=1)])

        self.assertEqual(6, len(xdata))
        self.assertEqual([0.0, 1.0], ydata[:2].tolist())
        self.assertEqual([0.0, 1.0], ydata[3:5].tolist())
        self.assertTrue(np.isnan(xdata[2]))
        self.assertTrue(np.isnan(xdata[5]))
        self.assertTrue(np.isnan(ydata[2]))
        self.assertEqual(xdata[0], xdata[1])
        self.assertEqual(xdata[3], xdata[4])

    def test_event_ticks_can_be_confined_to_a_lane(self):
        xdata, ydata = event_line_data(
            [datetime(2026, 7, 28, 15, 39, 5)], 0.11, 0.135)

        self.assertEqual([0.11, 0.135], ydata[:2].tolist())


class TestEventIndex(unittest.TestCase):
    def setUp(self):
        self.start = datetime(2026, 7, 28, 15, 39, 5)

    def test_sorts_times_and_keeps_content_aligned(self):
        index = EventIndex(
            [self.start + timedelta(seconds=2), self.start],
            ['later', 'earlier'])

        self.assertEqual([self.start, self.start + timedelta(seconds=2)],
                         index.times)
        self.assertEqual(['earlier', 'later'], index.contents)

    def test_nearest_distance_uses_adjacent_bisect_candidates(self):
        index = EventIndex(
            [self.start, self.start + timedelta(seconds=10)],
            ['first', 'second'])

        self.assertAlmostEqual(
            4.0, index.nearest_distance(self.start + timedelta(seconds=4)))
        self.assertAlmostEqual(
            1.0, index.nearest_distance(self.start + timedelta(seconds=9)))

    def test_contents_at_distance_finds_both_sides_and_duplicates(self):
        target = self.start + timedelta(seconds=5)
        index = EventIndex(
            [self.start + timedelta(seconds=4),
             self.start + timedelta(seconds=4, microseconds=500),
             self.start + timedelta(seconds=6)],
            ['left', 'left-near', 'right'])

        self.assertEqual(
            ['left', 'left-near', 'right'],
            index.contents_at_distance(target, 1.0))

    def test_empty_index(self):
        index = EventIndex()

        self.assertEqual(float('inf'), index.nearest_distance(self.start))
        self.assertEqual([], index.contents_at_distance(self.start, 0.0))


if __name__ == '__main__':
    unittest.main()
