#!/usr/bin/env python3
"""
Instagram Follow Manager - Auto Unfollow
一括でアンフォローを実行するスクリプト（DRY_RUN=false時に実行）
"""

import os
import sys
import json
from pathlib import Path
from main import InstagramFollowManager
from dotenv import load_dotenv

load_dotenv()


def auto_unfollow_non_reciprocal(max_count=None, confirm=True):
    """
    Automatically unfollow users who don't follow back
    
    Args:
        max_count: Maximum number of users to unfollow (None = all)
        confirm: Ask for confirmation before unfollowing (default: True)
    """
    manager = InstagramFollowManager()

    print("=" * 60)
    print("Instagram Auto-Unfollow Script")
    print("=" * 60)
    print(f"DRY_RUN: {manager.dry_run}")
    print(f"Delay between unfollows: {manager.delay}s")
    print("=" * 60 + "\n")

    if manager.dry_run:
        print("WARNING: Running in DRY_RUN mode. No actual unfollows will occur.")
        print("Set DRY_RUN=false in .env to enable actual unfollowing.\n")

    try:
        manager.login()

        # Load existing analysis if available
        if Path("follow_analysis.json").exists():
            with open("follow_analysis.json", "r", encoding="utf-8") as f:
                analysis = json.load(f)
            print("DEBUG: Using cached analysis from follow_analysis.json")
        else:
            # Get fresh data
            followers = manager.get_followers()
            followings = manager.get_followings()
            analysis = manager.find_non_mutual_follows(followers, followings)
            manager.save_analysis(analysis)

        target_users = analysis["unreciprocated_follows"]

        if not target_users:
            print("No users to unfollow. Everyone you follow also follows you back!")
            return

        if max_count:
            target_users = target_users[:max_count]

        print(f"\nTargeting {len(target_users)} users for unfollow:")
        print("-" * 60)
        for i, username in enumerate(target_users[:20], 1):
            print(f"{i:2d}. {username}")
        if len(target_users) > 20:
            print(f"... and {len(target_users) - 20} more")
        print("-" * 60)

        if confirm and not manager.dry_run:
            response = input(
                f"\nAre you sure you want to unfollow {len(target_users)} users? (yes/no): "
            ).strip().lower()
            if response != "yes":
                print("Cancelled")
                return

        manager.unfollow_users(target_users, analysis["unreciprocated_follows"])
        print("\nDone!")

    except Exception as e:
        print(f"FATAL ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Auto-unfollow non-reciprocal follows")
    parser.add_argument("--max", type=int, default=None, help="Maximum number to unfollow")
    parser.add_argument(
        "--no-confirm", action="store_true", help="Skip confirmation (use with caution!)"
    )

    args = parser.parse_args()
    auto_unfollow_non_reciprocal(max_count=args.max, confirm=not args.no_confirm)
