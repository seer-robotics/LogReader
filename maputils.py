# -*- coding: utf-8 -*-
"""Pure (GUI-free) utility functions extracted from MapWidget.py.

This module holds logic that does not depend on PyQt5 or matplotlib:
coordinate-frame transforms, laser-point conversion, theta normalization,
curve-data parsing and log-resource lookup.  Keep it free of GUI imports so
it stays unit-testable without a display.
"""
import os
import math
import ast
import hashlib
import json as js
from pathlib import Path

import numpy as np


def find_log_resource(log_file, resource_dir, filename):
    """查找与日志目录配套的地图、模型等资源文件。"""
    log_dir = os.path.dirname(log_file)
    parent_dir = os.path.dirname(log_dir)

    # 新版目录可能为 <root>/log/d，资源仍位于 <root>/maps 或 <root>/models。
    if (os.path.basename(log_dir).lower() == 'd'
            and os.path.basename(parent_dir).lower() == 'log'):
        root_dir = os.path.dirname(parent_dir)
        candidates = [
            os.path.join(root_dir, resource_dir, filename),
            os.path.join(parent_dir, resource_dir, filename),
        ]
    else:
        candidates = [os.path.join(parent_dir, resource_dir, filename)]

    candidates.extend([
        os.path.join(log_dir, filename),
        os.path.join(log_dir, resource_dir, filename),
    ])
    for candidate in candidates:
        if os.path.exists(candidate):
            return candidate
    return None


def get_md5_pathlib(path: Path, block_size=65536):
    """
    使用 pathlib 计算文件的MD5值（分块读取）。

    Args:
        filepath (Path): 文件的Path对象。
        block_size (int): 每次读取的字节数（默认64KB）。

    Returns:
        str: 文件的MD5哈希值，如果文件不存在则返回"文件未找到"，如果发生其他错误则返回错误信息。
    """
    from pathlib import Path
    filepath = Path(path)
    md5_hash = hashlib.md5()
    try:
        if not filepath.is_file():
            return "文件未找到"
        with filepath.open('rb') as f:
            while True:
                data = f.read(block_size)
                if not data:
                    break
                md5_hash.update(data)
        return md5_hash.hexdigest()
    except Exception as e:
        return f"发生错误: {e}"

def GetGlobalPos(p2b, b2g):
    x = p2b[0] * np.cos(b2g[2]) - p2b[1] * np.sin(b2g[2])
    y = p2b[0] * np.sin(b2g[2]) + p2b[1] * np.cos(b2g[2])
    x = x + b2g[0]
    y = y + b2g[1]
    return np.array([x, y])

def P2G(p2b, b2g):
    x = p2b[0] * np.cos(b2g[2]) - p2b[1] * np.sin(b2g[2])
    y = p2b[0] * np.sin(b2g[2]) + p2b[1] * np.cos(b2g[2])
    x = x + b2g[0]
    y = y + b2g[1]
    a = p2b[2] + b2g[2]
    return np.array([x, y, a])    

def Pos2Base(pos2world, base2world):
    pos2base = [0,0,0]
    x = pos2world[0] - base2world[0]
    y = pos2world[1] - base2world[1]
    pos2base[0] = x * np.cos(base2world[2]) + y * np.sin(base2world[2])
    pos2base[1] = -x * np.sin(base2world[2]) + y * np.cos(base2world[2])
    pos2base[2] = pos2world[2] - base2world[2]
    return pos2base

def convert2LaserPoints(org_laser_data, org_laser_pos, robot_pos):
    laser_data = GetGlobalPos(org_laser_data, org_laser_pos)
    laser_data2r = laser_data.T
    laser_data = GetGlobalPos(laser_data, robot_pos)
    laser_data = laser_data.T
    laser_pos = GetGlobalPos(org_laser_pos, robot_pos) # n*2
    circle_cs = laser_data
    c = np.zeros(laser_data.shape) + laser_pos
    org_lines = np.concatenate((c,laser_data), axis=1) #水平扩展
    lines = org_lines.reshape(laser_data.shape[0],2,2)
    return lines, circle_cs, laser_data2r

def normalize_theta(theta):
    if theta >= -math.pi and theta < math.pi:
        return theta
    multiplier = math.floor(theta / (2 * math.pi))
    theta = theta - multiplier * 2 * math.pi
    if theta >= math.pi:
        theta = theta - 2 * math.pi
    if theta < -math.pi:
        theta = theta + 2 * math.pi
    return theta

def normalize_theta_deg(theta):
    return normalize_theta(theta/180.0*math.pi)/math.pi*180.0


def _curve_points_to_xy(value):
    """Return x/y sequences when *value* is an array of point objects."""
    if not isinstance(value, (list, tuple)):
        return None
    if not value:
        return [], []
    if not all(isinstance(point, dict) and 'x' in point and 'y' in point
               for point in value):
        return None
    return ([point['x'] for point in value],
            [point['y'] for point in value])


def _curve_xy_values(x, y):
    """Validate and normalize two coordinate sequences for matplotlib."""
    if isinstance(x, (str, bytes)) or isinstance(y, (str, bytes)):
        raise ValueError("curve coordinates must be sequences")
    try:
        x = list(x)
        y = list(y)
    except TypeError:
        raise ValueError("curve coordinates must be sequences")
    if len(x) != len(y):
        raise ValueError("x and y must contain the same number of points")
    if not all(isinstance(value, (int, float, np.number)) for value in x + y):
        raise ValueError("curve coordinates must be numeric")
    return x, y


def _find_curve_xy(namespace):
    """Find x/y variables, including names such as ``pointx``/``pointy``."""
    values = {name: value for name, value in namespace.items()
              if isinstance(name, str) and not name.startswith('_')}
    if 'x' in values and 'y' in values:
        return values['x'], values['y']

    x_names = [name for name in values if 'x' in name.lower()]
    y_names = [name for name in values if 'y' in name.lower()]
    # Prefer the natural counterpart formed by changing the final x/y.
    for x_name in x_names:
        lower_x = x_name.lower()
        if lower_x.endswith('x'):
            for y_name in y_names:
                if y_name.lower() == lower_x[:-1] + 'y':
                    return values[x_name], values[y_name]
    # Fall back to a pair with the longest common prefix, which handles
    # names such as ``point_x``/``point_y`` as well.
    pairs = [(len(os.path.commonprefix((x_name.lower(), y_name.lower()))),
              x_name, y_name)
             for x_name in x_names for y_name in y_names]
    if pairs:
        _, x_name, y_name = max(pairs)
        return values[x_name], values[y_name]
    raise ValueError("curve input must define x/y coordinates")


def parse_curve_data(text):
    """Parse curve input in x/y-variable or JSON point-array form."""
    source = text.strip()
    if not source:
        raise ValueError("curve input is empty")

    # JSON point arrays are the most direct representation.  Try the whole
    # input first, then the bracketed portion so pasted labels such as
    # ``json: [...]`` do not prevent parsing.  literal_eval additionally
    # accepts single-quoted keys and trailing commas.
    json_candidates = [source]
    start = source.find('[')
    end = source.rfind(']')
    if start > 0 and end > start:
        json_candidates.append(source[start:end + 1])
    for candidate in json_candidates:
        for loader in (js.loads, ast.literal_eval):
            try:
                parsed = loader(candidate)
            except (ValueError, SyntaxError, TypeError):
                continue
            point_data = _curve_points_to_xy(parsed)
            if point_data is not None:
                return _curve_xy_values(*point_data)

    # Do not execute JSON-like input as Python.  Apart from being unsafe,
    # this produces confusing annotation errors for malformed pasted JSON.
    if source.startswith(('[', '{')):
        raise ValueError("invalid JSON curve point array")

    namespace = {}
    exec(source, globals(), namespace)
    return _curve_xy_values(*_find_curve_xy(namespace))
