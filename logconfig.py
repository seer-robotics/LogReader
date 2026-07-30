import json
import os
import tempfile


class LogConfigError(ValueError):
    pass


def _rule_name_from_entry(entry):
    rule_type = entry.get('type')
    if rule_type == 'Text':
        return entry.get('textKey', '')
    if isinstance(rule_type, str):
        return rule_type
    return ''


def validate_log_config_entry(name, entry):
    """Validate one top-level log_config.json entry."""
    if not isinstance(name, str) or not name.strip():
        raise LogConfigError('配置名称不能为空')
    if not isinstance(entry, dict):
        raise LogConfigError('{}: 规则必须是 JSON 对象'.format(name))
    if 'type' not in entry or 'content' not in entry:
        raise LogConfigError('{}: 缺少 type 或 content'.format(name))

    rule_type = entry['type']
    if isinstance(rule_type, str):
        if not rule_type:
            raise LogConfigError('{}: type 不能为空'.format(name))
    elif isinstance(rule_type, list):
        if not rule_type or not all(
                isinstance(item, str) and item for item in rule_type):
            raise LogConfigError('{}: type 列表包含无效值'.format(name))
    else:
        raise LogConfigError('{}: type 必须是字符串或字符串列表'.format(name))

    if rule_type == 'Text':
        text_key = entry.get('textKey')
        if not isinstance(text_key, str) or not text_key:
            raise LogConfigError('{}: Text 规则必须包含 textKey'.format(name))

    content = entry['content']
    if isinstance(content, str):
        if content not in ('key|value', 'path'):
            raise LogConfigError(
                '{}: content 字符串仅支持 key|value 或 path'.format(name))
        return
    if not isinstance(content, list) or not content:
        raise LogConfigError('{}: content 必须是非空字段列表'.format(name))

    field_names = set()
    for position, field in enumerate(content):
        if not isinstance(field, dict):
            raise LogConfigError(
                '{}: content[{}] 必须是对象'.format(name, position))
        field_name = field.get('name')
        field_type = field.get('type')
        if not isinstance(field_name, str) or not field_name:
            raise LogConfigError(
                '{}: content[{}].name 不能为空'.format(name, position))
        if field_name in field_names:
            raise LogConfigError(
                '{}: 字段 {} 重复'.format(name, field_name))
        field_names.add(field_name)
        if not isinstance(field_type, str) or not field_type:
            raise LogConfigError(
                '{}: 字段 {} 缺少 type'.format(name, field_name))
        if 'index' in field:
            index = field['index']
            if isinstance(index, bool) or not isinstance(index, int):
                raise LogConfigError(
                    '{}: 字段 {} 的 index 必须是整数'.format(
                        name, field_name))


def normalize_log_config_payload(payload, config_name=''):
    """Normalize a single rule or a mapping of named rules."""
    if not isinstance(payload, dict) or not payload:
        raise LogConfigError('JSON 顶层必须是非空对象')

    config_name = config_name.strip()
    if 'type' in payload or 'content' in payload:
        name = config_name or _rule_name_from_entry(payload)
        validate_log_config_entry(name, payload)
        return {name: payload}

    entries = {}
    for name, entry in payload.items():
        validate_log_config_entry(name, entry)
        entries[name] = entry
    return entries


def parse_log_config_text(text, config_name=''):
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise LogConfigError(
            'JSON 格式错误（第 {} 行，第 {} 列）：{}'.format(
                exc.lineno, exc.colno, exc.msg)) from exc
    return normalize_log_config_payload(payload, config_name)


def load_log_config(path):
    try:
        with open(path, encoding='utf-8') as stream:
            config = json.load(stream)
    except FileNotFoundError as exc:
        raise LogConfigError('配置文件不存在：{}'.format(path)) from exc
    except json.JSONDecodeError as exc:
        raise LogConfigError(
            '配置文件 JSON 无效（第 {} 行，第 {} 列）：{}'.format(
                exc.lineno, exc.colno, exc.msg)) from exc
    if not isinstance(config, dict):
        raise LogConfigError('配置文件顶层必须是对象：{}'.format(path))
    return config


def append_log_config_entries(path, entries):
    """Append named entries and atomically rewrite the JSON document."""
    if not isinstance(entries, dict) or not entries:
        raise LogConfigError('没有可添加的日志解释规则')
    for name, entry in entries.items():
        validate_log_config_entry(name, entry)

    config = load_log_config(path)
    duplicates = [name for name in entries if name in config]
    if duplicates:
        raise LogConfigError(
            '配置名称已存在：{}'.format(', '.join(duplicates)))

    config.update(entries)
    absolute_path = os.path.abspath(path)
    config_dir = os.path.dirname(absolute_path)
    file_descriptor, temporary_path = tempfile.mkstemp(
        prefix='.log_config_', suffix='.tmp', dir=config_dir, text=True)
    try:
        with os.fdopen(file_descriptor, 'w', encoding='utf-8',
                       newline='\n') as stream:
            json.dump(config, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_path, absolute_path)
    except Exception:
        try:
            os.unlink(temporary_path)
        except FileNotFoundError:
            pass
        raise
    return config
