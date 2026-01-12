#!/usr/bin/env python3
"""
Instagram Follow/Unfollow Manager
フォロワーとフォロー中のメンバーを比較して、相互フォローでないユーザーを特定します。
"""

import os
import json
import time
from pathlib import Path
from instagrapi import Client
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class InstagramFollowManager:
    """Instagram follow/unfollow management"""

    def __init__(self):
        self.username = os.getenv("INSTAGRAM_USERNAME")
        self.password = os.getenv("INSTAGRAM_PASSWORD")
        # Session file selection order:
        # 1) Use SESSION_FILE env var if provided
        # 2) If a session.json exists in current working directory, use it (preserves previous behavior)
        # 3) Fall back to session.json located next to this script
        env_session = os.getenv("SESSION_FILE")
        if env_session:
            self.session_file = env_session
        else:
            cwd_session = Path.cwd() / "session.json"
            if cwd_session.exists():
                self.session_file = str(cwd_session)
            else:
                self.session_file = str(Path(__file__).parent / "session.json")
        self.dry_run = os.getenv("DRY_RUN", "true").lower() == "true"
        self.delay = float(os.getenv("DELAY_BETWEEN_UNFOLLOWS", "3"))
        self.client = None

        if not self.username or not self.password:
            raise ValueError("INSTAGRAM_USERNAME and INSTAGRAM_PASSWORD must be set in .env")

    def login(self):
        """Login to Instagram and load session if available"""
        self.client = Client()

        # Try to load saved session
        if Path(self.session_file).exists():
            print(f"DEBUG: Loading session from {self.session_file}")
            try:
                self.client.load_settings(self.session_file)
                print("DEBUG: Session loaded successfully")
                return
            except Exception as e:
                print(f"DEBUG: Failed to load session: {e}")

        # Login with credentials
        print(f"DEBUG: Logging in as {self.username}")
        try:
            self.client.login(self.username, self.password)
            print("DEBUG: Login successful")
            # Save session for future use
            self.client.dump_settings(self.session_file)
            print(f"DEBUG: Session saved to {self.session_file}")
        except ClientLoginError as e:
            print(f"ERROR: Login failed - {e}")
            raise

    def get_followers(self):
        """Get list of followers"""
        print("DEBUG: Fetching followers...")
        try:
            user_id = self.client.user_id
            print(f"DEBUG: User ID: {user_id}")
            # Force a fresh fetch from Instagram (don't rely on local cache)
            followers = self.client.user_followers(user_id, use_cache=False, amount=0)
            print(f"DEBUG: Followers type: {type(followers)}")
            print(f"DEBUG: Followers length: {len(followers) if hasattr(followers, '__len__') else 'N/A'}")
            if isinstance(followers, dict):
                follower_dict = {user.username: user.pk for user in followers.values()}
            else:
                # If it's a list or other iterable
                follower_dict = {user.username: user.pk for user in followers}
            print(f"DEBUG: Found {len(follower_dict)} followers")
            return follower_dict
        except Exception as e:
            print(f"ERROR: Failed to fetch followers - {e}")
            import traceback
            traceback.print_exc()
            raise

    def get_followings(self):
        """Get list of users being followed"""
        print("DEBUG: Fetching followings...")
        try:
            user_id = self.client.user_id
            print(f"DEBUG: Username: {self.username}, User ID: {user_id}")
            # Force a fresh fetch from Instagram (don't rely on local cache)
            followings = self.client.user_following(user_id, use_cache=False, amount=0)
            print(f"DEBUG: Followings type: {type(followings)}")
            print(f"DEBUG: Followings length: {len(followings) if hasattr(followings, '__len__') else 'N/A'}")
            if isinstance(followings, dict):
                following_dict = {user.username: user.pk for user in followings.values()}
            else:
                # If it's a list or other iterable
                following_dict = {user.username: user.pk for user in followings}
            print(f"DEBUG: Found {len(following_dict)} followings")
            return following_dict
        except Exception as e:
            print(f"ERROR: Failed to fetch followings - {e}")
            import traceback
            traceback.print_exc()
            raise

    def find_non_mutual_follows(self, followers, followings):
        """Find users that are not mutually followed"""
        follower_set = set(followers.keys())
        following_set = set(followings.keys())

        # Users we follow but don't follow us back
        following_not_followers = following_set - follower_set
        # Users that follow us but we don't follow back
        followers_not_following = follower_set - following_set

        print(f"\n=== Follow Analysis ===")
        print(f"Followers: {len(follower_set)}")
        print(f"Following: {len(following_set)}")
        print(f"Mutual follows: {len(follower_set & following_set)}")
        print(f"We follow but they don't follow back: {len(following_not_followers)}")
        print(f"They follow us but we don't follow back: {len(followers_not_following)}")

        return {
            "unreciprocated_follows": list(following_not_followers),  # We follow but they don't
            "followers_not_reciprocated": list(followers_not_following),  # They follow but we don't
            "mutual_follows": list(follower_set & following_set),
        }

    def save_analysis(self, analysis):
        """Save analysis results to file"""
        output_file = "follow_analysis.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(analysis, f, ensure_ascii=False, indent=2)
        print(f"DEBUG: Analysis saved to {output_file}")

    def unfollow_user(self, user_pk):
        """Unfollow a single user"""
        if self.dry_run:
            print(f"DRY_RUN: Would unfollow user {user_pk}")
            return True

        try:
            self.client.user_unfollow(user_pk)
            print(f"DEBUG: Unfollowed user {user_pk}")
            return True
        except Exception as e:
            print(f"ERROR: Failed to unfollow user {user_pk} - {e}")
            return False

    def unfollow_users(self, usernames, user_id_map):
        """Unfollow multiple users with delay"""
        print(f"\nDRY_RUN={self.dry_run}")
        if self.dry_run:
            print(f"Would unfollow {len(usernames)} users:")
            for username in usernames:
                print(f"  - {username}")
            return

        print(f"Starting to unfollow {len(usernames)} users...")
        unfollowed = 0
        failed = []

        for username in usernames:
            if username not in user_id_map:
                print(f"DEBUG: Username {username} not found in user_id_map")
                continue

            user_pk = user_id_map[username]
            if self.unfollow_user(user_pk):
                unfollowed += 1
            else:
                failed.append(username)

            time.sleep(self.delay)

        print(f"\nUnfollow completed: {unfollowed} successful, {len(failed)} failed")
        if failed:
            print(f"Failed to unfollow: {failed}")

    def run(self):
        """Main execution flow"""
        try:
            self.login()

            # Get followers and followings
            followers = self.get_followers()
            followings = self.get_followings()

            # Analyze differences
            analysis = self.find_non_mutual_follows(followers, followings)
            self.save_analysis(analysis)

            # Show options
            while True:
                print("\n" + "=" * 60)
                print("INSTAGRAM FOLLOW MANAGER")
                print("=" * 60)
                print("\nOptions:")
                print("  1. Show followers")
                print("     → あなたをフォローしているユーザーの一覧を表示")
                print(f"     → 現在: {len(followers)} 人")
                print()
                print("  2. Show followings")
                print("     → あなたがフォローしているユーザーの一覧を表示")
                print(f"     → 現在: {len(followings)} 人")
                print()
                print("  3. Show unreciprocated follows (count only)")
                print("     → 相互フォローでないユーザーの件数を表示（一覧は表示しない）")
                print(f"     → 現在: {len(analysis['unreciprocated_follows'])} 人")
                print()
                print("  4. Show full unreciprocated list (3のリストをみる)")
                print("     → 相互フォローでないユーザーの一覧を表示します（必要なときだけ実行）")
                print()
                print("  5. Unfollow users who don't follow back")
                print("     → 相互フォローでないユーザーを一括アンフォロー")
                print("     → 確認メッセージが出ます")
                print()
                print("  6. Exit without unfollowing")
                print("     → 何もせず終了")
                print()
                print("=" * 60)

                choice = input("Enter choice (1-6): ").strip()

                if choice == "1":
                    if followers:
                        print(f"\n=== Followers ({len(followers)}) ===")
                        for username in sorted(followers.keys()):
                            print(f"  • {username}")
                    else:
                        print("No followers found")

                elif choice == "2":
                    if followings:
                        print(f"\n=== Followings ({len(followings)}) ===")
                        for username in sorted(followings.keys()):
                            print(f"  • {username}")
                    else:
                        print("No followings found")

                elif choice == "3":
                    target_users = analysis["unreciprocated_follows"]
                    print(f"\nWe follow but they don't follow back: {len(target_users)} 人")

                elif choice == "4":
                    target_users = analysis["unreciprocated_follows"]
                    if target_users:
                        print(f"\n=== We follow but they don't follow back ({len(target_users)}) ===")
                        for idx, username in enumerate(sorted(target_users), 1):
                            print(f"  {idx}. {username}")
                    else:
                        print("No unreciprocated follows")

                elif choice == "5":
                    target_users = analysis["unreciprocated_follows"]
                    if target_users:
                        print(f"\nFound {len(target_users)} users to unfollow.")
                        print("Will ask for confirmation for each user.\n")
                        unfollowed_count = 0
                        skipped_count = 0

                        for idx, username in enumerate(target_users, 1):
                            if username not in followings:
                                print(f"{idx}. {username} - NOT FOUND, skipping")
                                skipped_count += 1
                                continue

                            confirm = input(f"{idx}. Unfollow {username}? (y/n): ").strip().lower()
                            if confirm == "y":
                                user_pk = followings[username]
                                if self.unfollow_user(user_pk):
                                    unfollowed_count += 1
                                    print(f"   ✓ Unfollowed")
                                else:
                                    print(f"   ✗ Failed")
                            else:
                                print(f"   - Skipped")
                                skipped_count += 1

                            if idx < len(target_users):
                                time.sleep(self.delay)

                        print(f"\n=== Result ===")
                        print(f"Unfollowed: {unfollowed_count}")
                        print(f"Skipped: {skipped_count}")
                    else:
                        print("No unreciprocated follows to unfollow")
                    break

                elif choice == "6":
                    print("Exiting without action")
                    break
                else:
                    print("Invalid choice")

        except Exception as e:
            print(f"FATAL ERROR: {e}")
            raise


if __name__ == "__main__":
    manager = InstagramFollowManager()
    manager.run()
