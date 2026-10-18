"""Targeted clipping and font-independent window-control repairs."""
from PySide6.QtCore import Qt, QSize, QRectF
from PySide6.QtGui import QPainter, QPen, QColor, QPixmap, QIcon
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QBoxLayout, QScrollArea, QFrame, QLayout, QSizePolicy, QLineEdit


def control_icon(kind):
    image = QPixmap(40, 40)
    image.fill(Qt.GlobalColor.transparent)
    p = QPainter(image)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(QPen(QColor('#7d4563'), 2.2))
    if kind == 'minimize':
        p.drawLine(11, 21, 29, 21)
    elif kind == 'maximize':
        p.drawRect(QRectF(11, 11, 18, 18))
    elif kind == 'restore':
        p.drawLine(16, 10, 30, 10)
        p.drawLine(30, 10, 30, 24)
        p.drawLine(30, 24, 26, 24)
        p.drawRect(QRectF(10, 15, 15, 15))
    else:
        p.drawLine(12, 12, 28, 28)
        p.drawLine(28, 12, 12, 28)
    p.end()
    image.setDevicePixelRatio(2)
    return QIcon(image)


def install(ns, translate):
    Bar = ns['WindowsTitleBar']
    old_bar_init = Bar.__init__

    def sync_state(self):
        states = [('minimize_button', 'minimize', '最小化'),
                  ('maximize_button', 'restore' if self.host_window.isMaximized() else 'maximize', '还原' if self.host_window.isMaximized() else '最大化'),
                  ('close_button', 'close', '关闭')]
        for field, kind, tip in states:
            button = getattr(self, field)
            button.setText('')
            button.setIcon(control_icon(kind))
            button.setIconSize(QSize(20, 20))
            button.setToolTip(translate(tip))
            button.setAccessibleName(translate(tip))

    def bar_init(self, *args, **kwargs):
        old_bar_init(self, *args, **kwargs)
        self.setFixedHeight(44)
        self.controls.setFixedWidth(140)
        for name in ('minimize_button', 'maximize_button', 'close_button'):
            button = getattr(self, name)
            button.setFixedSize(44, 36)
            button.setStyleSheet('QToolButton { padding: 0; margin: 0; border: none; border-radius: 8px; background: transparent; } QToolButton:hover { background: rgba(235,120,173,35); } QToolButton:pressed { background: rgba(235,120,173,65); }')
        sync_state(self)

    Bar.__init__ = bar_init
    Bar.sync_state = sync_state
    General = ns['GeneralTab']
    old_build = General._build
    old_resize = General.resizeEvent

    def build(self):
        old_build(self)
        toggle = self.adv_toggle
        toggle.setObjectName('advancedOptionsToggle')
        toggle.setStyleSheet('QToolButton { padding: 0 14px; font-size: 15px; font-weight: 600; border-radius: 12px; min-height: 44px; }')
        toggle.ensurePolished()
        toggle.setFixedHeight(max(44, toggle.fontMetrics().height() + 16))
        toggle.setMinimumWidth(max(160, toggle.fontMetrics().horizontalAdvance(toggle.text()) + 60))
        toggle.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        toggle.setIconSize(QSize(16, 16))
        for field in self.findChildren(QLineEdit):
            field.setStyleSheet(field.styleSheet() + '\nQLineEdit { padding-top: 0; padding-bottom: 0; min-height: 48px; }')
            field.ensurePolished()
            field.setFixedHeight(max(48, field.fontMetrics().height() + 20))
        for button in (self.btn_probe, self.btn_download):
            button.setStyleSheet(button.styleSheet() + '\nQPushButton { padding-top: 0; padding-bottom: 0; min-height: 48px; }')
            button.setMinimumHeight(48)
        for name in ('chk_auto', 'chk_shaka', 'chk_subtitle', 'chk_convert'):
            checkbox = getattr(self, name)
            checkbox.setMinimumHeight(36)
        self.advanced_box.layout().setSizeConstraint(QLayout.SizeConstraint.SetMinimumSize)
        content = QWidget()
        original_layout = self.layout()
        content.setLayout(original_layout)
        original_layout.setSizeConstraint(QLayout.SizeConstraint.SetMinimumSize)
        self._responsive_layout = original_layout
        scroll = QScrollArea(self)
        scroll.setObjectName('generalFormScroll')
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet('QScrollArea#generalFormScroll, QScrollArea#generalFormScroll > QWidget > QWidget { background: transparent; border: none; }')
        scroll.setWidget(content)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(scroll)
        self._form_scroll = scroll

    def resized(self, event):
        old_resize(self, event)
        layout = getattr(self, '_responsive_layout', None)
        if isinstance(layout, QHBoxLayout):
            layout.setDirection(QBoxLayout.Direction.TopToBottom if self.width() < 1000 else QBoxLayout.Direction.LeftToRight)

    General._build = build
    General.resizeEvent = resized
