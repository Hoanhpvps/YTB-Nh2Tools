# PyQt5 Imports
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QFileDialog,
    QSizePolicy, QRadioButton, QButtonGroup, QLineEdit, QListWidget,
    QProgressBar, QFrame, QComboBox, QScrollArea, QMessageBox, QCheckBox,
    QGroupBox, QTextEdit, QDateEdit, QSpinBox, QDialog, 
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QDate, QTimer
from PyQt5.QtGui import QDragEnterEvent, QDropEvent

# Selenium Imports
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.keys import Keys

from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException, StaleElementReferenceException,
    ElementNotInteractableException, ElementClickInterceptedException,
    UnexpectedAlertPresentException, InvalidSelectorException, WebDriverException
)
from webdriver_manager.chrome import ChromeDriverManager

# Standard Library Imports
import logging
import os
import json
import time
import psutil
import shutil
import re
import requests
import zipfile
import io
import traceback
from subprocess import CREATE_NO_WINDOW
import win32api
from PyQt5.QtWidgets import QInputDialog, QMessageBox
from PyQt5.QtCore import Qt
from PyQt5.QtCore import QEventLoop
from .selectors import YouTubeSelectors as YTS
import random

class BrowserManager:
    def __init__(self):
        self.driver = None
    
    def cleanup_driver(self):
        try:
            if hasattr(self, 'driver') and self.driver:
                self.driver.quit()
        except Exception as e:
            print(f"Error cleaning up driver: {e}")

    def close_webdriver_processes(self):
        try:
            for process in psutil.process_iter(['pid', 'name']):
                if process.info['name'] in ['chromedriver.exe', 'geckodriver.exe']:
                    psutil.Process(process.info['pid']).terminate()
            time.sleep(2)
        except Exception as e:
            print(f"Error closing WebDriver processes: {e}")

    def setup_firefox(self, profile_name=None):
        try:
            # Close any existing webdriver processes
            self.close_webdriver_processes()
            time.sleep(2)
            
            # Load profiles if profile_name is provided
            if profile_name:
                profiles_dict = self.load_firefox_profiles()
                if profile_name not in profiles_dict:
                    raise Exception(f"Firefox profile '{profile_name}' not found")
                profile_path = os.path.expanduser(f'~\\AppData\\Roaming\\Mozilla\\Firefox\\Profiles\\{profiles_dict[profile_name]}')
            else:
                profile_path = None
            
            firefox_options = webdriver.FirefoxOptions()
            firefox_options.binary_location = r"C:/Program Files/Mozilla Firefox/firefox.exe"
            
            if profile_path:
                firefox_options.add_argument("-profile")
                firefox_options.add_argument(os.fspath(profile_path))
            
            self.driver = webdriver.Firefox(options=firefox_options)
            self.driver.set_window_size(1320, 960)
            return self.driver
            
        except Exception as e:
            raise Exception(f"Failed to setup Firefox: {str(e)}")

    def load_firefox_profiles(self):
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
                
                return profiles_dict
                
        except Exception as e:
            print(f"Error loading Firefox profiles: {str(e)}")
            return {}

    def get_chrome_version(self, chrome_path):
        try:
            chrome_dir = os.path.dirname(chrome_path)
            chrome_exe = os.path.join(chrome_dir, 'App', 'Chrome-bin', 'chrome.exe')
            version_info = win32api.GetFileVersionInfo(chrome_exe, '\\')
            ms = version_info['FileVersionMS']
            ls = version_info['FileVersionLS']
            return f"{ms >> 16}.{ms & 0xFFFF}.{ls >> 16}.{ls & 0xFFFF}"
        except Exception as e:
            print(f"Version detection error: {str(e)}")
            return None

    def download_chromedriver(self, chrome_version):
        try:
            # Create storage directory
            user_home = os.path.expanduser('~')
            chromedriver_dir = os.path.join(user_home, 'AppData', 'Local', 'ChromeDriver')
            os.makedirs(chromedriver_dir, exist_ok=True)
            
            # Extract major version
            major_version = chrome_version.split('.')[0]
            
            # Version mapping
            driver_version_map = {
                "129": "129.0.6668.59",
                "128": "128.0.6462.59",
            }
            
            driver_version = driver_version_map.get(major_version)
            if not driver_version:
                raise Exception(f"Unsupported Chrome version: {major_version}")
                
            # Download driver
            driver_path = ChromeDriverManager(driver_version=driver_version).install()
            
            # Move to managed location
            final_path = os.path.join(chromedriver_dir, f"chromedriver_{major_version}.exe")
            shutil.copy2(driver_path, final_path)
            
            return final_path
            
        except Exception as e:
            raise Exception(f"ChromeDriver download failed: {str(e)}")

    def find_existing_chromedriver(self, driver_dir, chrome_version):
        try:
            for root, dirs, files in os.walk(driver_dir):
                if 'chromedriver.exe' in files:
                    driver_path = os.path.join(root, 'chromedriver.exe')
                    # Verify version
                    import subprocess
                    output = subprocess.check_output([driver_path, '--version']).decode()
                    if f"ChromeDriver {chrome_version}." in output:
                        return driver_path
            return None
        except:
            return None

    # Modify setup_chrome to use these methods
    def setup_chrome(self, chrome_path):
        try:
            time.sleep(2)
            chrome_version = self.get_chrome_version(chrome_path)

            # Close any existing webdriver processes
            self.close_webdriver_processes()
            time.sleep(2)
            if not chrome_version:
                raise Exception("Unable to detect Chrome version")
            
            # Try to find existing driver first
            user_home = os.path.expanduser('~')
            chromedriver_dir = os.path.join(user_home, 'AppData', 'Local', 'ChromeDriver')
            driver_path = self.find_existing_chromedriver(chromedriver_dir, chrome_version)
            
            # If not found, download new one
            if not driver_path:
                driver_path = self.download_chromedriver(chrome_version)
                
            options = webdriver.ChromeOptions()
            options.binary_location = chrome_path
            
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--remote-debugging-port=9222')
            options.add_argument('--start-maximized')
            options.page_load_strategy = 'normal'
            
            data_dir = os.path.join(os.path.dirname(chrome_path), 'Data')
            if os.path.exists(data_dir):
                options.add_argument(f'--user-data-dir={data_dir}')
            
            driver_path = ChromeDriverManager(driver_version=chrome_version).install()
            service = Service(executable_path=driver_path)
            service.creation_flags = CREATE_NO_WINDOW
            
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    self.driver = webdriver.Chrome(service=service, options=options)
                    self.driver.set_window_size(1320, 960)
                    self.driver.execute_script('return document.readyState')
                    break
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise e
                    time.sleep(2)
            
            return self.driver
                    
        except Exception as e:
            raise Exception(f"Failed to setup Chrome: {str(e)}")

    def quit(self):
        self.cleanup_driver()

class UploadWorker(QThread):
    progress_updated = pyqtSignal(int, str)
    upload_complete = pyqtSignal()
    error_occurred = pyqtSignal(str)

    def __init__(self, channel_frame):
        super().__init__()
        self.channel_frame = channel_frame
        self.browser_manager = BrowserManager()
        self.driver = None  # Initialize driver attribute

    def run(self):
        try:
            if self.channel_frame.firefox_radio.isChecked():
                selected_profile = self.channel_frame.profile_combo.currentText()
                profile_id = self.channel_frame.profiles_dict[selected_profile]
                self.driver = self.browser_manager.setup_firefox(profile_id)  # Store as self.driver
            else:
                chrome_path = self.channel_frame.chrome_path_edit.text().strip()
                print(f"Using Chrome path: {chrome_path}")
                self.driver = self.browser_manager.setup_chrome(chrome_path)  # Store as self.driver
                
            self.perform_upload()
            
        except Exception as e:
            self.error_occurred.emit(str(e))

    def perform_upload(self):
        try:
            wait = WebDriverWait(self.driver, 15)
            self.progress_updated.emit(10, "Accessing YouTube Studio...")
            self.driver.get("https://studio.youtube.com")
            time.sleep(5)

            # Check login status
            try:
                wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                if "Sign in" in self.driver.page_source:
                    self.error_occurred.emit("Not logged in")
                    return False
            except TimeoutException:
                self.error_occurred.emit("Cannot load YouTube Studio page")
                return False

            self.progress_updated.emit(20, "Checking create button...")
            # Click create button
            try:
                create_button = wait.until(EC.element_to_be_clickable(
                    (By.XPATH, '//ytcp-button[@id="create-icon"]')))
                create_button.click()
                time.sleep(2)
            except TimeoutException:
                self.error_occurred.emit("Cannot find create button")
                return False

            self.progress_updated.emit(30, "Checking upload button...")
            # Click upload button
            try:
                upload_button = wait.until(EC.element_to_be_clickable(
                    (By.XPATH, '//tp-yt-paper-item[@id="text-item-0"]')))
                upload_button.click()
                time.sleep(2)
            except TimeoutException:
                self.error_occurred.emit("Cannot find upload button")
                return False

            # Prepare video paths and upload
            self.progress_updated.emit(40, "Preparing video paths...")
            video_paths = []
            for i in range(self.channel_frame.video_list.count()):
                file_path = self.channel_frame.video_list.item(i).text()
                normalized_path = os.path.abspath(file_path).replace('/', '\\')
                if not os.path.exists(normalized_path):
                    self.error_occurred.emit(f"Video file not found: {normalized_path}")
                    return False
                video_paths.append(normalized_path)

            if not video_paths:
                self.error_occurred.emit("No videos selected for upload")
                return False

            self.progress_updated.emit(45, "Starting file upload...")
            # Upload files
            try:
                file_input = wait.until(EC.presence_of_element_located(
                    (By.XPATH, '//input[@type="file"]')))
                file_input.send_keys('\n'.join(video_paths))
            except TimeoutException:
                self.error_occurred.emit("Cannot find file upload input")
                return False

            # Wait for upload progress monitor to appear
            time.sleep(5)
            self.progress_updated.emit(50, "Monitoring upload progress...")

            while True:
                try:
                    # Check for upload progress header
                    progress_header = wait.until(EC.presence_of_element_located(
                        (By.CLASS_NAME, "header.style-scope.ytcp-multi-progress-monitor")
                    ))

                    # Get upload count status
                    count_element = progress_header.find_element(
                        By.CLASS_NAME, "count.style-scope.ytcp-multi-progress-monitor")
                    count_text = count_element.text
                    self.progress_updated.emit(75, f"Uploading: {count_text}")

                    # Check for remaining time
                    try:
                        eta_element = self.driver.find_element(By.ID, "eta")
                        if eta_element.is_displayed():
                            eta_text = eta_element.text
                            self.progress_updated.emit(85, f"Uploading: {count_text} - {eta_text}")
                    except NoSuchElementException:
                        pass

                    # Check if upload is complete
                    try:
                        close_button = self.driver.find_element(
                            By.XPATH,
                            '//ytcp-icon-button[@id="close-button" and contains(@class, "style-scope ytcp-multi-progress-monitor")]'
                        )
                        if close_button.is_displayed():
                            self.progress_updated.emit(100, "Upload complete!")
                            time.sleep(2)
                            self.upload_complete.emit()
                            return True
                    except NoSuchElementException:
                        pass

                    time.sleep(1)

                except StaleElementReferenceException:
                    time.sleep(1)
                    continue
                except TimeoutException:
                    self.error_occurred.emit("Upload progress monitor not found")
                    return False
                except Exception as e:
                    self.error_occurred.emit(f"Error monitoring upload progress: {str(e)}")
                    return False

        except Exception as e:
            self.error_occurred.emit(str(e))
            return False
        finally:
            if hasattr(self, 'driver') and self.driver:
                self.driver.quit()

class ChannelFrame(QFrame):
    action_type_changed = pyqtSignal()
    def __init__(self, channel_name):
        super().__init__()
        self.anti_bq_manager = AntiBQManagerDialog(self)
        self.setFrameStyle(QFrame.StyledPanel)
        self.video_files = []
        self.profiles_dict = {}
        self.chrome_path = ""
        self.remove_after_upload = False
        self.is_browser_hidden = False  # Thêm biến theo dõi trạng thái ẩn/hiện
        self.init_channel_ui(channel_name)
        self.edit_video_info = EditVideoInfo
        self.setup_progress_tracking()
        # The parent tab will handle loading profiles

    def init_channel_ui(self, channel_name):
        main_layout = QHBoxLayout()  

        # Left Panel - Video List
        left_panel = QVBoxLayout()
        
        # Video list
        self.video_list = DragDropListWidget(self)
        self.video_list.setMinimumHeight(250)
        self.video_list.setMinimumWidth(300)
        self.video_list.setAcceptDrops(True)
        self.video_list.setDragEnabled(True)
        
        # Video controls
        video_controls = QHBoxLayout()
        add_video_btn = QPushButton("Thêm Video")
        remove_video_btn = QPushButton("Xóa Video")
        self.remove_videos_cb = QCheckBox("Xóa sau khi upload")
        
        video_controls.addWidget(add_video_btn)
        video_controls.addWidget(remove_video_btn)
        video_controls.addWidget(self.remove_videos_cb)
        
        add_video_btn.clicked.connect(self.add_videos)
        remove_video_btn.clicked.connect(self.remove_video)
        self.remove_videos_cb.toggled.connect(self.toggle_remove_videos)
        
        left_panel.addWidget(QLabel("Danh sách video:"))
        left_panel.addWidget(self.video_list)
        left_panel.addLayout(video_controls)

        # Right Panel - Settings
        right_panel = QVBoxLayout()
        
        # Channel header
        header = QLabel(f"Kênh: {channel_name}")
        header.setStyleSheet("font-weight: bold;")

        # Function selection group
        function_group = QGroupBox("Chọn chức năng")
        function_layout = QHBoxLayout()
        self.function_type = QButtonGroup()
        
        self.upload_function = QRadioButton("Upload video")
        self.edit_function = QRadioButton("Edit video")
        self.anti_bq_function = QRadioButton("Kháng BQ video")
        
        self.function_type.addButton(self.upload_function)
        self.function_type.addButton(self.edit_function)
        self.function_type.addButton(self.anti_bq_function)
        
        self.upload_function.setChecked(True)
        
        function_layout.addWidget(self.upload_function)
        function_layout.addWidget(self.edit_function)
        function_layout.addWidget(self.anti_bq_function)
        function_group.setLayout(function_layout)

        # Upload Frame
        self.upload_frame = QFrame()
        upload_layout = QVBoxLayout()
        
        # Browser selection
        browser_group = QGroupBox("Chọn trình duyệt")
        browser_layout = QVBoxLayout()
        self.browser_type = QButtonGroup()
        self.firefox_radio = QRadioButton("Firefox")
        self.chrome_radio = QRadioButton("Chrome Portable")
        self.browser_type.addButton(self.firefox_radio)
        self.browser_type.addButton(self.chrome_radio)
        browser_layout.addWidget(self.firefox_radio)
        browser_layout.addWidget(self.chrome_radio)
        browser_group.setLayout(browser_layout)
        self.firefox_radio.setChecked(True)
        
        # Profile frame
        self.profile_frame = QFrame()
        profile_layout = QVBoxLayout()
        self.profile_combo = QComboBox()
        self.check_profile_btn = QPushButton("Kiểm tra Profile")
        profile_layout.addWidget(QLabel("Profile:"))
        profile_layout.addWidget(self.profile_combo)
        profile_layout.addWidget(self.check_profile_btn)
        self.profile_frame.setLayout(profile_layout)
        
        # Chrome frame
        self.chrome_frame = QFrame()
        chrome_layout = QVBoxLayout()
        self.chrome_path_edit = QLineEdit()
        self.chrome_select_btn = QPushButton("Chọn File Chrome")
        chrome_layout.addWidget(self.chrome_path_edit)
        chrome_layout.addWidget(self.chrome_select_btn)
        self.chrome_frame.setLayout(chrome_layout)
        self.chrome_frame.hide()
        
        upload_layout.addWidget(browser_group)
        upload_layout.addWidget(self.profile_frame)
        upload_layout.addWidget(self.chrome_frame)
        self.upload_frame.setLayout(upload_layout)

        # Edit Function Frame
        self.edit_function_frame = QFrame()
        edit_function_layout = QVBoxLayout()

        # Action Type Group using checkboxes
        edit_action_group = QGroupBox("Kiểu chỉnh sửa")
        edit_action_layout = QVBoxLayout()

        # Browser selection for Edit Video
        edit_browser_group = QGroupBox("Chọn trình duyệt")
        edit_browser_layout = QVBoxLayout()
        self.edit_browser_type = QButtonGroup()
        self.edit_firefox_radio = QRadioButton("Firefox")
        self.edit_chrome_radio = QRadioButton("Chrome Portable")
        self.edit_browser_type.addButton(self.edit_firefox_radio)
        self.edit_browser_type.addButton(self.edit_chrome_radio)
        edit_browser_layout.addWidget(self.edit_firefox_radio)
        edit_browser_layout.addWidget(self.edit_chrome_radio)
        edit_browser_group.setLayout(edit_browser_layout)
        self.edit_firefox_radio.setChecked(True)

        # Profile frame for Edit Video
        self.edit_profile_frame = QFrame()
        edit_profile_layout = QVBoxLayout()
        self.edit_profile_combo = QComboBox()
        self.edit_check_profile_btn = QPushButton("Kiểm tra Profile")
        edit_profile_layout.addWidget(QLabel("Profile:"))
        edit_profile_layout.addWidget(self.edit_profile_combo)
        edit_profile_layout.addWidget(self.edit_check_profile_btn)
        self.edit_profile_frame.setLayout(edit_profile_layout)

        # Chrome frame for Edit Video
        self.edit_chrome_frame = QFrame()
        edit_chrome_layout = QVBoxLayout()
        self.edit_chrome_path_edit = QLineEdit()
        self.edit_chrome_select_btn = QPushButton("Chọn File Chrome")
        edit_chrome_layout.addWidget(self.edit_chrome_path_edit)
        edit_chrome_layout.addWidget(self.edit_chrome_select_btn)
        self.edit_chrome_frame.setLayout(edit_chrome_layout)
        self.edit_chrome_frame.hide()

        # Add browser components to edit function layout
        edit_function_layout.addWidget(edit_browser_group)
        edit_function_layout.addWidget(self.edit_profile_frame)
        edit_function_layout.addWidget(self.edit_chrome_frame)
        self.edit_info_action = QCheckBox("Sửa thông tin video")
        self.edit_status_action = QCheckBox("Sửa trạng thái video")
        edit_action_layout.addWidget(self.edit_info_action)
        edit_action_layout.addWidget(self.edit_status_action)
        edit_action_group.setLayout(edit_action_layout)

        # Edit Info Components
        self.edit_info_frame = QFrame()
        edit_info_layout = QVBoxLayout()

        # Tiêu đề video
        title_group = QGroupBox("Tiêu đề video")
        title_layout = QVBoxLayout()
        self.title_edit = QTextEdit()
        self.title_edit.setPlaceholderText("Nhập danh sách tiêu đề (mỗi dòng một tiêu đề)")
        title_layout.addWidget(self.title_edit)
        title_group.setLayout(title_layout)

        # Mô tả video
        desc_group = QGroupBox("Mô tả video")
        desc_layout = QVBoxLayout()
        self.desc_edit = QTextEdit()
        self.desc_edit.setPlaceholderText("Nhập mô tả (sử dụng {title} để chèn tiêu đề)")
        desc_layout.addWidget(self.desc_edit)
        desc_group.setLayout(desc_layout)

        # Tags
        tags_group = QGroupBox("Thẻ tag")
        tags_layout = QVBoxLayout()
        self.tags_edit = QTextEdit()
        self.tags_edit.setPlaceholderText("Nhập các từ khóa, phân cách bằng dấu phẩy")
        self.random_tags_cb = QCheckBox("Random tags (tối đa 500 ký tự)")
        tags_layout.addWidget(self.tags_edit)
        tags_layout.addWidget(self.random_tags_cb)
        tags_group.setLayout(tags_layout)

        # Thumbnail
        thumb_group = QGroupBox("Ảnh thumbnail")
        thumb_layout = QHBoxLayout()
        self.thumb_path_edit = QLineEdit()
        self.thumb_select_btn = QPushButton("Chọn thư mục")
        thumb_layout.addWidget(self.thumb_path_edit)
        thumb_layout.addWidget(self.thumb_select_btn)
        thumb_group.setLayout(thumb_layout)

        edit_info_layout.addWidget(title_group)
        edit_info_layout.addWidget(desc_group)
        edit_info_layout.addWidget(tags_group)
        edit_info_layout.addWidget(thumb_group)
        self.edit_info_frame.setLayout(edit_info_layout)

        # Edit Status Components
        self.edit_status_frame = QFrame()
        edit_status_layout = QVBoxLayout()

        # Radio buttons cho trạng thái
        status_group = QGroupBox("Trạng thái")
        status_layout = QVBoxLayout()
        self.status_type = QButtonGroup()
        self.schedule_radio = QRadioButton("Đặt lịch")
        self.public_radio = QRadioButton("Public")
        self.status_type.addButton(self.schedule_radio)
        self.status_type.addButton(self.public_radio)
        self.schedule_radio.setChecked(True)
        status_layout.addWidget(self.schedule_radio)
        status_layout.addWidget(self.public_radio)
        status_group.setLayout(status_layout)

        # Thời gian
        time_group = QGroupBox("Thời gian")
        time_layout = QVBoxLayout()
        self.time_edit = QLineEdit()
        self.time_edit.setPlaceholderText("hh:mm,hh:mm,hh:mm")
        time_layout.addWidget(self.time_edit)
        time_group.setLayout(time_layout)

        # Ngày tháng
        date_group = QGroupBox("Ngày tháng")
        date_layout = QVBoxLayout()
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(QDate.currentDate())
        date_layout.addWidget(self.date_edit)
        date_group.setLayout(date_layout)

        # Số video xử lý
        video_count_group = QGroupBox("Số video cần xử lý")
        video_count_layout = QVBoxLayout()
        self.video_count_spin = QSpinBox()
        self.video_count_spin.setMinimum(1)
        video_count_layout.addWidget(self.video_count_spin)
        video_count_group.setLayout(video_count_layout)

        edit_status_layout.addWidget(status_group)
        edit_status_layout.addWidget(time_group)
        edit_status_layout.addWidget(date_group)
        edit_status_layout.addWidget(video_count_group)
        self.edit_status_frame.setLayout(edit_status_layout)


        # Add all to edit function layout
        edit_function_layout.addWidget(edit_action_group)
        edit_function_layout.addWidget(self.edit_info_frame)
        edit_function_layout.addWidget(self.edit_status_frame)
        self.edit_function_frame.setLayout(edit_function_layout)

        start_edit_btn = QPushButton("Bắt đầu chỉnh sửa")
        edit_function_layout.addWidget(start_edit_btn)
        start_edit_btn.clicked.connect(self.start_edit_video)

        # Anti BQ Frame
        self.anti_bq_frame = QFrame()
        anti_bq_layout = QVBoxLayout()
        
        anti_bq_browser_group = QGroupBox("Chọn trình duyệt")
        anti_bq_browser_layout = QVBoxLayout()
        self.anti_bq_browser_type = QButtonGroup()
        self.anti_bq_firefox_radio = QRadioButton("Firefox")
        self.anti_bq_chrome_radio = QRadioButton("Chrome Portable")
        self.anti_bq_browser_type.addButton(self.anti_bq_firefox_radio)
        self.anti_bq_browser_type.addButton(self.anti_bq_chrome_radio)
        anti_bq_browser_layout.addWidget(self.anti_bq_firefox_radio)
        anti_bq_browser_layout.addWidget(self.anti_bq_chrome_radio)
        anti_bq_browser_group.setLayout(anti_bq_browser_layout)
        self.anti_bq_firefox_radio.setChecked(True)
        
        self.anti_bq_profile_frame = QFrame()
        anti_bq_profile_layout = QVBoxLayout()
        self.anti_bq_profile_combo = QComboBox()
        self.anti_bq_check_profile_btn = QPushButton("Kiểm tra Profile")
        anti_bq_profile_layout.addWidget(QLabel("Profile:"))
        anti_bq_profile_layout.addWidget(self.anti_bq_profile_combo)
        anti_bq_profile_layout.addWidget(self.anti_bq_check_profile_btn)
        self.anti_bq_profile_frame.setLayout(anti_bq_profile_layout)
        
        self.anti_bq_chrome_frame = QFrame()
        anti_bq_chrome_layout = QVBoxLayout()
        self.anti_bq_chrome_path_edit = QLineEdit()
        self.anti_bq_chrome_select_btn = QPushButton("Chọn File Chrome")
        anti_bq_chrome_layout.addWidget(self.anti_bq_chrome_path_edit)
        anti_bq_chrome_layout.addWidget(self.anti_bq_chrome_select_btn)
        self.anti_bq_chrome_frame.setLayout(anti_bq_chrome_layout)
        self.anti_bq_chrome_frame.hide()
        
        anti_bq_layout.addWidget(anti_bq_browser_group)
        anti_bq_layout.addWidget(self.anti_bq_profile_frame)
        anti_bq_layout.addWidget(self.anti_bq_chrome_frame)
        self.anti_bq_frame.setLayout(anti_bq_layout)

        # Connect signals
        self.firefox_radio.toggled.connect(self.toggle_browser_options)
        self.chrome_select_btn.clicked.connect(self.select_chrome)
        self.check_profile_btn.clicked.connect(self.open_profile_for_check)
        self.anti_bq_firefox_radio.toggled.connect(self.toggle_anti_bq_browser_options)
        self.anti_bq_chrome_select_btn.clicked.connect(self.select_anti_bq_chrome)
        self.anti_bq_check_profile_btn.clicked.connect(self.open_anti_bq_profile_for_check)
        self.edit_info_action.toggled.connect(lambda checked: self.edit_info_frame.setVisible(checked))
        self.edit_status_action.toggled.connect(lambda checked: self.edit_status_frame.setVisible(checked))
        # Add these in the signal connection section
        self.edit_firefox_radio.toggled.connect(self.toggle_edit_browser_options)
        self.edit_chrome_select_btn.clicked.connect(self.select_edit_chrome)
        self.edit_check_profile_btn.clicked.connect(self.open_edit_profile_for_check)
        
        # Connect function toggle signals
        self.upload_function.toggled.connect(self.toggle_function_frames)
        self.edit_function.toggled.connect(self.toggle_function_frames)
        self.anti_bq_function.toggled.connect(self.toggle_function_frames)
        
        # Add components to right panel
        right_panel.addWidget(header)
        right_panel.addWidget(function_group)
        right_panel.addWidget(self.upload_frame)
        right_panel.addWidget(self.edit_function_frame)
        right_panel.addWidget(self.anti_bq_frame)
        right_panel.addStretch()

        # Add panels to main layout
        main_layout.addLayout(left_panel, stretch=40)
        main_layout.addLayout(right_panel, stretch=60)
        
        # Set initial visibility states
        self.edit_info_frame.hide()
        self.edit_status_frame.hide()
        self.edit_function_frame.hide()
        self.anti_bq_frame.hide()
        self.upload_frame.show()

        self.setLayout(main_layout)

    def toggle_edit_frames(self):
        if self.edit_info_action.isChecked():
            self.edit_info_frame.show()
            self.edit_status_frame.hide()
        else:
            self.edit_info_frame.hide()
            self.edit_status_frame.show()

    def toggle_function_frames(self, checked):
        if self.upload_function.isChecked():
            self.upload_frame.show()
            self.edit_function_frame.hide()
            self.anti_bq_frame.hide()
        elif self.edit_function.isChecked():
            self.upload_frame.hide()
            self.edit_function_frame.show()
            self.anti_bq_frame.hide()
        else:  # anti_bq_function checked
            self.upload_frame.hide()
            self.edit_function_frame.hide()
            self.anti_bq_frame.show()
    
    def toggle_edit_browser_options(self, checked):
        if checked:
            self.edit_chrome_frame.hide()
        else:
            self.edit_chrome_frame.show()

    def select_edit_chrome(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Chọn file Chrome", "", "Chrome Executable (*.exe)")
        if file_path:
            self.edit_chrome_path_edit.setText(file_path)

    def open_edit_profile_for_check(self):
        # Implement profile check functionality here
        pass

    def start_anti_bq(self):
        # Initialize anti-BQ queue
        self.anti_bq_queue = []
        
        # Add all selected channel frames to queue
        for channel_frame in self.channel_frames:
            if channel_frame.anti_bq_function.isChecked():
                self.anti_bq_queue.append(channel_frame)
                
        # Start processing if queue is not empty    
        if self.anti_bq_queue:
            self.process_next_anti_bq()
   
    def show_anti_bq_manager(self):
        self.anti_bq_manager.exec_()

    def toggle_browser_visibility(self):
        if hasattr(self, 'anti_bq_worker') and self.anti_bq_worker and self.anti_bq_worker.driver:
            try:
                if self.anti_bq_worker.is_browser_hidden:
                    # Hiện trình duyệt
                    self.anti_bq_worker.driver.set_window_position(0, 0)
                    self.anti_bq_worker.is_browser_hidden = False
                    #self.toggle_browser_btn.setText("Ẩn trình duyệt")
                else:
                    # Ẩn trình duyệt
                    self.anti_bq_worker.driver.set_window_position(-3000, 0)
                    self.anti_bq_worker.is_browser_hidden = True
                    #self.toggle_browser_btn.setText("Hiện trình duyệt")
                return True
            except Exception as e:
                print(f"Error toggling browser visibility: {str(e)}")
                return False
        return False

    def on_edit_action_toggled(self, checked):
        if checked:
            self.start_edit_video_worker()

    def on_action_type_changed(self):
        self.action_type_changed.emit()

    def toggle_action_frames(self):
        if self.upload_action.isChecked():
            self.video_list.setEnabled(True)
            self.edit_info_frame.hide()
            self.edit_status_frame.hide()
        elif self.edit_info_action.isChecked():
            self.video_list.setEnabled(False)
            self.edit_info_frame.show()
            self.edit_status_frame.hide()
        else:  # edit_status_action
            self.video_list.setEnabled(False)
            self.edit_info_frame.hide()
            self.edit_status_frame.show()

    def select_thumb_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Chọn thư mục chứa ảnh thumbnail")
        if folder:
            self.thumb_path_edit.setText(folder)\

    def show_input_dialog(self, title, message):
        dialog = QInputDialog(self)
        dialog.setWindowTitle(title)
        dialog.setLabelText(message)
        dialog.resize(500, 200)
        
        if dialog.exec_() == QDialog.Accepted:
            self.current_worker.input_text = dialog.textValue()
            self.current_worker.input_received.emit(dialog.textValue())
        else:
            self.current_worker.input_text = None
            self.current_worker.input_received.emit("")

    def show_confirmation_dialog(self, title, message):
        reply = QMessageBox.question(self, title, message,
                                   QMessageBox.Yes | QMessageBox.No)
        result = reply == QMessageBox.Yes
        self.current_worker.confirmation_result = result
        self.current_worker.confirmation_received.emit(result)

    def setup_anti_bq_worker(self):
        self.anti_bq_worker = AntiBQWorker(self)
        
        # Connect dialog signals
        self.anti_bq_worker.show_input_dialog.connect(self.show_input_dialog)
        self.anti_bq_worker.show_question_dialog.connect(self.show_question_dialog)

    def show_question_dialog(self, title, message):
        # Ensure dialog runs in main thread
        reply = QMessageBox.question(None, title, message,
                                   QMessageBox.Yes | QMessageBox.No)
        return reply == QMessageBox.Yes

    def toggle_anti_bq_browser_options(self, checked):
        if checked:
            self.anti_bq_profile_frame.show()
            self.anti_bq_chrome_frame.hide()
        else:
            self.anti_bq_profile_frame.hide()
            self.anti_bq_chrome_frame.show()

    def select_anti_bq_chrome(self):
        file_path = QFileDialog.getOpenFileName(
            self,
            "Select Chrome Portable",
            "",
            "Executable files (*.exe)"
        )[0]
        if file_path:
            self.anti_bq_chrome_path_edit.setText(file_path)

    def open_anti_bq_profile_for_check(self):
        if self.anti_bq_firefox_radio.isChecked():
            selected_profile = self.anti_bq_profile_combo.currentText()
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

    def start_anti_bq(self):
        if self.video_list.count() == 0:
            QMessageBox.warning(self, "Lỗi", "Vui lòng thêm video trước khi kháng BQ!")
            return
            
        self.anti_bq_worker = AntiBQWorker(self)
        self.anti_bq_worker.progress_updated.connect(self.update_progress)
        self.anti_bq_worker.process_complete.connect(self.on_anti_bq_complete)
        self.anti_bq_worker.error_occurred.connect(self.on_anti_bq_error)
        self.anti_bq_worker.start()

    def on_anti_bq_complete(self):
        QMessageBox.information(self, "Thành công", "Đã hoàn thành kháng BQ!")
        
    def on_anti_bq_error(self, error_message):
        QMessageBox.warning(self, "Lỗi", f"Lỗi khi kháng BQ: {error_message}")

    def toggle_function_frames(self, checked):
        if self.upload_function.isChecked():
            self.upload_frame.show()
            self.edit_function_frame.hide()
            self.anti_bq_frame.hide()
        elif self.edit_function.isChecked():
            self.upload_frame.hide()
            self.edit_function_frame.show()
            self.anti_bq_frame.hide()
        else:  # anti_bq_function checked
            self.upload_frame.hide()
            self.edit_function_frame.hide()
            self.anti_bq_frame.show()

    def show_anti_bq_manager(self):
        dialog = AntiBQManagerDialog(self)
        dialog.exec_()

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
            urls = event.mimeData().urls()
            for url in urls:
                file_path = url.toLocalFile()
                if file_path.lower().endswith(('.mp4', '.avi', '.mkv')):
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        files = [url.toLocalFile() for url in event.mimeData().urls()]
        self.add_files_to_list(files)
        event.acceptProposedAction()

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

    def add_files_to_list(self, files):
        valid_extensions = ('.mp4', '.avi', '.mkv')
        for file_path in files:
            if file_path.lower().endswith(valid_extensions):
                normalized_path = os.path.abspath(file_path).replace('/', '\\')
                existing_items = [self.video_list.item(i).text() 
                                for i in range(self.video_list.count())]
                if normalized_path not in existing_items:
                    self.video_list.addItem(normalized_path)

    def add_videos(self):
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Videos",
            "",
            "Video files (*.mp4 *.avi *.mkv)"
        )
        self.add_files_to_list(files)
    
    def remove_video(self):
        current_row = self.video_list.currentRow()
        if current_row >= 0:
            self.video_list.takeItem(current_row)

    def start_edit_video_worker(self):
        self.edit_video_worker = EditVideoWorker(self)
        
        # Connect signals properly
        self.edit_video_worker.progress_updated.connect(self.update_progress)
        self.edit_video_worker.process_complete.connect(self.on_edit_complete)
        self.edit_video_worker.error_occurred.connect(self.on_edit_error)
        
        # Start the worker
        self.edit_video_worker.start()

    def update_progress(self, value, message):
        print(f"Progress: {value}% - {message}")

    def on_edit_complete(self):
        print("Edit process completed!")

    def on_edit_error(self, error_message):
        print(f"Error: {error_message}")

    def process_next_edit_info(self):
        if self.upload_queue:
            channel_frame = self.upload_queue[0]
            # Fix: Add the missing process_complete parameter
            editor = EditVideoInfo(
                driver=channel_frame.driver, 
                progress_updated=self.update_progress,
                process_complete=self.on_edit_complete  # Add this line
            )

    def process_next_edit_status(self):
        if self.upload_queue:
            channel_frame = self.upload_queue[0]
            editor = EditVideoStatus(channel_frame.driver, self.update_progress)
            try:
                results = editor.start_edit_process()
                # Xử lý kết quả
            except Exception as e:
                QMessageBox.critical(self, "Lỗi", f"Lỗi khi sửa trạng thái: {str(e)}")
            finally:
                self.upload_queue.pop(0)
                if self.upload_queue:
                    self.process_next_edit_status()

    def add_channel(self):
        print("Adding new channel")
        channel_frame = ChannelFrame(self)
        print(f"Anti-BQ checkbox state: {channel_frame.anti_bq_function.isChecked()}")
        self.channel_frames.append(channel_frame)

    def start_edit_video(self):
        browser_manager = None
        try:
            # 1. Validate inputs first
            self.validate_edit_inputs()
            browser_manager = BrowserManager()
            
            # 2. Setup browser driver once
            driver = None
            if self.edit_firefox_radio.isChecked():
                print("Using Firefox for Edit Video")
                profile_name = self.edit_profile_combo.currentText()
                driver = browser_manager.setup_firefox(profile_name)
            else:
                chrome_path = self.edit_chrome_path_edit.text().strip()
                if not os.path.exists(chrome_path) or not chrome_path.lower().endswith('.exe'):
                    raise Exception("Invalid Chrome executable path")
                print("Chrome path validated successfully")
                driver = browser_manager.setup_chrome(chrome_path)

            # 3. Initialize EditVideoInfo once
            edit_video = EditVideoInfo(
                driver=driver,
                progress_updated=self.update_progress,
                process_complete=lambda: QMessageBox.information(self, "Success", "Video editing completed!"),
                edit_info_action=self.edit_info_action,
                edit_status_action=self.edit_status_action,
                channel_frame=self
            )


            # 4. Navigate to studio
            if not edit_video.navigate_to_studio():
                raise Exception("Failed to navigate to YouTube Studio")

            # 5. Get schedule parameters
            video_count = self.video_count_spin.value()
            schedule_times = self.time_edit.text().strip().split(',')
            schedule_date = self.date_edit.date()
            is_schedule = self.schedule_radio.isChecked()

            # 6. Process videos
            success = edit_video.process_draft_videos(
                video_count=video_count,
                schedule_times=schedule_times,
                schedule_date=schedule_date,
                is_schedule=is_schedule
            )

            if not success:
                raise Exception("Failed to process draft videos")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Edit video failed: {str(e)}")
            
        finally:
            if browser_manager:
                browser_manager.quit()

    def validate_edit_inputs(self):
        if self.edit_status_action.isChecked():
            # Validate time format
            times = self.time_edit.text().strip()
            if not times or not all(re.match(r'\d{2}:\d{2}', t.strip()) for t in times.split(',')):
                raise ValueError("Invalid time format. Use hh:mm,hh:mm,...")
                
            # Validate video count
            if self.video_count_spin.value() < 1:
                raise ValueError("Video count must be at least 1")
                
        if self.edit_chrome_radio.isChecked() and not self.edit_chrome_path_edit.text():
            raise ValueError("Chrome path is required when using Chrome")

    def setup_progress_tracking(self):
        self.progress_bar = QProgressBar()
        self.progress_label = QLabel("Ready...")
        
        # Add to existing layout
        progress_layout = QVBoxLayout()
        self.layout().addWidget(self.progress_label)
        self.layout().addWidget(self.progress_bar)
        self.layout().addLayout(progress_layout)
        
    def edit_video(self):
        worker = EditVideoWorker(self)
        worker.progress_updated.connect(self.update_progress_tracking)
        worker.process_complete.connect(self.on_process_complete_tracking)
        worker.error_occurred.connect(self.on_error_tracking)
        worker.start()
        
    def update_progress_tracking(self, value, message):
        self.progress_bar.setValue(value)
        self.progress_label.setText(message)
        
    def on_process_complete_tracking(self):
        self.progress_bar.setValue(100)
        self.progress_label.setText("Process completed!")
        
    def on_error_tracking(self, error_message):
        QMessageBox.critical(self, "Error", error_message)

class UploadYoutubeTab(QWidget):
    progress_updated = pyqtSignal(int, str)  # Add this signal
    def __init__(self):
        super().__init__()
        self.upload_queue = []  # Hàng đợi upload
        self.current_worker = None
        self.current_channel_frame = None  # Add this line
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.channel_frames = []
        self.anti_bq_queue = []  # Thêm queue cho kháng BQ
        self.init_upload_ui()
        self.load_firefox_profiles()
        # Connect the signal to update progress bar
        self.progress_updated.connect(self.update_progress)
        self.browser_manager = BrowserManager()
        self.edit_video_worker = None


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
        self.upload_all_btn = QPushButton("Upload Tất Cả")  # Store as instance variable
        anti_bq_all_btn = QPushButton("Kháng BQ Tất Cả")
        
        controls.addWidget(add_channel_btn)
        controls.addWidget(self.upload_all_btn)  # Use instance variable
        controls.addWidget(anti_bq_all_btn)
        
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
        self.upload_all_btn.clicked.connect(self.start_upload_all)  # Use instance variable
        anti_bq_all_btn.clicked.connect(self.start_anti_bq)
        self.upload_all_btn.clicked.connect(self.on_upload_all_clicked)

    def start_edit_video(self):
        self.cleanup_workers()
        if not self.current_channel_frame:
            QMessageBox.warning(self, "Cảnh báo", "Vui lòng chọn kênh!")
            return

        # Create worker with channel frame
        self.edit_video_worker = EditVideoWorker(self.current_channel_frame)
        
        # Connect signals
        self.edit_video_worker.progress_updated.connect(self.update_progress)
        self.edit_video_worker.process_complete.connect(self.on_edit_complete)
        self.edit_video_worker.error_occurred.connect(self.on_edit_error)
        
        # Start worker
        self.edit_video_worker.start()

    def process_next_edit_info(self):
        if not self.upload_queue:
            self.on_all_uploads_complete()
            return
            
        channel_frame = self.upload_queue[0]
        editor = EditVideoInfo(None, self.update_progress)
        
        try:
            # Initialize browser
            if channel_frame.firefox_radio.isChecked():
                profile_path = channel_frame.get_selected_profile()
                if not profile_path:
                    raise Exception("Chưa chọn profile Firefox")
                self.browser_manager.setup_firefox(profile_path)
            else:
                chrome_path = channel_frame.chrome_path_edit.text().strip()
                chrome_version = self.browser_manager.get_chrome_version(chrome_path)
                if not chrome_version:
                    raise Exception("Unable to detect Chrome version")
                self.browser_manager.setup_chrome(chrome_path, chrome_version)
                
            # Start edit process
            results = editor.start_edit_process()
            
            # Process results
            for result in results:
                if result["status"] == "success":
                    video = result["video"]
                    editor.update_video_info(
                        video,
                        channel_frame.title_edit.toPlainText(),
                        channel_frame.desc_edit.toPlainText(),
                        channel_frame.tags_edit.toPlainText(),
                        channel_frame.thumb_path_edit.text()
                    )
                    
            self.upload_queue.pop(0)
            self.process_next_edit_info()
            
        except Exception as e:
            self.on_upload_error(str(e))
        finally:
            if hasattr(editor, 'driver'):
                editor.driver.quit()

    def on_edit_complete(self):
        QMessageBox.information(self, "Thông báo", "Đã hoàn thành chỉnh sửa video!")
        self.edit_video_worker = None
        
    def on_upload_all_clicked(self):
        if not self.current_channel_frame:
            return
            
        # Kiểm tra loại thao tác được chọn
        if self.current_channel_frame.edit_status_action.isChecked():
            self.start_edit_video()
        elif self.current_channel_frame.upload_action.isChecked():
            # Xử lý upload hiện tại
            self.start_upload_all()
        # Thêm các action khác nếu cần

    def start_anti_bq(self):
        self.cleanup_workers()
        # Debug print
        print("Starting Anti-BQ process")
        print(f"Total channels: {len(self.channel_frames)}")
        
        for channel_frame in self.channel_frames:
            if channel_frame.anti_bq_function.isChecked():
                self.anti_bq_queue.append(channel_frame)
        
        if self.anti_bq_queue:
            self.process_next_anti_bq()
        else:
            QMessageBox.information(self, "Thông báo", "Không có kênh nào để xử lý!")

    def show_input_dialog(self, title, message):
        dialog = QInputDialog(self)
        dialog.setWindowTitle(title)
        dialog.setLabelText(message)
        dialog.resize(500, 200)
        
        if dialog.exec_() == QDialog.Accepted:
            self.current_worker.input_text = dialog.textValue()
            self.current_worker.input_received.emit(dialog.textValue())
        else:
            self.current_worker.input_text = None
            self.current_worker.input_received.emit("")

    def show_confirmation_dialog(self, title, message):
        reply = QMessageBox.question(
            self, 
            title,
            message,
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.No:  # Khi chọn No
            # Chuyển sang kênh tiếp theo
            if self.anti_bq_queue:
                self.anti_bq_queue.pop(0)  # Bỏ kênh hiện tại
                QTimer.singleShot(2000, self.process_next_anti_bq)
            else:
                self.on_all_anti_bq_complete()
        else:  # Khi chọn Yes
            # Tiếp tục xử lý kênh hiện tại
            self.process_next_anti_bq()

    def process_next_anti_bq(self):
        if not hasattr(self, 'anti_bq_queue'):
            self.anti_bq_queue = []
        if self.anti_bq_queue:
            channel_frame = self.anti_bq_queue[0]
            self.current_worker = AntiBQWorker(channel_frame, channel_frame.anti_bq_manager)
            
            # Connect all signals
            self.current_worker.progress_updated.connect(self.update_progress)
            self.current_worker.process_complete.connect(self.on_anti_bq_channel_complete)
            self.current_worker.error_occurred.connect(self.on_anti_bq_error)
            self.current_worker.countdown_updated.connect(self.update_countdown)
            self.current_worker.request_input.connect(self.show_input_dialog)
            self.current_worker.request_confirmation.connect(self.show_confirmation_dialog)
            
            self.current_worker.start()
            self.status_label.setText(f"Đang xử lý kháng BQ {channel_frame.findChild(QLabel).text()}")
        else:
            QMessageBox.warning(self, "Thông báo", "Kháng BQ thất bại: Anti BQ queue is empty")

    def update_countdown(self, seconds):
        self.status_label.setText(f"Tự động chuyển kênh sau {seconds}s. Click vào page tiếp theo để tiếp tục kháng")

    def on_anti_bq_channel_complete(self):
        # Xóa kênh đã xử lý khỏi queue
        if self.anti_bq_queue:
            self.anti_bq_queue.pop(0)
            self.browser_manager.cleanup_driver()
            self.browser_manager.close_webdriver_processes()    
        
        # Kiểm tra còn kênh nào trong queue không
        if self.anti_bq_queue:
            # Nếu còn thì xử lý kênh tiếp theo
            self.process_next_anti_bq()
        else:
            # Nếu không còn kênh nào thì thông báo hoàn tất
            QMessageBox.information(self, "Thông báo", "Đã hoàn tất xử lý tất cả các kênh!")

    def on_all_anti_bq_complete(self):
        QMessageBox.information(self, "Success", "Tất cả các kênh đã kháng BQ xong!")
        self.progress_bar.setValue(100)
        self.status_label.setText("Hoàn tất kháng BQ tất cả")

    def on_anti_bq_error(self, error_message):
        QMessageBox.warning(self, "Error", f"Kháng BQ thất bại: {error_message}")

    def add_channel(self):
        channel_frame = ChannelFrame(f"Kênh {len(self.channel_frames) + 1}")
        self.channels_layout.addWidget(channel_frame)
        self.channel_frames.append(channel_frame)
        
        # Kết nối signal mới
        channel_frame.action_type_changed.connect(self.update_action_button_text)
        
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
                
                # Update profiles for specific channel or all channels
                channels_to_update = [specific_channel] if specific_channel else self.channel_frames
                for channel in channels_to_update:
                    channel.profiles_dict = profiles_dict.copy()
                    channel.profile_combo.clear()
                    channel.anti_bq_profile_combo.clear()  # Update both combos
                    channel.profile_combo.addItems(profiles_dict.keys())
                    channel.anti_bq_profile_combo.addItems(profiles_dict.keys())
                    
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error loading Firefox profiles: {str(e)}")

    def update_action_button_text(self):
        # Get the sender channel frame
        sender = self.sender()
        if sender:
            self.current_channel_frame = sender
            
        if self.current_channel_frame:
            if self.current_channel_frame.upload_action.isChecked():
                self.upload_all_btn.setText("Upload Tất Cả")
            elif self.current_channel_frame.edit_info_action.isChecked():
                self.upload_all_btn.setText("Sửa Thông Tin Tất Cả")
            elif self.current_channel_frame.edit_status_action.isChecked():
                self.upload_all_btn.setText("Sửa Trạng Thái Tất Cả")

    def start_upload_all(self):
        self.cleanup_workers()
        
        # Clear existing queue
        self.upload_queue = []
        
        # Add enabled channels to queue
        for channel_frame in self.channel_frames:
            if channel_frame.isEnabled():
                self.upload_queue.append(channel_frame)
        
        if not self.upload_queue:
            self.status_label.setText("Không có kênh nào được chọn")
            return
            
        # Get current channel frame if not set
        if not self.current_channel_frame:
            for frame in self.channel_frames:
                if frame.isActiveWindow():
                    self.current_channel_frame = frame
                    break
                    
        # Start appropriate process based on selected action
        if self.current_channel_frame:
            if self.current_channel_frame.upload_action.isChecked():
                # Use QTimer to process uploads asynchronously
                QTimer.singleShot(0, self.process_next_upload)
                
            elif self.current_channel_frame.edit_info_action.isChecked():
                QTimer.singleShot(0, self.process_next_edit_info)
                
            elif self.current_channel_frame.edit_status_action.isChecked():
                QTimer.singleShot(0, self.process_next_edit_status)

    def process_next_upload(self):
        if self.upload_queue:
                
            channel_frame = self.upload_queue[0]
            # Debug print
            print(f"Processing channel: {channel_frame.findChild(QLabel).text()}")
            print(f"Chrome path: {channel_frame.chrome_path_edit.text().strip()}")

            self.current_worker = UploadWorker(channel_frame)

            # Connect signals
            self.current_worker.progress_updated.connect(self.update_progress)
            self.current_worker.upload_complete.connect(self.on_channel_complete)
            self.current_worker.error_occurred.connect(self.handle_upload_error)
            
            self.status_label.setText(f"Đang xử lý {channel_frame.findChild(QLabel).text()}")
            self.current_worker.start()

    def on_channel_complete(self):
        if self.upload_queue:
            completed_channel = self.upload_queue.pop(0)
            print(f"Completed channel: {completed_channel.findChild(QLabel).text()}")
            
        if self.upload_queue:
            self.process_next_upload()
        else:
            self.on_all_uploads_complete()

    def handle_upload_error(self, error):
        if error == "LOGIN_FAILED":
            # Get current channel name for logging
            current_channel = self.upload_queue[0].findChild(QLabel).text()
            self.status_label.setText(f"Đăng nhập thất bại: {current_channel}")
            
            # Remove failed channel from queue
            self.upload_queue.pop(0)
            
            # Process next channel if available
            if self.upload_queue:
                self.process_next_upload()
            else:
                self.on_all_uploads_complete()
        else:
            # Handle other errors through existing error handler
            self.on_upload_error(error)

    def process_next_edit_info(self):
        if not self.upload_queue:
            self.on_all_uploads_complete()
            return
            
        channel_frame = self.upload_queue[0]
        
        try:
            # Initialize browser first
            if channel_frame.firefox_radio.isChecked():
                profile_path = channel_frame.get_selected_profile()
                if not profile_path:
                    raise Exception("Chưa chọn profile Firefox")
                    
                # Setup Firefox driver
                firefox_options = webdriver.FirefoxOptions()
                firefox_options.binary_location = r"C:/Program Files/Mozilla Firefox/firefox.exe"
                firefox_options.add_argument("-profile")
                firefox_options.add_argument(os.fspath(profile_path))
                
                driver = webdriver.Firefox(options=firefox_options)
                driver.set_window_size(1320, 960)
                
            else:
                # Setup Chrome Portable
                chrome_path = channel_frame.chrome_path_edit.text().strip()
                chrome_version = self.browser_manager.get_chrome_version(chrome_path)
                if not chrome_version:
                    raise Exception("Unable to detect Chrome version")
                    
                options = webdriver.ChromeOptions()
                options.binary_location = chrome_path
                options.add_argument('--no-sandbox')
                options.add_argument('--disable-dev-shm-usage')
                options.add_argument('--disable-gpu')
                options.add_argument('--remote-debugging-port=9222')
                
                data_dir = os.path.join(os.path.dirname(chrome_path), 'Data')
                if os.path.exists(data_dir):
                    options.add_argument(f'--user-data-dir={data_dir}')
                
                driver_path = ChromeDriverManager(driver_version=chrome_version).install()
                service = Service(executable_path=driver_path)
                service.creation_flags = CREATE_NO_WINDOW
                
                driver = webdriver.Chrome(service=service, options=options)
                driver.set_window_size(1320, 960)
                
            # Create editor with initialized driver
            editor = EditVideoInfo(driver, self.progress_updated)  # Use self.progress_updated instead
                
            # Start edit process
            results = editor.start_edit_process()
            
            # Process results
            for result in results:
                if result["status"] == "success":
                    video = result["video"]
                    editor.update_video_info(
                        video,
                        channel_frame.title_edit.toPlainText(),
                        channel_frame.desc_edit.toPlainText(),
                        channel_frame.tags_edit.toPlainText(),
                        channel_frame.thumb_path_edit.text()
                    )
                    
            self.upload_queue.pop(0)
            self.process_next_edit_info()
            
        except Exception as e:
            self.on_upload_error(str(e))
        finally:
            if 'driver' in locals():
                driver.quit()

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

    # Add cleanup methods to properly handle thread termination

    def closeEvent(self, event):
        # Clean up any running workers before closing
        if self.current_worker and self.current_worker.isRunning():
            self.current_worker.quit()
            self.current_worker.wait()
        
        if self.edit_video_worker and self.edit_video_worker.isRunning():
            self.edit_video_worker.quit()
            self.edit_video_worker.wait()
            
        # Clean up browser manager
        if hasattr(self, 'browser_manager'):
            self.browser_manager.cleanup_driver()
            self.browser_manager.close_webdriver_processes()
            
        event.accept()

    def cleanup_workers(self):
        # Method to clean up workers when switching tasks
        if self.current_worker and self.current_worker.isRunning():
            self.current_worker.quit()
            self.current_worker.wait()
            self.current_worker = None
            
        if self.edit_video_worker and self.edit_video_worker.isRunning():
            self.edit_video_worker.quit() 
            self.edit_video_worker.wait()
            self.edit_video_worker = None

class YTS:
    # Base URLs
    STUDIO_URL = "https://studio.youtube.com"
    
    # XPath selectors
    AVATAR_BTN = "//button[@id='avatar-btn']"
    CONTENT_TAB = "//div[@id='menu-item-1']"
    UPLOADS_TAB = "//tp-yt-paper-tab[@id='uploads-tab']"

    # Video list elements
    VIDEO_LIST = "ytcp-video-section-content#video-list"
    VIDEO_ROW = "ytcp-video-row.style-scope.ytcp-video-section-content"
    RESTRICTIONS_TEXT = "restrictions-text"
    COPYRIGHT_TEXTS = ["Bản quyền", "Copyright"]
    SEE_DETAIL_BUTTON = "//a[@class='action-link style-scope ytcp-video-restrictions-tooltip-body']"
    # Claims elements
    CLAIMS_CONTAINER = "ytcr-video-content-list-old.style-scope.ytcr-video-home-section-old"
    CLAIM_ROW = "//div[@class='content-row-container style-scope ytcr-video-content-list-old']"
    DISPUTE_STATUS = "#dispute-status"
    ASSET_TITLE = "span#asset-title.title-text.style-scope.ytcr-video-content-list-claim-row"
    ACTIONS_BUTTON = "ytcp-button#actions-button"
    
    # Dispute dialog elements
    DISPUTE_OPTION = "//div[@class='action-card-container style-scope ytcr-video-actions-dialog' and @action='NON_TAKEDOWN_CLAIM_OPTION_DISPUTE']"
    CONFIRM_BUTTON = "//ytcp-button[@id='confirm-button' and @class='style-scope ytcr-video-actions-dialog']"
    CONTINUE_BUTTON = "//ytcp-button[@id='continue-button']"
    RADIO_GROUP = "//tp-yt-paper-radio-group[@id='type-radios']"
    LICENSE_RADIO_BUTTON = ".//tp-yt-paper-radio-button[2]"
    REVIEW_CHECKBOX = "//ytcp-checkbox-lit[@id='review-checkbox']"
    RATIONALE_TEXTAREA = "//ytcp-form-textarea[@id='rationale']//textarea"
    FORM_CHECKBOXES = "//ytcp-checkbox-lit[@class='style-scope ytcp-form-checkbox']"
    SIGNATURE_FIELD = "signature"
    SUBMIT_BUTTON = "submit-button"
    CLOSE_SUMBITIED_DISPUTE = "//ytcp-button[@id='confirm-button' and @class='style-scope ytcp-confirmation-dialog']"
    NEXT_PAGE_CONTINUE = "//ytcp-icon-button[@id='navigate-after']"
    CLOSE_DIALOG = "ytcp-icon-button.close-button.style-scope.ytcr-video-home-dialog"
    
    # CSS Selectors for video elements
    VIDEO_LIST_CONTAINER = "ytcp-video-section-content#video-list"
    VIDEO_ROW = "ytcp-video-row.style-scope.ytcp-video-section-content"
    VISIBILITY_BUTTON = "ytcp-video-visibility-select"
    VISIBILITY_DIALOG = "ytcp-video-visibility-dialog"
    
    # Visibility dialog elements
    SCHEDULE_RADIO = "#schedule-radio-button"
    PUBLIC_RADIO = "#public-radio-button"
    DATE_PICKER = "#datepicker-trigger"
    TIME_INPUT = "#time-of-day-input"

class EditVideoWorker(QThread):
    progress_updated = pyqtSignal(int, str)
    process_complete = pyqtSignal()
    error_occurred = pyqtSignal(str)

    def __init__(self, channel_frame):
        super().__init__()
        self.channel_frame = channel_frame
        self.browser_manager = BrowserManager()
        self.driver = None

    def run(self):
        video_count = self.channel_frame.video_count_spin.value()
        schedule_times = self.channel_frame.time_edit.text().split(',')
        schedule_date = self.channel_frame.date_edit.date()
        is_schedule = self.channel_frame.schedule_radio.isChecked()

        try:            
            if self.channel_frame.anti_bq_firefox_radio.isChecked():
                print("Using Firefox for Anti-BQ")
                selected_profile = self.channel_frame.profile_combo.currentText()
                profile_id = self.channel_frame.profiles_dict[selected_profile]
                self.driver = self.browser_manager.setup_firefox(profile_id)
            else:
                chrome_path = self.channel_frame.anti_bq_chrome_path_edit.text().strip()
                if not chrome_path:
                    raise Exception("Chrome path is empty")
                if not os.path.exists(chrome_path):
                    raise Exception(f"Chrome file not found: {chrome_path}")
                if not chrome_path.lower().endswith('.exe'):
                    raise Exception("Must be .exe file")
                    
                self.driver = self.browser_manager.setup_chrome(chrome_path)

            self.edit_video_info = EditVideoInfo(
                driver=self.driver,
                progress_updated=lambda v, m: self.progress_updated.emit(v, m),
                process_complete=lambda: self.process_complete.emit(),
                channel_frame=self.channel_frame
            )


            self.edit_video_info.process_draft_videos(
                video_count=video_count,
                schedule_times=schedule_times,
                schedule_date=schedule_date,
                is_schedule=is_schedule
            )

        except Exception as e:
            self.error_occurred.emit(str(e))
        finally:
            if self.driver:
                self.driver.quit()

class EditVideoInfo:
    def __init__(self, driver, progress_updated, process_complete, channel_frame, edit_info_action=None, edit_status_action=None):
        # Remove the signal definitions from here
        self.driver = driver
        # Store the callback functions
        self.progress_updated = progress_updated  # This will be the emit function from the worker
        self.process_complete = process_complete
        self.wait = WebDriverWait(self.driver, 30)
        self.thumbnail_path = None
        self.video_tags = []
        self.browser_manager = BrowserManager()
        self.channel_frame = channel_frame
        self.edit_info_action = edit_info_action
        self.edit_status_action = edit_status_action
        self.current_title = None

    def generate_title(self):
        # Get titles from channel frame's title edit
        titles_text = self.channel_frame.title_edit.toPlainText()
        if not titles_text:
            return "Default Title"
            
        # Split into list and remove empty lines
        titles = [t.strip() for t in titles_text.split('\n') if t.strip()]
        if not titles:
            return "Default Title"
            
        # Select random title
        self.current_title = random.choice(titles)
        return self.current_title

    def generate_description(self):
        # Get description template
        desc_template = self.channel_frame.desc_edit.toPlainText()
        if not desc_template:
            return "Default Description"
            
        # Replace {title} with current random title
        if self.current_title:
            desc = desc_template.replace("{title}", self.current_title)
        else:
            desc = desc_template
            
        return desc

    def upload_thumbnail(self, thumb_wrapper):
        # Get thumbnail directory path
        thumb_dir = self.channel_frame.thumb_path_edit.text()
        if not thumb_dir or not os.path.isdir(thumb_dir):
            return
            
        # Get list of image files
        image_files = []
        for ext in ('*.png', '*.jpg', '*.jpeg'):
            image_files.extend(glob.glob(os.path.join(thumb_dir, ext)))
            
        if not image_files:
            return
            
        # Select random thumbnail
        self.thumbnail_path = random.choice(image_files)
        
        try:
            upload_button = thumb_wrapper.find_element(By.CSS_SELECTOR, "input[type='file']")
            upload_button.send_keys(self.thumbnail_path)
            time.sleep(2)
        except Exception as e:
            print(f"Error uploading thumbnail: {str(e)}")
    
    def navigate_to_studio(self):
        try:
            # Navigate only once
            self.driver.get(YTS.STUDIO_URL)
            self.progress_updated(10, "Vào trang studio.youtube.com")
            time.sleep(1)
            
            # Check login status
            avatar = self.wait.until(EC.visibility_of_element_located((By.XPATH, YTS.AVATAR_BTN)))
            self.progress_updated(20, "Kiểm tra thông tin đăng nhập")
            
            # Wait for page load
            self.wait.until(lambda driver: driver.execute_script("return document.readyState") == "complete")
            
            # Click content tab once
            content_tab = self.wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//a[@id='menu-item-1']") or 
                (By.XPATH, "//tp-yt-paper-icon-item[@id='menu-paper-icon-item-1']")
            ))
            self.driver.execute_script("arguments[0].click();", content_tab)
            self.progress_updated(30, "Chuyển đến trang cotent")
            time.sleep(1)
            
            # Click uploads tab once
            uploads_tab = self.wait.until(EC.element_to_be_clickable((By.ID, "video-list-uploads-tab")))
            self.driver.execute_script("arguments[0].click();", uploads_tab)
            self.progress_updated(40, "Chuyển đến trang Video Upload")
            
            return True
            
        except Exception as e:
            print(f"Navigation error: {str(e)}")
            return False

    def process_draft_videos(self, video_count, schedule_times, schedule_date, is_schedule=True):
        try:
            print(f"Edit info action checked: {self.edit_info_action.isChecked() if self.edit_info_action else 'None'}")
            print(f"Edit status action checked: {self.edit_status_action.isChecked() if self.edit_status_action else 'None'}")
            # Điều hướng đến YouTube Studio
            if not self.navigate_to_studio():
                self.progress_updated(10, "Đăng nhập thất bại chuyển sang kênh khác")
                return False
                
            # Tìm div chứa bảng video
            video_table = self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'div.video-table-content.style-scope.ytcp-video-section-content'))
            )
            
            # Lấy danh sách tất cả các video
            all_videos = video_table.find_elements(By.CSS_SELECTOR, 'ytcp-video-row.style-scope.ytcp-video-section-content')
            
            if not all_videos:
                self.progress_updated(20, "Không tìm thấy video trong danh sách")
                print("Không tìm thấy video nào trong bảng")
                return False
                
            # Tìm các video có nút draft
            draft_videos = []
            for video in all_videos:
                try:
                    draft_button = video.find_element(
                        By.CSS_SELECTOR,
                        "ytcp-button.edit-draft-button.style-scope.ytcp-video-list-cell-actions"
                    )
                    if draft_button:
                        draft_videos.append(video)
                except:
                    continue

            if not draft_videos:
                print("Không tìm thấy video nháp nào")
                self.progress_updated(30, "Không tìm thấy video bản nháp")
                return False

            print(f"Tìm thấy {len(draft_videos)} video nháp")
            self.progress_updated(30, f"Tìm thấy {len(draft_videos)} video nháp")
            
            processed_count = 0
            current_date = schedule_date
            time_index = 0
            
            for video in draft_videos:
                try:
                    edit_button = video.find_element(By.CSS_SELECTOR, "ytcp-button.edit-draft-button")
                    self.driver.execute_script("arguments[0].click();", edit_button)
                    self.progress_updated(60, f"Bắt đầu chỉnh sửa video thứ: {video_count}")
                    time.sleep(1)
                    
                    dialog = self.wait.until(EC.presence_of_element_located(
                        (By.CSS_SELECTOR, ".dialog-content.style-scope.ytcp-uploads-dialog")
                    ))
                    
                    # Kiểm tra thuộc tính trước khi sử dụng
                    if self.edit_info_action is not None and self.edit_info_action.isChecked():
                        self.update_video_details()
                        
                    if hasattr(self, 'edit_status_action') and self.edit_status_action and self.edit_status_action.isChecked():
                        if is_schedule:
                            video_count = self.channel_frame.video_count_spin.value()
                            # Pass the processed_count as current_video_index
                            success = self.set_schedule_visibility(current_date, schedule_times[time_index], video_count, processed_count)
                            
                            # Update time index for next video
                            time_index = (time_index + 1) % len(schedule_times)
                        else:
                            self.set_public_visibility()
                    
                    processed_count += 1
                    
                except Exception as e:
                    print(f"Lỗi khi xử lý video: {str(e)}")
                    continue
                    
            self.process_complete()
            return True
            
        except TimeoutException:
            print("Không thể tải danh sách video - Timeout")
            return False
            
        except Exception as e:
            print(f"Có lỗi xảy ra trong quá trình xử lý: {str(e)}")
            return False

            
        except Exception as e:
            print(f"Lỗi: {str(e)}")
            return False

    def clean_text(self, text):
        # Remove non-BMP characters
        cleaned_text = ''.join(char for char in text if ord(char) < 0x10000)
        # Remove any problematic whitespace
        cleaned_text = ' '.join(cleaned_text.split())
        return cleaned_text

    def clean_text_description(self, text):
        # Remove non-BMP characters
        cleaned_text = ''.join(char for char in text if ord(char) < 0x10000)
        
        # Split by newlines to preserve them
        lines = cleaned_text.split('\n')
        
        # Clean each line individually
        cleaned_lines = []
        for line in lines:
            # Remove extra whitespace within each line
            cleaned_line = ' '.join(line.split())
            cleaned_lines.append(cleaned_line)
        
        # Rejoin with newlines
        return '\n'.join(cleaned_lines)

    def update_video_details(self):
        try:
            # Wait for dialog to be fully loaded
            self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".dialog-content.style-scope.ytcp-uploads-dialog")))
            time.sleep(2)

            # Get video link
            try:
                span_element = self.driver.find_element(By.XPATH, "//span[@class='video-url-fadeable style-scope ytcp-video-info']")
                a_element = span_element.find_element(By.TAG_NAME, "a")
                video_link = a_element.get_attribute("href")
                print(f"Found video link: {video_link}")
            except Exception as e:
                print(f"Không lấy được link video: {e}")
                video_link = ''

            # Update title with length control and character cleaning
            title_input = self.wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, "#title-textarea #textbox")
            ))
            self.driver.execute_script("arguments[0].click();", title_input)
            self.driver.execute_script("arguments[0].value = '';", title_input)
            title_input.clear()
            
            # Generate, clean and truncate title
            title = self.generate_title()
            title = self.clean_text(title)
            if len(title) > 100:
                title = title[:100]
            print(f"Processed title: {title}")    
            title_input.send_keys(title)
            self.progress_updated(60, "Đã cập nhật tiêu đề")

            # Update description with link integration and character cleaning
            desc_input = self.wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, "#description-textarea #textbox")
            ))
            self.driver.execute_script("arguments[0].click();", desc_input)
            self.driver.execute_script("arguments[0].value = '';", desc_input)
            desc_input.clear()
            
            description = self.generate_description()
            description = self.clean_text_description(description)
            description = description.replace("{link}", video_link)
            print(f"Processed description length: {len(description)}")
            desc_input.send_keys(description)
            self.progress_updated(70, "Đã cập nhật mô tả")

            # Handle thumbnail
            thumb_wrapper = self.wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, "div#custom-still-editor-wrapper")
            ))
            if self.thumbnail_path:
                self.upload_thumbnail(thumb_wrapper)
                self.progress_updated(80, "Đã cập nhật thumbnail")

            # Set Made for Kids
            not_for_kids = self.wait.until(EC.element_to_be_clickable(
                (By.CSS_SELECTOR, 'tp-yt-paper-radio-button[name="VIDEO_MADE_FOR_KIDS_NOT_MFK"]')
            ))
            self.driver.execute_script("arguments[0].click();", not_for_kids)
            self.progress_updated(90, "Đã cài đặt Made for Kids")

            # Add tags
            self.add_video_tags()
            self.progress_updated(95, "Đã thêm tags")

            return True

        except Exception as e:
            print(f"Lỗi khi cập nhật thông tin video: {str(e)}")
            return False

    def add_video_tags(self):
        try:
            # Mở rộng phần tags
            toggle_button = self.wait.until(EC.element_to_be_clickable(
                (By.CSS_SELECTOR, 'ytcp-button#toggle-button')
            ))
            self.driver.execute_script("arguments[0].click();", toggle_button)
            time.sleep(1)
            
            # Nhập tags
            tags_container = self.wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, 'ytcp-form-input-container#tags-container')
            ))
            tags_input = tags_container.find_element(By.CSS_SELECTOR, 'input')
            
            for tag in self.video_tags:
                tags_input.send_keys(tag)
                tags_input.send_keys(Keys.ENTER)
                time.sleep(0.5)
                
            return True
        except Exception as e:
            print(f"Lỗi khi thêm tags: {str(e)}")
            return False

    def set_schedule_visibility(self, date, time_str, video_count, current_video_index):
        try:
            # Click tabs in order
            for step_id in ["step-badge-1", "step-badge-2", "step-badge-3"]:
                step_button = self.wait.until(EC.element_to_be_clickable((By.ID, step_id)))
                self.driver.execute_script("arguments[0].click();", step_button)
                print(step_id)
                self.progress_updated(70, "kiểm tra các bước để chỉnh sửa video")
                time.sleep(1)

            # Get page language
            html_element = self.driver.find_element(By.TAG_NAME, "html")
            page_lang = html_element.get_attribute("lang").lower()
            
            # Format date based on language
            if "vi" or "en-GB" in page_lang:
                formatted_date = date.toString("dd thg M, yyyy")  # For Vietnamese: "25 thg 2, 2024"
            else:
                formatted_date = date.toString("MMM dd, yyyy")    # For English: "Feb 25, 2024"
                
            print(f"Page language: {page_lang}")
            print(f"Formatted date: {formatted_date}")

            if current_video_index > 0 and current_video_index % video_count == 0:
                date = date.addDays(1)

            # Set schedule
            schedule_button = self.wait.until(EC.element_to_be_clickable(
                (By.XPATH, '//ytcp-icon-button[@id="second-container-expand-button"]')
            ))
            self.driver.execute_script("arguments[0].click();", schedule_button)
            time.sleep(2)

            # Click date picker
            date_picker = self.wait.until(EC.element_to_be_clickable(
                (By.CSS_SELECTOR, "#datepicker-trigger.style-scope.ytcp-datetime-picker")
            ))
            self.driver.execute_script("arguments[0].click();", date_picker)
            self.progress_updated(75, "Chọn Ngày tháng đặt lịch")
            time.sleep(2)

            # Input date
            date_input = self.wait.until(EC.visibility_of_element_located(
                (By.CSS_SELECTOR, 'tp-yt-paper-input[id="textbox"][class="style-scope ytcp-date-picker"]')
            ))
            self.driver.execute_script("arguments[0].value = '';", date_input)
            date_input.send_keys(formatted_date)
            date_input.send_keys(Keys.ENTER)
            self.progress_updated(80, f"Nhập ngày public {formatted_date}")
            time.sleep(1)

            # Rest of your code remains the same...
            time_input = self.wait.until(EC.visibility_of_element_located(
                (By.XPATH, '//div[@id="child-input"]//input[@class="style-scope tp-yt-paper-input"]')
            ))
            self.driver.execute_script("arguments[0].value = '';", time_input)
            time_input.send_keys(time_str)
            time_input.send_keys(Keys.ENTER)
            self.progress_updated(85, f"Nhập giờ đặt lịch {time_str}")
            time.sleep(1)

            # Click Done button
            done_button = self.wait.until(EC.element_to_be_clickable(
                (By.CSS_SELECTOR, '#done-button')
            ))
            self.driver.execute_script("arguments[0].click();", done_button)
            self.progress_updated(90, "Đặt lịch cho video")
            time.sleep(2)

            # Handle close buttons
            try:
                close_button = self.wait.until(EC.presence_of_element_located((By.XPATH, "//ytcp-icon-button[@id='close-icon-button']")))
                close_button.click()
                time.sleep(5)
            except Exception as e:
                print(f"Không tìm thấy thành phần Close Info trong multiple_upload: {e}")
                try:
                    close_button = self.wait.until(EC.presence_of_element_located((By.XPATH, "//ytcp-button[@id='close-button'][contains(@class, 'style-scope ytcp-video-share-dialog')]")))
                    close_button.click()
                    self.progress_updated(95, "Đặt lịch cho video thành công")
                    time.sleep(5)
                except Exception as e:
                    print(f"close info: {e}")
                    try:
                        close_button = self.wait.until(EC.presence_of_element_located((By.XPATH,  "//ytcp-button[@id='close-icon-button']")))
                        close_button.click()
                        time.sleep(5)
                    except Exception as e:
                        print(f"close info: {e}")

            return True

        except Exception as e:
            print(f"Schedule setting error: {str(e)}")
            return False

    def on_edit_complete(self):
        QMessageBox.information(self, "Thông báo", "Đã hoàn thành chỉnh sửa video!")
        self.edit_video_worker = None

class DragDropListWidget(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            for url in urls:
                file_path = url.toLocalFile()
                if file_path.lower().endswith(('.mp4', '.avi', '.mkv')):
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        files = [url.toLocalFile() for url in event.mimeData().urls()]
        self.parent().add_files_to_list(files)
        event.acceptProposedAction()

class AntiBQManagerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Quản lý nội dung kháng BQ")
        self.setMinimumWidth(800)
        self.setMinimumHeight(600)
        self.init_ui()
        self.load_saved_content()

    def init_ui(self):
        layout = QVBoxLayout()

        # Input section
        input_group = QGroupBox("Nhập nội dung mới")
        input_layout = QVBoxLayout()

        # Title input
        title_layout = QHBoxLayout()
        title_layout.addWidget(QLabel("Tiêu đề video:"))
        self.title_edit = QLineEdit()
        title_layout.addWidget(self.title_edit)

        # Content input
        content_layout = QVBoxLayout()
        content_layout.addWidget(QLabel("Nội dung kháng:"))
        self.content_edit = QTextEdit()
        content_layout.addWidget(self.content_edit)

        # Buttons
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("Lưu")
        clear_btn = QPushButton("Xóa trắng")
        save_btn.clicked.connect(self.save_content)
        clear_btn.clicked.connect(self.clear_fields)
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(clear_btn)

        input_layout.addLayout(title_layout)
        input_layout.addLayout(content_layout)
        input_layout.addLayout(btn_layout)
        input_group.setLayout(input_layout)

        # Saved content list
        list_group = QGroupBox("Danh sách nội dung đã lưu")
        list_layout = QVBoxLayout()
        self.content_list = QListWidget()
        self.content_list.itemClicked.connect(self.load_content)
        
        # Delete and edit buttons
        control_layout = QHBoxLayout()
        edit_btn = QPushButton("Sửa")
        delete_btn = QPushButton("Xóa")
        edit_btn.clicked.connect(self.edit_content)
        delete_btn.clicked.connect(self.delete_selected)
        control_layout.addWidget(edit_btn)
        control_layout.addWidget(delete_btn)

        list_layout.addWidget(self.content_list)
        list_layout.addLayout(control_layout)
        list_group.setLayout(list_layout)

        # Add all components
        layout.addWidget(input_group)
        layout.addWidget(list_group)
        self.setLayout(layout)

    def save_content(self):
        title = self.title_edit.text().strip()
        content = self.content_edit.toPlainText().strip()
        
        if not title or not content:
            QMessageBox.warning(self, "Lỗi", "Vui lòng nhập đầy đủ tiêu đề và nội dung!")
            return

        data = self.load_data()
        data[title] = content
        self.save_data(data)
        self.update_content_list()
        self.clear_fields()
        QMessageBox.information(self, "Thành công", "Đã lưu nội dung!")

    def edit_content(self):
        current_item = self.content_list.currentItem()
        if current_item:
            title = current_item.text()
            data = self.load_data()
            if title in data:
                self.title_edit.setText(title)
                self.content_edit.setText(data[title])

    def delete_selected(self):
        current_item = self.content_list.currentItem()
        if current_item:
            reply = QMessageBox.question(self, 'Xác nhận', 
                                       'Bạn có chắc muốn xóa nội dung này?',
                                       QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                title = current_item.text()
                data = self.load_data()
                if title in data:
                    del data[title]
                    self.save_data(data)
                    self.update_content_list()
                    self.clear_fields()

    def load_data(self):
        try:
            with open('anti_bq_content.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    def get_content_for_title(self, video_title):
        data = self.load_data()
        # Tìm nội dung phù hợp nhất dựa trên tiêu đề video
        for saved_title, content in data.items():
            if video_title.lower().find(saved_title.lower()) != -1:
                return content
        return None

    def save_data(self, data):
        with open('anti_bq_content.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def update_content_list(self):
        self.content_list.clear()
        data = self.load_data()
        self.content_list.addItems(sorted(data.keys()))

    def clear_fields(self):
        self.title_edit.clear()
        self.content_edit.clear()

    def load_content(self, item):
        title = item.text()
        data = self.load_data()
        if title in data:
            self.title_edit.setText(title)
            self.content_edit.setText(data[title])

    def load_saved_content(self):
        """Load and display previously saved content in the list"""
        try:
            data = self.load_data()
            self.content_list.clear()
            self.content_list.addItems(sorted(data.keys()))
        except Exception as e:
            QMessageBox.warning(self, "Lỗi", f"Không thể tải nội dung đã lưu: {str(e)}")

class AntiBQWorker(QThread):
    progress_updated = pyqtSignal(int, str)
    process_complete = pyqtSignal()
    error_occurred = pyqtSignal(str)
    request_input = pyqtSignal(str, str)
    request_confirmation = pyqtSignal(str, str)
    input_received = pyqtSignal(str)
    confirmation_received = pyqtSignal(bool)
    show_continue_dialog = pyqtSignal(str)
    countdown_updated = pyqtSignal(int)  # Add this signal

    def __init__(self, channel_frame, manager):
        super().__init__()
        self.setup_logger()
        self.channel_frame = channel_frame
        self.manager = manager
        self.driver = None
        self.anti_bq_queue = [channel_frame]
        self.is_browser_hidden = False
        self.input_text = None
        self.confirmation_result = None
        show_continue_dialog = pyqtSignal(str, name='showContinueDialog')
        self.browser_manager = BrowserManager()
        self.uploadYoutubeTab = UploadYoutubeTab()

    def setup_logger(self):
        self.logger = logging.getLogger('AntiBQWorker')
        self.logger.setLevel(logging.INFO)
        
        # Create console handler
        handler = logging.StreamHandler()
        handler.setLevel(logging.INFO)
        
        # Create formatter
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        
        # Add handler to logger if it doesn't already have one
        if not self.logger.handlers:
            self.logger.addHandler(handler)

    def set_anti_bq_queue(self, queue):
        self.anti_bq_queue = queue

    def get_dispute_text(self, claim_title):
        data = self.manager.load_data()
        
        for saved_title, content in data.items():
            if saved_title.lower() in claim_title.lower():
                return content
                
        # Emit signals and wait for response
        self.request_confirmation.emit(
            "Nội dung kháng cáo không tìm thấy",
            f"Không tìm thấy nội dung kháng cáo cho video '{claim_title}'.\nBạn có muốn thêm nội dung mới không?"
        )
        
        # Use event loop to wait for response
        loop = QEventLoop()
        self.confirmation_received.connect(loop.quit)
        loop.exec_()
        
        if self.confirmation_result:
            self.request_input.emit(
                "Nhập nội dung kháng cáo",
                f"Nhập nội dung kháng cáo cho video '{claim_title}':"
            )
            
            # Wait for input
            loop = QEventLoop()
            self.input_received.connect(loop.quit)
            loop.exec_()
            
            if self.input_text:
                data[claim_title] = self.input_text
                self.manager.save_data(data)
                return self.input_text
                
        return None

    def match_claim_title(self, claim_title):
        # Load saved content data
        data = self.manager.load_data()
        
        # Try to find matching title
        for saved_title in data.keys():
            if saved_title.lower() in claim_title.lower():
                return True
        return False

    def run(self):
        process_complete = pyqtSignal()  # Thêm signal này

        try:            
            if self.channel_frame.anti_bq_firefox_radio.isChecked():
                print("Using Firefox for Anti-BQ")
                selected_profile = self.channel_frame.profile_combo.currentText()
                profile_id = self.channel_frame.profiles_dict[selected_profile]
                self.driver = self.browser_manager.setup_firefox(profile_id)
            else:
                # Validate Chrome path before setup
                chrome_path = self.channel_frame.anti_bq_chrome_path_edit.text().strip()
                print(f"Chrome path for validation: {chrome_path}")
                
                if not chrome_path:
                    raise Exception("Chrome path is empty. Please select Chrome executable file")
                if not os.path.exists(chrome_path):
                    raise Exception(f"Chrome file not found at: {chrome_path}")
                if not chrome_path.lower().endswith('.exe'):
                    raise Exception("Selected file must be an executable (.exe) file")
                    
                print("Chrome path validated successfully")
                self.driver = self.browser_manager.setup_chrome(chrome_path)
                #self.channel_frame.toggle_browser_btn.setEnabled(True)
            self.process_anti_bq()
            self.process_complete.emit()  # Emit signal khi hoàn thành
        except Exception as e:
            self.error_occurred.emit(str(e))
        finally:
            if self.driver:
                self.driver.quit()
            #self.channel_frame.toggle_browser_btn.setEnabled(False)

    def process_anti_bq(self):
        if not self.anti_bq_queue:
            raise Exception("Anti BQ queue is empty")
            
        wait = WebDriverWait(self.driver, 10)
        
        try:
            # 1. Navigate to YouTube Studio
            self.driver.get(YTS.STUDIO_URL)
            self.progress_updated.emit(10, "Đang truy cập trang Content")
            
            # 2. Check login with safe element finding
            try:
                avatar = wait.until(EC.visibility_of_element_located((By.XPATH, YTS.AVATAR_BTN)))
                self.progress_updated.emit(20, "Đăng nhập thành công")
            except TimeoutException:
                self.handle_login_failure()
                return
                
            # 3. Navigate to content tab safely
            if not self.navigate_to_content_tab(wait):
                return
                
            # 4. Click Uploads tab with retry
            if not self.navigate_to_uploads_tab(wait):
                return
                
            # 5. Process videos with improved error handling
            current_page = 1
            found_bq = False
            all_pages_checked = False
            
            while not all_pages_checked:
                try:
                    video_list = wait.until(EC.presence_of_element_located(
                        (By.CSS_SELECTOR, YTS.VIDEO_LIST)
                    ))
                    video_rows = video_list.find_elements(By.CSS_SELECTOR, YTS.VIDEO_ROW)
                    
                    # Check for BQ content
                    has_bq_content = self.check_for_bq_content(video_rows, wait)
                    if has_bq_content:
                        found_bq = True
                        self.process_video_rows(video_rows, wait)
                    
                    # Check if we should continue to next page
                    if self.has_next_page():
                        self.go_to_next_page()
                        current_page += 1
                    else:
                        all_pages_checked = True
                        
                    # If no BQ found after checking all pages
                    if all_pages_checked and not found_bq:
                        self.request_confirmation.emit(
                            "Thông báo",
                            "Không tìm thấy nội dung BQ nào trên kênh này. Chuyển sang kênh tiếp theo?"
                        )
                        self.uploadYoutubeTab.show_confirmation_dialog()
                        
                except Exception as e:
                    print(f"Error processing page {current_page}: {str(e)}")
                    all_pages_checked = True
                    
            self.process_complete.emit()
            
        except Exception as e:
            print(f"Critical error: {str(e)}")
            traceback.print_exc()
            raise

    def navigate_to_content_tab(self, wait):
        try:
            # Đợi trang load hoàn toàn
            wait.until(lambda driver: driver.execute_script("return document.readyState") == "complete")
            time.sleep(2)  # Đợi thêm 2 giây cho UI render

            # In ra URL hiện tại để debug
            print(f"Current URL: {self.driver.current_url}")
            
            # Thử tìm bằng cả hai cách
            try:
                content_tab = wait.until(EC.element_to_be_clickable((By.XPATH, "//a[@id='menu-item-1']")))
            except:
                content_tab = wait.until(EC.element_to_be_clickable((By.XPATH, "//tp-yt-paper-icon-item[@id='menu-paper-icon-item-1']")))

            # Scroll đến element
            self.driver.execute_script("arguments[0].scrollIntoView(true);", content_tab)
            time.sleep(1)

            # Click bằng JavaScript
            self.driver.execute_script("arguments[0].click();", content_tab)
            
            self.progress_updated.emit(30, "Đang chuyển vào trang content")
            return True
            
        except TimeoutException as e:
            print(f"Content tab error: {str(e)}")
            # In ra source HTML để debug
            print("Page source:", self.driver.page_source)
            return False

    def navigate_to_uploads_tab(self, wait):
        try:
            # Đợi trang load hoàn toàn
            wait.until(lambda driver: driver.execute_script("return document.readyState") == "complete")
            time.sleep(2)

            # Tìm uploads tab bằng ID
            uploads_tab = wait.until(EC.element_to_be_clickable((By.ID, "video-list-uploads-tab")))
            
            # Scroll đến element và click
            self.driver.execute_script("arguments[0].scrollIntoView(true);", uploads_tab)
            self.driver.execute_script("arguments[0].click();", uploads_tab)
            
            self.progress_updated.emit(40, "Đang chuyển vào trang danh sách video")
            return True
            
        except TimeoutException:
            print("Uploads tab not found or not clickable")
            return False

    def check_for_bq_content(self, video_rows, wait):
        for row in video_rows:
            try:
                restriction_elem = row.find_element(By.ID, YTS.RESTRICTIONS_TEXT)
                restriction_text = restriction_elem.text.strip()
                if restriction_text in YTS.COPYRIGHT_TEXTS:
                    return True
            except NoSuchElementException:
                continue
        return False

    def process_video_rows(self, video_rows, wait):
        for index, row in enumerate(video_rows):
            try:
                self.progress_updated.emit(75, f"Processing video {index + 1}/{len(video_rows)}")
                restriction_elem = row.find_element(By.ID, YTS.RESTRICTIONS_TEXT)
                
                if not restriction_elem:
                    continue
                    
                restriction_text = restriction_elem.text.strip()
                if restriction_text in YTS.COPYRIGHT_TEXTS:
                    self.handle_copyright_restriction(row, restriction_elem, wait)
                    
            except NoSuchElementException:
                continue
            except Exception as e:
                print(f"Error processing video {index + 1}: {str(e)}")
                continue
                
            time.sleep(1)

    def handle_copyright_restriction(self, row, restriction_elem, wait):
        try:
            self.progress_updated.emit(75, "Tìm thấy bản quyền, Đang xử lý...")
            self.driver.execute_script(
                "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", 
                restriction_elem
            )
            time.sleep(2)
            
            restriction_elem.click()
            time.sleep(1)
            
            see_details = wait.until(EC.element_to_be_clickable(
                (By.XPATH, YTS.SEE_DETAIL_BUTTON)
            ))
            see_details.click()
            
            self.process_copyright_claims()
        except Exception as e:
            print(f"Error handling copyright restriction: {str(e)}")

    def update_countdown(self, seconds):
        self.status_label.setText(f"Tự động chuyển kênh sau {seconds}s. Click vào page tiếp theo để tiếp tục kháng")

    def process_copyright_claims(self):
        wait = WebDriverWait(self.driver, 10)
        
        try:
            while True:
                # Check if claims container exists
                try:
                    claims_container = wait.until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, YTS.CLAIMS_CONTAINER))
                    )
                except TimeoutException:
                    self.logger.info("Video đã kháng BQ - Đang chờ kết quả")
                    return True
                    
                # Check for claim rows
                try:
                    claim_rows = wait.until(
                        EC.presence_of_all_elements_located((By.XPATH, YTS.CLAIM_ROW))
                    )
                    self.logger.info(f"Found {len(claim_rows)} claim rows")
                except TimeoutException:
                    self.logger.info("No claim rows found - container may be empty")
                    return True
                    
                unprocessed_found = False
                processed_count = 0
                total_claims = len(claim_rows)
                
                for row in claim_rows:
                    try:
                        # Check if claim already processed
                        dispute_status = row.find_elements(By.CSS_SELECTOR, YTS.DISPUTE_STATUS)
                        if dispute_status:
                            processed_count += 1
                            continue
                            
                        unprocessed_found = True
                        self.logger.info(f"Processing claim {processed_count + 1}/{total_claims}")
                        self.progress_updated.emit(75, f"Processing claim {processed_count + 1}/{total_claims}")
                        
                        # Safely scroll and get asset title
                        self.driver.execute_script("arguments[0].scrollIntoView(true);", row)
                        time.sleep(1)
                        
                        try:
                            asset_title = row.find_element(By.CSS_SELECTOR, YTS.ASSET_TITLE).text
                            self.logger.info(f"Processing claim: {asset_title}")
                        except NoSuchElementException:
                            asset_title = "Unknown Asset"
                            
                        # Click action button with improved retry
                        action_button = self.retry_find_element(
                            row, 
                            By.CSS_SELECTOR, 
                            YTS.ACTIONS_BUTTON,
                            max_retries=3
                        )
                        if action_button:
                            self.driver.execute_script("arguments[0].click();", action_button)
                            time.sleep(2)
                        else:
                            continue
                        
                        # Handle dispute with retry
                        if not self.retry_handle_dispute(asset_title):
                            continue
                            
                        break  # Successfully processed one claim
                        
                    except Exception as e:
                        self.logger.error(f"Error processing claim: {str(e)}")
                        self.recover_from_error()
                        continue
                
                if not unprocessed_found:
                    self.logger.info("All claims processed")
                    if not self.close_claims_dialog(wait):
                        return False
                        
                time.sleep(2)
                
        except Exception as e:
            self.logger.error(f"Critical error in process_copyright_claims: {str(e)}")
            raise Exception(f"Lỗi xử lý claim: {str(e)}")
            
        return True

    def retry_find_element(self, parent, by, selector, max_retries=3):
        for attempt in range(max_retries):
            try:
                return parent.find_element(by, selector)
            except NoSuchElementException:
                if attempt == max_retries - 1:
                    return None
                time.sleep(1)
        return None

    def retry_handle_dispute(self, asset_title, max_retries=3):
        for attempt in range(max_retries):
            try:
                self.handle_dispute_popup(asset_title)
                return True
            except Exception as e:
                if attempt == max_retries - 1:
                    self.logger.error(f"Failed to handle dispute after {max_retries} attempts")
                    return False
                time.sleep(2)
        return False

    def recover_from_error(self):
        try:
            actions = ActionChains(self.driver)
            actions.send_keys(Keys.ESCAPE).perform()
            time.sleep(2)
        except:
            pass

    def close_claims_dialog(self, wait):
        for attempt in range(3):
            try:
                close_button = wait.until(EC.element_to_be_clickable((
                    By.CSS_SELECTOR, 
                    YTS.CLOSE_DIALOG
                )))
                self.driver.execute_script("arguments[0].scrollIntoView(true);", close_button)
                time.sleep(1)
                self.driver.execute_script("arguments[0].click();", close_button)
                return True
            except Exception:
                if attempt == 2:
                    self.logger.error("Failed to close claims dialog")
                    return False
                time.sleep(2)
        return False

    def handle_dispute_popup(self, asset_title):
        wait = WebDriverWait(self.driver, 10)
        
        try:
            # Click dispute option
            dispute_option = wait.until(EC.visibility_of_element_located((
                By.XPATH, 
                YTS.DISPUTE_OPTION
            )))
            dispute_option.click()
            print(" Select Option Dispute")
            self.progress_updated.emit(80, "Thực hiện Click Option Dispute")
            time.sleep(1)

            # Click confirm 
            try:
                confirm_btn = wait.until(EC.visibility_of_element_located((
                    By.XPATH, YTS.CONFIRM_BUTTON
                )))
            except:
                confirm_btn = wait.until(EC.visibility_of_element_located((
                    By.XPATH, YTS.CONTINUE_BUTTON
                )))
            confirm_btn.click()
            print("Click button to next step")
            self.progress_updated.emit(80, "Thực hiện Click button to next step")
            time.sleep(1)

            # Click continue Overview
            confirm_btn_Overview = wait.until(EC.visibility_of_element_located((
                By.XPATH,YTS.CONTINUE_BUTTON
            )))
            confirm_btn_Overview.click()
            print("Click button on Overview")
            self.progress_updated.emit(80, "Thực hiện Click button on Overview")
            time.sleep(1)

            #Radio button list select
            radio_btn_list = wait.until(EC.visibility_of_element_located((By.XPATH, YTS.RADIO_GROUP)))
            second_radio = radio_btn_list.find_element(By.XPATH, YTS.LICENSE_RADIO_BUTTON)
            second_radio.click()
            print("Select License radio button")
            self.progress_updated.emit(80, "Thực hiện Click Select License radio button")
            time.sleep(1)  

            # Click continue Reason
            confirm_btn_Reason = wait.until(EC.visibility_of_element_located((
                By.XPATH, YTS.CONTINUE_BUTTON
            )))
            confirm_btn_Reason.click()
            print("Click button next in Reason")
            self.progress_updated.emit(80, "Thực hiện Click button next in Reason")
            time.sleep(1)

            #Review check box tick
            review_checkbox = wait.until(EC.visibility_of_element_located((By.XPATH, YTS.REVIEW_CHECKBOX)))
            review_checkbox.click()
            print("click CheckBox accept")
            self.progress_updated.emit(80, "Thực hiện click CheckBox accept")
            time.sleep(1)

            # Click continue Details
            continue_btn_Details = wait.until(EC.visibility_of_element_located((
                By.XPATH, YTS.CONTINUE_BUTTON
            )))
            continue_btn_Details.click()
            print("Click button Next in Details")
            self.progress_updated.emit(80, "Thực hiện Click button Next in Details")
            time.sleep(1)

            dispute_text = self.get_dispute_text(asset_title)
            if not dispute_text:
                # Show dialog to get new content from user
                reply = QMessageBox.question(
                    None,
                    "Nội dung kháng cáo không tìm thấy",
                    f"Không tìm thấy nội dung kháng cáo cho video '{asset_title}'.\nBạn có muốn thêm nội dung mới không?",
                    QMessageBox.Yes | QMessageBox.No
                )
                
                if reply == QMessageBox.Yes:
                    dialog = QInputDialog()
                    dialog.setWindowTitle("Nhập nội dung kháng cáo")
                    dialog.setLabelText(f"Nhập nội dung kháng cáo cho video '{asset_title}':")
                    dialog.resize(500, 200)
                    
                    if dialog.exec_():
                        dispute_text = dialog.textValue()
                        # Save new content
                        data = self.manager.load_data()
                        data[asset_title] = dispute_text
                        self.manager.save_data(data)
                    else:
                        print(f"Skipping dispute - user cancelled input for: {asset_title}")
                        return
                else:
                    print(f"Skipping dispute - no content provided for: {asset_title}")
                    self.uploadYoutubeTab.show_confirmation_dialog()

            # Continue with the dispute process
            textarea = wait.until(EC.visibility_of_element_located((
                By.XPATH, YTS.RATIONALE_TEXTAREA
            )))
            textarea.click()
            textarea.clear()
            textarea.send_keys(dispute_text)
            print("insert content coppyright to text area")
            self.progress_updated.emit(80, "Nhập thông tin BQ")
            
            # Find all checkboxes first
            checkboxes = wait.until(EC.presence_of_all_elements_located((
                By.XPATH, YTS.FORM_CHECKBOXES
            )))

            # Click each checkbox in order
            for i, checkbox in enumerate(checkboxes[:3]):  # Limit to first 3 checkboxes
                print(f"Clicking checkbox {i+1}")
                self.progress_updated.emit(80, f"Clicking checkbox {i+1}")
                checkbox.click()
                time.sleep(1)

            # Fill signature
            signature = wait.until(EC.presence_of_element_located(
                (By.ID, YTS.SIGNATURE_FIELD)))
            signature.send_keys("Khanhtbk")
            print("Đã nhập signature")
            self.progress_updated.emit(80, "Nhập Chữ ký")
            
            # Submit dispute
            submit_btn = wait.until(EC.element_to_be_clickable(
                (By.ID, YTS.SUBMIT_BUTTON)))
            submit_btn.click()
            print("Click button accept")
            self.progress_updated.emit(80, "Click button accept")
        
            max_retries = 3
            retry_count = 0

            while retry_count < max_retries:
                try:
                    close_Dispute_submitted = wait.until(EC.element_to_be_clickable((
                        By.XPATH, YTS.CLOSE_SUMBITIED_DISPUTE
                    )))
                    self.driver.execute_script("arguments[0].click();", close_Dispute_submitted)
                    time.sleep(3)
                    
                    # Kiểm tra nếu nút close đã biến mất
                    try:
                        wait.until_not(EC.presence_of_element_located((
                            By.XPATH, YTS.CLOSE_SUMBITIED_DISPUTE
                        )))
                        print("Close button successfully disappeared")
                        self.progress_updated.emit(80, "Close button successfully disappeared")
                        break
                    except TimeoutException:
                        retry_count += 1
                        if retry_count == max_retries:
                            # Thử phương án khác nếu không click được
                            actions = ActionChains(self.driver)
                            actions.send_keys(Keys.ESCAPE).perform()
                            time.sleep(1)
                except Exception:
                    break

        except Exception as e:
            raise Exception(f"Lỗi khi xử lý dispute popup: {str(e)}")

    def has_next_page(self):
        try:
            # Find the next page button
            next_button = self.driver.find_element(
                By.XPATH, 
                YTS.NEXT_PAGE_CONTINUE
            )
            
            # Check if button is enabled
            return 'disabled' not in next_button.get_attribute('class')
        except:
            return False

    def go_to_next_page(self):
        next_button = self.driver.find_element(
            By.XPATH, 
            YTS.NEXT_PAGE_CONTINUE
        )
        next_button.click()
        time.sleep(2)  # Wait for page load

    def show_continue_dialog(self, message):
        reply = QMessageBox.question(self, 'Tiếp tục?', message,
                                   QMessageBox.Yes | QMessageBox.No)
        return reply == QMessageBox.Yes

    def show_confirmation_dialog(self, title, message):
        reply = QMessageBox.question(self, title, message,
                                   QMessageBox.Yes | QMessageBox.No)
        return reply == QMessageBox.Yes
