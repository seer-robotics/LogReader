# -*- coding: utf-8 -*-
"""Pure helpers for reading robot parameter databases."""
from dataclasses import dataclass
import os
from pathlib import Path
import sqlite3

from maputils import find_log_resource


UNUSED_DEFAULT_VALUE = '_default_value_'


@dataclass(frozen=True)
class ParameterRecord:
    module: str
    key: str
    value: str
    default_value: str
    type_name: str
    mutable: bool


def find_parameter_database(log_files):
    """Find ``params/robot.param`` associated with one of the log files."""
    for log_file in log_files or []:
        database_path = find_log_resource(log_file, 'params', 'robot.param')
        if database_path:
            return database_path
    return None


def _quote_identifier(identifier):
    return '"{}"'.format(str(identifier).replace('"', '""'))


def read_parameter_database(database_path):
    """Read all supported parameter tables through a read-only connection."""
    if not database_path or not os.path.isfile(database_path):
        raise FileNotFoundError(database_path)

    uri = Path(database_path).resolve().as_uri() + '?mode=ro'
    connection = sqlite3.connect(uri, uri=True)
    try:
        connection.execute('PRAGMA query_only = ON')
        tables = connection.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type = 'table' AND name NOT LIKE 'sqlite_%' "
            "ORDER BY name COLLATE NOCASE"
        ).fetchall()

        records = []
        required_columns = ('key', 'type', 'value', 'mutable', 'defaultvalue')
        for (table_name,) in tables:
            quoted_table = _quote_identifier(table_name)
            table_info = connection.execute(
                'PRAGMA table_info({})'.format(quoted_table)).fetchall()
            columns = {str(row[1]).lower(): str(row[1]) for row in table_info}
            if not all(column in columns for column in required_columns):
                continue

            selected_columns = [
                _quote_identifier(columns[column]) for column in required_columns
            ]
            query = 'SELECT {} FROM {}'.format(
                ', '.join(selected_columns), quoted_table)
            for key, type_name, value, mutable, default_value in connection.execute(query):
                if (default_value is not None
                        and str(default_value).strip() == UNUSED_DEFAULT_VALUE):
                    continue
                records.append(ParameterRecord(
                    module=str(table_name),
                    key='' if key is None else str(key),
                    value='' if value is None else str(value),
                    default_value='' if default_value is None else str(default_value),
                    type_name='' if type_name is None else str(type_name),
                    mutable=bool(mutable),
                ))
    finally:
        connection.close()

    records.sort(key=lambda record: (record.module.lower(), record.key.lower()))
    return records
