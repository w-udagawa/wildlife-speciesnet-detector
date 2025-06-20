# Wildlife Detector - ファイル整理記録

整理日: 2025年6月20日

## ファイル整理の概要

Wildlife Detectorアプリケーションのファイル構造を整理し、バックアップファイルと使用されていない古いバージョンのファイルを適切に管理しました。

## 整理前の状況

- `core`ディレクトリに8つの異なるバージョンの`species_detector`ファイルが混在
- `gui`ディレクトリに複数のバックアップファイルが存在
- `__pycache__`ディレクトリが複数箇所に散在

## 実施した整理作業

### 1. バックアップディレクトリの作成
- `/backups/core/` - coreモジュールのバックアップ用
- `/backups/gui/` - GUIモジュールのバックアップ用

### 2. 移動したファイル

#### coreディレクトリから移動:
- `species_detector_direct_backup_20250606_195109.py` → `/backups/core/`
- `species_detector_real.py.backup` → `/backups/core/`
- `species_detector_direct_fixed.py` → `/backups/core/`
- `species_detector_fixed.py` → `/backups/core/`
- `species_detector_real.py` → `/backups/core/`
- `species_detector_subprocess.py` → `/backups/core/`

#### guiディレクトリから移動:
- `main_window_backup.py` → `/backups/gui/`
- `main_window_original_backup.py` → `/backups/gui/`

## 現在のファイル構成

### アクティブなファイル（使用中）

#### coreディレクトリ:
- `species_detector_direct.py` - メインの検出器実装
- `species_detector.py` - 基本クラスとDetectionResult定義
- `batch_processor.py` - バッチ処理ロジック
- `config.py` - 設定管理
- `mock_species_net.py` - テスト用モック
- `__init__.py` - パッケージ初期化

#### guiディレクトリ:
- `main_window.py` - メインGUIウィンドウ
- `icons.py` - アイコン管理
- `splash.py` - スプラッシュスクリーン
- `themes.py` - テーマ設定
- `__init__.py` - パッケージ初期化

#### utilsディレクトリ:
- `csv_exporter.py` - CSV出力機能
- `file_manager.py` - ファイル管理機能
- `__init__.py` - パッケージ初期化

### メインファイル:
- `main.py` - アプリケーションエントリーポイント

## 推奨事項

1. **__pycache__ディレクトリの管理**
   - `.gitignore`ファイルに`__pycache__/`を追加して、バージョン管理から除外することを推奨
   - 定期的に削除しても問題ありません（Pythonが自動再生成）

2. **バックアップファイルの管理**
   - 必要に応じて`/backups/`ディレクトリからファイルを復元可能
   - 長期的には不要なバックアップは削除を検討

3. **今後の開発**
   - 新しいバージョンを作成する際は、適切なバージョン管理（Git）の使用を推奨
   - ファイル名に日付やバージョン番号を含めるのではなく、Gitのブランチとタグを活用

## 注意事項

- `batch_processor.py`は`species_detector_direct.py`を最優先で使用するよう設定されています
- 他のバージョンのspecies_detectorファイルは、フォールバックとして定義されていましたが、現在はバックアップディレクトリに移動済みです
