# 🚀 Wildlife Detector - Git Setup Quick Start

## 準備するもの
- [ ] GitHubアカウント
- [ ] Git for Windows（インストール済みか確認）
- [ ] Personal Access Token（まだの場合は`GITHUB_AUTH_GUIDE.md`参照）

## 実行手順

### 方法1: バッチファイルを使う（簡単）

1. **エクスプローラーで以下のフォルダを開く:**
   ```
   C:\Users\AU3009\Claudeworks\wildlife_detector
   ```

2. **`setup_git.bat`をダブルクリック**

3. **画面の指示に従う**
   - GitHubの認証が求められたら：
     - Username: あなたのGitHubユーザー名
     - Password: Personal Access Token（パスワードではない！）

### 方法2: PowerShellスクリプトを使う（詳細）

1. **PowerShellを管理者として実行**
   - Windowsキー + X → Windows PowerShell (管理者)

2. **実行ポリシーを一時的に変更（必要な場合）:**
   ```powershell
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
   ```

3. **スクリプトを実行:**
   ```powershell
   C:\Users\AU3009\Claudeworks\wildlife_detector\setup_git.ps1
   ```

4. **画面の指示に従う**

### 方法3: 手動でコマンドを実行

1. **コマンドプロンプトまたはPowerShellを開く**

2. **以下のコマンドを順番に実行:**

```bash
# ディレクトリに移動
cd C:\Users\AU3009\Claudeworks\wildlife_detector

# Git初期化
git init

# リモートリポジトリを追加
git remote add origin https://github.com/w-udagawa/wildlife-speciesnet-detector.git

# すべてのファイルを追加
git add .

# 初回コミット
git commit -m "Initial commit: Wildlife Detector application with SpeciesNet integration"

# mainブランチに変更
git branch -M main

# GitHubにプッシュ（認証が必要）
git push -u origin main
```

## ✅ 成功したら

1. ブラウザで https://github.com/w-udagawa/wildlife-speciesnet-detector を開く
2. ファイルがアップロードされていることを確認

## ❌ エラーが出たら

### "git: command not found"
→ Gitがインストールされていません。https://git-scm.com/ からダウンロード

### "Authentication failed"
→ Personal Access Tokenが間違っています。`GITHUB_AUTH_GUIDE.md`を参照

### "remote origin already exists"
→ すでに設定済みです。以下のコマンドで確認：
```bash
git remote -v
```

## 🎉 完了後の開発

```bash
# 変更をコミット
git add .
git commit -m "Update: 変更内容の説明"
git push

# 最新を取得
git pull

# 状態確認
git status
```

---
問題があれば、`GIT_SETUP.md`と`GITHUB_AUTH_GUIDE.md`も参照してください。
