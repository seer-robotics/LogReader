# -*- coding: utf-8 -*-
"""Efficient helpers for plotting and querying timestamped log events."""
from bisect import bisect_left, bisect_right
from datetime import timedelta

import matplotlib.dates as mdates
import numpy as np


def event_line_data(times, lane_bottom=0.0, lane_top=1.0):
    """Return one NaN-separated polyline of short event-lane ticks."""
    if not times:
        return np.array([], dtype=float), np.array([], dtype=float)

    positions = np.asarray(mdates.date2num(times), dtype=float)
    xdata = np.empty(len(positions) * 3, dtype=float)
    ydata = np.empty(len(positions) * 3, dtype=float)
    xdata[0::3] = positions
    xdata[1::3] = positions
    xdata[2::3] = np.nan
    ydata[0::3] = lane_bottom
    ydata[1::3] = lane_top
    ydata[2::3] = np.nan
    return xdata, ydata


class EventIndex:
    """Sorted event lookup supporting nearest queries in logarithmic time."""

    def __init__(self, times=(), contents=()):
        event_count = min(len(times), len(contents))
        self.times = list(times[:event_count])
        self.contents = list(contents[:event_count])
        if any(self.times[i] > self.times[i + 1]
               for i in range(len(self.times) - 1)):
            entries = sorted(
                zip(self.times, self.contents), key=lambda item: item[0])
            self.times = [entry[0] for entry in entries]
            self.contents = [entry[1] for entry in entries]

    def __len__(self):
        return len(self.times)

    def nearest_distance(self, target):
        """Return the distance in seconds to the nearest event."""
        if not self.times:
            return float('inf')

        position = bisect_left(self.times, target)
        candidates = []
        if position < len(self.times):
            candidates.append(self.times[position])
        if position > 0:
            candidates.append(self.times[position - 1])
        return min(abs((event_time - target).total_seconds())
                   for event_time in candidates)

    def contents_at_distance(self, target, distance, tolerance=1e-3):
        """Return events whose absolute distance matches within tolerance."""
        if not self.times or not np.isfinite(distance):
            return []

        result_indices = set()
        delta = timedelta(seconds=distance)
        margin = timedelta(seconds=tolerance)
        for center in (target - delta, target + delta):
            begin = bisect_left(self.times, center - margin)
            end = bisect_right(self.times, center + margin)
            for index in range(begin, end):
                actual_distance = abs(
                    (self.times[index] - target).total_seconds())
                if abs(actual_distance - distance) < tolerance:
                    result_indices.add(index)
        return [self.contents[index] for index in sorted(result_indices)]
