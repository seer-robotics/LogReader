# -*- coding: utf-8 -*-
"""Unit tests for loglibPlus time helpers, file opening and a real-log smoke test."""
import os
import sys
import tempfile
import unittest
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# loglibPlus uses matplotlib.dates.date2num but only does `import matplotlib`;
# in the running app the submodule is pulled in by other modules, so import it
# here explicitly to mirror that environment.
import matplotlib.dates  # noqa: F401

from loglibPlus import rbktimetodate, date2num, num2date, open_log_file, ReadLog

REAL_LOG = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "robokit-Debug-20260721171819", "log", "robokit_2026-07-21_16-52-32.7.log")


class TestRbkTimeToDate(unittest.TestCase):
    def test_short_format(self):
        result = rbktimetodate("260721 165232.576")
        self.assertEqual(result, datetime(2026, 7, 21, 16, 52, 32, 576000))

    def test_long_format(self):
        result = rbktimetodate("2026-07-21 16:52:32.576")
        self.assertEqual(result, datetime(2026, 7, 21, 16, 52, 32, 576000))


class TestDateNumRoundTrip(unittest.TestCase):
    def test_roundtrip(self):
        for d in (datetime(2026, 7, 21, 16, 52, 32),
                  datetime(2020, 1, 1, 0, 0, 0),
                  datetime(1999, 12, 31, 23, 59, 59)):
            result = num2date(date2num(d))
            self.assertIsNone(result.tzinfo)
            self.assertLess(abs((result - d).total_seconds()), 1e-3)


class TestOpenLogFile(unittest.TestCase):
    def test_plain_log_file_readable(self):
        content = b"[260721 165232.576][1][R][d] [Text][hello]\nsecond line\n"
        with tempfile.NamedTemporaryFile(suffix=".log", delete=False) as f:
            f.write(content)
            path = f.name
        self.addCleanup(os.remove, path)
        with open_log_file(path, "rb") as f:
            data = f.read()
        self.assertEqual(data, content)


@unittest.skipUnless(os.path.exists(REAL_LOG), "real robot log not available")
class TestRealLogSmoke(unittest.TestCase):
    HEAD_LINES = 3000  # keep < 4000 so ReadLog stays on the single-process path

    def test_parse_real_log_head(self):
        with tempfile.NamedTemporaryFile(suffix=".log", delete=False) as tmp:
            tmp_path = tmp.name
            with open_log_file(REAL_LOG, "rb") as src:
                for ind, line in enumerate(src):
                    if ind >= self.HEAD_LINES:
                        break
                    tmp.write(line)
        self.addCleanup(os.remove, tmp_path)

        log = ReadLog([tmp_path])
        log.parse()  # no data parsers: must not raise
        self.assertGreater(len(log.lines), 0)
        self.assertGreater(log.lines_num, 0)
        self.assertIsNotNone(log.tmin)
        self.assertIsNotNone(log.tmax)
        self.assertLessEqual(log.tmin, log.tmax)


if __name__ == "__main__":
    unittest.main()
