"""
Wildlife Detector カスタムUIウィジェット

フィールドグリーン基調のデザイン（claude.ai/design 由来）を PySide6 で再現するための
再利用可能なウィジェット群をまとめています。

含まれるもの:
    - パレット定数（COL / CAT）
    - ToggleSwitch: ピル型トグルスイッチ
    - Bar: 角丸の進捗/メーターバー（カスタム描画）
    - ConfidenceMeter: 信頼度メーター（バー＋数値）
    - category_chip / classify_category: カテゴリチップ（色ドット＋テキスト）
    - StatCard: 統計タイル
    - StepperItem: サイドバーの番号付きステッパー項目
    - Card / SectionTitle: 白カード／見出しの薄いラッパ
    - DropArea: ドラッグ＆ドロップ受け入れ領域
"""
from typing import Callable, List, Optional

from PySide6.QtCore import Qt, Signal, QSize, QRectF
from PySide6.QtGui import QPainter, QColor, QBrush, QPen
from PySide6.QtWidgets import (
    QWidget, QFrame, QLabel, QHBoxLayout, QVBoxLayout, QAbstractButton,
    QSizePolicy,
)

# ---- パレット（デザイントークン） ---------------------------------------
COL = {
    "green":        "#2E6B4F",
    "green_dark":   "#245641",
    "paper":        "#F6F5F1",
    "panel":        "#FBFAF8",
    "white":        "#FFFFFF",
    "border":       "#E4E2DA",
    "ink":          "#1C1B18",
    "muted":        "#52514E",
    "faint":        "#898781",
    "track_off":    "#CFCDC4",
    "bar_track":    "#DCEAE1",
    "active_bg":    "#DFEDE4",
    "hover":        "#EFEEE8",
    "tint":         "#F0F6F2",
    "danger":       "#D03B3B",
    "danger_bd":    "#EBC5C5",
    "danger_bg":    "#FBEDED",
    "ok":           "#0CA30C",
}

# カテゴリごとの色（色だけに頼らず必ずテキストラベルを併記する）
CAT = {
    "bird":   {"bg": "#E7F0FB", "dot": "#2A78D6", "label": "鳥類",  "tc": "#1C1B18"},
    "mammal": {"bg": "#FCEBE3", "dot": "#EB6834", "label": "哺乳類", "tc": "#1C1B18"},
    "other":  {"bg": "#E2F5EE", "dot": "#1BAF7A", "label": "その他", "tc": "#1C1B18"},
    "none":   {"bg": "#EFEEEA", "dot": "#898781", "label": "未検出", "tc": "#52514E"},
}


def classify_category(raw: str) -> str:
    """SpeciesNet の生カテゴリ文字列を chip 用のキーに正規化する。"""
    if not raw:
        return "none"
    t = str(raw).lower()
    if "bird" in t or t == "鳥類":
        return "bird"
    if "mamm" in t or t == "哺乳類":
        return "mammal"
    if t in ("blank", "no_detection", "no detection", "未検出", "none"):
        return "none"
    return "other"


# ---- トグルスイッチ -----------------------------------------------------
class ToggleSwitch(QAbstractButton):
    """ピル型のトグルスイッチ（QCheckBox 互換の checkable API）。"""

    def __init__(self, checked: bool = False, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setChecked(checked)
        self.setCursor(Qt.PointingHandCursor)
        self._w, self._h = 36, 20
        self.setFixedSize(self._w, self._h)

    def sizeHint(self) -> QSize:
        return QSize(self._w, self._h)

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        on = self.isChecked()
        track = QColor(COL["green"] if on else COL["track_off"])
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(track))
        p.drawRoundedRect(0, 0, self._w, self._h, self._h / 2, self._h / 2)
        # ノブ
        d = 16
        x = self._w - d - 2 if on else 2
        p.setBrush(QBrush(QColor(COL["white"])))
        p.drawEllipse(x, 2, d, d)
        p.end()


# ---- バー（進捗・メーター） ---------------------------------------------
class Bar(QWidget):
    """左詰めで塗られる角丸バー。fraction は 0.0〜1.0。"""

    def __init__(self, fraction: float = 0.0, height: int = 6,
                 fill: str = COL["green"], track: str = COL["bar_track"],
                 parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._frac = max(0.0, min(1.0, fraction))
        self._fill = fill
        self._track = track
        self._h = height
        self.setFixedHeight(height)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def set_fraction(self, f: float):
        self._frac = max(0.0, min(1.0, f))
        self.update()

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = self._h / 2
        w = self.width()
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(self._track))
        p.drawRoundedRect(QRectF(0, 0, w, self._h), r, r)
        fw = w * self._frac
        if fw > 0:
            p.setBrush(QColor(self._fill))
            p.drawRoundedRect(QRectF(0, 0, max(fw, self._h), self._h), r, r)
        p.end()


class ConfidenceMeter(QWidget):
    """信頼度メーター: バー＋数値。conf は 0.0〜1.0、None で「—」。"""

    def __init__(self, conf: Optional[float], parent: Optional[QWidget] = None):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)
        if conf is None:
            dash = QLabel("—")
            dash.setStyleSheet(f"color:{COL['faint']}; font-size:12px;")
            lay.addWidget(dash)
            lay.addStretch()
        else:
            bar = Bar(conf, height=6)
            bar.setMinimumWidth(70)
            lay.addWidget(bar, 1)
            val = QLabel(f"{conf:.2f}")
            val.setStyleSheet("font-size:12px;")
            val.setProperty("tnum", True)
            lay.addWidget(val, 0)


# ---- カテゴリチップ -----------------------------------------------------
def category_chip(cat_key: str) -> QWidget:
    """色ドット＋テキストラベルのカテゴリチップ（左寄せ）を返す。"""
    c = CAT.get(cat_key, CAT["none"])
    wrap = QWidget()
    outer = QHBoxLayout(wrap)
    outer.setContentsMargins(0, 0, 0, 0)
    outer.setSpacing(0)

    chip = QFrame()
    chip.setObjectName("Chip")
    chip.setStyleSheet(f"QFrame#Chip {{ background:{c['bg']}; border-radius:11px; }}")
    ch = QHBoxLayout(chip)
    ch.setContentsMargins(8, 3, 11, 3)
    ch.setSpacing(6)
    dot = QLabel()
    dot.setFixedSize(8, 8)
    dot.setStyleSheet(f"background:{c['dot']}; border-radius:4px;")
    lbl = QLabel(c["label"])
    lbl.setStyleSheet(f"color:{c['tc']}; font-size:12px; font-weight:500; background:transparent;")
    ch.addWidget(dot)
    ch.addWidget(lbl)

    outer.addWidget(chip, 0, Qt.AlignVCenter)
    outer.addStretch()
    return wrap


# ---- 統計タイル ---------------------------------------------------------
class StatCard(QFrame):
    """統計タイル（見出し・大きな数値・補足）。"""

    def __init__(self, title: str, value: str = "0", sub: str = "",
                 value_color: str = COL["ink"], parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("Card")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(2)

        self.title_lbl = QLabel(title)
        self.title_lbl.setStyleSheet(f"color:{COL['muted']}; font-size:12px;")

        self.value_lbl = QLabel(value)
        self.value_lbl.setStyleSheet(
            f"color:{value_color}; font-size:26px; font-weight:600;")
        self.value_lbl.setProperty("tnum", True)

        self.sub_lbl = QLabel(sub)
        self.sub_lbl.setStyleSheet(f"color:{COL['faint']}; font-size:11px;")
        self.sub_lbl.setVisible(bool(sub))

        lay.addWidget(self.title_lbl)
        lay.addWidget(self.value_lbl)
        lay.addWidget(self.sub_lbl)

    def set_value(self, value: str, sub: Optional[str] = None):
        self.value_lbl.setText(value)
        if sub is not None:
            self.sub_lbl.setText(sub)
            self.sub_lbl.setVisible(bool(sub))


# ---- サイドバー ステッパー項目 -----------------------------------------
class StepperItem(QWidget):
    """番号付きステッパー項目（active / done / todo の3状態）。"""

    clicked = Signal()

    def __init__(self, num: str, label: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("StepItem")
        self.setCursor(Qt.PointingHandCursor)
        self.setAttribute(Qt.WA_StyledBackground, True)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(10, 9, 10, 9)
        lay.setSpacing(10)

        self.badge = QLabel(num)
        self.badge.setFixedSize(22, 22)
        self.badge.setAlignment(Qt.AlignCenter)

        self.text = QLabel(label)
        self.text.setStyleSheet("font-size:13px; background:transparent;")

        lay.addWidget(self.badge, 0)
        lay.addWidget(self.text, 1)
        self.set_state(False, False)

    def set_state(self, active: bool, done: bool):
        # 番号バッジ
        if active:
            self.badge.setStyleSheet(
                f"border:1.5px solid {COL['green']}; background:{COL['green']};"
                f"color:#fff; border-radius:11px; font-size:11px; font-weight:600;")
        elif done:
            self.badge.setStyleSheet(
                f"border:1.5px solid {COL['green']}; background:transparent;"
                f"color:{COL['green']}; border-radius:11px; font-size:11px; font-weight:600;")
        else:
            self.badge.setStyleSheet(
                f"border:1.5px solid {COL['faint']}; background:transparent;"
                f"color:{COL['faint']}; border-radius:11px; font-size:11px; font-weight:600;")
        # 行全体
        if active:
            self.setStyleSheet(
                f"#StepItem {{ background:{COL['active_bg']}; border-radius:8px; }}")
            self.text.setStyleSheet(
                f"font-size:13px; font-weight:600; color:{COL['green_dark']}; background:transparent;")
        else:
            self.setStyleSheet(
                f"#StepItem {{ background:transparent; border-radius:8px; }}"
                f"#StepItem:hover {{ background:{COL['hover']}; }}")
            self.text.setStyleSheet(
                f"font-size:13px; font-weight:400; color:{COL['muted']}; background:transparent;")

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class NavItem(QWidget):
    """ステッパー以外のサイドバー項目（設定など）。"""

    clicked = Signal()

    def __init__(self, text: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("NavItem")
        self.setCursor(Qt.PointingHandCursor)
        self.setAttribute(Qt.WA_StyledBackground, True)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 9, 12, 9)
        lay.setSpacing(8)
        self.text = QLabel(text)
        self.text.setStyleSheet("font-size:13px; background:transparent;")
        lay.addWidget(self.text, 1)
        self.set_active(False)

    def set_active(self, active: bool):
        if active:
            self.setStyleSheet(
                f"#NavItem {{ background:{COL['active_bg']}; border-radius:8px; }}")
            self.text.setStyleSheet(
                f"font-size:13px; font-weight:600; color:{COL['green_dark']}; background:transparent;")
        else:
            self.setStyleSheet(
                f"#NavItem {{ background:transparent; border-radius:8px; }}"
                f"#NavItem:hover {{ background:{COL['hover']}; }}")
            self.text.setStyleSheet(
                f"font-size:13px; font-weight:400; color:{COL['muted']}; background:transparent;")

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


# ---- 白カード / 見出し --------------------------------------------------
def card() -> QFrame:
    """白背景・角丸・薄枠のカードコンテナを返す（QVBoxLayout 済み）。"""
    f = QFrame()
    f.setObjectName("Card")
    lay = QVBoxLayout(f)
    lay.setContentsMargins(20, 18, 20, 18)
    lay.setSpacing(12)
    return f


def section_title(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet("font-size:14px; font-weight:600;")
    return lbl


# ---- ドラッグ＆ドロップ領域 ---------------------------------------------
class DropArea(QFrame):
    """画像/フォルダのドラッグ＆ドロップを受け付ける領域。"""

    dropped = Signal(list)  # List[str] のローカルパス

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("DropArea")
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setProperty("hover", True)
            self.style().unpolish(self)
            self.style().polish(self)

    def dragLeaveEvent(self, event):
        self.setProperty("hover", False)
        self.style().unpolish(self)
        self.style().polish(self)

    def dropEvent(self, event):
        self.setProperty("hover", False)
        self.style().unpolish(self)
        self.style().polish(self)
        paths = [u.toLocalFile() for u in event.mimeData().urls() if u.toLocalFile()]
        if paths:
            self.dropped.emit(paths)
            event.acceptProposedAction()
