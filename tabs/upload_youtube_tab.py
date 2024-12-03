from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
                            QFileDialog, QSizePolicy, QRadioButton, QButtonGroup, 
                            QLineEdit, QListWidget, QProgressBar, QFrame, QComboBox,
                            QScrollArea, QMessageBox, QCheckBox)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
import os
import json
import time
import psutil
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
# Thêm imports cần thiết
from PyQt5.QtCore import QThread, pyqtSignal
import re
from selenium.common.exceptions import (TimeoutException, NoSuchElementException,
    StaleElementReferenceException, ElementNotInteractableException,
    ElementClickInterceptedException, UnexpectedAlertPresentException,
    InvalidSelectorException, WebDriverException)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QDragEnterEvent, QDropEvent

class UploadWorker(QThread):
    progress_updated = pyqtSignal(int, str)
    upload_complete = pyqtSignal()
    error_occurred = pyqtSignal(str)

    def __init__(self, channel_frame):
        super().__init__()
        self.channel_frame = channel_frame
        
    def run(self):
        try:
            if self.channel_frame.firefox_radio.isChecked():
                self.setup_firefox_driver()
            else:
                self.setup_chrome_driver()
                
            self.perform_upload()
            
        except Exception as e:
            self.error_occurred.emit(str(e))

    def setup_firefox_driver(self):
        selected_profile = self.channel_frame.profile_combo.currentText()
        profile_id = self.channel_frame.profiles_dict[selected_profile]
        profile_path = os.path.expanduser(f'~\\AppData\\Roaming\\Mozilla\\Firefox\\Profiles\\{profile_id}')
        
        firefox_options = webdriver.FirefoxOptions()
        firefox_options.binary_location = r"C:/Program Files/Mozilla Firefox/firefox.exe"
        firefox_options.add_argument("-profile")
        firefox_options.add_argument(os.fspath(profile_path))
        
        self.driver = webdriver.Firefox(options=firefox_options)
        self.driver.set_window_size(1320, 960)

    def setup_chrome_driver(self):
        options = webdriver.ChromeOptions()
        options.binary_location = self.channel_frame.chrome_path_edit.text()
        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), 
                                     options=options)
        self.driver.set_window_size(1320, 960)

    def perform_upload(self):
        wait = WebDriverWait(self.driver, 15)
        self.driver.get("https://studio.youtube.com")
        
        try:
            account_button = wait.until(
                EC.presence_of_element_located((By.ID, "account-button"))
            )
            self.progress_updated.emit(10, "Đăng nhập thành công")
            
            # Click create and upload buttons
            retries = 0
            max_retries = 3
            while retries < max_retries:
                try:
                    create_button = wait.until(
                        EC.element_to_be_clickable((By.XPATH, '//ytcp-button[@id="create-icon"]'))
                    )
                    self.driver.execute_script("arguments[0].click();", create_button)
                    time.sleep(2)
                    
                    upload_button = wait.until(
                        EC.element_to_be_clickable((By.XPATH, '//tp-yt-paper-item[@id="text-item-0"]'))
                    )
                    self.driver.execute_script("arguments[0].click();", upload_button)
                    break
                except Exception:
                    retries += 1
                    self.progress_updated.emit(10, f"Thử lại lần {retries}")
                    self.driver.refresh()
                    time.sleep(2)

            # Upload files
            file_input = self.driver.find_element(By.XPATH, '//input[@type="file"]')
            video_paths = [self.channel_frame.video_list.item(i).text() 
                          for i in range(self.channel_frame.video_list.count())]
            
            combined_paths = '\n'.join(video_paths)
            file_input.send_keys(combined_paths)
            
            # Monitor upload progress
            while True:
                try:
                    progress_element = wait.until(
                        EC.presence_of_element_located((By.XPATH, "//span[contains(@class, 'progress-label')]"))
                    )
                    progress_text = progress_element.text.lower()
                    
                    if any(text in progress_text for text in ["uploads complete", "đã hoàn tất"]):
                        self.upload_complete.emit()
                        break
                        
                    if "uploading video" in progress_text or "đang tải lên" in progress_text:
                        match = re.search(r'(\d+)/(\d+)', progress_text)
                        if match:
                            current, total = map(int, match.groups())
                            progress = (current / total) * 100
                            self.progress_updated.emit(progress, progress_text)
                            
                    time.sleep(2)
                    
                except Exception as e:
                    print(f"Error tracking progress: {str(e)}")
                    break
                    
        # Sau khi upload thành công
            if self.channel_frame.remove_after_upload:
                self.channel_frame.video_list.clear()
                
            self.upload_complete.emit()
            
        except Exception as e:
            self.error_occurred.emit(str(e))
        finally:
            self.driver.quit()


class ChannelFrame(QFrame):
    def __init__(self, channel_name):
        super().__init__()
        self.setFrameStyle(QFrame.StyledPanel)
        self.video_files = []
        self.profiles_dict = {}
        self.chrome_path = ""
        self.remove_after_upload = False  # Thêm biến kiểm soát xóa video
        self.init_channel_ui(channel_name)

    def init_channel_ui(self, channel_name):
        main_layout = QVBoxLayout()
        
        # Channel header
        header = QLabel(f"Kênh: {channel_name}")
        header.setStyleSheet("font-weight: bold;")
        
        # Browser selection
        browser_frame = QFrame()
        browser_layout = QHBoxLayout()
        browser_frame.setLayout(browser_layout)
        self.browser_type = QButtonGroup()
        self.firefox_radio = QRadioButton("Firefox")
        self.chrome_radio = QRadioButton("Chrome Portable")
        self.browser_type.addButton(self.firefox_radio)
        self.browser_type.addButton(self.chrome_radio)
        self.firefox_radio.setChecked(True)
        browser_layout.addWidget(self.firefox_radio)
        browser_layout.addWidget(self.chrome_radio)
        
        # Chrome path selection
        self.chrome_frame = QFrame()
        chrome_layout = QHBoxLayout()
        self.chrome_frame.setLayout(chrome_layout)
        self.chrome_path_edit = QLineEdit()
        self.chrome_select_btn = QPushButton("Chọn File")
        chrome_layout.addWidget(self.chrome_path_edit)
        chrome_layout.addWidget(self.chrome_select_btn)
        self.chrome_frame.hide()
        
        # Profile selection with check button
        self.profile_frame = QFrame()
        profile_layout = QHBoxLayout()
        self.profile_frame.setLayout(profile_layout)
        self.profile_combo = QComboBox()
        self.check_profile_btn = QPushButton("Kiểm tra Profile")
        profile_layout.addWidget(QLabel("Profile:"))
        profile_layout.addWidget(self.profile_combo)
        profile_layout.addWidget(self.check_profile_btn)
        
        # Video list with fixed minimum height
        self.video_list = QListWidget()
        self.video_list.setMinimumHeight(250)
        self.video_list.setAcceptDrops(True)
        
        # Video controls with remove option
        video_controls = QHBoxLayout()
        add_video_btn = QPushButton("Thêm Video")
        remove_video_btn = QPushButton("Xóa Video")
        self.remove_videos_cb = QCheckBox("Xóa video sau khi upload")
        video_controls.addWidget(add_video_btn)
        video_controls.addWidget(remove_video_btn)
        video_controls.addStretch()
        video_controls.addWidget(self.remove_videos_cb)
        
        # Add all components to main layout
        main_layout.addWidget(header)
        main_layout.addWidget(browser_frame)
        main_layout.addWidget(self.profile_frame)  # Changed to self.profile_frame
        main_layout.addWidget(self.chrome_frame)
        main_layout.addWidget(self.video_list)
        main_layout.addLayout(video_controls)
        
        self.setLayout(main_layout)
        
        # Connect signals
        self.check_profile_btn.clicked.connect(self.open_profile_for_check)
        self.remove_videos_cb.toggled.connect(self.toggle_remove_videos)
        self.firefox_radio.toggled.connect(self.toggle_browser_options)
        self.chrome_select_btn.clicked.connect(self.select_chrome)
        add_video_btn.clicked.connect(self.add_videos)
        remove_video_btn.clicked.connect(self.remove_video)


    def toggle_remove_videos(self, checked):
        self.remove_after_upload = checked

    def open_profile_for_check(self):
        if self.firefox_radio.isChecked():
            selected_profile = self.profile_combo.currentText()
            if selected_profile in self.profiles_dict:
                profile_id = self.profiles_dict[selected_profile]
                self.close_existing_firefox()
                
                try:
                    firefox_options = webdriver.FirefoxOptions()
                    firefox_options.binary_location = r"C:/Program Files/Mozilla Firefox/firefox.exe"
                    profile_path = os.path.expanduser(f'~\\AppData\\Roaming\\Mozilla\\Firefox\\Profiles\\{profile_id}')
                    firefox_options.add_argument("-profile")
                    firefox_options.add_argument(os.fspath(profile_path))
                    
                    driver = webdriver.Firefox(options=firefox_options)
                    driver.get("https://studio.youtube.com")
                    QMessageBox.information(self, "Thông báo", 
                        "Profile đã được mở. Hãy kiểm tra và đóng trình duyệt khi hoàn tất!")
                except Exception as e:
                    QMessageBox.warning(self, "Lỗi", f"Không thể mở profile: {str(e)}")
        else:
            QMessageBox.information(self, "Thông báo", 
                "Tính năng này chỉ khả dụng cho Firefox!")

    def close_existing_firefox(self):
        for process in psutil.process_iter(['pid', 'name']):
            try:
                if process.info['name'] == 'firefox.exe':
                    psutil.Process(process.info['pid']).terminate()
                    time.sleep(1)  # Đợi process đóng hoàn toàn
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        files = [url.toLocalFile() for url in event.mimeData().urls()]
        for file_path in files:
            if file_path.lower().endswith(('.mp4', '.avi', '.mkv')):
                # Chuẩn hóa đường dẫn file
                normalized_path = os.path.normpath(file_path).replace('"', '')
                self.video_list.addItem(normalized_path)

    def toggle_browser_options(self):
        if self.firefox_radio.isChecked():
            self.chrome_frame.hide()
            self.profile_frame.show()
        else:
            self.profile_frame.hide()
            self.chrome_frame.show()

    def select_chrome(self):
        file_path = QFileDialog.getOpenFileName(
            self,
            "Select Chrome Portable",
            "",
            "Executable files (*.exe)"
        )[0]
        if file_path:
            self.chrome_path_edit.setText(file_path)

    def add_videos(self):
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Videos",
            "",
            "Video files (*.mp4 *.avi *.mkv)"
        )
        for file_path in files:
            self.video_list.addItem(file_path)

    def remove_video(self):
        current_row = self.video_list.currentRow()
        if current_row >= 0:
            self.video_list.takeItem(current_row)

class UploadYoutubeTab(QWidget):
    def __init__(self):
        super().__init__()
        self.upload_queue = []  # Hàng đợi upload
        self.current_worker = None
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.channel_frames = []
        self.init_upload_ui()
        self.load_firefox_profiles()

    def init_upload_ui(self):
        main_layout = QVBoxLayout()
        
        # Scroll area for channels
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        self.channels_layout = QVBoxLayout(scroll_content)
        
        # Add first channel
        self.add_channel()
        
        scroll.setWidget(scroll_content)
        
        # Control buttons
        controls = QHBoxLayout()
        add_channel_btn = QPushButton("Thêm Kênh Mới")
        upload_all_btn = QPushButton("Upload Tất Cả")
        controls.addWidget(add_channel_btn)
        controls.addWidget(upload_all_btn)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.status_label = QLabel()
        
        # Add components to main layout
        main_layout.addWidget(scroll)
        main_layout.addLayout(controls)
        main_layout.addWidget(self.progress_bar)
        main_layout.addWidget(self.status_label)
        
        self.setLayout(main_layout)
        
        # Connect signals
        add_channel_btn.clicked.connect(self.add_channel)
        upload_all_btn.clicked.connect(self.start_upload_all)

    def add_channel(self):
        channel_frame = ChannelFrame(f"Kênh {len(self.channel_frames) + 1}")
        self.channels_layout.addWidget(channel_frame)
        self.channel_frames.append(channel_frame)
        # Load profiles ngay khi thêm kênh mới
        self.load_firefox_profiles(channel_frame)

    def load_firefox_profiles(self, specific_channel=None):
        try:
            firefox_path = os.path.expanduser('~\\AppData\\Roaming\\Mozilla\\Firefox')
            profiles_ini_path = os.path.join(firefox_path, 'profiles.ini')
            
            if os.path.exists(profiles_ini_path):
                profiles_dict = {}
                with open(profiles_ini_path, 'r', encoding='utf-8') as f:
                    current_section = None
                    current_data = {}
                    
                    for line in f:
                        line = line.strip()
                        if line.startswith('['):
                            if current_section and 'Name' in current_data and 'Path' in current_data:
                                profiles_dict[current_data['Name']] = current_data['Path'].split('/')[-1]
                            current_section = line[1:-1]
                            current_data = {}
                        elif '=' in line:
                            key, value = line.split('=', 1)
                            current_data[key.strip()] = value.strip()
                
                # Cập nhật profiles cho kênh cụ thể hoặc tất cả các kênh
                channels_to_update = [specific_channel] if specific_channel else self.channel_frames
                for channel in channels_to_update:
                    channel.profiles_dict = profiles_dict.copy()
                    channel.profile_combo.clear()
                    channel.profile_combo.addItems(profiles_dict.keys())
                    
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error loading Firefox profiles: {str(e)}")

    def start_upload_all(self):
        # Xóa hàng đợi cũ nếu có
        self.upload_queue = []
        
        # Thêm các kênh có video vào hàng đợi
        for channel_frame in self.channel_frames:
            if channel_frame.video_list.count() > 0:
                self.upload_queue.append(channel_frame)
        
        if self.upload_queue:
            self.process_next_channel()
        else:
            QMessageBox.information(self, "Thông báo", "Không có video nào để upload!")

    def process_next_channel(self):
        if self.upload_queue:
            channel_frame = self.upload_queue[0]
            
            # Kiểm tra và đóng Firefox trước khi upload
            if channel_frame.firefox_radio.isChecked():
                channel_frame.close_existing_firefox()
            
            self.current_worker = UploadWorker(channel_frame)
            self.current_worker.progress_updated.connect(self.update_progress)
            self.current_worker.upload_complete.connect(self.on_channel_complete)
            self.current_worker.error_occurred.connect(self.on_upload_error)
            self.current_worker.start()
            self.status_label.setText(f"Đang xử lý {channel_frame.findChild(QLabel).text()}")
        else:
            self.on_all_uploads_complete()

    def on_channel_complete(self):
        # Xử lý kênh tiếp theo
        self.process_next_channel()

    def on_all_uploads_complete(self):
        QMessageBox.information(self, "Success", "Tất cả các kênh đã upload xong!")
        self.progress_bar.setValue(100)
        self.status_label.setText("Hoàn tất tất cả")

    def update_progress(self, value, message):
        self.progress_bar.setValue(value)
        self.status_label.setText(message)

    def on_upload_complete(self):
        QMessageBox.information(self, "Success", "Upload completed successfully!")
        self.progress_bar.setValue(100)
        self.status_label.setText("Upload completed")

    def on_upload_error(self, error_message):
        QMessageBox.warning(self, "Error", f"Upload failed: {error_message}")
