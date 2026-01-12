#!/usr/bin/env python3
"""
Instagram Follow Analysis Report Generator
フォロー/フォロワー差分を詳細に分析し、レポートを生成します。
"""

import json
from pathlib import Path
from datetime import datetime


def generate_report(analysis_file="follow_analysis.json"):
    """Generate a detailed report from analysis"""
    if not Path(analysis_file).exists():
        print(f"ERROR: {analysis_file} not found. Run main.py first.")
        return

    with open(analysis_file, "r", encoding="utf-8") as f:
        analysis = json.load(f)

    # Generate report
    report_file = f"follow_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

    with open(report_file, "w", encoding="utf-8") as f:
        f.write("=" * 60 + "\n")
        f.write("Instagram Follow/Unfollow Analysis Report\n")
        f.write(f"Generated: {datetime.now().isoformat()}\n")
        f.write("=" * 60 + "\n\n")

        # Summary
        mutual = len(analysis.get("mutual_follows", []))
        unreciprocated = len(analysis.get("unreciprocated_follows", []))
        followers_not_following = len(analysis.get("followers_not_reciprocated", []))

        f.write("SUMMARY\n")
        f.write("-" * 60 + "\n")
        f.write(f"Mutual follows: {mutual}\n")
        f.write(f"You follow but they don't: {unreciprocated}\n")
        f.write(f"They follow but you don't: {followers_not_following}\n")
        f.write(f"Total followers + following (unique): {mutual + unreciprocated + followers_not_following}\n\n")

        # Unreciprocated follows (we follow but they don't follow back)
        if unreciprocated > 0:
            f.write("RECOMMENDED FOR UNFOLLOW\n")
            f.write("-" * 60 + "\n")
            f.write(f"Users you follow but who don't follow back ({unreciprocated} total):\n\n")
            for username in sorted(analysis.get("unreciprocated_follows", [])):
                f.write(f"  • {username}\n")
            f.write("\n")

        # Followers not reciprocated
        if followers_not_following > 0:
            f.write("UNRECIPROCATED FOLLOWERS\n")
            f.write("-" * 60 + "\n")
            f.write(f"Users who follow you but you don't follow back ({followers_not_following} total):\n\n")
            for username in sorted(analysis.get("followers_not_reciprocated", [])):
                f.write(f"  • {username}\n")
            f.write("\n")

    print(f"Report generated: {report_file}")


if __name__ == "__main__":
    generate_report()
