# Backup History

このドキュメントは、wildlife_detectorアプリケーションの開発過程で作成されたバックアップファイルの履歴を記録しています。

## バックアップファイル一覧

### Core モジュール (/backups/core/)

1. **species_detector_direct_backup_20250606_195109.py**
   - 作成日: 2025年6月6日 19:51:09
   - 説明: species_detector_direct.pyの初期バージョンのバックアップ

2. **species_detector_direct_fixed.py**
   - 説明: バグ修正版の試作

3. **species_detector_fixed.py**
   - 説明: 初期の修正版実装

4. **species_detector_real.py**
   - 説明: 実際のSpeciesNet統合を試みた初期バージョン

5. **species_detector_real.py.backup**
   - 説明: species_detector_real.pyのバックアップ

6. **species_detector_subprocess.py**
   - 説明: サブプロセスを使用した実装の試み

### GUI モジュール (/backups/gui/)

1. **main_window_backup.py**
   - 説明: メインウィンドウの最初のバックアップ

2. **main_window_original_backup.py**
   - 説明: オリジナルのメインウィンドウ実装

## 開発履歴

1. **初期開発** - species_detector_real.pyで基本実装
2. **サブプロセス版** - species_detector_subprocess.pyでプロセス分離を試行
3. **修正版** - species_detector_fixed.pyでバグ修正
4. **直接統合版** - species_detector_direct.pyで最終的な実装（現在使用中）

## 注意事項

- これらのバックアップファイルは参考用として保存されています
- 現在のアクティブなコードは`/core/`と`/gui/`ディレクトリにあります
- Gitを使用したバージョン管理に移行したため、今後はGitで履歴を管理します
