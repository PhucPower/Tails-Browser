import sys, os, json, datetime
from dlm import DownloadManager
from PyQt5.QtCore import QUrl, Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QToolBar, QAction, QLineEdit, 
    QStatusBar, QDialog, QVBoxLayout, QListWidget, QListWidgetItem, 
    QTabWidget, QToolButton
)
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineProfile, QWebEnginePage

class NewWindowPage(QWebEnginePage):
    def __init__(self, parent=None):
        super(NewWindowPage, self).__init__(parent)
        self.firstNavigation = True

    def acceptNavigationRequest(self, url, navType, isMainFrame):
        if self.firstNavigation and url.toString() != "about:blank":
            self.firstNavigation = False
            return True
        return super(NewWindowPage, self).acceptNavigationRequest(url, navType, isMainFrame)

class BrowserTab(QWebEngineView):
    def __init__(self, parent=None):
        super(BrowserTab, self).__init__(parent)
        profile = QWebEngineProfile.defaultProfile()
        profile.setPersistentCookiesPolicy(QWebEngineProfile.ForcePersistentCookies)
        cache_path = os.path.join(os.getcwd(), "cache")
        storage_path = os.path.join(os.getcwd(), "storage")
        os.makedirs(cache_path, exist_ok=True)
        os.makedirs(storage_path, exist_ok=True)
        profile.setCachePath(cache_path)
        profile.setPersistentStoragePath(storage_path)
    
    def createWindow(self, _type):
        new_browser = MainWindow.instance.add_new_tab(QUrl("about:blank"), "New Tab")
        new_page = NewWindowPage(new_browser)
        new_browser.setPage(new_page)
        new_page.linkHovered.connect(MainWindow.instance.link_hovered)
        return new_browser

class MainWindow(QMainWindow):
    instance = None
    def __init__(self):
        super(MainWindow, self).__init__()
        MainWindow.instance = self
        self.setWindowTitle("Tails browser")  # Trusted And Intuitive Local Secure Browser

        self.status = QStatusBar()
        self.setStatusBar(self.status)

        self.connection_status = ""
        self.hovered_link = ""
        self.download_status = ""

        self.history_file = os.path.join(os.getcwd(), "history.json")
        self.history = self.load_history()

        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_current_tab)
        self.tabs.currentChanged.connect(self.current_tab_changed)
        self.setCentralWidget(self.tabs)

        self.new_tab_button = QToolButton()
        self.new_tab_button.setText("+")
        self.new_tab_button.setCursor(Qt.PointingHandCursor)
        self.new_tab_button.setToolTip("Open new tab")
        self.new_tab_button.clicked.connect(self.add_new_tab)
        self.tabs.setCornerWidget(self.new_tab_button, Qt.TopRightCorner)

        self.toolbar = QToolBar()
        self.addToolBar(self.toolbar)

        back_btn = QAction("<", self)
        back_btn.triggered.connect(lambda: self.tabs.currentWidget().back())
        self.toolbar.addAction(back_btn)

        forward_btn = QAction(">", self)
        forward_btn.triggered.connect(lambda: self.tabs.currentWidget().forward())
        self.toolbar.addAction(forward_btn)

        reload_btn = QAction("⟳", self)
        reload_btn.triggered.connect(lambda: self.tabs.currentWidget().reload())
        self.toolbar.addAction(reload_btn)

        home_btn = QAction("🏠", self)
        home_btn.triggered.connect(self.navigate_home)
        self.toolbar.addAction(home_btn)

        self.url_bar = QLineEdit()
        self.url_bar.returnPressed.connect(self.navigate_to_url)
        self.toolbar.addWidget(self.url_bar)

        history_btn = QAction("⏰", self)
        history_btn.triggered.connect(self.show_history)
        self.toolbar.addAction(history_btn)

        self.dlm = DownloadManager(self.status, status_callback=self.update_download_status)
        download_history_action = self.dlm.get_download_history_action()
        self.toolbar.addAction(download_history_action)

        self.add_new_tab(QUrl("https://www.google.com"), "Home page")
        self.showMaximized()

    def load_history(self):
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, "r") as f:
                    return json.load(f)
            except Exception as e:
                print("Error when load history:", e)
                return []
        return []

    def save_history(self):
        try:
            with open(self.history_file, "w") as f:
                json.dump(self.history, f, indent=4)
        except Exception as e:
            print("Error when save history:", e)

    def update_download_status(self, msg):
        self.download_status = msg
        self.update_status_bar()

    def update_status_bar(self):
        status_text = self.connection_status
        if self.hovered_link:
            status_text += " | " + self.hovered_link
        if self.download_status:
            status_text += " | " + self.download_status
        self.status.showMessage(status_text)

    def update_status_load_started(self):
        sender = self.sender()
        if sender == self.tabs.currentWidget():
            self.connection_status = "Send request GET, TLS Handshake in progress..."
            self.update_status_bar()

    def update_status_load_progress(self, progress):
        sender = self.sender()
        if sender == self.tabs.currentWidget():
            self.connection_status = f"Receiving data: {progress}%"
            self.update_status_bar()

    def update_status_load_finished(self, ok):
        sender = self.sender()
        if sender == self.tabs.currentWidget():
            self.connection_status = "Ready"
            self.update_status_bar()
            current_url = sender.url().toString()
            if current_url:
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                record = {"url": current_url, "timestamp": timestamp}
                self.history.append(record)
                self.save_history()

    def link_hovered(self, url):
        if self.tabs.currentWidget() and self.tabs.currentWidget().page() == self.sender():
            self.hovered_link = url
            self.update_status_bar()

    def add_new_tab(self, qurl=None, label="New Tab"):
        if isinstance(qurl, bool):
            qurl = None
        if qurl is None:
            qurl = QUrl("https://www.google.com")
        browser = BrowserTab()
        browser.setUrl(qurl)

        browser.loadStarted.connect(self.update_status_load_started)
        browser.loadProgress.connect(self.update_status_load_progress)
        browser.loadFinished.connect(self.update_status_load_finished)
        browser.urlChanged.connect(lambda qurl, browser=browser: self.update_urlbar(qurl, browser))
        browser.titleChanged.connect(lambda title, browser=browser: 
                                       self.tabs.setTabText(self.tabs.indexOf(browser), title))
        browser.page().iconChanged.connect(lambda icon, browser=browser: self.update_tab_icon(icon, browser))
        browser.page().linkHovered.connect(self.link_hovered)

        index = self.tabs.addTab(browser, label)
        self.tabs.setCurrentIndex(index)
        return browser

    def update_tab_icon(self, icon, browser):
        index = self.tabs.indexOf(browser)
        if index != -1 and not icon.isNull():
            self.tabs.setTabIcon(index, icon)

    def close_current_tab(self, index):
        if self.tabs.count() <= 1:
            return
        self.tabs.removeTab(index)

    def current_tab_changed(self, index):
        if self.tabs.currentWidget():
            self.update_urlbar(self.tabs.currentWidget().url(), self.tabs.currentWidget())

    def navigate_home(self):
        self.tabs.currentWidget().setUrl(QUrl("https://www.google.com"))

    def navigate_to_url(self):
        url_text = self.url_bar.text()
        if not url_text.startswith("http"):
            url_text = "http://" + url_text
        self.tabs.currentWidget().setUrl(QUrl(url_text))

    def update_urlbar(self, qurl, browser):
        if self.tabs.currentWidget() == browser:
            self.url_bar.setText(qurl.toString())
            self.url_bar.setCursorPosition(0)

    def show_history(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Web browsing history")
        layout = QVBoxLayout()
        list_widget = QListWidget()
        for rec in self.history:
            item_text = f"{rec['timestamp']} - {rec['url']}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, rec["url"])
            list_widget.addItem(item)
        list_widget.itemDoubleClicked.connect(lambda item: self.navigate_from_history(item.data(Qt.UserRole), dialog))
        layout.addWidget(list_widget)
        dialog.setLayout(layout)
        dialog.resize(500, 400)
        dialog.exec_()

    def navigate_from_history(self, url, dialog):
        self.tabs.currentWidget().setUrl(QUrl(url))
        dialog.close()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    QApplication.setApplicationName("Tails browser")
    window = MainWindow()
    sys.exit(app.exec_())
