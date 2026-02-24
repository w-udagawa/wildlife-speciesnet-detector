# Wildlife Detector

野生生物検出デスクトップアプリケーション - Google SpeciesNetを使用した高精度な鳥類・哺乳類検出

## 概要

Wildlife Detectorは、画像から野生生物（特に鳥類と哺乳類）を自動検出するデスクトップアプリケーションです。Google SpeciesNetの最新のAIモデルを使用して、高精度な種の識別を実現します。

**v2.0の主な改善**: SpeciesNetネイティブAPI化による高速バッチ処理、メモリ効率の大幅改善。

## 主な機能

- **高精度な種識別**: Google SpeciesNetによる最先端のAI検出
- **大量バッチ処理**: 数万枚の画像を安定して処理（ストリーミング処理対応）
- **メモリ効率化**: 中間結果のCSV保存とメモリ自動解放
- **ページング表示**: 100件ずつの結果表示でUI負荷を軽減
- **自動ファイル整理**: 検出結果に基づいて画像を種別に振り分け
- **CSV出力**: 結果をExcelで開けるCSV形式で保存
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

## プロジェクト構造

```
wildlife_detector/
├── core/                          # コア検出ロジック
│   ├── __init__.py
│   ├── species_detector_direct.py # SpeciesNet検出器
│   ├── batch_processor.py         # バッチ処理（ストリーミング対応）
│   └── config.py                  # 設定管理
├── gui/                           # GUIコンポーネント
│   ├── __init__.py
│   ├── main_window.py             # メインウィンドウ（ページング対応）
│   ├── themes.py                  # UIテーマ
│   └── icons.py                   # アイコンリソース
├── utils/                         # ユーティリティ
│   ├── __init__.py
│   ├── csv_exporter.py            # CSV出力（ストリーミング対応）
│   └── file_manager.py            # ファイル管理（CSV対応）
├── main.py                        # エントリーポイント
└── requirements.txt               # 依存関係
```

## 設定オプション

### 検出設定
- **信頼度閾値**: 検出の最小信頼度（0.0-1.0、デフォルト: 0.1）
- **バッチサイズ**: SpeciesNet内部のGPU処理単位（デフォルト: 32）
- **予測チャンクサイズ**: `predict()` 1回あたりの画像数（デフォルト: 500）
- **地域フィルター**: 特定地域の種に限定（JPN, USA, etc.）
- **実行モード**: SpeciesNet APIの実行モード（`multi_thread` / `single`、デフォルト: `multi_thread`）

### パフォーマンス設定
- **最大ワーカー数**: 並列処理スレッド数（デフォルト: 2）
- **GPU使用**: GPUアクセラレーションの有効/無効

### メモリ管理設定
- **GC間隔**: ガベージコレクション実行間隔（デフォルト: 50枚ごと）
- **中間保存間隔**: CSV保存とメモリ解放間隔（デフォルト: 100枚ごと）
- **連続エラー上限**: 自動中断までのエラー回数（デフォルト: 3回）

## 自動ファイル振り分け機能

検出結果に基づいて画像ファイルを自動的に振り分ける機能を追加しました：

- **種別フォルダ自動作成**: 検出された種ごとにフォルダを作成
- **コピー/移動選択**: 元ファイルを保持するコピーモードと移動モードを選択可能
- **未検出ファイル処理**: 何も検出されなかった画像も「undetected」フォルダに整理

## 大量画像処理について

数万枚の画像を安定して処理するためのメモリ効率化機能：

1. **ストリーミング処理**: 全結果をメモリに保持せず、100件ごとにCSVへ保存してメモリを解放
2. **ページング表示**: 結果画面で100件ずつ表示し、UIのメモリ負荷を軽減
3. **定期的なGC**: 処理中に定期的なガベージコレクションを実行
4. **中断機能**: 連続エラー発生時に自動的に処理を中断して結果を保存

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




