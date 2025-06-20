# Git Setup Instructions

Wildlife DetectorプロジェクトのGitリポジトリセットアップ手順

## リポジトリ情報
- **GitHub URL**: https://github.com/w-udagawa/wildlife-speciesnet-detector
- **作成日**: 2025年6月20日

## セットアップ手順

1. **コマンドプロンプトまたはPowerShellを開いて、プロジェクトディレクトリに移動:**
```bash
cd C:\Users\AU3009\Claudeworks\wildlife_detector
```

2. **Gitリポジトリを初期化:**
```bash
git init
```

3. **GitHubリモートリポジトリを追加:**
```bash
git remote add origin https://github.com/w-udagawa/wildlife-speciesnet-detector.git
```

4. **すべてのファイルをステージング:**
```bash
git add .
```

5. **初回コミット:**
```bash
git commit -m "Initial commit: Wildlife Detector application with SpeciesNet integration"
```

6. **mainブランチに変更（必要な場合）:**
```bash
git branch -M main
```

7. **GitHubにプッシュ:**
```bash
git push -u origin main
```

## 認証について

GitHubにプッシュする際は、以下のいずれかの方法で認証が必要です：

1. **Personal Access Token (推奨)**
   - GitHubの Settings > Developer settings > Personal access tokens で作成
   - `git push`時にパスワードの代わりに使用

2. **SSH Key**
   - SSH鍵を生成してGitHubに登録
   - リモートURLをSSH形式に変更: `git remote set-url origin git@github.com:w-udagawa/wildlife-speciesnet-detector.git`

## 今後の開発フロー

1. **新機能の開発:**
```bash
git checkout -b feature/new-feature
# 開発作業
git add .
git commit -m "Add: new feature description"
git push origin feature/new-feature
```

2. **バグ修正:**
```bash
git checkout -b fix/bug-description
# 修正作業
git add .
git commit -m "Fix: bug description"
git push origin fix/bug-description
```

3. **プルリクエストの作成:**
   - GitHubでPull Requestを作成
   - コードレビュー後にmainブランチにマージ

## 便利なGitコマンド

- 状態確認: `git status`
- ログ確認: `git log --oneline`
- 差分確認: `git diff`
- ブランチ一覧: `git branch -a`
- 最新を取得: `git pull origin main`
