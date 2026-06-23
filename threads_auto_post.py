"""
Threads 三段投稿 自動投稿スクリプト
アカウント: @sakichan122

使い方:
    python threads_auto_post.py           # 実際に投稿
    python threads_auto_post.py --dry-run # テストのみ（投稿しない）
"""

import json
import time
import sys
import os
import requests
from datetime import datetime

# ============================================================
# 設定（ACCESS_TOKEN と USER_ID をここに入力してください）
# ============================================================
ACCESS_TOKEN = "THAA8hJlSDtEdBYlkxLVJqZAllVWGd4ZAzIwR3lBSEVlU1RleEd2b1JyTnotVm4zTEhrbkJDcm1hM3RTY0FQUUtlbWpzSkRSaThFQk52aUtkbnN1QzVoVEtKMXVkVE04Q3B3Tlgyd1IzQVRpMVpya2VmV1hNa3ZAxLThOUVJNYVJnYzNyOFpjYkJ3a0hfQTdfbUUZD"
USER_ID = "26732151053133237"

# ファイルパス（スクリプトと同じフォルダに置く）
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
POSTS_FILE = os.path.join(SCRIPT_DIR, "threads_posts.json")
PROGRESS_FILE = os.path.join(SCRIPT_DIR, "progress.json")

# Threads Graph API のベースURL
API_BASE = "https://graph.threads.net/v1.0"

# 投稿間のウェイト（秒）
POST_INTERVAL = 5


def load_posts():
    """投稿原稿を読み込む"""
    with open(POSTS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def load_progress():
    """進捗ファイルを読み込む（なければ初期値）"""
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"next_id": 1, "total_posted": 0}


def save_progress(progress):
    """進捗を保存する"""
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(progress, f, ensure_ascii=False, indent=2)


def create_thread_container(text, reply_to_id=None):
    """Threads メディアコンテナを作成する"""
    url = f"{API_BASE}/{USER_ID}/threads"
    params = {
        "media_type": "TEXT",
        "text": text,
        "access_token": ACCESS_TOKEN,
    }
    if reply_to_id:
        params["reply_to_id"] = reply_to_id

    resp = requests.post(url, data=params, timeout=30)
    resp.raise_for_status()
    return resp.json()["id"]


def publish_thread(creation_id):
    """コンテナを公開して投稿IDを返す"""
    url = f"{API_BASE}/{USER_ID}/threads_publish"
    params = {
        "creation_id": creation_id,
        "access_token": ACCESS_TOKEN,
    }
    resp = requests.post(url, data=params, timeout=30)
    resp.raise_for_status()
    return resp.json()["id"]


def post_triple(post_data, dry_run=False):
    """三段投稿を実行する"""
    theme = post_data["theme"]
    texts = [
        post_data["post1"] + "\n\n☛",
        post_data["post2"] + "\n\n☛",
        post_data["post3"],
    ]
    labels = ["メイン投稿", "返信1", "返信2"]

    print(f"\n[テーマ: {theme}]")

    parent_id = None

    for i, (text, label) in enumerate(zip(texts, labels)):
        print(f"\n--- {label} ---")
        print(text[:50] + "..." if len(text) > 50 else text)

        if dry_run:
            print(f"  [DRY-RUN] 投稿をスキップ")
            parent_id = f"dry-run-id-{i}"
            continue

        try:
            # コンテナ作成
            container_id = create_thread_container(text, reply_to_id=parent_id)
            print(f"  コンテナ作成完了: {container_id}")
            time.sleep(2)

            # 公開
            thread_id = publish_thread(container_id)
            print(f"  投稿完了: {thread_id}")
            parent_id = thread_id

            if i < len(texts) - 1:
                print(f"  {POST_INTERVAL}秒待機中...")
                time.sleep(POST_INTERVAL)

        except requests.exceptions.HTTPError as e:
            print(f"  エラー: {e}")
            print(f"  レスポンス: {e.response.text}")
            raise

    return True


def main():
    dry_run = "--dry-run" in sys.argv

    print("=" * 50)
    print("Threads 三段投稿 自動投稿スクリプト")
    print(f"実行日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    if dry_run:
        print("【DRY-RUN モード: 実際には投稿しません】")
    print("=" * 50)

    # 認証情報のチェック
    if not dry_run:
        if ACCESS_TOKEN == "YOUR_ACCESS_TOKEN_HERE":
            print("エラー: ACCESS_TOKEN が設定されていません。")
            print("スクリプト内の ACCESS_TOKEN を実際のトークンに変更してください。")
            sys.exit(1)
        if USER_ID == "YOUR_USER_ID_HERE":
            print("エラー: USER_ID が設定されていません。")
            print("スクリプト内の USER_ID を実際のユーザーIDに変更してください。")
            sys.exit(1)

    # 投稿原稿を読み込む
    posts = load_posts()
    post_map = {p["id"]: p for p in posts}
    total = len(posts)  # 100

    # 進捗を読み込む
    progress = load_progress()
    next_id = progress["next_id"]
    total_posted = progress["total_posted"]

    print(f"\n投稿原稿: {total}本")
    print(f"今日投稿するNo: {next_id}")
    print(f"累計投稿セット数: {total_posted}")

    # 対象の投稿を取得
    post_data = post_map.get(next_id)
    if not post_data:
        print(f"エラー: No.{next_id} の投稿データが見つかりません。")
        sys.exit(1)

    # 三段投稿を実行
    post_triple(post_data, dry_run=dry_run)

    # 進捗を更新（ループ: 100→1に戻る）
    next_next_id = (next_id % total) + 1
    progress["next_id"] = next_next_id
    progress["total_posted"] = total_posted + 1
    progress["last_posted"] = {
        "id": next_id,
        "theme": post_data["theme"],
        "timestamp": datetime.now().isoformat(),
        "dry_run": dry_run,
    }

    if not dry_run:
        save_progress(progress)
        print(f"\n✓ 投稿完了！次回はNo.{next_next_id}を投稿します。")
    else:
        print(f"\n✓ DRY-RUN 完了。進捗は保存していません。次回は引き続きNo.{next_id}です。")


if __name__ == "__main__":
    main()
