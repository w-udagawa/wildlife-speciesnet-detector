# Wildlife Detector

野生生物検出デスクトップアプリケーション - Google SpeciesNetを使用した高精度な鳥類・哺乳類検出

## 概要

Wildlife Detectorは、画像から野生生物（特に鳥類と哺乳類）を自動検出するデスクトップアプリケーションです。Google SpeciesNetの最新のAIモデルを使用して、高精度な種の識別を実現します。

## 主な機能

- 🦅 **高精度な種識別**: Google SpeciesNetによる最先端のAI検出
- 🖼️ **バッチ処理**: 複数の画像を一度に処理
- 📊 **詳細な結果表示**: 種名、学名、信頼度スコアなどを表示
- 📁 **自動ファイル整理**: 検出結果に基づいて画像を種別に振り分け
- 📈 **CSV出力**: 結果をExcelで開けるCSV形式で保存
- 🎨 **直感的なGUI**: PySide6による使いやすいインターフェース

## 必要要件

- Python 3.12以上
- Windows 10/11（他のOSは未テスト）
- 4GB以上のRAM推奨
- GPU（オプション - パフォーマンス向上のため）

## インストール

1. リポジトリをクローン:
```bash
git clone https://github.com/yourusername/wildlife-detector.git
cd wildlife-detector
```

2. 仮想環境を作成・有効化:
```bash
python -m venv wildlife_env
wildlife_env\Scripts\activate  # Windows
```

3. 依存関係をインストール:
```bash
pip install -r requirements.txt
```

4. SpeciesNetをインストール:
```bash
pip install speciesnet
```

## 使い方

1. アプリケーションを起動:
```bash
python main.py
```

2. 「入力・設定」タブで画像またはフォルダを選択

3. 出力フォルダを指定

4. 「検出処理開始」をクリック

5. 処理完了後、「結果」タブで検出結果を確認

## プロジェクト構造

```
wildlife_detector/
├── core/               # コア検出ロジック
│   ├── species_detector_direct.py  # メイン検出器
│   ├── batch_processor.py          # バッチ処理
│   └── config.py                   # 設定管理
├── gui/                # GUIコンポーネント
│   ├── main_window.py  # メインウィンドウ
│   └── themes.py       # UIテーマ
├── utils/              # ユーティリティ
│   ├── csv_exporter.py # CSV出力
│   └── file_manager.py # ファイル管理
├── main.py             # エントリーポイント
└── requirements.txt    # 依存関係
```

## 設定オプション

- **信頼度閾値**: 検出の最小信頼度（0.0-1.0）
- **バッチサイズ**: 同時処理する画像数
- **地域フィルター**: 特定地域の種に限定（JPN, USA, etc.）
- **GPU使用**: GPUアクセラレーションの有効/無効

## ライセンス

このプロジェクトはMITライセンスの下で公開されています。詳細は[LICENSE](LICENSE)ファイルを参照してください。

## 貢献

プルリクエストを歓迎します！大きな変更を行う場合は、まずissueを開いて変更内容について議論してください。

## 謝辞

- Google SpeciesNetチームの優れたAIモデル
- PySide6コミュニティ
- すべての貢献者とテスター
