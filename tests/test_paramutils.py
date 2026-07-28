# -*- coding: utf-8 -*-
import os
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from paramutils import find_parameter_database, read_parameter_database


class TestParameterDatabase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = self._tmp.name
        self.log_file = os.path.join(self.root, 'log', 'robot.log')
        self.database_path = os.path.join(self.root, 'params', 'robot.param')
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
        os.makedirs(os.path.dirname(self.database_path), exist_ok=True)
        with open(self.log_file, 'w') as fid:
            fid.write('')
        connection = sqlite3.connect(self.database_path)
        connection.execute(
            'CREATE TABLE MoveFactory ('
            'Key TEXT, Type TEXT, Value TEXT, Mutable BOOLEAN, '
            'DefaultValue TEXT)')
        connection.executemany(
            'INSERT INTO MoveFactory VALUES (?, ?, ?, ?, ?)',
            [
                ('MaxSpeed', 'd', '1.0', 1, '1.0'),
                ('MaxAcc', 'd', '0.6', 1, '1.0'),
                ('UnusedSpeed', 'd', '2.0', 1, '_default_value_'),
            ])
        connection.execute('CREATE TABLE Unsupported (Name TEXT)')
        connection.commit()
        connection.close()

    def test_finds_database_beside_log_directory(self):
        self.assertEqual(
            find_parameter_database([self.log_file]), self.database_path)

    def test_reads_supported_tables(self):
        records = read_parameter_database(self.database_path)
        self.assertEqual(len(records), 2)
        self.assertEqual(records[0].module, 'MoveFactory')
        self.assertEqual(records[0].key, 'MaxAcc')
        self.assertEqual(records[1].key, 'MaxSpeed')
        self.assertEqual(records[1].value, '1.0')
        self.assertTrue(records[1].mutable)
        self.assertNotIn('UnusedSpeed', [record.key for record in records])

    def test_missing_database_raises(self):
        with self.assertRaises(FileNotFoundError):
            read_parameter_database(os.path.join(self.root, 'missing.param'))


if __name__ == '__main__':
    unittest.main()
