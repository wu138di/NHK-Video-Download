"""Surface preparation errors and refresh missing playlist metadata."""
import re
from datetime import datetime


def readable_error(error):
    text = str(error or '未知错误')
    text = re.sub(r'https?://\S+', '[请求地址]', text)
    text = re.sub(r'(?i)(bearer\s+)\S+', r'\1[已隐藏]', text)
    if '401' in text or '403' in text:
        return '节目授权请求被拒绝（' + ('401' if '401' in text else '403') + '），请在网页内确认登录和播放权限'
    if '没有找到加密信息' in text:
        return '未取得节目播放资料，请在网页内播放节目后重试'
    if '登录状态尚未准备好' in text:
        return '尚未取得登录状态，请在网页内登录并播放节目后重试'
    return text[:500]


def install(ns):
    Main = ns['MainWindow']
    original_failed = Main._on_web_key_failed
    def failed(self, error):
        original_failed(self, error)
        message = readable_error(error)
        self.web_tab._set_status(message, '#B05C68')
        self.web_tab.download_popover.speed_label.setText(message)
        self.web_tab.download_popover.speed_label.setToolTip(message)
        self._statusbar.showMessage('下载准备失败：' + message, 30000)
        log = ns['get_config_dir']() / 'preparation-errors.log'
        with log.open('a', encoding='utf-8') as stream:
            stream.write(datetime.now().isoformat(timespec='seconds') + ' ' + message + '\n')
    Main._on_web_key_failed = failed

    original_launch = Main._launch_web_download
    def launch(self, task):
        # MainWindow queues an envelope: {payload: programme, filename: ...}.
        payload = task.get('payload', {})
        if payload.get('_widevine_pssh'):
            original_launch(self, task)
            return
        if not payload.get('manifest_url'):
            failed(self, '节目媒体地址缺失，请重新识别当前节目')
            ns['QTimer'].singleShot(0, self._start_next_web_download)
            return
        try:
            self._web_pipeline_active = True
            self._web_key_failed = False
            self._active_web_payload = dict(payload)
            self.web_tab.begin_download(payload)
            self.web_tab.set_download_status('正在准备')
            self.web_tab._set_status('正在补全节目播放资料', '#FF4FA3')
            worker = ns['_ManifestFetchThread'](payload['manifest_url'], payload.get('manifest_kind', 'hls'), payload.get('_request_headers', {}))
            self._preparation_manifest_thread = worker
            timer = ns['QTimer'](self)
            timer.setSingleShot(True)
            expired = [False]
            def timeout():
                expired[0] = True
                worker.requestInterruption()
                failed(self, '读取节目播放资料超时，请重新播放当前节目后重试')
            timer.timeout.connect(timeout)
            timer.start(20000)
            def ready(result):
                if expired[0]:
                    return
                timer.stop()
                updated_payload = dict(payload)
                parsed = result.get('parsed', {})
                updated_payload['_widevine_pssh'] = parsed.get('_widevine_pssh', '')
                if not updated_payload.get('duration'):
                    updated_payload['duration'] = parsed.get('duration', 0)
                updated_task = dict(task)
                updated_task['payload'] = updated_payload
                original_launch(self, updated_task)
            def fetch_failed(error):
                if not expired[0]:
                    timer.stop()
                    failed(self, '读取节目播放资料失败：' + str(error))
            worker.parsed.connect(ready)
            worker.failed.connect(fetch_failed)
            def finished():
                timer.stop()
                timer.deleteLater()
                self._preparation_manifest_thread = None
                worker.deleteLater()
                if self._web_key_failed and not self._web_pipeline_active:
                    ns['QTimer'].singleShot(0, self._start_next_web_download)
            worker.finished.connect(finished)
            worker.start()
        except Exception as error:
            failed(self, '准备流程异常：' + str(error))
            ns['QTimer'].singleShot(0, self._start_next_web_download)
    Main._launch_web_download = launch

    original_close = Main.closeEvent
    def close(self, event):
        worker = getattr(self, '_preparation_manifest_thread', None)
        if worker is not None and worker.isRunning():
            # Keep the owner alive until network work finishes; never destroy
            # a running QThread when the user closes during preparation.
            self.web_tab._set_status('节目资料读取中，请稍后关闭', '#B05C68')
            event.ignore()
            return
        original_close(self, event)
    Main.closeEvent = close
