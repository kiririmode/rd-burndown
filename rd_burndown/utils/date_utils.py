"""日付処理ユーティリティ"""

from datetime import date, datetime, timedelta
from typing import Any, Optional

import holidays
import pendulum


def get_business_days(
    start_date: date, end_date: date, country: str = "JP", exclude_holidays: bool = True
) -> list[date]:
    """営業日リスト取得"""
    business_days: list[date] = []
    current_date = start_date

    country_holidays: Any = holidays.country_holidays(country) if exclude_holidays else {}

    while current_date <= end_date:
        # 土日をスキップし、かつ祝日でない場合のみ追加
        if current_date.weekday() < 5 and (
            not exclude_holidays or current_date not in country_holidays
        ):
            business_days.append(current_date)

        current_date += timedelta(days=1)

    return business_days


def get_all_days(start_date: date, end_date: date) -> list[date]:
    """全日リスト取得"""
    all_days: list[date] = []
    current_date = start_date

    while current_date <= end_date:
        all_days.append(current_date)
        current_date += timedelta(days=1)

    return all_days


def parse_date_string(date_string: str, timezone: str = "Asia/Tokyo") -> Optional[date]:
    """日付文字列をパース"""
    try:
        parsed = pendulum.parse(date_string, tz=timezone)
        if (
            parsed
            and hasattr(parsed, "date")
            and callable(getattr(parsed, "date", None))
        ):
            return parsed.date()  # type: ignore
    except Exception:  # nosec B110
        pass
    return None


def parse_datetime_string(
    datetime_string: str, timezone: str = "Asia/Tokyo"
) -> Optional[datetime]:
    """日時文字列をパース"""
    try:
        parsed = pendulum.parse(datetime_string, tz=timezone)
        if (
            parsed
            and hasattr(parsed, "to_datetime")
            and callable(getattr(parsed, "to_datetime", None))
        ):
            return parsed.to_datetime()  # type: ignore
    except Exception:  # nosec B110
        pass
    return None


def format_date(target_date: date, format_string: str = "YYYY-MM-DD") -> str:
    """日付フォーマット"""
    pendulum_date = pendulum.instance(
        datetime.combine(target_date, datetime.min.time())
    )
    return pendulum_date.format(format_string)


def format_datetime(
    target_datetime: datetime, format_string: str = "YYYY-MM-DD HH:mm:ss"
) -> str:
    """日時フォーマット"""
    pendulum_datetime = pendulum.instance(target_datetime)
    return pendulum_datetime.format(format_string)


def days_between(start_date: date, end_date: date) -> int:
    """日数差計算"""
    return (end_date - start_date).days


def add_business_days(start_date: date, days: int, country: str = "JP") -> date:
    """営業日加算"""
    current_date = start_date
    added_days = 0
    country_holidays: Any = holidays.country_holidays(country)

    while added_days < days:
        current_date += timedelta(days=1)

        # 営業日チェック
        if current_date.weekday() < 5 and current_date not in country_holidays:
            added_days += 1

    return current_date


def is_business_day(check_date: date, country: str = "JP") -> bool:
    """営業日判定"""
    if check_date.weekday() >= 5:  # 土日
        return False

    country_holidays: Any = holidays.country_holidays(country)
    return check_date not in country_holidays


def get_business_days_between(
    start_date: date, end_date: date, country: str = "JP"
) -> int:
    """営業日数計算"""
    return len(get_business_days(start_date, end_date, country))


def get_project_duration(
    start_date: date,
    end_date: date,
    business_days_only: bool = False,
    country: str = "JP",
) -> int:
    """プロジェクト期間計算"""
    if business_days_only:
        return len(get_business_days(start_date, end_date, country))
    return days_between(start_date, end_date) + 1  # 両端含む
