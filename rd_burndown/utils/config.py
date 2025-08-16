"""設定管理ユーティリティ"""

import logging
import os
from pathlib import Path
from typing import Any, Optional

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ConfigError(Exception):
    """設定関連エラー"""


class RedmineConfig(BaseModel):
    """Redmine接続設定"""

    url: str = Field(default="http://localhost:3000")
    api_key: str = Field(default="")
    timeout: int = Field(default=30)
    verify_ssl: bool = Field(default=True)


class OutputConfig(BaseModel):
    """出力設定"""

    default_format: str = Field(default="png")
    default_width: int = Field(default=1200)
    default_height: int = Field(default=800)
    default_dpi: int = Field(default=300)
    output_dir: str = Field(default="./output")


class ChartColors(BaseModel):
    """チャート色設定"""

    ideal: str = Field(default="#2E8B57")
    actual: str = Field(default="#DC143C")
    scope: str = Field(default="#4169E1")
    dynamic_ideal: str = Field(default="#FF8C00")
    background: str = Field(default="#FFFFFF")
    grid: str = Field(default="#E0E0E0")


class LineStyles(BaseModel):
    """線種設定"""

    ideal: str = Field(default="dashed")
    actual: str = Field(default="solid")
    scope: str = Field(default="solid")
    dynamic_ideal: str = Field(default="dashdot")


class ChartConfig(BaseModel):
    """チャート設定"""

    font_family: str = Field(default="DejaVu Sans")
    font_size: int = Field(default=12)
    colors: ChartColors = Field(default_factory=ChartColors)
    line_styles: LineStyles = Field(default_factory=LineStyles)


class DataConfig(BaseModel):
    """データ設定"""

    cache_dir: str = Field(default="./cache")
    cache_ttl_hours: int = Field(default=1)
    incremental_sync: bool = Field(default=True)
    max_batch_size: int = Field(default=100)


class DateConfig(BaseModel):
    """日付設定"""

    timezone: str = Field(default="Asia/Tokyo")
    business_days_only: bool = Field(default=False)
    exclude_holidays: bool = Field(default=True)
    holiday_country: str = Field(default="JP")


class LoggingConfig(BaseModel):
    """ログ設定"""

    level: str = Field(default="INFO")
    format: str = Field(default="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    file: str = Field(default="./logs/rd-burndown.log")


class Config(BaseModel):
    """メイン設定"""

    redmine: RedmineConfig = Field(default_factory=RedmineConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)
    chart: ChartConfig = Field(default_factory=ChartConfig)
    data: DataConfig = Field(default_factory=DataConfig)
    date: DateConfig = Field(default_factory=DateConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)


class ConfigManager:
    """設定管理クラス"""

    def __init__(self, config_path: Optional[Path] = None) -> None:
        self.config_path = config_path or Path.home() / ".rd-burndown" / "config.yaml"
        self._config: Optional[Config] = None
        load_dotenv()

    def load_config(self) -> Config:
        """設定を読み込み"""
        if self._config is not None:
            return self._config

        config_dict: dict[str, Any] = {}

        try:
            if self.config_path.exists():
                with open(self.config_path, encoding="utf-8") as f:
                    config_dict = yaml.safe_load(f) or {}

            config_dict = self._apply_env_overrides(config_dict)

            # 設定値バリデーション
            self._validate_config_dict(config_dict)

            self._config = Config(**config_dict)
            return self._config

        except yaml.YAMLError as e:
            logger.error(f"Failed to parse config file: {e}")
            raise ConfigError(f"Invalid YAML in config file: {e}") from e
        except ValueError as e:
            logger.error(f"Invalid configuration values: {e}")
            raise ConfigError(f"Invalid configuration values: {e}") from e
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            raise ConfigError(f"Failed to load config: {e}") from e

    def _apply_env_overrides(self, config_dict: dict[str, Any]) -> dict[str, Any]:
        """環境変数でオーバーライド"""
        env_mappings = {
            "RD_REDMINE_URL": ("redmine", "url"),
            "RD_REDMINE_API_KEY": ("redmine", "api_key"),
            "RD_OUTPUT_DIR": ("output", "output_dir"),
            "RD_OUTPUT_FORMAT": ("output", "default_format"),
            "RD_CACHE_DIR": ("data", "cache_dir"),
            "RD_CACHE_TTL_HOURS": ("data", "cache_ttl_hours"),
        }

        for env_var, (section, key) in env_mappings.items():
            env_value = os.getenv(env_var)
            if env_value is not None:
                if section not in config_dict:
                    config_dict[section] = {}

                if key == "cache_ttl_hours":
                    try:
                        config_dict[section][key] = int(env_value)
                    except ValueError:
                        continue
                else:
                    config_dict[section][key] = env_value

        return config_dict

    def _validate_config_dict(self, config_dict: dict[str, Any]) -> None:
        """設定値のバリデーション"""
        # Redmine設定の検証
        if "redmine" in config_dict:
            redmine_config = config_dict["redmine"]

            # URL検証
            if "url" in redmine_config:
                url = redmine_config["url"]
                if not isinstance(url, str) or not url.strip():
                    raise ValueError("Redmine URL must be a non-empty string")
                if not url.startswith(("http://", "https://")):
                    raise ValueError("Redmine URL must start with http:// or https://")

            # API キー検証
            if "api_key" in redmine_config:
                api_key = redmine_config["api_key"]
                if not isinstance(api_key, str) or not api_key.strip():
                    raise ValueError("Redmine API key must be a non-empty string")
                if len(api_key.strip()) < 10:
                    raise ValueError("Redmine API key appears to be too short")

            # タイムアウト検証
            if "timeout" in redmine_config:
                timeout = redmine_config["timeout"]
                if not isinstance(timeout, (int, float)) or timeout <= 0:
                    raise ValueError("Redmine timeout must be a positive number")

        # データ設定の検証
        if "data" in config_dict:
            data_config = config_dict["data"]

            # キャッシュTTL検証
            if "cache_ttl_hours" in data_config:
                ttl = data_config["cache_ttl_hours"]
                if not isinstance(ttl, int) or ttl < 0:
                    raise ValueError("Cache TTL must be a non-negative integer")

            # バッチサイズ検証
            if "max_batch_size" in data_config:
                batch_size = data_config["max_batch_size"]
                if (
                    not isinstance(batch_size, int)
                    or batch_size <= 0
                    or batch_size > 1000
                ):
                    raise ValueError("Max batch size must be between 1 and 1000")

        # 出力設定の検証
        if "output" in config_dict:
            output_config = config_dict["output"]

            # DPI検証
            if "default_dpi" in output_config:
                dpi = output_config["default_dpi"]
                if not isinstance(dpi, int) or dpi < 72 or dpi > 600:
                    raise ValueError("DPI must be between 72 and 600")

            # 画像サイズ検証
            for dimension in ["default_width", "default_height"]:
                if dimension in output_config:
                    size = output_config[dimension]
                    if not isinstance(size, int) or size < 100 or size > 5000:
                        raise ValueError(
                            f"{dimension} must be between 100 and 5000 pixels"
                        )

    def save_config(self, config: Config) -> None:
        """設定を保存"""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        with open(self.config_path, "w", encoding="utf-8") as f:
            yaml.dump(
                config.model_dump(),
                f,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=True,
            )

        self._config = config

    def create_default_config(self) -> Config:
        """デフォルト設定を作成"""
        config = Config()
        self.save_config(config)
        return config

    def get_config(self) -> Config:
        """設定を取得（キャッシュ済みまたは新規読み込み）"""
        return self.load_config()


def get_config_manager(config_path: Optional[Path] = None) -> ConfigManager:
    """設定マネージャーのインスタンスを取得"""
    return ConfigManager(config_path)
