"""
Threads 三段投稿 自動投稿スクリプト（朝/昼/夜 3回投稿版）
アカウント: @sakichan122

スケジュール:
    朝  6:00 JST → 朝コンテンhツを投稿
    昼 12:00 JST → 昼コンテンツを投稿
    夜 20:00 JST → 夜コンテンツを投稿（投稿後にday+1）

100日でループ（101日目は1日目に戻る）

使い方:
    python threads_auto_post.py           # 実際に投稿
    python threads_auto_post.py --dry-run # テストのみ（投稿しない）
"""

import json
import time
import sys
import os
import requests
from datetime import datetime, timezone, timedelta

# ============================================================
# 設定（GitHub Secrets から取得）
# ============================================================
ACCESS_TOKEN = os.environ.get("THREADS_ACCESS_TOKEN", "")
USER_ID = "26732151053133237"

# ファイルパス（スクリプトと同じフォルダ）
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
POSTS_FILE = os.path.join(SCRIPT_DIR, "threads_posts_all300.json")
PROGRESS_FILE = os.path.join(SCRIPT_DIR, "progress.json")

API_BASE = "https://graph.threads.net/v1.0"
POST_INTERVAL = 5  # 投稿間の待機秒数


# ============================================================
# 時間帯判定（JST基準）
# ============================================================
JST = timezone(timedelta(hours=9))

def get_slot():
    """現在のJST時刻から投稿スロット（朝/昼/夜）を返す"""
    now_jst = datetime.now(JST)
    hour = now_jst.hour
    if 3 <= hour < 9:      # 3〜8時 → 朝（6時投稿）
        return "朝"
    elif 9 <= hour < 19:   # 9〜16時 → 昼（12時投稿）
        return "昼"
    else:                   # 17〜翌3時 → 夜（20時投稿）
        return "夜"


# ============================================================
# データ読み書き
# ============================================================
def load_posts():
    with open(POSTS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def load_progress():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"day": 0, "total_days": 0}


def save_progress(progress):
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(progress, f, ensure_ascii=False, indent=2)


# ============================================================
# Threads API
# ============================================================
def create_thread_container(text, reply_to_id=None):
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
    url = f"{API_BASE}/{USER_ID}/threads_publish"
    params = {
        "creation_id": creation_id,
        "access_token": ACCESS_TOKEN,
    }
    resp = requests.post(url, data=params, timeout=30)
    resp.raise_for_status()
    return resp.json()["id"]


def post_triple(post_data, dry_run=False):
    """3段投稿を実行する"""
    theme = post_data["theme"]
    texts = [post_data["post1"], post_data["post2"], post_data["post3"]]
    labels = ["メイン投稿", "返信1（2段目）", "返信2（3段目）"]

    print(f"\n[テーマ: {theme}]")
    parent_id = None

    for i, (text, label) in enumerate(zip(texts, labels)):
        print(f"\n--- {label} ---")
        print(text[:60] + "..." if len(text) > 60 else text)

        if dry_run:
            print("  [DRY-RUN] 投稿をスキップ")
            parent_id = f"dry-run-id-{i}"
            continue

        try:
            container_id = create_thread_container(text, reply_to_id=parent_id)
            print(f"  コンテナ作成: {container_id}")
            time.sleep(2)

            thread_id = publish_thread(container_id)
            print(f"  投稿完了: {thread_id}")
            parent_id = thread_id

            if i < len(texts) - 1:
                print(f"  {POST_INTERVAL}秒待機...")
                time.sleep(POST_INTERVAL)

        except requests.exceptions.HTTPError as e:
            print(f"  エラー: {e}")
            print(f"  レスポンス: {e.response.text}")
            raise

    return True


# ============================================================
# メイン処理
# ============================================================
def main():
    dry_run = "--dry-run" in sys.argv

    now_jst = datetime.now(JST)
    slot = get_slot()

    print("=" * 50)
    print("Threads 自動投稿スクリプト（朝/昼/夜 3回投稿版）")
    print(f"実行日時（JST）: {now_jst.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"投稿スロット: {slot}")
    if dry_run:
        print("【DRY-RUN モード: 実際には投稿しません】")
    print("=" * 50)

    if not dry_run and not ACCESS_TOKEN:
        print("エラー: THREADS_ACCESS_TOKEN 環境変数が設定されていません。")
        sys.exit(1)

    # 投稿データ読み込み
    all_posts = load_posts()
    asa  = [p for p in all_posts if p.get("time") == "朝"]   # 100本
    hiru = [p for p in all_posts if p.get("time") == "昼"]   # 100本
    yoru = [p for p in all_posts if p.get("time") == "夜"]   # 100本

    # 進捗読み込み
    progress = load_progress()
    day = progress.get("day", 0)  # 0〜99

    # 今日のスロット投稿を選択
    if slot == "朝":
        post_data = asa[day]
    elif slot == "昼":
        post_data = hiru[day]
    else:
        post_data = yoru[day]

    print(f"\n📅 Day {day + 1}/100 [{slot}]")
    print(f"   投稿テーマ: {post_data['theme']} (ID: {post_data['id']})")

    # 投稿実行
    post_triple(post_data, dry_run=dry_run)

    # 進捗更新
    if not dry_run:
        progress["last_posted"] = {
            "slot": slot,
            "day": day + 1,
            "id": post_data["id"],
            "theme": post_data["theme"],
            "timestamp": now_jst.isoformat(),
        }

        # 夜投稿後にdayを進める（100日でループ）
        if slot == "夜":
            next_day = (day + 1) % 100
            progress["day"] = next_day
            progress["total_days"] = progress.get("total_days", 0) + 1
            print(f"\n📅 Day {day + 1} 完了 → 次は Day {next_day + 1}")

        save_progress(progress)
        print(f"\n✅ {slot}投稿完了！")
    else:
        print(f"\n✅ DRY-RUN 完了。進捗は保存していません。")


if __name__ == "__main__":
    main()
