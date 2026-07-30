# -*- coding: utf-8 -*-
import json
import os
import tempfile
import unittest

from logconfig import (
    LogConfigError,
    append_log_config_entries,
    parse_log_config_text,
)


class TestLogConfigPayload(unittest.TestCase):
    def test_single_rule_infers_name_from_type(self):
        entries = parse_log_config_text(json.dumps({
            'type': 'DynamicState',
            'content': [{'name': 'value', 'type': 'double'}],
        }))

        self.assertEqual(['DynamicState'], list(entries))

    def test_named_payload_accepts_multiple_rules(self):
        entries = parse_log_config_text(json.dumps({
            'First': {
                'type': 'First',
                'content': [{'name': 'value', 'type': 'double'}],
            },
            'Second': {'type': 'Second', 'content': 'key|value'},
        }))

        self.assertEqual(['First', 'Second'], list(entries))

    def test_text_rule_requires_text_key(self):
        with self.assertRaisesRegex(LogConfigError, 'textKey'):
            parse_log_config_text(json.dumps({
                'type': 'Text',
                'content': [{'name': 'value', 'type': 'double'}],
            }), 'TextRule')

    def test_rejects_duplicate_field_names(self):
        with self.assertRaisesRegex(LogConfigError, '重复'):
            parse_log_config_text(json.dumps({
                'type': 'DynamicState',
                'content': [
                    {'name': 'value', 'type': 'double'},
                    {'name': 'value', 'type': 'double'},
                ],
            }))


class TestAppendLogConfig(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_path = os.path.join(
            self.temp_dir.name, 'log_config.json')
        with open(self.config_path, 'w', encoding='utf-8') as stream:
            json.dump({
                'Existing': {
                    'type': 'Existing',
                    'content': [{'name': 'value', 'type': 'double'}],
                },
            }, stream)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_appends_entry_at_end_and_keeps_unicode(self):
        append_log_config_entries(self.config_path, {
            '新规则': {
                'type': 'DynamicState',
                'content': [{
                    'name': 'value', 'type': 'double',
                    'description': '动态值',
                }],
            },
        })

        with open(self.config_path, encoding='utf-8') as stream:
            text = stream.read()
        parsed = json.loads(text)
        self.assertEqual(['Existing', '新规则'], list(parsed))
        self.assertIn('动态值', text)

    def test_duplicate_does_not_modify_file(self):
        with open(self.config_path, 'rb') as stream:
            before = stream.read()

        with self.assertRaisesRegex(LogConfigError, '已存在'):
            append_log_config_entries(self.config_path, {
                'Existing': {
                    'type': 'Existing',
                    'content': [{'name': 'other', 'type': 'double'}],
                },
            })

        with open(self.config_path, 'rb') as stream:
            self.assertEqual(before, stream.read())


if __name__ == '__main__':
    unittest.main()
