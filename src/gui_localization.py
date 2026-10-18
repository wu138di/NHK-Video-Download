"""Final GUI title and language lock; translations are shared with the CLI."""
from app_i18n import LANGUAGE, translate, localize_code, localize_extension

def finish_install(ns):
    ns['APP_NAME'] = translate('NHK 下载器 V2.0')
    OriginalApplication = ns['QApplication']
    class LockedApplication(OriginalApplication):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            from PySide6.QtCore import QTranslator, QLibraryInfo, QLocale
            QLocale.setDefault(QLocale({'zh':'zh_CN','en':'en_US','ja':'ja_JP'}[LANGUAGE]))
            if LANGUAGE != 'en':
                translator = QTranslator(self)
                code = 'zh_CN' if LANGUAGE == 'zh' else 'ja'
                if translator.load('qtbase_' + code, QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)):
                    self.installTranslator(translator)
                self._installed_language_translator = translator
    ns['QApplication'] = LockedApplication
    Main = ns['MainWindow']
    old_init = Main.__init__

    def init(self, *args, **kwargs):
        old_init(self, *args, **kwargs)
        self.setWindowTitle(ns['APP_NAME'])
        self._installation_language = LANGUAGE
        self._language_locked = True
        from PySide6.QtWidgets import QLabel
        for label in self.findChildren(QLabel):
            if label.text().strip() in ('流媒体解析与下载', translate('流媒体解析与下载')):
                label.hide()
            elif label.text().strip().startswith('NHK Video Download'):
                label.setText(ns['APP_NAME'])
    Main.__init__ = init
