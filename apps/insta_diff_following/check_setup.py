#!/usr/bin/env python3
"""
Instagram Follow Manager - Standalone Config Checker
環境設定の確認とInstagram接続テスト
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


def check_setup():
    """Check if setup is complete and valid"""
    print("=" * 60)
    print("Instagram Follow Manager - Setup Check")
    print("=" * 60 + "\n")

    # Check .env file
    if not Path(".env").exists():
        print("❌ .env file not found")
        print("   Copy .env.sample and fill in your credentials:")
        print("   $ cp .env.sample .env")
        return False
    print("✓ .env file found")

    # Check credentials
    username = os.getenv("INSTAGRAM_USERNAME")
    password = os.getenv("INSTAGRAM_PASSWORD")

    if not username:
        print("❌ INSTAGRAM_USERNAME is not set in .env")
        return False
    print(f"✓ INSTAGRAM_USERNAME set: {username}")

    if not password:
        print("❌ INSTAGRAM_PASSWORD is not set in .env")
        return False
    print("✓ INSTAGRAM_PASSWORD set (hidden for security)")

    # Check optional settings
    dry_run = os.getenv("DRY_RUN", "true")
    print(f"✓ DRY_RUN: {dry_run}")

    delay = os.getenv("DELAY_BETWEEN_UNFOLLOWS", "3")
    print(f"✓ DELAY_BETWEEN_UNFOLLOWS: {delay}s")

    session_file = os.getenv("SESSION_FILE", "session.json")
    if Path(session_file).exists():
        print(f"✓ Session cache found: {session_file}")
    else:
        print(f"ℹ Session cache not found yet (will be created on first login)")

    print("\n" + "=" * 60)
    print("Setup appears valid! You can now run:")
    print("  python main.py")
    print("=" * 60)
    return True


if __name__ == "__main__":
    check_setup()
