# -*- coding: utf-8 -*-
import json
import os
import tempfile
import unittest
from types import SimpleNamespace

from ReadThread import ReadThread


class TestReadThreadReport(unittest.TestCase):
    def test_report_output_is_disabled(self):
        reader = ReadThread()

        self.assertEqual('', reader.getReportFileAddr())


class TestDynamicLogConfig(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_path = os.path.join(
            self.temp_dir.name, 'log_config.json')
        with open(self.config_path, 'w', encoding='utf-8') as stream:
            json.dump({}, stream)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_adds_and_parses_rule_from_loaded_lines(self):
        reader = ReadThread()
        reader.reader = SimpleNamespace(lines=[
            '[260728 153405.493][1][MF][d] '
            '[DynamicState][1.5|true]\n',
        ])
        entry = {
            'DynamicState': {
                'type': 'DynamicState',
                'content': [
                    {'name': 'value', 'type': 'double'},
                    {'name': 'enabled', 'type': 'bool'},
                ],
            },
        }

        new_series = reader.add_log_configs(entry, self.config_path)

        self.assertEqual(
            ['DynamicState.value', 'DynamicState.enabled'], new_series)
        self.assertEqual([1.5], reader.getData('DynamicState.value')[0])
        self.assertEqual([1.0], reader.getData('DynamicState.enabled')[0])
        self.assertTrue(reader.content['DynamicState'].parsed_flag)
        with open(self.config_path, encoding='utf-8') as stream:
            self.assertIn('DynamicState', json.load(stream))

    def test_dynamic_key_value_rule_registers_discovered_fields(self):
        reader = ReadThread()
        reader.reader = SimpleNamespace(lines=[
            '[260728 153405.493][1][MF][d] '
            '[DynamicCost][solve|12|publish|3]\n',
        ])

        new_series = reader.add_log_configs({
            'DynamicCost': {
                'type': 'DynamicCost',
                'content': 'key|value',
            },
        }, self.config_path)

        self.assertEqual(
            ['DynamicCost.solve', 'DynamicCost.publish'], new_series)
        self.assertEqual([12.0], reader.getData('DynamicCost.solve')[0])

    def test_requires_loaded_log(self):
        reader = ReadThread()

        with self.assertRaisesRegex(RuntimeError, '先加载日志'):
            reader.add_log_configs({
                'DynamicState': {
                    'type': 'DynamicState',
                    'content': [{'name': 'value', 'type': 'double'}],
                },
            }, self.config_path)


if __name__ == '__main__':
    unittest.main()
