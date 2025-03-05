# dlm.py
import os, json, datetime, time
from PyQt5.QtCore import QTimer, QUrl, QObject, pyqtSlot
from PyQt5.QtWidgets import QStatusBar, QDialog, QVBoxLayout, QListWidget, QListWidgetItem, QAction, QFileDialog
from PyQt5.QtWebEngineWidgets import QWebEngineDownloadItem
from PyQt5.QtGui import QIcon

class DownloadManager(QObject):
    def __init__(self, status_bar: QStatusBar, status_callback=None, parent=None, history_file=None):
        super(DownloadManager, self).__init__(parent)
        self.status_bar = status_bar
        
        self.status_callback = status_callback  
        self.history_file = history_file or os.path.join(os.getcwd(), "download_history.json")
        self.downloads = {}  
        self.current_download_item = None

        from PyQt5.QtWebEngineWidgets import QWebEngineProfile
        profile = QWebEngineProfile.defaultProfile()
        profile.downloadRequested.connect(self.handle_download)

    @pyqtSlot(QWebEngineDownloadItem)
    def handle_download(self, download_item: QWebEngineDownloadItem):
        from PyQt5.QtWidgets import QFileDialog
        
        save_path, _ = QFileDialog.getSaveFileName(None, "Save File", os.path.basename(download_item.path()))
        if save_path:
            download_item.setPath(save_path)
            download_item.accept()
            self.current_download_item = download_item
            self.downloads[download_item] = {
                "prev_bytes": 0,
                "prev_time": time.time()
            }
            download_item.downloadProgress.connect(
                lambda rec, tot: self.on_download_progress(download_item, rec, tot)
            )
            download_item.finished.connect(
                lambda: self.on_download_finished(download_item)
            )
            msg = f"Downloading: {os.path.basename(save_path)}"
            if self.status_callback:
                self.status_callback(msg)
            else:
                self.status_bar.showMessage(msg)
        else:
            download_item.cancel()

    def on_download_progress(self, download_item: QWebEngineDownloadItem, bytes_received, bytes_total):
        if bytes_total > 0:
            percent = int(bytes_received * 100 / bytes_total)
        else:
            percent = 0
        info = self.downloads.get(download_item)
        now = time.time()
        if info:
            delta_bytes = bytes_received - info["prev_bytes"]
            delta_time = now - info["prev_time"]
            speed = delta_bytes / delta_time if delta_time > 0 else 0
            info["prev_bytes"] = bytes_received
            info["prev_time"] = now
        else:
            speed = 0
        speed_kb = speed / 1024  # KB/s
        file_name = os.path.basename(download_item.path())
        msg = f"Downloading: {file_name} - {percent}% - {speed_kb:.2f} KB/s"
        if self.status_callback:
            self.status_callback(msg)
        else:
            self.status_bar.showMessage(msg)

    def on_download_finished(self, download_item: QWebEngineDownloadItem):
        file_name = os.path.basename(download_item.path())
        msg = f"Download completed: {file_name}"
        if self.status_callback:
            self.status_callback(msg)
        else:
            self.status_bar.showMessage(msg)
        
        record = {
            "file_name": file_name,
            "path": download_item.path(),
            "url": download_item.url().toString(),
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        self.save_download_history(record)
        QTimer.singleShot(5000, self.clear_download_status)
        if download_item in self.downloads:
            del self.downloads[download_item]
        self.current_download_item = None

    def clear_download_status(self):
        if self.status_callback:
            self.status_callback("")
        else:
            self.status_bar.clearMessage()

    def save_download_history(self, record):
        history = []
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, "r") as f:
                    history = json.load(f)
            except Exception as e:
                print("Error loading download history:", e)
        history.append(record)
        try:
            with open(self.history_file, "w") as f:
                json.dump(history, f, indent=4)
        except Exception as e:
            print("Error saving download history:", e)

    def show_download_history(self):
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QListWidget, QListWidgetItem
        dialog = QDialog()
        dialog.setWindowTitle("Download History")
        layout = QVBoxLayout()
        list_widget = QListWidget()
        history = []
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, "r") as f:
                    history = json.load(f)
            except Exception as e:
                print("Error loading download history:", e)
        for record in history:
            item_text = f"{record['timestamp']} - {record['file_name']} - {record['path']}"
            item = QListWidgetItem(item_text)
            list_widget.addItem(item)
        layout.addWidget(list_widget)
        dialog.setLayout(layout)
        dialog.resize(500, 400)
        dialog.exec_()

    def get_download_history_action(self):
        action = QAction(QIcon.fromTheme("⤓"), "⤓", self)
        action.triggered.connect(self.show_download_history)
        return action
