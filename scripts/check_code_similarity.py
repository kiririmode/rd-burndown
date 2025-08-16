#!/usr/bin/env python3
"""
コード類似度チェックスクリプト

similarity-pyを使用してコードの重複や類似箇所を検出し、
リファクタリングの必要性をアドバイスします。
"""

import subprocess  # nosec B404
import sys
from pathlib import Path


def main() -> int:
    """メイン関数"""
    project_root = Path(__file__).parent.parent
    source_dir = project_root / "rd_burndown"

    if not source_dir.exists():
        print(
            "rd_burndown/ディレクトリが見つかりません。まだソースコードがない可能性があります。"
        )
        return 0

    try:
        # similarity-pyでコード類似度チェック
        result = subprocess.run(  # nosec B603, B607
            ["similarity-py", str(source_dir)],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode == 0:
            if result.stdout.strip():
                print("⚠️  類似コードが検出されました:")
                print(result.stdout)
                print("\n💡 リファクタリングを検討してください。")
            else:
                print("✅ コード類似度チェック: 重複なし")
        else:
            print(f"⚠️  similarity-pyエラー: {result.stderr}")

    except subprocess.TimeoutExpired:
        print("⚠️  類似度チェックがタイムアウトしました")
    except FileNotFoundError:
        print("⚠️  similarity-pyがインストールされていません")
        print("   インストール: cargo install similarity-py")
    except Exception as e:
        print(f"⚠️  予期しないエラー: {e}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
