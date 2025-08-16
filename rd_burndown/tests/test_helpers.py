"""ヘルパー関数のテスト"""

import os
import tempfile
from pathlib import Path

from rd_burndown.utils.helpers import (
    chunks,
    deep_merge,
    ensure_directory,
    extract_redmine_id,
    filter_dict,
    format_file_size,
    format_hours,
    format_percentage,
    get_file_size,
    parse_date_range,
    safe_float,
    safe_get_nested,
    safe_int,
    truncate_string,
    validate_project_id,
)


class TestEnsureDirectory:
    """ensure_directory のテスト"""

    def test_create_new_directory(self):
        """新規ディレクトリ作成のテスト"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            new_dir = Path(tmp_dir) / "new_directory"

            result = ensure_directory(new_dir)

            assert new_dir.exists()
            assert new_dir.is_dir()
            assert result == new_dir

    def test_existing_directory(self):
        """既存ディレクトリのテスト"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            existing_dir = Path(tmp_dir)

            result = ensure_directory(existing_dir)

            assert existing_dir.exists()
            assert result == existing_dir

    def test_create_nested_directories(self):
        """ネストしたディレクトリ作成のテスト"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            nested_dir = Path(tmp_dir) / "level1" / "level2" / "level3"

            result = ensure_directory(nested_dir)

            assert nested_dir.exists()
            assert nested_dir.is_dir()
            assert result == nested_dir

    def test_string_path(self):
        """文字列パスのテスト"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            new_dir_str = str(Path(tmp_dir) / "string_dir")

            result = ensure_directory(new_dir_str)

            assert Path(new_dir_str).exists()
            assert isinstance(result, Path)


class TestSafeGetNested:
    """safe_get_nested のテスト"""

    def test_simple_key(self):
        """単純キーのテスト"""
        data = {"a": "value"}
        result = safe_get_nested(data, ["a"])
        assert result == "value"

    def test_nested_keys(self):
        """ネストしたキーのテスト"""
        data = {"a": {"b": {"c": "nested_value"}}}
        result = safe_get_nested(data, ["a", "b", "c"])
        assert result == "nested_value"

    def test_missing_key_returns_default(self):
        """存在しないキーのテスト"""
        data = {"a": "value"}
        result = safe_get_nested(data, ["b"], "default")
        assert result == "default"

    def test_missing_nested_key(self):
        """存在しないネストキーのテスト"""
        data = {"a": {"b": "value"}}
        result = safe_get_nested(data, ["a", "c"], "default")
        assert result == "default"

    def test_none_default(self):
        """Noneデフォルトのテスト"""
        data = {"a": "value"}
        result = safe_get_nested(data, ["b"])
        assert result is None

    def test_empty_keys(self):
        """空キーリストのテスト"""
        data = {"a": "value"}
        result = safe_get_nested(data, [])
        assert result == data


class TestSafeFloat:
    """safe_float のテスト"""

    def test_valid_float(self):
        """有効なfloat値のテスト"""
        assert safe_float(3.14) == 3.14
        assert safe_float("2.5") == 2.5
        assert safe_float(42) == 42.0

    def test_none_value(self):
        """None値のテスト"""
        assert safe_float(None) == 0.0
        assert safe_float(None, 5.0) == 5.0

    def test_invalid_value(self):
        """無効な値のテスト"""
        assert safe_float("invalid") == 0.0
        assert safe_float("invalid", 10.0) == 10.0

    def test_empty_string(self):
        """空文字列のテスト"""
        assert safe_float("") == 0.0


class TestSafeInt:
    """safe_int のテスト"""

    def test_valid_int(self):
        """有効なint値のテスト"""
        assert safe_int(42) == 42
        assert safe_int("123") == 123
        assert safe_int(3.14) == 3

    def test_none_value(self):
        """None値のテスト"""
        assert safe_int(None) == 0
        assert safe_int(None, 5) == 5

    def test_invalid_value(self):
        """無効な値のテスト"""
        assert safe_int("invalid") == 0
        assert safe_int("invalid", 10) == 10


class TestFormatHours:
    """format_hours のテスト"""

    def test_zero_hours(self):
        """0時間のテスト"""
        assert format_hours(0) == "0h"

    def test_small_hours(self):
        """1時間未満のテスト"""
        assert format_hours(0.5) == "0.5h"
        assert format_hours(0.25, 2) == "0.25h"

    def test_regular_hours(self):
        """通常時間のテスト"""
        assert format_hours(8.0) == "8.0h"
        assert format_hours(16.5) == "16.5h"

    def test_precision(self):
        """精度のテスト"""
        assert format_hours(8.123, 2) == "8.12h"
        assert format_hours(8.999, 0) == "9h"


class TestFormatPercentage:
    """format_percentage のテスト"""

    def test_whole_number(self):
        """整数のテスト"""
        assert format_percentage(50.0) == "50.0%"

    def test_decimal(self):
        """小数のテスト"""
        assert format_percentage(33.333) == "33.3%"
        assert format_percentage(33.333, 2) == "33.33%"

    def test_zero(self):
        """0のテスト"""
        assert format_percentage(0.0) == "0.0%"


class TestTruncateString:
    """truncate_string のテスト"""

    def test_short_string(self):
        """短い文字列のテスト"""
        text = "short"
        result = truncate_string(text, 10)
        assert result == "short"

    def test_exact_length(self):
        """ちょうどの長さのテスト"""
        text = "exactly10c"
        result = truncate_string(text, 10)
        assert result == "exactly10c"

    def test_long_string(self):
        """長い文字列のテスト"""
        text = "this is a very long string"
        result = truncate_string(text, 10)
        assert result == "this is..."
        assert len(result) == 10

    def test_custom_suffix(self):
        """カスタム接尾辞のテスト"""
        text = "long string"
        result = truncate_string(text, 8, suffix=">>>")
        assert result == "long >>>"
        assert len(result) == 8  # 切り詰め後の長さチェック


class TestGetFileSize:
    """get_file_size のテスト"""

    def test_existing_file(self):
        """存在するファイルのテスト"""
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as tmp_file:
            tmp_file.write("test content")
            tmp_file.flush()

            size = get_file_size(tmp_file.name)
            assert size > 0

            os.unlink(tmp_file.name)

    def test_nonexistent_file(self):
        """存在しないファイルのテスト"""
        size = get_file_size("/nonexistent/file.txt")
        assert size == 0

    def test_directory(self):
        """ディレクトリのテスト"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            size = get_file_size(tmp_dir)
            # ディレクトリサイズは0またはプラットフォーム依存
            assert size >= 0


class TestFormatFileSize:
    """format_file_size のテスト"""

    def test_zero_bytes(self):
        """0バイトのテスト"""
        assert format_file_size(0) == "0B"

    def test_bytes(self):
        """バイト単位のテスト"""
        assert format_file_size(512) == "512.0B"

    def test_kilobytes(self):
        """キロバイト単位のテスト"""
        assert format_file_size(1024) == "1.0KB"
        assert format_file_size(1536) == "1.5KB"

    def test_megabytes(self):
        """メガバイト単位のテスト"""
        assert format_file_size(1024 * 1024) == "1.0MB"
        assert format_file_size(int(2.5 * 1024 * 1024)) == "2.5MB"

    def test_gigabytes(self):
        """ギガバイト単位のテスト"""
        assert format_file_size(1024 * 1024 * 1024) == "1.0GB"


class TestValidateProjectId:
    """validate_project_id のテスト"""

    def test_valid_integer(self):
        """有効な整数のテスト"""
        assert validate_project_id(1) == 1
        assert validate_project_id(123) == 123

    def test_valid_string_integer(self):
        """有効な文字列整数のテスト"""
        assert validate_project_id("1") == 1
        assert validate_project_id("123") == 123

    def test_zero_or_negative(self):
        """0または負の数のテスト"""
        assert validate_project_id(0) is None
        assert validate_project_id(-1) is None

    def test_invalid_value(self):
        """無効な値のテスト"""
        assert validate_project_id("invalid") is None
        assert validate_project_id(None) is None
        assert validate_project_id(3.14) == 3  # floatは変換される


class TestParseDateRange:
    """parse_date_range のテスト"""

    def test_valid_range(self):
        """有効な範囲のテスト"""
        result = parse_date_range("2024-01-01:2024-01-31")
        expected = {"start": "2024-01-01", "end": "2024-01-31"}
        assert result == expected

    def test_with_spaces(self):
        """スペース付きのテスト"""
        result = parse_date_range("2024-01-01 : 2024-01-31 ")
        expected = {"start": "2024-01-01", "end": "2024-01-31"}
        assert result == expected

    def test_no_colon(self):
        """コロンなしのテスト"""
        result = parse_date_range("2024-01-01")
        assert result is None

    def test_empty_string(self):
        """空文字列のテスト"""
        result = parse_date_range("")
        assert result is None


class TestChunks:
    """chunks のテスト"""

    def test_even_division(self):
        """均等分割のテスト"""
        data = [1, 2, 3, 4, 5, 6]
        result = list(chunks(data, 2))
        expected = [[1, 2], [3, 4], [5, 6]]
        assert result == expected

    def test_uneven_division(self):
        """不均等分割のテスト"""
        data = [1, 2, 3, 4, 5]
        result = list(chunks(data, 2))
        expected = [[1, 2], [3, 4], [5]]
        assert result == expected

    def test_larger_chunk_size(self):
        """大きなチャンクサイズのテスト"""
        data = [1, 2, 3]
        result = list(chunks(data, 5))
        expected = [[1, 2, 3]]
        assert result == expected

    def test_empty_list(self):
        """空リストのテスト"""
        data = []
        result = list(chunks(data, 2))
        assert result == []


class TestFilterDict:
    """filter_dict のテスト"""

    def test_filter_existing_keys(self):
        """存在するキーのフィルタリングテスト"""
        data = {"a": 1, "b": 2, "c": 3}
        result = filter_dict(data, ["a", "c"])
        expected = {"a": 1, "c": 3}
        assert result == expected

    def test_filter_nonexistent_keys(self):
        """存在しないキーのフィルタリングテスト"""
        data = {"a": 1, "b": 2}
        result = filter_dict(data, ["a", "c"])
        expected = {"a": 1}
        assert result == expected

    def test_empty_keys(self):
        """空キーリストのテスト"""
        data = {"a": 1, "b": 2}
        result = filter_dict(data, [])
        assert result == {}


class TestDeepMerge:
    """deep_merge のテスト"""

    def test_simple_merge(self):
        """単純マージのテスト"""
        dict1 = {"a": 1, "b": 2}
        dict2 = {"c": 3, "d": 4}
        result = deep_merge(dict1, dict2)
        expected = {"a": 1, "b": 2, "c": 3, "d": 4}
        assert result == expected

    def test_override_merge(self):
        """上書きマージのテスト"""
        dict1 = {"a": 1, "b": 2}
        dict2 = {"b": 3, "c": 4}
        result = deep_merge(dict1, dict2)
        expected = {"a": 1, "b": 3, "c": 4}
        assert result == expected

    def test_nested_merge(self):
        """ネストマージのテスト"""
        dict1 = {"a": {"x": 1, "y": 2}, "b": 3}
        dict2 = {"a": {"y": 3, "z": 4}, "c": 5}
        result = deep_merge(dict1, dict2)
        expected = {"a": {"x": 1, "y": 3, "z": 4}, "b": 3, "c": 5}
        assert result == expected

    def test_original_unchanged(self):
        """元の辞書が変更されないテスト"""
        dict1 = {"a": 1}
        dict2 = {"b": 2}
        original_dict1 = dict1.copy()

        deep_merge(dict1, dict2)

        assert dict1 == original_dict1


class TestExtractRedmineId:
    """extract_redmine_id のテスト"""

    def test_numeric_string(self):
        """数値文字列のテスト"""
        assert extract_redmine_id("123") == 123

    def test_project_url(self):
        """プロジェクトURLのテスト"""
        url = "https://redmine.example.com/projects/456"
        assert extract_redmine_id(url) == 456

    def test_issue_url(self):
        """チケットURLのテスト"""
        url = "https://redmine.example.com/issues/789"
        assert extract_redmine_id(url) == 789

    def test_complex_url(self):
        """複雑なURLのテスト"""
        url = "https://redmine.example.com/projects/123/issues/456"
        # 最初にマッチしたIDを返す
        assert extract_redmine_id(url) == 123

    def test_invalid_url(self):
        """無効なURLのテスト"""
        assert extract_redmine_id("https://example.com/invalid") is None

    def test_non_numeric(self):
        """非数値のテスト"""
        assert extract_redmine_id("abc") is None
