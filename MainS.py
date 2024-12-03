import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QTabWidget
from tabs.convert_file_tab import ConvertFileTab
from tabs.merge_av_tab import MergeAVTab
from tabs.merge_files_tab import MergeFilesTab
from tabs.create_short_tab import CreateShortTab
from tabs.loop_video_tab import LoopVideoTab
from tabs.mix_audio_tab import MixAudioTab
from tabs.fix_camera_tab import FixCameraTab
from tabs.create_title_tab import CreateTitleTab
from tabs.create_long_video_tab import CreateLongVideoTab
from tabs.upload_youtube_tab import UploadYoutubeTab
import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QTabWidget, QSizePolicy
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt

import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QTabWidget, QSizePolicy
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt, QTimer
from loading_screen import LoadingScreen
from network_checker import NetworkChecker

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.loading_screen = None
        self.init_loading_screen()
        
    def check_requirements(self):
        # Kiểm tra cập nhật trước
        self.loading_screen.status_label.setText("Đang kiểm tra cập nhật...")
        updater = AutoUpdater()
        needs_update, message = updater.check_update(self)
        
        if needs_update:
            self.loading_screen.close()
            sys.exit()
            
        # Tiếp tục với các kiểm tra khác
        self.loading_screen.status_label.setText("Đang kiểm tra kết nối internet...")
        internet_ok, internet_msg = NetworkChecker.check_internet()
        if not internet_ok:
            self.loading_screen.show_error(internet_msg)
            return
        
    def init_loading_screen(self):
        self.loading_screen = LoadingScreen()
        self.loading_screen.show()
        
        # Sử dụng QTimer để kiểm tra không đồng bộ
        QTimer.singleShot(1000, self.check_requirements)
    
    def check_requirements(self):
        # Kiểm tra kết nối internet
        self.loading_screen.status_label.setText("Đang kiểm tra kết nối internet...")
        internet_ok, internet_msg = NetworkChecker.check_internet()
        if not internet_ok:
            self.loading_screen.show_error(internet_msg)
            return
            
        # Kiểm tra Gemini API
        self.loading_screen.status_label.setText("Đang Kiểm Ứng Dụng ...") #Đang kiểm tra Gemini API...
        api_ok, api_msg = NetworkChecker.check_gemini_api()
        if not api_ok:
            self.loading_screen.show_error(api_msg)
            return
            
        # Nếu mọi thứ OK, khởi tạo giao diện chính
        self.loading_screen.status_label.setText("Đang khởi tạo ứng dụng...")
        QTimer.singleShot(1000, self.initialize_main_ui)
    
    def initialize_main_ui(self):
        # Đóng màn hình loading
        self.loading_screen.close()
        
        # Khởi tạo giao diện chính
        self.setWindowTitle("NH IMS full tools")
        self.setGeometry(100, 100, 1524, 768)
        self.setAcceptDrops(True)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # Khởi tạo tabs TRƯỚC KHI sử dụng
        self.tabs = QTabWidget()
        self.tabs.setAcceptDrops(True)
        self.setCentralWidget(self.tabs)
        
        # Tùy chỉnh font cho tab
        tab_font = QFont()
        tab_font.setPointSize(10)
        tab_font.setBold(True)
        self.tabs.setFont(tab_font)
        
        # Tùy chỉnh style cho tab
        self.tabs.setStyleSheet("""
            QTabBar::tab {
                min-width: 120px;
                padding: 5px;
                margin: 2px;
            }
            QTabBar::tab:selected {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                          stop: 0 #fafafa, stop: 0.4 #f4f4f4,
                                          stop: 0.5 #e7e7e7, stop: 1.0 #fafafa);
            }
        """)
        
        # Khởi tạo giao diện chính (phần code cũ của bạn)
        self.setWindowTitle("NH IMS full tools")
        self.setGeometry(100, 100, 1524, 768)
        self.setAcceptDrops(True)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        # Create and add tabs
        self.tabs.addTab(ConvertFileTab(), "Convert File")
        self.tabs.addTab(MergeAVTab(), "Ghép audio and video")
        self.tabs.addTab(MergeFilesTab(), "Ghép nhiều file")
        self.tabs.addTab(CreateShortTab(), "Create video Short")
        self.tabs.addTab(LoopVideoTab(), "Loop video")
        self.tabs.addTab(MixAudioTab(), "Mix Audio")
        self.tabs.addTab(FixCameraTab(), "Fix Camera video")
        self.tabs.addTab(CreateTitleTab(), "Create Title and description")
        self.tabs.addTab(CreateLongVideoTab(), "Auto create long video")
        # Update the tab creation to use the new class name
        self.tabs.addTab(UploadYoutubeTab(), "Upload Youtube")  # Changed class name
        self.tabs = QTabWidget()
        self.show()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    sys.exit(app.exec_())