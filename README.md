# Wildlife Detector

野生生物検出デスクトップアプリケーション - Google SpeciesNetを使用した高精度な鳥類・哺乳類検出

## 概要

Wildlife Detectorは、画像から野生生物（特に鳥類と哺乳類）を自動検出するデスクトップアプリケーションです。Google SpeciesNetの最新のAIモデルを使用して、高精度な種の識別を実現します。

**v2.1の主な改善**: 1万枚以上の大量連続処理に向けた堅牢性強化（レジューム機能、EXIF撮影日のCSV保存、進捗コールバックのスロットリング、チャンク境界中間保存、パス長対策、ほか）。

## 主な機能

- **高精度な種識別**: Google SpeciesNetによる最先端のAI検出
- **大量バッチ処理**: 数万枚の画像を安定して処理（ストリーミング処理対応）
- **レジューム対応**: 中断したCSVから未処理分だけを続行 (1万枚処理中のクラッシュ耐性)
- **日付別振り分け**: EXIF DateTimeOriginal を抽出し `{日付}/{種別}/` 構造で整理
- **日付×種別ピボットCSV**: 日付を列・撮影種を行とした集計表を出力（Excelですぐ開ける）
- **メモリ効率化**: チャンク境界でCSVへ保存しメモリを解放 (`gc.collect()` 併用)
- **英語（日本語）表示**: 学名と和名を併記 (例: `Corvus macrorhynchos (ハシブトガラス)`)
- **未検出フォルダの統一**: blank / no cv result / 検出なし を `未検出_No_Detection/` に集約
- **ページング表示**: 100件ずつの結果表示でUI負荷を軽減 (メタデータはキャッシュ)
- **CSV出力**: 結果をExcelで開けるCSV形式で保存（`image_date` 列を含む）
- **直感的なGUI**: PySide6による使いやすいインターフェース

## 必要要件

- Python 3.12以上
- Windows 10/11（他のOSは未テスト）
- 8GB以上のRAM推奨（大量画像処理時）
- GPU（オプション - パフォーマンス向上のため）

## インストール

1. リポジトリをクローン:
```bash
git clone https://github.com/w-udagawa/wildlife-speciesnet-detector.git
cd wildlife-speciesnet-detector
```

2. 仮想環境を作成・有効化:

**PowerShell:**
```powershell
python -m venv wildlife_env
wildlife_env\Scripts\Activate.ps1
```

**コマンドプロンプト (cmd):**
```cmd
python -m venv wildlife_env
wildlife_env\Scripts\activate.bat
```

3. pip を最新化し、依存関係をインストール:
```bash
python -m pip install --upgrade pip
pip install "setuptools<81" wheel
pip install -r requirements.txt
```

> **Note**: `setuptools<81` は必ず `requirements.txt` より先にインストールしてください。speciesnet が内部で使用する `pkg_resources` は setuptools 81 で削除されたため、setuptools >= 81 では import に失敗します。

## 使い方

1. アプリケーションを起動:
```bash
python main.py
```

2. 「入力・設定」タブで画像またはフォルダを選択

3. 出力フォルダを指定

4. 「検出処理開始」をクリック

5. 処理完了後、「結果」タブで検出結果を確認
   - 結果は100件ずつページング表示されます
   - 「前へ」「次へ」ボタンでページ移動
   - 「日付×種別ピボット出力」ボタンで集計CSVを生成

### 出力オプション

「入力・設定」タブに以下のチェックボックスがあります：
- **種別フォルダを作成**: 検出結果に基づく自動振り分け
- **画像をコピー**: チェックなしの場合は移動
- **撮影日ごとにサブフォルダを作成**: 振り分けを `{YYYY-MM-DD}/{種別}/` 構造にする

## プロジェクト構造

```
wildlife-speciesnet-detector/
├── core/                          # コア検出ロジック
│   ├── species_detector_direct.py # SpeciesNet検出器（構造化パース / 未検出判定）
│   ├── batch_processor.py         # バッチ処理（ストリーミング / レジューム対応）
│   └── config.py                  # 設定管理
├── gui/                           # GUIコンポーネント
│   ├── main_window.py             # メインウィンドウ（ページング / 振り分け進捗）
│   ├── themes.py                  # UIテーマ
│   ├── icons.py                   # アイコンリソース
│   └── splash.py                  # スプラッシュスクリーン
├── utils/                         # ユーティリティ
│   ├── image_meta.py              # EXIF 撮影日抽出
│   ├── csv_exporter.py            # CSV出力（ピボット / サマリー）
│   └── file_manager.py            # ファイル管理（日付別振り分け / パス長検証）
├── tests/                         # pytest ユニットテスト (63件)
│   ├── conftest.py
│   ├── test_config.py
│   ├── test_species_detector_parser.py
│   ├── test_species_detector_structured.py
│   ├── test_file_manager.py
│   ├── test_csv_exporter.py
│   ├── test_extract_image_date.py
│   ├── test_pivot_export.py
│   ├── test_batch_processor_resume.py
│   └── test_organize_progress_and_paths.py
├── scripts/
│   └── smoke_test.py              # CLI スモークテスト（動作確認 / ベンチマーク）
├── main.py                        # エントリーポイント
├── pyproject.toml                 # プロジェクト設定・ツール設定
├── requirements.txt               # 実行時依存関係
└── requirements-dev.txt           # 開発用依存関係
```

## 設定オプション

### 検出設定
- **信頼度閾値**: 検出の最小信頼度（0.0-1.0、デフォルト: 0.1）
- **バッチサイズ**: SpeciesNet内部のGPU処理単位（デフォルト: 32）
- **予測チャンクサイズ**: `predict()` 1回あたりの画像数（デフォルト: 500）
- **地域フィルター**: 特定地域の種に限定（JPN, USA, etc.）
- **実行モード**: SpeciesNet APIの実行モード（`multi_thread` / `single`、デフォルト: `multi_thread`）

### 表示カテゴリマッピング
SpeciesNet の `class` フィールドを以下のカテゴリにマッピングして表示します（未登録の分類群は小文字クラス名をそのまま使用）：

| SpeciesNet class | 表示カテゴリ |
|------------------|-------------|
| aves             | bird        |
| mammalia         | mammal      |
| reptilia         | reptile     |
| amphibia         | amphibian   |
| actinopterygii   | fish        |
| insecta          | insect      |

### パフォーマンス設定
- **GPU使用**: GPUアクセラレーションの有効/無効

### メモリ管理設定
- **GC間隔**: ガベージコレクション実行間隔（デフォルト: 50枚ごと）
- **中間保存**: チャンク境界（`predict_chunk_size` 完了時）で自動的にCSVに追記＋メモリ解放
- **連続エラー上限**: 自動中断までのAPI例外連続回数（デフォルト: 3、検出0件は加算しない）

### 出力CSVのカラム構成

検出結果CSVには以下の列が出力されます：

| 列名 | 内容 |
|------|------|
| image_path | 入力画像のフルパス |
| image_name | 画像ファイル名 |
| image_date | EXIF DateTimeOriginal → DateTimeDigitized → DateTime → mtime の順に解決した撮影日 (YYYY-MM-DD) |
| species | 表示種名（`学名 (common_name)` 併記、未検出は空） |
| scientific_name | 学名のみ |
| confidence | 信頼度 (0.0-1.0) |
| category | 表示カテゴリ (bird/mammal/reptile/.../no_detection) |
| common_name | 一般名（日本語 common_name があればここに入る） |
| timestamp | 検出時刻 (ISO8601) |

## 自動ファイル振り分け機能

検出結果CSV（ストリーミング読込）に基づいて画像ファイルを自動的に振り分けます：

- **種別フォルダ自動作成**: 検出された種ごとにフォルダを作成（`{common_name}_{scientific}` 併記）
- **日付別サブフォルダ**: 「撮影日ごとにサブフォルダを作成」を有効化すると `{YYYY-MM-DD}/{種別}/` 階層で振り分け
- **コピー/移動選択**: 元ファイルを保持するコピーモードと移動モードを選択可能
- **未検出ファイル処理**: `blank`・`no cv result`・検出なし を全て `未検出_No_Detection/` に集約
- **進捗表示**: 100枚ごとに進捗コールバックが発火（1万枚コピー中のハング懸念を解消）
- **Windows MAX_PATH 対策**: 振り分け先パスが240字を超える場合、フォルダ名をSHA-1ハッシュ(8桁)付きで短縮

## 日付×撮影種ピボットCSV

検出CSVをもとに、日付を列・撮影種を行としたピボット集計CSVを出力できます（「結果」タブの「日付×種別ピボット出力」ボタン、または `CSVExporter.export_daily_species_pivot()`）。

出力イメージ：
```
日付,2024-11-21,2024-11-22,2024-12-05,...
合計撮影枚数,10,5,3,...
撮影無し,3,2,1,...
ハシブトガラス,5,1,0,...
Nyctereutes procyonoides,0,2,1,...
...
合計,10,5,3,...
```
- 日本語 common_name があれば行ラベルに優先利用
- `blank` / `no cv result` / 検出なし はすべて **撮影無し** 行に集約
- 日付は検出CSVの `image_date` 列を参照（EXIF再読込なし）

## 大量画像処理について（1万枚以上を想定）

数万枚の画像を安定して処理するための堅牢性機能：

1. **ストリーミング処理**: チャンク境界でCSVに追記＋メモリ解放。バッファ滞留はチャンクサイズ以内
2. **レジューム機能**: クラッシュ／停止後、既存検出CSVを `resume_from_csv=` に渡すと未処理分だけ続行
3. **EXIF撮影日のCSV保存**: 処理中に1回だけEXIFを読み、以降の振り分け/ピボットで再利用（10倍高速化）
4. **API例外のみでエラーカウント**: 「検出0件」は停止条件に含めない（blank連続でも止まらない）
5. **進捗コールバックのスロットリング**: 20枚／0.5秒ごとに間引き、UIスレッドの飽和を防止
6. **CSVヘッダーの明示管理**: 部分書込み後でもヘッダー重複・欠落を起こさない
7. **ページング表示**: 結果画面で100件ずつ表示、総行数・種数はメタデータとしてキャッシュ
8. **定期的なGC**: チャンク境界で `gc.collect()` を実行

### スモークテスト / ベンチマーク

`scripts/smoke_test.py` でCLIから検出パイプラインを直接検証できます（GUI不要）：

```bash
# 既定: 3枚で動作確認
python scripts/smoke_test.py

# 全画像を処理 + 自動振り分け + ピボット出力
python scripts/smoke_test.py --all --organize --organize-by-date

# 既存CSVからレジューム
python scripts/smoke_test.py --all --resume smoke_output/detection_results_YYYYMMDD_HHMMSS.csv

# 別フォルダを対象にする
python scripts/smoke_test.py --input /path/to/images --all
```

出力先は `smoke_output/` (既定)。`--clean` で実行前に削除できます。

## テスト

pytest によるユニットテストを同梱しています（**63件**）。

```bash
# 開発用依存関係のインストール
pip install -r requirements-dev.txt

# テスト実行
pytest tests/ --no-cov

# カバレッジ付きで実行（pyproject.toml の設定に従う）
pytest tests/
```

テスト対象：
- `core.config.AppConfig` の設定互換性（旧バージョン設定ファイルの未知キーを無視）
- `SpeciesDetectorDirect` の予測パース（構造化キー優先 / 文字列フォールバック / blank・no cv result 判定 / 英語(日本語) 併記）
- `BatchProcessor` のレジューム機能・API例外のみ連続エラー加算・CSVヘッダー管理・image_date 列・find_images
- `FileManager` のフォルダ名サニタイズ・衝突回避・未検出統一・日付別振り分け・進捗コールバック・パス長短縮
- `CSVExporter` のストリーミング集計・日付×種別ピボット
- `extract_image_date` の EXIF 解釈 (DateTimeOriginal / DateTimeDigitized / DateTime / mtime 優先順)

## トラブルシューティング

### speciesnet の import に失敗する

```
ERROR - ✗ speciesnet - 未インストール
```
または
```
ModuleNotFoundError: No module named 'pkg_resources'
```

**原因**: setuptools >= 81 がインストールされている環境では、speciesnet が依存する `pkg_resources` が利用できません。

**対処法**:
```bash
pip install "setuptools<81"
pip install --force-reinstall speciesnet
```

### Python 3.12+ の venv で setuptools が自動的に 82+ になる

Python 3.12 以降の `python -m venv` は setuptools 82+ をバンドルする場合があります。仮想環境作成後、最初に `pip install "setuptools<81"` を実行してください。

## ライセンス

このプロジェクトはMITライセンスの下で公開されています。詳細は[LICENSE](LICENSE)ファイルを参照してください。

## 貢献

プルリクエストを歓迎します！大きな変更を行う場合は、まずissueを開いて変更内容について議論してください。

## 謝辞

- Google SpeciesNetチームの優れたAIモデル
- PySide6コミュニティ
- すべての貢献者とテスター




