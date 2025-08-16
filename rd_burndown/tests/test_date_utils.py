"""日付処理ユーティリティのテスト"""

from datetime import date, datetime

from rd_burndown.utils.date_utils import (
    add_business_days,
    days_between,
    format_date,
    format_datetime,
    get_all_days,
    get_business_days,
    get_project_duration,
    is_business_day,
    parse_date_string,
    parse_datetime_string,
)


class TestDateUtils:
    """日付ユーティリティのテスト"""

    def test_get_business_days(self):
        """営業日取得のテスト"""
        start_date = date(2024, 1, 1)  # 月曜日
        end_date = date(2024, 1, 7)  # 日曜日

        # 営業日のみ取得（祝日除外なし）
        business_days = get_business_days(start_date, end_date, exclude_holidays=False)
        assert len(business_days) == 5  # 月-金

        # 営業日取得（祝日除外あり）
        business_days_with_holidays = get_business_days(
            start_date, end_date, exclude_holidays=True
        )
        # 元日は祝日なので除外される
        assert len(business_days_with_holidays) == 4

    def test_get_all_days(self):
        """全日取得のテスト"""
        start_date = date(2024, 1, 1)
        end_date = date(2024, 1, 7)

        all_days = get_all_days(start_date, end_date)
        assert len(all_days) == 7
        assert all_days[0] == start_date
        assert all_days[-1] == end_date

    def test_parse_date_string(self):
        """日付文字列パースのテスト"""
        # 有効な日付文字列
        parsed = parse_date_string("2024-01-15")
        assert parsed == date(2024, 1, 15)

        # ISO 8601形式
        parsed_iso = parse_date_string("2024-01-15T10:30:00")
        assert parsed_iso == date(2024, 1, 15)

        # 無効な文字列
        assert parse_date_string("invalid-date") is None
        assert parse_date_string("") is None

    def test_parse_datetime_string(self):
        """日時文字列パースのテスト"""
        # 有効な日時文字列
        parsed = parse_datetime_string("2024-01-15T10:30:00")
        if parsed is not None:  # Pendulumが利用可能な場合
            assert isinstance(parsed, datetime)
            assert parsed.date() == date(2024, 1, 15)

        # 無効な文字列
        assert parse_datetime_string("invalid-datetime") is None
        assert parse_datetime_string("") is None

    def test_format_date(self):
        """日付フォーマットのテスト"""
        test_date = date(2024, 1, 15)

        # デフォルトフォーマット
        formatted = format_date(test_date)
        assert formatted == "2024-01-15"

        # カスタムフォーマット
        custom_formatted = format_date(test_date, "DD/MM/YYYY")
        assert custom_formatted == "15/01/2024"

    def test_format_datetime(self):
        """日時フォーマットのテスト"""
        test_datetime = datetime(2024, 1, 15, 10, 30, 45)

        # デフォルトフォーマット
        formatted = format_datetime(test_datetime)
        assert formatted == "2024-01-15 10:30:45"

        # カスタムフォーマット
        custom_formatted = format_datetime(test_datetime, "YYYY/MM/DD HH:mm")
        assert custom_formatted == "2024/01/15 10:30"

    def test_days_between(self):
        """日数差計算のテスト"""
        start_date = date(2024, 1, 1)
        end_date = date(2024, 1, 10)

        diff = days_between(start_date, end_date)
        assert diff == 9

        # 逆順
        diff_reverse = days_between(end_date, start_date)
        assert diff_reverse == -9

    def test_add_business_days(self):
        """営業日加算のテスト"""
        start_date = date(2024, 1, 1)  # 月曜日（元日は祝日）

        # 5営業日後
        result = add_business_days(start_date, 5)
        # 元日は祝日なので、実際には6日後になる
        expected = date(2024, 1, 9)  # 火曜日
        assert result == expected

    def test_is_business_day(self):
        """営業日判定のテスト"""
        # 平日
        weekday = date(2024, 1, 2)  # 火曜日
        assert is_business_day(weekday) is True

        # 土曜日
        saturday = date(2024, 1, 6)
        assert is_business_day(saturday) is False

        # 日曜日
        sunday = date(2024, 1, 7)
        assert is_business_day(sunday) is False

        # 祝日（元日）
        holiday = date(2024, 1, 1)
        assert is_business_day(holiday) is False

    def test_get_project_duration(self):
        """プロジェクト期間計算のテスト"""
        start_date = date(2024, 1, 1)
        end_date = date(2024, 1, 7)

        # 全日数（両端含む）
        duration_all = get_project_duration(
            start_date, end_date, business_days_only=False
        )
        assert duration_all == 7

        # 営業日のみ
        duration_business = get_project_duration(
            start_date, end_date, business_days_only=True
        )
        assert duration_business == 4  # 元日は祝日、土日除外

    def test_edge_cases(self):
        """エッジケースのテスト"""
        # 同じ日付
        same_date = date(2024, 1, 15)
        assert len(get_all_days(same_date, same_date)) == 1
        assert days_between(same_date, same_date) == 0

        # 週末のみの期間
        saturday = date(2024, 1, 6)
        sunday = date(2024, 1, 7)
        weekend_business_days = get_business_days(saturday, sunday)
        assert len(weekend_business_days) == 0
