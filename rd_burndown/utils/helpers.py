"""汎用ヘルパー関数"""

import os
from pathlib import Path
from typing import Any, Optional, Union


def ensure_directory(directory_path: Union[str, Path]) -> Path:
    """ディレクトリの存在確認・作成"""
    path = Path(directory_path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def safe_get_nested(data: dict[str, Any], keys: list[str], default: Any = None) -> Any:
    """ネストした辞書から安全に値を取得"""
    current: Any = data
    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return default
    return current


def safe_float(value: Any, default: float = 0.0) -> float:
    """安全なfloat変換"""
    if value is None:
        return default

    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def safe_int(value: Any, default: int = 0) -> int:
    """安全なint変換"""
    if value is None:
        return default

    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def format_hours(hours: float, precision: int = 1) -> str:
    """工数フォーマット"""
    if hours == 0:
        return "0h"
    if hours < 1:
        return f"{hours:.{precision}f}h"
    return f"{hours:.{precision}f}h"


def format_percentage(value: float, precision: int = 1) -> str:
    """パーセンテージフォーマット"""
    return f"{value:.{precision}f}%"


def truncate_string(text: str, max_length: int, suffix: str = "...") -> str:
    """文字列切り詰め"""
    if len(text) <= max_length:
        return text

    return text[: max_length - len(suffix)] + suffix


def get_file_size(file_path: Union[str, Path]) -> int:
    """ファイルサイズ取得（バイト）"""
    try:
        return os.path.getsize(file_path)
    except (OSError, FileNotFoundError):
        return 0


def format_file_size(size_bytes: int) -> str:
    """ファイルサイズフォーマット"""
    if size_bytes == 0:
        return "0B"

    size_names = ["B", "KB", "MB", "GB"]
    size = float(size_bytes)
    unit_index = 0

    while size >= 1024.0 and unit_index < len(size_names) - 1:
        size /= 1024.0
        unit_index += 1

    return f"{size:.1f}{size_names[unit_index]}"


def validate_project_id(project_id: Any) -> Optional[int]:
    """プロジェクトID検証"""
    try:
        pid = int(project_id)
        return pid if pid > 0 else None
    except (ValueError, TypeError):
        return None


def parse_date_range(date_string: str) -> Optional[dict[str, str]]:
    """日付範囲文字列をパース（例: "2024-01-01:2024-01-31"）"""
    if ":" not in date_string:
        return None

    try:
        start_str, end_str = date_string.split(":", 1)
        return {"start": start_str.strip(), "end": end_str.strip()}
    except ValueError:
        return None


def chunks(data: list[Any], chunk_size: int) -> list[list[Any]]:
    """リストをチャンクに分割"""
    result: list[list[Any]] = []
    for i in range(0, len(data), chunk_size):
        result.append(data[i : i + chunk_size])
    return result


def filter_dict(data: dict[str, Any], keys: list[str]) -> dict[str, Any]:
    """辞書から指定キーのみを抽出"""
    return {key: data[key] for key in keys if key in data}


def deep_merge(dict1: dict[str, Any], dict2: dict[str, Any]) -> dict[str, Any]:
    """辞書の深いマージ"""
    result = dict1.copy()

    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value

    return result


def extract_redmine_id(url_or_id: str) -> Optional[int]:
    """RedmineのURLまたはIDからID部分を抽出"""
    if url_or_id.isdigit():
        return int(url_or_id)

    # URL形式の場合
    import re

    match = re.search(r"/(?:projects|issues)/(\d+)", url_or_id)
    if match:
        return int(match.group(1))

    return None
