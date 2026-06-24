"""
Threads アクセストークン 自動更新スクリプト
毎月1回GitHub Actionsから実行される

必要なSecrets:
  THREADS_ACCESS_TOKEN  - 現在のThreadsトークン
  GH_PAT                - GitHubのPersonal Access Token（secrets:write権限）
"""

import os
import sys
import requests
import base64
from nacl import encoding, public

OWNER = "pinkcatichino-lang"
REPO = "threads-auto-post"
SECRET_NAME = "THREADS_ACCESS_TOKEN"


def refresh_threads_token(current_token):
    """Threadsトークンを更新して新しいトークンを返す"""
    url = "https://graph.threads.net/refresh_access_token"
    resp = requests.get(url, params={
        "grant_type": "th_refresh_token",
        "access_token": current_token,
    }, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    new_token = data["access_token"]
    expires_in = data.get("expires_in", "不明")
    print(f"✅ トークン更新成功！有効期限: {int(expires_in) // 86400}日")
    return new_token


def update_github_secret(new_token, gh_pat):
    """GitHubのSecretsに新しいトークンを保存する"""
    headers = {
        "Authorization": f"token {gh_pat}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    # リポジトリの公開鍵を取得（暗号化に必要）
    key_resp = requests.get(
        f"https://api.github.com/repos/{OWNER}/{REPO}/actions/secrets/public-key",
        headers=headers, timeout=30
    )
    key_resp.raise_for_status()
    key_data = key_resp.json()

    # トークンを公開鍵で暗号化
    pub_key = public.PublicKey(key_data["key"].encode("utf-8"), encoding.Base64Encoder())
    sealed_box = public.SealedBox(pub_key)
    encrypted = base64.b64encode(
        sealed_box.encrypt(new_token.encode("utf-8"))
    ).decode("utf-8")

    # Secretを更新
    secret_resp = requests.put(
        f"https://api.github.com/repos/{OWNER}/{REPO}/actions/secrets/{SECRET_NAME}",
        headers=headers,
        json={"encrypted_value": encrypted, "key_id": key_data["key_id"]},
        timeout=30
    )
    secret_resp.raise_for_status()
    print(f"✅ GitHub Secret '{SECRET_NAME}' を更新しました！")


def main():
    current_token = os.environ.get("THREADS_ACCESS_TOKEN", "")
    gh_pat = os.environ.get("GH_PAT", "")

    if not current_token:
        print("エラー: THREADS_ACCESS_TOKEN が設定されていません")
        sys.exit(1)
    if not gh_pat:
        print("エラー: GH_PAT が設定されていません")
        sys.exit(1)

    print("🔄 Threadsトークンを更新中...")
    new_token = refresh_threads_token(current_token)

    print("🔄 GitHubのSecretを更新中...")
    update_github_secret(new_token, gh_pat)

    print("\n🎉 完了！次の更新は来月自動で行われます。")


if __name__ == "__main__":
    main()
