# GitHub Authentication Guide

Wildlife DetectorをGitHubにプッシュするための認証設定ガイド

## Personal Access Token (PAT) の作成手順

### 1. GitHubにログイン
https://github.com にアクセスしてログインしてください。

### 2. Personal Access Tokenページへ移動
1. 右上のプロフィールアイコンをクリック
2. **Settings** を選択
3. 左側メニューの一番下にある **Developer settings** をクリック
4. **Personal access tokens** → **Tokens (classic)** を選択

### 3. 新しいトークンを生成
1. **Generate new token** → **Generate new token (classic)** をクリック
2. **Note** に `Wildlife Detector` など識別しやすい名前を入力
3. **Expiration** で有効期限を選択（90日推奨）
4. **Select scopes** で以下を選択：
   - ✅ **repo** (Full control of private repositories)
   - ✅ **workflow** (Update GitHub Action workflows)

### 4. トークンを生成して保存
1. ページ下部の **Generate token** をクリック
2. 表示されたトークンをコピー（この画面を離れると二度と表示されません！）
3. 安全な場所（パスワードマネージャーなど）に保存

## トークンの使用方法

### コマンドラインでの使用
`git push` 実行時：
- Username: あなたのGitHubユーザー名
- Password: **生成したPersonal Access Token**（通常のパスワードではありません）

### 認証情報の保存（オプション）
毎回入力を避けるため、認証情報を保存できます：

```bash
# Windowsの場合（Git Credential Manager）
git config --global credential.helper manager

# 認証情報をキャッシュ（1時間）
git config --global credential.helper cache

# 認証情報をキャッシュ（カスタム時間、例：8時間）
git config --global credential.helper 'cache --timeout=28800'
```

## トラブルシューティング

### "Authentication failed" エラーが出る場合
1. Personal Access Tokenが正しくコピーされているか確認
2. トークンの有効期限が切れていないか確認
3. `repo` スコープが選択されているか確認

### "Permission denied" エラーが出る場合
1. リポジトリのURLが正しいか確認：
   ```bash
   git remote -v
   ```
2. 正しいユーザー名を使用しているか確認

### 認証情報をリセットしたい場合
```bash
# Windows
git config --global --unset credential.helper

# 保存された認証情報をクリア
git credential reject
```

## セキュリティのベストプラクティス

1. **トークンは絶対に他人と共有しない**
2. **コードにトークンを直接書かない**
3. **不要になったトークンは削除する**
4. **最小限の権限（スコープ）のみ付与する**
5. **定期的にトークンを更新する**

## 参考リンク

- [GitHub Docs: Personal Access Tokens](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token)
- [Git Credential Storage](https://git-scm.com/book/en/v2/Git-Tools-Credential-Storage)
