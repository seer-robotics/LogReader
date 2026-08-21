# -*- coding: utf-8 -*-
"""Unit tests for the pure functions in maputils.py (no PyQt5/matplotlib needed)."""
import math
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np

import maputils
from maputils import (
    find_goods_resource,
    find_log_resource,
    GetGlobalPos,
    P2G,
    Pos2Base,
    convert2LaserPoints,
    normalize_theta,
    normalize_theta_deg,
    interpolate_pose_at_time,
    nearest_value_at_time,
    read_goods_dimensions,
    _curve_points_to_xy,
    _curve_polygons_to_xy,
    _curve_xy_values,
    _find_curve_xy,
    parse_curve_data,
)

REAL_LOG = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "robokit-Debug-20260721171819", "log", "robokit_2026-07-21_16-52-32.7.log")


class TestNormalizeTheta(unittest.TestCase):
    def assertInRange(self, value):
        self.assertGreaterEqual(value, -math.pi)
        self.assertLess(value, math.pi)

    def test_zero(self):
        self.assertEqual(normalize_theta(0.0), 0.0)

    def test_pi_becomes_minus_pi(self):
        self.assertAlmostEqual(normalize_theta(math.pi), -math.pi)

    def test_minus_pi_stays(self):
        self.assertAlmostEqual(normalize_theta(-math.pi), -math.pi)

    def test_two_pi_becomes_zero(self):
        self.assertAlmostEqual(normalize_theta(2 * math.pi), 0.0)

    def test_large_angles_in_range(self):
        for theta in (0.0, math.pi, -math.pi, 2 * math.pi, 3 * math.pi,
                      -3 * math.pi, 100.0, -100.0, 1e6, -1e6):
            self.assertInRange(normalize_theta(theta))

    def test_deg_boundaries(self):
        self.assertAlmostEqual(normalize_theta_deg(0.0), 0.0)
        self.assertAlmostEqual(normalize_theta_deg(180.0), -180.0)
        self.assertAlmostEqual(normalize_theta_deg(-180.0), -180.0)
        self.assertAlmostEqual(normalize_theta_deg(360.0), 0.0)
        self.assertAlmostEqual(normalize_theta_deg(270.0), -90.0)
        self.assertAlmostEqual(normalize_theta_deg(-270.0), 90.0)
        self.assertAlmostEqual(normalize_theta_deg(90.0), 90.0)
        for deg in (720.0, -720.0, 12345.0, -12345.0):
            value = normalize_theta_deg(deg)
            self.assertGreaterEqual(value, -180.0)
            self.assertLess(value, 180.0)


class TestCoordinateTransforms(unittest.TestCase):
    def test_getglobalpos_identity_single_point(self):
        result = GetGlobalPos([1.0, 2.0], [0.0, 0.0, 0.0])
        np.testing.assert_allclose(result, [1.0, 2.0], atol=1e-12)

    def test_getglobalpos_identity_array(self):
        points = np.array([[1.0, 3.0, -2.0], [2.0, -4.0, 0.5]])  # 2xN
        result = GetGlobalPos(points, [0.0, 0.0, 0.0])
        np.testing.assert_allclose(result, points, atol=1e-12)

    def test_getglobalpos_rotation_90deg(self):
        result = GetGlobalPos([1.0, 0.0], [0.0, 0.0, math.pi / 2])
        np.testing.assert_allclose(result, [0.0, 1.0], atol=1e-12)

    def test_getglobalpos_translation(self):
        result = GetGlobalPos([1.0, 2.0], [10.0, 20.0, 0.0])
        np.testing.assert_allclose(result, [11.0, 22.0], atol=1e-12)

    def test_p2g_identity(self):
        result = P2G([1.0, 2.0, 0.3], [0.0, 0.0, 0.0])
        np.testing.assert_allclose(result, [1.0, 2.0, 0.3], atol=1e-12)

    def test_p2g_rotation_90deg(self):
        result = P2G([1.0, 0.0, math.pi / 2], [0.0, 0.0, math.pi / 2])
        np.testing.assert_allclose(result, [0.0, 1.0, math.pi], atol=1e-12)

    def test_pos2base_identity(self):
        self.assertEqual(Pos2Base([1.0, 2.0, 0.5], [0.0, 0.0, 0.0]),
                         [1.0, 2.0, 0.5])

    def test_pos2base_rotation_90deg(self):
        result = Pos2Base([1.0, 0.0, 0.0], [0.0, 0.0, math.pi / 2])
        np.testing.assert_allclose(result, [0.0, -1.0, -math.pi / 2], atol=1e-12)

    def test_p2g_pos2base_roundtrip(self):
        base = [3.0, -2.0, 0.7]
        pose = [1.5, 0.5, -0.2]
        world = P2G(pose, base)
        back = Pos2Base(world, base)
        np.testing.assert_allclose(back, pose, atol=1e-12)


class TestConvert2LaserPoints(unittest.TestCase):
    def test_identity_transform(self):
        org = np.array([[1.0], [0.0]])  # one point (1, 0) in laser frame
        lines, circle_cs, laser_data2r = convert2LaserPoints(
            org, [0.0, 0.0, 0.0], [0.0, 0.0, 0.0])
        self.assertEqual(lines.shape, (1, 2, 2))
        np.testing.assert_allclose(lines[0], [[0.0, 0.0], [1.0, 0.0]], atol=1e-12)
        np.testing.assert_allclose(circle_cs, [[1.0, 0.0]], atol=1e-12)
        np.testing.assert_allclose(laser_data2r, [[1.0, 0.0]], atol=1e-12)

    def test_robot_pose_applied(self):
        org = np.array([[1.0], [0.0]])
        robot_pos = [1.0, 0.0, math.pi / 2]
        lines, circle_cs, laser_data2r = convert2LaserPoints(
            org, [0.0, 0.0, 0.0], robot_pos)
        # laser origin in global frame = (1, 0); point -> (1, 1)
        np.testing.assert_allclose(lines[0], [[1.0, 0.0], [1.0, 1.0]], atol=1e-12)
        np.testing.assert_allclose(circle_cs, [[1.0, 1.0]], atol=1e-12)
        np.testing.assert_allclose(laser_data2r, [[1.0, 0.0]], atol=1e-12)


class TestFindLogResource(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = self._tmp.name

    def _make(self, *relpath):
        path = os.path.join(self.root, *relpath)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write("x")
        return path

    def test_new_layout_log_d(self):
        """<root>/log/d/xxx.log finds <root>/maps/m.smap."""
        expected = self._make("maps", "m.smap")
        log_file = self._make("log", "d", "xxx.log")
        result = find_log_resource(log_file, "maps", "m.smap")
        self.assertEqual(result, expected)

    def test_new_layout_finds_models(self):
        expected = self._make("models", "robot.model")
        log_file = self._make("log", "d", "xxx.log")
        result = find_log_resource(log_file, "models", "robot.model")
        self.assertEqual(result, expected)

    def test_old_layout_log(self):
        """<root>/log/xxx.log finds <root>/maps/m.smap."""
        expected = self._make("maps", "m.smap")
        log_file = self._make("log", "xxx.log")
        result = find_log_resource(log_file, "maps", "m.smap")
        self.assertEqual(result, expected)

    def test_fallback_file_beside_log(self):
        expected = self._make("log", "m.smap")
        log_file = os.path.join(self.root, "log", "xxx.log")
        result = find_log_resource(log_file, "maps", "m.smap")
        self.assertEqual(result, expected)

    def test_not_found_returns_none(self):
        log_file = self._make("log", "xxx.log")
        self.assertIsNone(find_log_resource(log_file, "maps", "missing.smap"))

    @unittest.skipUnless(os.path.exists(REAL_LOG), "real robot log not available")
    def test_real_log_finds_maps(self):
        result = find_log_resource(REAL_LOG, "maps", "default.smap")
        self.assertIsNotNone(result)
        self.assertTrue(os.path.exists(result))
        self.assertEqual(os.path.basename(result), "default.smap")

    @unittest.skipUnless(os.path.exists(REAL_LOG), "real robot log not available")
    def test_real_log_finds_models(self):
        result = find_log_resource(REAL_LOG, "models", "robot.model")
        self.assertIsNotNone(result)
        self.assertTrue(os.path.exists(result))
        self.assertEqual(os.path.basename(result), "robot.model")


class TestGoodsHelpers(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = self._tmp.name
        self.model = os.path.join(self.root, 'models', 'robot.model')
        self.goods = os.path.join(self.root, 'objects', 'shelf', 'sg3.shelf')
        os.makedirs(os.path.dirname(self.model), exist_ok=True)
        os.makedirs(os.path.dirname(self.goods), exist_ok=True)
        with open(self.model, 'w') as fid:
            fid.write('{}')
        with open(self.goods, 'w') as fid:
            fid.write('''{
                "deviceParams": [{"arrayParam": {"params": [
                    {"key": "width", "doubleValue": 1.25},
                    {"key": "length", "doubleValue": 1.15}
                ]}}]
            }''')

    def test_find_goods_beside_models_directory(self):
        self.assertEqual(
            find_goods_resource(self.model, 'shelf/sg3.shelf'), self.goods)

    def test_find_goods_rejects_parent_traversal(self):
        self.assertIsNone(find_goods_resource(self.model, '../robot.model'))

    def test_read_goods_dimensions(self):
        self.assertEqual(read_goods_dimensions(self.goods), (1.15, 1.25))

    def test_interpolate_goods_pose_at_localization_time(self):
        start = datetime(2026, 7, 22, 8, 52, 54)
        times = [start, start + timedelta(seconds=2)]
        pose = interpolate_pose_at_time(
            times, [1.0, 3.0], [2.0, 6.0], [10.0, 30.0],
            start + timedelta(seconds=1))
        self.assertEqual(pose, (2.0, 4.0, 20.0))

    def test_interpolate_angle_across_180_degrees(self):
        start = datetime(2026, 7, 22, 8, 52, 54)
        pose = interpolate_pose_at_time(
            [start, start + timedelta(seconds=2)],
            [0.0, 0.0], [0.0, 0.0], [170.0, -170.0],
            start + timedelta(seconds=1))
        self.assertAlmostEqual(abs(pose[2]), 180.0)

    def test_pose_outside_range_uses_nearest_endpoint(self):
        start = datetime(2026, 7, 22, 8, 52, 54)
        pose = interpolate_pose_at_time(
            [start], [7.1], [2.2], [178.0], start - timedelta(seconds=1))
        self.assertEqual(pose, (7.1, 2.2, 178.0))

    def test_nearest_goods_name_supports_start_of_log(self):
        start = datetime(2026, 7, 22, 8, 52, 54)
        value = nearest_value_at_time(
            [start + timedelta(milliseconds=893)], ['shelf/sg3.shelf'], start)
        self.assertEqual(value, 'shelf/sg3.shelf')


class TestCurveHelpers(unittest.TestCase):
    def test_curve_points_to_xy_valid(self):
        points = [{"x": 1, "y": 2}, {"x": 3, "y": 4}]
        self.assertEqual(_curve_points_to_xy(points), ([1, 3], [2, 4]))

    def test_curve_points_to_xy_empty_list(self):
        self.assertEqual(_curve_points_to_xy([]), ([], []))

    def test_curve_points_to_xy_rejects_non_points(self):
        self.assertIsNone(_curve_points_to_xy({"x": 1, "y": 2}))
        self.assertIsNone(_curve_points_to_xy([{"x": 1}]))
        self.assertIsNone(_curve_points_to_xy([1, 2, 3]))

    def test_curve_polygons_to_xy_flattens_polygons(self):
        polygons = [
            {"type": "Polygon", "points": [
                {"x": 1, "y": 2}, {"x": 3, "y": 4}
            ], "radius": None},
            {"type": "Polygon", "points": [
                {"x": 5, "y": 6}, {"x": 7, "y": 8}
            ], "radius": None},
        ]
        x, y = _curve_polygons_to_xy(polygons)
        self.assertEqual(x, [1, 3, 5, 7])
        self.assertEqual(y, [2, 4, 6, 8])

    def test_curve_xy_values_valid(self):
        self.assertEqual(_curve_xy_values([1, 2], [3.0, 4.0]), ([1, 2], [3.0, 4.0]))

    def test_curve_xy_values_accepts_numpy(self):
        x, y = _curve_xy_values(np.arange(3), np.array([1.0, 2.0, 3.0]))
        self.assertEqual(len(x), 3)
        self.assertEqual(len(y), 3)

    def test_curve_xy_values_length_mismatch(self):
        with self.assertRaises(ValueError):
            _curve_xy_values([1, 2, 3], [1, 2])

    def test_curve_xy_values_non_numeric(self):
        with self.assertRaises(ValueError):
            _curve_xy_values([1, "a"], [1, 2])

    def test_curve_xy_values_rejects_strings(self):
        with self.assertRaises(ValueError):
            _curve_xy_values("ab", [1, 2])

    def test_curve_xy_values_rejects_scalars(self):
        with self.assertRaises(ValueError):
            _curve_xy_values(1, 2)

    def test_find_curve_xy_plain(self):
        self.assertEqual(_find_curve_xy({"x": [1], "y": [2]}), ([1], [2]))

    def test_find_curve_xy_pointx_pointy(self):
        self.assertEqual(_find_curve_xy({"pointx": [1], "pointy": [2]}), ([1], [2]))

    def test_find_curve_xy_underscore_names(self):
        self.assertEqual(_find_curve_xy({"point_x": [1], "point_y": [2]}), ([1], [2]))

    def test_find_curve_xy_missing(self):
        with self.assertRaises(ValueError):
            _find_curve_xy({"foo": [1, 2]})


class TestParseCurveData(unittest.TestCase):
    def test_json_point_array(self):
        x, y = parse_curve_data('[{"x": 1, "y": 2}, {"x": 3, "y": 4}]')
        self.assertEqual((x, y), ([1, 3], [2, 4]))

    def test_python_literal_point_array(self):
        x, y = parse_curve_data("[{'x': 1, 'y': 2}, {'x': 3, 'y': 4}]")
        self.assertEqual((x, y), ([1, 3], [2, 4]))

    def test_json_polygon_array(self):
        source = '''[
            {"type": "Polygon", "points": [
                {"x": 0.78417, "y": -24.06445},
                {"x": -1.61261, "y": -24.02261},
                {"x": -1.5908, "y": -22.7728},
                {"x": 0.80599, "y": -22.81464}
            ], "radius": null},
            {"type": "Polygon", "points": [
                {"x": 0.76735, "y": -24.21293},
                {"x": -2.02937, "y": -24.16411},
                {"x": -2.00232, "y": -22.61435},
                {"x": 0.79441, "y": -22.66316}
            ], "radius": null}
        ]'''
        x, y = parse_curve_data(source)
        self.assertEqual(x, [0.78417, -1.61261, -1.5908, 0.80599,
                             0.76735, -2.02937, -2.00232, 0.79441])
        self.assertEqual(y, [-24.06445, -24.02261, -22.7728, -22.81464,
                             -24.21293, -24.16411, -22.61435, -22.66316])

    def test_xy_variables(self):
        x, y = parse_curve_data("x = [1, 2, 3]\ny = [4, 5, 6]")
        self.assertEqual((x, y), ([1, 2, 3], [4, 5, 6]))

    def test_pointx_pointy_variables(self):
        x, y = parse_curve_data("pointx = [1, 2]\npointy = [3, 4]")
        self.assertEqual((x, y), ([1, 2], [3, 4]))

    def test_numpy_expression(self):
        x, y = parse_curve_data("x = np.arange(3)\ny = [1, 2, 3]")
        self.assertEqual(list(x), [0, 1, 2])
        self.assertEqual(y, [1, 2, 3])

    def test_empty_input(self):
        with self.assertRaises(ValueError):
            parse_curve_data("   ")

    def test_length_mismatch(self):
        with self.assertRaises(ValueError):
            parse_curve_data("x = [1, 2, 3]\ny = [1, 2]")

    def test_non_numeric(self):
        with self.assertRaises(ValueError):
            parse_curve_data("x = [1, 'a']\ny = [1, 2]")

    def test_missing_xy(self):
        with self.assertRaises(ValueError):
            parse_curve_data("foo = [1, 2]")

    def test_invalid_json_array(self):
        with self.assertRaises(ValueError):
            parse_curve_data('[{"x": 1}]')


if __name__ == "__main__":
    unittest.main()
