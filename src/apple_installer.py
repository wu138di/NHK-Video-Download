"""Apple-design material shell over the existing, reversible Inno installation engine.

No application or author guide is rewritten here. All installation operations are
performed by the same bundled engine; this module owns presentation only.
"""
from __future__ import annotations
import ctypes
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

from PySide6.QtCore import (Qt, QTimer, QRectF, QSize, QPropertyAnimation,
                            QEasingCurve, QProcess, QSettings, QUrl)
from PySide6.QtGui import (QPainter, QPainterPath, QColor, QPixmap, QFont, QIcon,
                          QDesktopServices, QTextOption, QTextBlockFormat,
                          QTextCursor, QPalette)
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QToolButton, QMenu, QStackedWidget, QTextBrowser,
    QLineEdit, QFileDialog, QCheckBox, QProgressBar, QMessageBox,
    QGraphicsOpacityEffect, QSizePolicy)

ROOT = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parents[1] / 'bootstrap'))
LANGS = ('zh', 'en', 'ja')
ENGINE_LANG = {'zh': 'chinesesimplified', 'en': 'english', 'ja': 'japanese'}
GUIDES = {'zh': 'guide-zh.txt', 'en': 'guide-en.txt', 'ja': 'guide-ja.txt'}
INSTALLED_GUIDES = {'zh': '使用说明.txt', 'en': 'UserGuide.en.txt', 'ja': '使い方.ja.txt'}
TEXT = {
    'app': ('NHK 下载器', 'NHK Downloader', 'NHK ダウンローダー'),
    'setup': ('安装向导', 'Setup', 'セットアップ'),
    'made': ('由 wu138di 制作', 'Made by wu138di', '制作：wu138di'),
    'notice': ('请勿用于非法用途', 'Do not use for illegal purposes.', '違法な用途に使用しないでください。'),
    'next': ('下一步', 'Continue', '次へ'),
    'back': ('上一步', 'Back', '戻る'),
    'cancel': ('取消', 'Cancel', 'キャンセル'),
    'guide': ('使用说明', 'User guide', '使い方'),
    'folder': ('安装位置', 'Installation folder', 'インストール先'),
    'choose': ('选择安装文件夹', 'Choose installation folder', 'インストール先を選択'),
    'browse': ('浏览', 'Browse', '参照'),
    'shortcut': ('创建桌面快捷方式', 'Create a desktop shortcut', 'デスクトップにショートカットを作成'),
    'ready': ('准备安装', 'Ready to install', 'インストールの準備完了'),
    'location': ('安装位置', 'Destination', 'インストール先'),
    'install': ('安装', 'Install', 'インストール'),
    'installing': ('正在安装', 'Installing', 'インストール中'),
    'preparing': ('正在准备文件…', 'Preparing files…', 'ファイルを準備しています…'),
    'done': ('安装完成', 'Installation complete', 'インストール完了'),
    'open': ('打开下载器', 'Open downloader', 'ダウンローダーを開く'),
    'finish': ('完成', 'Finish', '完了'),
    'read': ('查看使用说明', 'Read user guide', '使い方を見る'),
    'retry': ('重试', 'Try again', '再試行'),
    'error': ('安装未完成', 'Installation did not complete', 'インストールは完了していません'),
    'invalid': ('请选择一个可写的安装文件夹。', 'Choose a writable installation folder.', '書き込み可能なフォルダーを選択してください。'),
    'stop': ('停止安装？', 'Stop installation?', 'インストールを中止しますか？'),
    'stop_body': ('安装程序将撤销本次尚未完成的安装。', 'The installer will roll back this unfinished installation.', '今回の未完了のインストールを元に戻します。'),
    'cancelled': ('安装已取消', 'Installation cancelled', 'インストールを中止しました'),
    'cancelling': ('正在取消并撤销安装…', 'Cancelling and rolling back…', '中止して元に戻しています…'),
    'rolled_back': ('本次安装已撤销。', 'This installation has been rolled back.', '今回のインストールを元に戻しました。'),
    'failure': ('安装程序返回代码：', 'Installer exit code: ', 'インストーラーの終了コード：'),
    'space': ('所需空间约 1.1 GB', 'Approximately 1.1 GB required', '必要な空き容量：約 1.1 GB'),
}


def text(key: str, language: str) -> str:
    return TEXT[key][LANGS.index(language)]


def system_preferences():
    motion, high_contrast = True, False
    if os.name == 'nt':
        enabled = ctypes.c_int(1)
        ctypes.windll.user32.SystemParametersInfoW(0x1042, 0, ctypes.byref(enabled), 0)
        motion = bool(enabled.value)
        class HIGHCONTRAST(ctypes.Structure):
            _fields_ = [('size', ctypes.c_uint), ('flags', ctypes.c_uint), ('scheme', ctypes.c_void_p)]
        contrast = HIGHCONTRAST(ctypes.sizeof(HIGHCONTRAST), 0, None)
        ctypes.windll.user32.SystemParametersInfoW(0x42, contrast.size, ctypes.byref(contrast), 0)
        high_contrast = bool(contrast.flags & 1)
    settings = QSettings(r'HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Themes\Personalize', QSettings.Format.NativeFormat)
    transparency = str(settings.value('EnableTransparency', 1)) != '0'
    return motion, transparency, high_contrast


class MaterialCard(QWidget):
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()).adjusted(1, 1, -1, -1), 28, 28)
        p.setClipPath(path)
        host = self.window()
        if host.transparency and not host.high_contrast and not host.blurred.isNull():
            p.drawPixmap(-self.x(), -self.y(), host.blurred)
            p.fillPath(path, QColor(255, 255, 255, 205))
        else:
            p.fillPath(path, QColor('#ffffff'))
        p.setClipping(False)
        p.setPen(QColor(255, 255, 255, 225))
        p.drawPath(path)


class GlobeButton(QToolButton):
    def __init__(self, parent):
        super().__init__(parent)
        self.renderer = QSvgRenderer(str(ROOT / 'language.svg'))
        self.setFixedSize(44, 44)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAccessibleName('Language / 语言 / 言語')
        self.setToolTip('Language / 语言 / 言語')
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(QColor(255, 255, 255, 190))
        p.setBrush(QColor(255, 255, 255, 225 if self.underMouse() else 190))
        p.drawEllipse(QRectF(1, 1, 42, 42))
        if self.isDown():
            p.translate(1, 1)
        self.renderer.render(p, QRectF(11, 11, 22, 22))
        if self.hasFocus():
            p.setPen(QColor('#007aff'))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(QRectF(2, 2, 40, 40))


class Installer(QWidget):
    def __init__(self, preview=False):
        super().__init__()
        self.preview = preview
        self.language = 'zh'
        self.page = 0
        self.motion, self.transparency, self.high_contrast = system_preferences()
        self.setObjectName('installer')
        self.setWindowIcon(QIcon(str(ROOT / 'app-icon.ico')))
        self.wallpaper = QPixmap(str(ROOT / 'background.png'))
        self.scaled = QPixmap()
        self.blurred = QPixmap()
        self.last_size = QSize()
        self.process = None
        self.install_result = None
        self.cancel_requested = False
        self.percent = 0
        self.log_path = None
        self.cancel_path = None
        self.install_language = None
        self.animation = None
        self.default_dir = str(Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'Programs' / 'NHKDownloader')
        self.setMinimumSize(700, 520)
        self.resize(1000, 740)
        self.card = MaterialCard(self)
        self.card.setObjectName('material')
        self.stack = QStackedWidget(self.card)
        self.globe = GlobeButton(self)
        self.globe.clicked.connect(self.show_languages)
        self.pages = []
        self.build_welcome()
        self.build_guide()
        self.build_folder()
        self.build_ready()
        self.build_progress()
        self.build_done()
        self.timer = QTimer(self)
        self.timer.setInterval(120)
        self.timer.timeout.connect(self.poll_progress)
        self.apply_language()
        self.setTabOrder(self.globe, self.welcome_next)
        self.setTabOrder(self.welcome_next, self.welcome_cancel)

    def label(self, value='', role='body'):
        label = QLabel(value)
        label.setProperty('role', role)
        label.setWordWrap(True)
        label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        return label

    def button(self, key, slot, primary=False):
        button = QPushButton()
        button.setProperty('primary', primary)
        button.setProperty('key', key)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setMinimumHeight(44)
        button.clicked.connect(slot)
        return button

    def new_page(self):
        page = QWidget()
        page.setObjectName('page')
        self.pages.append(page)
        self.stack.addWidget(page)
        return page

    def column(self, page, margins=(48, 38, 48, 30)):
        layout = QVBoxLayout(page)
        layout.setContentsMargins(*margins)
        layout.setSpacing(16)
        return layout

    def header(self, layout, key, step=None):
        top = QHBoxLayout()
        title = self.label(role='page-title')
        title.setProperty('key', key)
        top.addWidget(title, 1)
        if step:
            number = self.label(f'{step} / 3', 'step')
            number.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            top.addWidget(number)
        layout.addLayout(top)
        line = self.label(role='eyebrow')
        line.setProperty('key', 'app')
        line.setProperty('versioned', True)
        layout.addWidget(line)
        layout.addSpacing(8)

    def navigation(self, layout, next_key, slot):
        layout.addSpacing(8)
        row = QHBoxLayout()
        row.addWidget(self.button('back', self.back))
        row.addStretch()
        row.addWidget(self.button('cancel', self.close))
        next_button = self.button(next_key, slot, True)
        next_button.setMinimumWidth(120)
        row.addWidget(next_button)
        layout.addLayout(row)

    def build_welcome(self):
        page = self.new_page()
        layout = self.column(page, (40, 42, 40, 30))
        layout.setSpacing(0)
        layout.addStretch(1)
        self.logo = QLabel()
        self.logo.setPixmap(QIcon(str(ROOT / 'app-icon.ico')).pixmap(64, 64))
        self.logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.logo)
        layout.addSpacing(24)
        self.welcome_title = self.label(role='display')
        self.welcome_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.welcome_title)
        layout.addSpacing(10)
        self.welcome_subtitle = self.label(role='subtitle')
        self.welcome_subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.welcome_subtitle)
        layout.addStretch(2)
        self.welcome_next = self.button('next', self.next_page, True)
        self.welcome_next.setFixedWidth(216)
        self.welcome_cancel = self.button('cancel', self.close)
        self.welcome_cancel.setFixedWidth(216)
        layout.addWidget(self.welcome_next, 0, Qt.AlignmentFlag.AlignHCenter)
        layout.addSpacing(6)
        layout.addWidget(self.welcome_cancel, 0, Qt.AlignmentFlag.AlignHCenter)
        layout.addStretch(1)
        self.footer = self.label(role='footer')
        self.footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.footer)

    def build_guide(self):
        layout = self.column(self.new_page())
        self.header(layout, 'guide', 1)
        self.guide = QTextBrowser()
        self.guide.setObjectName('guide')
        self.guide.setOpenExternalLinks(False)
        self.guide.setReadOnly(True)
        self.guide.setWordWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
        layout.addWidget(self.guide, 1)
        self.navigation(layout, 'next', self.next_page)

    def build_folder(self):
        layout = self.column(self.new_page())
        self.header(layout, 'folder', 2)
        layout.addStretch(1)
        row = QHBoxLayout()
        self.path_edit = QLineEdit(self.default_dir)
        self.path_edit.setMinimumHeight(48)
        self.path_edit.setAccessibleName('Installation folder')
        row.addWidget(self.path_edit, 1)
        row.addWidget(self.button('browse', self.browse))
        layout.addLayout(row)
        self.shortcut = QCheckBox()
        self.shortcut.setMinimumHeight(44)
        layout.addWidget(self.shortcut)
        self.folder_error = self.label(role='error')
        self.folder_error.hide()
        layout.addWidget(self.folder_error)
        layout.addStretch(2)
        self.navigation(layout, 'next', self.next_page)

    def build_ready(self):
        layout = self.column(self.new_page())
        self.header(layout, 'ready', 3)
        layout.addStretch(1)
        self.location_label = self.label(role='eyebrow')
        self.location_label.setProperty('key', 'location')
        layout.addWidget(self.location_label)
        self.destination = self.label(role='destination')
        layout.addWidget(self.destination)
        layout.addStretch(2)
        self.navigation(layout, 'install', self.install)

    def build_progress(self):
        layout = self.column(self.new_page())
        layout.addStretch()
        self.progress_title = self.label(role='display')
        self.progress_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.progress_title)
        layout.addSpacing(16)
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(8)
        layout.addWidget(self.progress)
        self.progress_detail = self.label(role='subtitle')
        self.progress_detail.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.progress_detail)
        layout.addStretch()
        layout.addWidget(self.button('cancel', self.close), 0, Qt.AlignmentFlag.AlignHCenter)

    def build_done(self):
        layout = self.column(self.new_page())
        layout.addStretch()
        self.done_mark = self.label('✓', 'success')
        self.done_mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.done_mark)
        self.done_title = self.label(role='display')
        self.done_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.done_title)
        self.done_detail = self.label(role='subtitle')
        self.done_detail.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.done_detail)
        layout.addStretch()
        self.open_button = self.button('open', self.open_application, True)
        self.open_button.setFixedWidth(216)
        layout.addWidget(self.open_button, 0, Qt.AlignmentFlag.AlignHCenter)
        self.retry_button = self.button('retry', lambda: self.show_page(3), True)
        self.retry_button.setFixedWidth(216)
        layout.addWidget(self.retry_button, 0, Qt.AlignmentFlag.AlignHCenter)
        self.read_button = self.button('read', self.open_guide)
        layout.addWidget(self.read_button, 0, Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(self.button('finish', self.close), 0, Qt.AlignmentFlag.AlignHCenter)

    def stylesheet(self):
        family = {'zh': 'Microsoft YaHei UI', 'en': 'Segoe UI', 'ja': 'Yu Gothic UI'}[self.language]
        return f'''
        QWidget {{ font-family: "{family}"; font-size: 14px; color: #1d1d1f; }}
        QWidget#page, QStackedWidget {{ background: transparent; }}
        QLabel {{ background: transparent; }}
        QLabel[role="display"] {{ font-size: 32px; font-weight: 600; }}
        QLabel[role="page-title"] {{ font-size: 26px; font-weight: 600; }}
        QLabel[role="subtitle"] {{ font-size: 16px; color: #424247; }}
        QLabel[role="eyebrow"], QLabel[role="step"] {{ font-size: 12px; color: #515156; }}
        QLabel[role="footer"] {{ font-size: 12px; color: #424247; line-height: 1.5; }}
        QLabel[role="destination"] {{ font-size: 18px; font-weight: 500; }}
        QLabel[role="success"] {{ font-size: 52px; color: #258448; }}
        QLabel[role="error"] {{ color: #b42318; }}
        QPushButton {{ background: transparent; border: 1px solid transparent;
            border-radius: 12px; padding: 0 20px; font-size: 14px; }}
        QPushButton:hover {{ background: rgba(29,29,31,16); }}
        QPushButton:pressed {{ background: rgba(29,29,31,28); }}
        QPushButton:focus {{ border: 2px solid #007aff; }}
        QPushButton[primary="true"] {{ background: #007aff; color: white; font-weight: 600; }}
        QPushButton[primary="true"]:hover {{ background: #0872e8; }}
        QPushButton[primary="true"]:pressed {{ background: #0062cc; }}
        QPushButton[primary="true"]:focus {{ border: 2px solid #003f91; }}
        QTextBrowser#guide {{ border: none; border-radius: 0; background: transparent;
            padding: 0 4px; selection-background-color: #007aff; font-size: 14px; }}
        QLineEdit {{ border: 1px solid #d2d2d7; border-radius: 12px;
            background: rgba(255,255,255,235); padding: 0 14px; selection-background-color: #007aff; }}
        QLineEdit:focus {{ border: 2px solid #007aff; padding: 0 13px; }}
        QCheckBox {{ spacing: 10px; }}
        QCheckBox::indicator {{ width: 18px; height: 18px; }}
        QProgressBar {{ border: none; border-radius: 4px; background: #d2d2d7; }}
        QProgressBar::chunk {{ border-radius: 4px; background: #007aff; }}
        QScrollBar:vertical {{ width: 6px; background: transparent; margin: 0; }}
        QScrollBar::handle:vertical {{ background: #a7a7ad; min-height: 28px; border-radius: 3px; }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}
        QMenu {{ background: #fcfcfd; border: 1px solid #e5e5e8; border-radius: 14px;
            padding: 6px; }}
        QMenu::item {{ padding: 12px 30px 12px 16px; border-radius: 8px; }}
        QMenu::item:selected {{ background: #007aff; color: white; }}
        '''

    def apply_language(self, language=None):
        if self.install_language is not None and language and language != self.install_language:
            return
        if language:
            self.language = language
        self.setWindowTitle(f'{text("app", self.language)} V2.0 · {text("setup", self.language)}' + (' [UI Preview]' if self.preview else ''))
        self.setStyleSheet(self.stylesheet())
        self.welcome_title.setText(text('app', self.language))
        self.welcome_subtitle.setText(f'{text("setup", self.language)}  ·  V2.0')
        self.footer.setText(f'{text("made", self.language)}\n{text("notice", self.language)}')
        for widget in self.findChildren(QWidget):
            key = widget.property('key')
            if key and hasattr(widget, 'setText'):
                widget.setText(text(key, self.language) + (' · V2.0' if widget.property('versioned') else ''))
                widget.setAccessibleName(text(key, self.language))
        self.shortcut.setText(text('shortcut', self.language))
        self.path_edit.setAccessibleName(text('folder', self.language))
        self.folder_error.setText(text('invalid', self.language))
        self.progress_title.setText(text('installing', self.language))
        position = self.guide.verticalScrollBar().value()
        self.guide.setPlainText((ROOT / GUIDES[self.language]).read_text('utf-8-sig'))
        cursor = QTextCursor(self.guide.document())
        cursor.select(QTextCursor.SelectionType.Document)
        block = QTextBlockFormat()
        block.setLineHeight(150, 1)
        cursor.mergeBlockFormat(block)
        self.guide.verticalScrollBar().setValue(position)
        self.update_status()
        self.layout_card()

    def show_languages(self):
        if self.install_language is not None:
            return
        menu = QMenu(self)
        for language, label in [('zh', '简体中文'), ('en', 'English'), ('ja', '日本語')]:
            action = menu.addAction(label)
            action.setCheckable(True)
            action.setChecked(self.language == language)
            action.triggered.connect(lambda checked=False, lang=language: self.apply_language(lang))
        menu.adjustSize()
        menu.exec(self.globe.mapToGlobal(self.globe.rect().bottomRight()) - menu.rect().topRight())

    def show_page(self, page):
        self.page = page
        self.stack.setCurrentIndex(page)
        self.layout_card()
        if self.animation:
            self.animation.stop()
        if self.motion and not self.high_contrast and not os.environ.get('NHK_NO_MOTION'):
            effect = QGraphicsOpacityEffect(self.stack)
            self.stack.setGraphicsEffect(effect)
            self.animation = QPropertyAnimation(effect, b'opacity', self)
            self.animation.setDuration(140)
            self.animation.setStartValue(0.72)
            self.animation.setEndValue(1.0)
            self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
            self.animation.start()
        self.update_status()

    def next_page(self):
        if self.page == 2 and not self.valid_folder():
            return
        self.destination.setText(self.path_edit.text())
        self.show_page(min(self.page + 1, 3))

    def back(self):
        self.show_page(max(0, self.page - 1))

    def browse(self):
        folder = QFileDialog.getExistingDirectory(self, text('choose', self.language), self.path_edit.text())
        if folder:
            self.path_edit.setText(folder)
            self.folder_error.hide()

    def valid_folder(self):
        value = self.path_edit.text().strip()
        path = Path(value)
        valid = bool(value) and path.is_absolute() and path != Path(path.anchor)
        if valid:
            try:
                ancestor = path
                while not ancestor.exists():
                    ancestor = ancestor.parent
                valid = ancestor.is_dir() and os.access(ancestor, os.W_OK)
            except OSError:
                valid = False
        self.folder_error.setVisible(not valid)
        return valid

    def install(self):
        if not self.valid_folder():
            self.show_page(2)
            return
        self.install_result = None
        self.cancel_requested = False
        self.percent = 0
        if not self.preview:
            self.install_language = self.language
            self.globe.setEnabled(False)
        self.show_page(4)
        if self.preview:
            self.show_page(3)
            QMessageBox.information(self, 'UI Preview', '界面预览 / UI preview / UIプレビュー')
            return
        self.log_path = Path(tempfile.gettempdir()) / f'NHK-setup-{os.getpid()}.log'
        self.cancel_path = Path(tempfile.gettempdir()) / f'NHK-setup-{os.getpid()}.cancel'
        self.cancel_path.unlink(missing_ok=True)
        self.process = QProcess(self)
        self.process.setProgram(str(ROOT / 'engine.exe'))
        self.process.setArguments([
            '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART',
            '/LANG=' + ENGINE_LANG[self.install_language],
            '/DIR=' + self.path_edit.text().strip(),
            '/TASKS=' + ('desktopicon' if self.shortcut.isChecked() else ''),
            '/LOG=' + str(self.log_path),
            '/CANCELFILE=' + str(self.cancel_path),
        ])
        self.process.finished.connect(self.install_finished)
        self.process.errorOccurred.connect(self.process_error)
        self.process.start()
        self.timer.start()

    def process_error(self, error):
        if error == QProcess.ProcessError.FailedToStart:
            self.install_finished(-1, QProcess.ExitStatus.CrashExit)

    def poll_progress(self):
        if self.log_path and self.log_path.exists():
            try:
                content = self.log_path.read_text('utf-8-sig', errors='replace')
                total = 3293
                self.percent = min(96, max(2, content.count('Successfully installed the file.') * 94 // total + 2))
            except OSError:
                pass
        self.update_status()

    def install_finished(self, code, status):
        self.timer.stop()
        self.install_result = int(code)
        self.percent = 100 if code == 0 else self.percent
        self.show_page(5)

    def update_status(self):
        self.progress.setValue(self.percent)
        self.progress_detail.setText(text('cancelling', self.language) if self.cancel_requested else (f'{self.percent}%' if self.percent else text('preparing', self.language)))
        success = self.install_result == 0
        self.done_mark.setText('✓' if success else '—')
        self.done_mark.setStyleSheet('font-size: 52px; color: ' + ('#258448' if success else ('#515156' if self.cancel_requested else '#b42318')) + ';')
        self.done_title.setText(text('done' if success else ('cancelled' if self.cancel_requested else 'error'), self.language))
        self.done_detail.setText(text('app', self.language) + ' · V2.0' if success else (text('rolled_back', self.language) if self.cancel_requested else text('failure', self.language) + str(self.install_result)))
        self.open_button.setVisible(success)
        self.retry_button.setVisible(not success and not self.cancel_requested)
        self.read_button.setVisible(success)

    def open_application(self):
        app = Path(self.path_edit.text()) / 'NHK-Downloader-V2.0.exe'
        if app.is_file():
            QProcess.startDetached(str(app), [], str(app.parent))
            self.close()

    def open_guide(self):
        path = Path(self.path_edit.text()) / INSTALLED_GUIDES[self.language]
        if path.is_file():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    def closeEvent(self, event):
        if self.process and self.process.state() != QProcess.ProcessState.NotRunning:
            if self.cancel_requested:
                event.ignore()
                return
            answer = QMessageBox.question(self, text('stop', self.language), text('stop_body', self.language))
            if answer == QMessageBox.StandardButton.Yes:
                self.cancel_requested = True
                self.cancel_path.write_text('cancel', encoding='ascii')
                self.update_status()
            event.ignore()
            return
        event.accept()

    def layout_card(self):
        welcome = self.page == 0
        width = min(self.width() - 64, 660 if welcome else 860)
        height = min(self.height() - 72, 552 if welcome else 680)
        self.card.setGeometry((self.width() - width) // 2, (self.height() - height) // 2, width, height)
        self.stack.setGeometry(0, 0, width, height)
        self.globe.move(self.width() - 68, 24)
        self.globe.raise_()

    def resizeEvent(self, event):
        if self.wallpaper.isNull():
            return
        self.scaled = self.wallpaper.scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
        x, y = (self.scaled.width() - self.width()) // 2, (self.scaled.height() - self.height()) // 2
        self.scaled = self.scaled.copy(x, y, self.width(), self.height())
        small = self.scaled.toImage().scaled(max(1, self.width() // 20), max(1, self.height() // 20), Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
        self.blurred = QPixmap.fromImage(small.scaled(self.size(), Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation))
        self.layout_card()
        self.card.update()

    def paintEvent(self, event):
        p = QPainter(self)
        if not self.scaled.isNull():
            p.drawPixmap(0, 0, self.scaled)
        else:
            p.fillRect(self.rect(), QColor('#f7edf3'))
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        bounds = QRectF(self.card.geometry())
        for spread in range(24, 0, -2):
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(52, 33, 52, 2))
            p.drawRoundedRect(bounds.adjusted(-spread, -spread + 7, spread, spread + 7), 28 + spread, 28 + spread)


def self_test(app, report):
    window = Installer(preview=True)
    checks = []
    for size in [(720, 540), (1000, 740), (1706, 1044)]:
        window.resize(*size)
        window.show()
        app.processEvents()
        for lang in LANGS:
            window.path_edit.setText(str(Path(tempfile.gettempdir()) / 'NHK-test-custom'))
            expected_dir = window.path_edit.text()
            window.apply_language(lang)
            app.processEvents()
            assert window.path_edit.text() == expected_dir
            assert window.guide.toPlainText().replace('\r\n', '\n') == (ROOT / GUIDES[lang]).read_text('utf-8-sig').replace('\r\n', '\n')
            for page in range(6):
                window.show_page(page)
                app.processEvents()
                assert window.rect().contains(window.card.geometry())
                layout = window.pages[page].layout()
                assert layout.minimumSize().height() <= window.stack.height(), (size, lang, page, layout.minimumSize(), window.stack.size())
                for button in window.pages[page].findChildren(QPushButton):
                    if button.isVisible():
                        assert button.height() >= 44
                        assert button.width() >= button.fontMetrics().horizontalAdvance(button.text()) + 24, (lang, button.text(), button.size())
            checks.append({'size': size, 'language': lang, 'pages': 6, 'directory_preserved': True, 'author_guide_exact': True, 'buttons_min_44': True})
    window.close()
    Path(report).write_text(json.dumps({'result': 'PASS', 'checks': checks}, ensure_ascii=False, indent=2), encoding='utf-8')


def main():
    if any(arg.upper().startswith('/VERYSILENT') for arg in sys.argv[1:]):
        return subprocess.run([str(ROOT / 'engine.exe'), *sys.argv[1:]], creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0)).returncode
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    if '--self-test' in sys.argv:
        self_test(app, sys.argv[sys.argv.index('--self-test') + 1])
        return 0
    window = Installer(preview='--preview' in sys.argv)
    if '--language' in sys.argv:
        window.apply_language(sys.argv[sys.argv.index('--language') + 1])
    window.showMaximized()
    return app.exec()


if __name__ == '__main__':
    sys.exit(main())
