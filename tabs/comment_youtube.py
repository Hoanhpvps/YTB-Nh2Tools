from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtCore import QObject, pyqtSignal
import threading
import time
import os
import psutil
import shutil
import random
import win32api
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from win32con import CREATE_NO_WINDOW


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

    def setup_chrome_portable(self, portable_path):
        try:
            chrome_version = self.get_chrome_version(portable_path)
            self.close_webdriver_processes()
            time.sleep(2)

            chrome_exe = os.path.join(os.path.dirname(portable_path), 'App', 'Chrome-bin', 'chrome.exe')
            if not os.path.exists(chrome_exe):
                raise Exception("Chrome.exe not found in Portable directory")

            options = webdriver.ChromeOptions()
            options.binary_location = chrome_exe
            
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--remote-debugging-port=9222')
            options.add_argument('--start-maximized')
            
            data_dir = os.path.join(os.path.dirname(portable_path), 'Data')
            if os.path.exists(data_dir):
                options.add_argument(f'--user-data-dir={data_dir}')

            driver_path = self.download_chromedriver(chrome_version)
            service = Service(executable_path=driver_path)
            service.creation_flags = CREATE_NO_WINDOW

            self.driver = webdriver.Chrome(service=service, options=options)
            self.driver.set_window_size(1320, 960)
            return self.driver

        except Exception as e:
            raise Exception(f"Failed to initialize Chrome Portable: {str(e)}")

    def quit(self):
        self.cleanup_driver()

class comment_youtube(QWidget):
    def __init__(self):
        super().__init__()
        self.groups = []
        self.comment_manager = CommentManager()
        # Kết nối signal với slot
        self.comment_manager.progress_updated.connect(self.update_progress)
        self.comment_manager.task_completed.connect(self.on_task_completed)
        self.comment_manager.error_occurred.connect(self.show_error)
        
        # Initialize UI elements as class attributes
        self.video_links = None
        self.comments = None
        self.firefox_radio = None
        self.chrome_radio = None
        self.profile_combo = None
        self.chrome_path = None
        self.time_min = None
        self.time_max = None
        self.like_cb = None
        self.subscribe_cb = None
        self.random_cb = None
        
        self.init_ui()
        
    def init_ui(self):
        # Main vertical layout
        main_layout = QVBoxLayout()
        
        # Create scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        # Container widget for scroll area
        container = QWidget()
        container_layout = QVBoxLayout()
        
        # Horizontal layout for panels
        panels_layout = QHBoxLayout()
        
        # Add left and right panels
        left_panel = self.create_left_panel()
        panels_layout.addLayout(left_panel, stretch=50)
        
        self.right_panel = QWidget()
        right_layout = self.create_right_panel()
        self.right_panel.setLayout(right_layout)
        panels_layout.addWidget(self.right_panel, stretch=50)
        
        # Add panels to container
        container_layout.addLayout(panels_layout)
        container.setLayout(container_layout)
        
        # Set container as scroll area widget
        scroll.setWidget(container)
        
        # Add scroll area and bottom panel to main layout
        main_layout.addWidget(scroll)
        main_layout.addLayout(self.create_bottom_panel())
        
        self.setLayout(main_layout)
        self.connect_signals()
      
    def create_left_panel(self):
        left_layout = QVBoxLayout()
        
        # Video Links Group
        video_group = QGroupBox("Danh sách link video")
        video_layout = QVBoxLayout()
        self.video_links = QTextEdit()  # Assign to class attribute
        self.video_links.setObjectName("video_links")
        self.video_links.setPlaceholderText("Nhập link video (mỗi video một dòng)")
        video_layout.addWidget(self.video_links)
        video_group.setLayout(video_layout)
        
        # Comments Group
        comment_group = QGroupBox("Nội dung comment")
        comment_layout = QVBoxLayout()
        self.comments = QTextEdit()  # Assign to class attribute
        self.comments.setObjectName("comments")
        self.comments.setPlaceholderText("Nhập nội dung comment (phân cách bằng Enter)")
        comment_layout.addWidget(self.comments)
        comment_group.setLayout(comment_layout)
        
        left_layout.addWidget(video_group)
        left_layout.addWidget(comment_group)
        return left_layout
       
    def create_right_panel(self):
        right_layout = QVBoxLayout()
        
        # Browser Selection Group
        browser_group = QGroupBox("Chọn trình duyệt")
        browser_layout = QVBoxLayout()
        
        self.browser_type = QButtonGroup()
        self.firefox_radio = QRadioButton("Firefox Profile")
        self.chrome_radio = QRadioButton("Chrome Portable")
        self.browser_type.addButton(self.firefox_radio)
        self.browser_type.addButton(self.chrome_radio)
        self.chrome_radio.setChecked(True)
        
        # Firefox Profile Frame
        self.firefox_frame = QFrame()
        firefox_layout = QVBoxLayout()
        self.profile_combo = QComboBox()
        firefox_layout.addWidget(self.profile_combo)
        self.firefox_frame.setLayout(firefox_layout)
        self.firefox_frame.hide()
        
        # Chrome Frame
        self.chrome_frame = QFrame()
        chrome_layout = QVBoxLayout()
        self.chrome_path = QLineEdit()
        self.chrome_path.setObjectName("chrome_path")
        self.chrome_btn = QPushButton("Chọn File Chrome")
        self.chrome_btn.setObjectName("chrome_btn")
        chrome_layout.addWidget(self.chrome_path)
        chrome_layout.addWidget(self.chrome_btn)
        self.chrome_frame.setLayout(chrome_layout)
        
        browser_layout.addWidget(self.firefox_radio)
        browser_layout.addWidget(self.firefox_frame)
        browser_layout.addWidget(self.chrome_radio)
        browser_layout.addWidget(self.chrome_frame)
        browser_group.setLayout(browser_layout)
        
        # Time range group
        time_group = QGroupBox("Thời gian xem video")
        time_layout = QHBoxLayout()
        
        self.time_min = QSpinBox()
        self.time_min.setObjectName("time_min")
        self.time_min.setMinimum(5)
        self.time_min.setMaximum(999)
        
        self.time_max = QSpinBox()
        self.time_max.setObjectName("time_max")
        self.time_max.setMinimum(20)
        self.time_max.setMaximum(999)
        
        time_layout.addWidget(QLabel("Từ:"))
        time_layout.addWidget(self.time_min)
        time_layout.addWidget(QLabel("đến:"))
        time_layout.addWidget(self.time_max)
        time_layout.addWidget(QLabel("giây"))
        time_group.setLayout(time_layout)
        
        # Options Group
        options_group = QGroupBox("Tùy chọn")
        options_layout = QVBoxLayout()
        self.like_cb = QCheckBox("Like")
        self.subscribe_cb = QCheckBox("Đăng ký")
        self.random_cb = QCheckBox("Random")
        options_layout.addWidget(self.like_cb)
        options_layout.addWidget(self.subscribe_cb)
        options_layout.addWidget(self.random_cb)
        options_group.setLayout(options_layout)
        
        # Add all groups to right layout
        right_layout.addWidget(browser_group)
        right_layout.addWidget(time_group)
        right_layout.addWidget(options_group)
        right_layout.addStretch()
        
        return right_layout
     
    def create_bottom_panel(self):
        bottom_layout = QHBoxLayout()
        
        self.add_task_btn = QPushButton("Add New Task")
        self.start_btn = QPushButton("Start Comment")
        self.reset_btn = QPushButton("Reset")
        self.progress_bar = QProgressBar()
        
        bottom_layout.addWidget(self.add_task_btn)
        bottom_layout.addWidget(self.start_btn)
        bottom_layout.addWidget(self.reset_btn)
        bottom_layout.addWidget(self.progress_bar)
        
        return bottom_layout
      
    def connect_signals(self):
        self.firefox_radio.toggled.connect(self.toggle_browser_frames)
        self.chrome_radio.toggled.connect(self.toggle_browser_frames)
        self.chrome_btn.clicked.connect(self.select_chrome_file)
        self.add_task_btn.clicked.connect(self.add_new_task)
        self.start_btn.clicked.connect(self.start_comment)
        self.reset_btn.clicked.connect(self.reset_ui)

    def add_new_task(self):
        task_container = QWidget()
        task_container.setObjectName("task_container")
        task_layout = QHBoxLayout()
        
        # Create left panel
        left_panel = self.create_left_panel()
        task_layout.addLayout(left_panel, stretch=50)
        
        # Create right panel
        right_panel = QWidget()
        right_layout = QVBoxLayout()
        
        # Browser Selection Group
        browser_group = QGroupBox("Chọn trình duyệt")
        browser_layout = QVBoxLayout()
        
        chrome_frame = QFrame()
        chrome_layout = QVBoxLayout()
        chrome_path = QLineEdit()
        chrome_path.setObjectName("chrome_path")
        chrome_btn = QPushButton("Chọn File Chrome")
        chrome_btn.clicked.connect(lambda: self.select_chrome_file_for_group(chrome_path))
        
        chrome_layout.addWidget(chrome_path)
        chrome_layout.addWidget(chrome_btn)
        chrome_frame.setLayout(chrome_layout)
        
        browser_layout.addWidget(chrome_frame)
        browser_group.setLayout(browser_layout)
        
        # Time range group
        time_group = QGroupBox("Thời gian xem video")
        time_layout = QHBoxLayout()
        time_min = QSpinBox()
        time_min.setObjectName("time_min")
        time_min.setMinimum(10)
        time_min.setMaximum(999)
        time_max = QSpinBox()
        time_max.setObjectName("time_max")
        time_max.setMinimum(20)
        time_max.setMaximum(999)
        
        time_layout.addWidget(QLabel("Từ:"))
        time_layout.addWidget(time_min)
        time_layout.addWidget(QLabel("đến:"))
        time_layout.addWidget(time_max)
        time_layout.addWidget(QLabel("giây"))
        time_group.setLayout(time_layout)
        
        # Options Group with proper object names
        options_group = QGroupBox("Tùy chọn")
        options_layout = QVBoxLayout()
        like_cb = QCheckBox("Like")
        like_cb.setObjectName("like_checkbox")  # Add specific object name
        subscribe_cb = QCheckBox("Đăng ký")
        subscribe_cb.setObjectName("subscribe_checkbox")  # Add specific object name
        random_cb = QCheckBox("Random")
        random_cb.setObjectName("random_checkbox")  # Add specific object name
        
        options_layout.addWidget(like_cb)
        options_layout.addWidget(subscribe_cb)
        options_layout.addWidget(random_cb)
        options_group.setLayout(options_layout)
        
        right_layout.addWidget(browser_group)
        right_layout.addWidget(time_group)
        right_layout.addWidget(options_group)
        right_layout.addStretch()
        
        right_panel.setLayout(right_layout)
        task_layout.addWidget(right_panel, stretch=50)
        
        task_container.setLayout(task_layout)
        
        scroll = self.findChild(QScrollArea)
        if scroll:
            container = scroll.widget()
            if container:
                container.layout().insertWidget(0, task_container)

    def toggle_browser_frames(self):
        if self.firefox_radio.isChecked():
            self.firefox_frame.show()
            self.chrome_frame.hide()
            self.load_firefox_profiles()
        else:
            self.firefox_frame.hide()
            self.chrome_frame.show()

    def load_firefox_profiles(self):
        # Load danh sách profile Firefox
        firefox_path = os.path.expanduser('~\\AppData\\Roaming\\Mozilla\\Firefox\\Profiles')
        if os.path.exists(firefox_path):
            profiles = [d for d in os.listdir(firefox_path) if os.path.isdir(os.path.join(firefox_path, d))]
            self.profile_combo.clear()
            self.profile_combo.addItems(profiles)

    def add_group(self):
        # Create new group
        new_group = self.create_browser_group(f"Browser Group {self.get_group_count() + 1}")
        
        # Add to right panel layout before stretch
        right_layout = self.right_panel.layout()
        right_layout.insertWidget(right_layout.count() - 1, new_group)

    def add_all_groups(self):
        # Create container for the complete new group
        group_container = QWidget()
        group_container.setObjectName("group_container")
        group_layout = QHBoxLayout()
        
        # Create new left panel (group_text)
        left_panel = self.create_left_panel()
        group_layout.addLayout(left_panel, stretch=50)
        
        # Create new right panel (channel_group)
        right_panel = QWidget()
        right_layout = QVBoxLayout()
        browser_group = self.create_browser_group(f"Browser Group {self.get_group_count() + 1}")
        right_layout.addWidget(browser_group)
        right_layout.addStretch()
        right_panel.setLayout(right_layout)
        group_layout.addWidget(right_panel, stretch=50)
        
        # Set layout for container
        group_container.setLayout(group_layout)
        
        # Add to main container
        scroll = self.findChild(QScrollArea)
        if scroll:
            container = scroll.widget()
            if container:
                container.layout().insertWidget(0, group_container)

    def connect_new_group_signals(self, frame):
        # Kết nối signals cho các components mới
        for group in frame.findChildren(QGroupBox):
            firefox_radio = group.findChild(QRadioButton, "Firefox Profile")
            chrome_radio = group.findChild(QRadioButton, "Chrome Portable")
            firefox_frame = group.findChild(QFrame, "firefox_frame")
            chrome_frame = group.findChild(QFrame, "chrome_frame")
            chrome_btn = group.findChild(QPushButton, "Chọn File Chrome")
            
            if firefox_radio and chrome_radio:
                firefox_radio.toggled.connect(
                    lambda checked, f=firefox_frame, c=chrome_frame: 
                    self.toggle_new_browser_frames(f, c, checked)
                )
            
            if chrome_btn:
                chrome_btn.clicked.connect(
                    lambda _, btn=chrome_btn: 
                    self.select_chrome_file_for_group(btn.parent())
                )

    def reset_ui(self):
        # Reset text boxes
        self.video_links.clear()
        self.comments.clear()
        
        # Reset browser selection
        self.chrome_radio.setChecked(True)
        self.firefox_frame.hide()
        self.chrome_frame.show()
        self.chrome_path.clear()
        
        # Reset checkboxes
        self.like_cb.setChecked(False)
        self.subscribe_cb.setChecked(False)
        self.random_cb.setChecked(False)
        
        # Reset progress bar
        self.progress_bar.setValue(0)
        
        # Xóa tất cả các group đã thêm
        layout = self.layout()
        for i in reversed(range(layout.count())):
            item = layout.itemAt(i)
            if isinstance(item.widget(), QFrame):
                # Kiểm tra nếu là frame chứa các group
                frame = item.widget()
                if frame != self.firefox_frame and frame != self.chrome_frame:
                    frame.deleteLater()
        
        # Đưa layout về trạng thái ban đầu
        self.init_ui()

    def start_comment(self):
        tasks = []
        
        # Get main task
        main_task = {
            'video_links': self.video_links.toPlainText().split('\n'),
            'comments': self.comments.toPlainText().split('\n'),
            'browser_config': {
                'type': 'firefox' if self.firefox_radio.isChecked() else 'chrome',
                'profile': self.profile_combo.currentText() if self.firefox_radio.isChecked() else self.chrome_path.text()
            },
            'options': {
                'like': self.like_cb.isChecked(),
                'subscribe': self.subscribe_cb.isChecked(),
                'random': self.random_cb.isChecked(),
                'time_range': (self.time_min.value(), self.time_max.value())
            }
        }
        tasks.append(main_task)
        
        # Get additional tasks
        for container in self.findChildren(QWidget, "task_container"):
            # Find text editors using findChild
            video_edit = container.findChild(QTextEdit, "video_links")
            comment_edit = container.findChild(QTextEdit, "comments")
            chrome_path_edit = container.findChild(QLineEdit, "chrome_path")
            time_min_spin = container.findChild(QSpinBox, "time_min")
            time_max_spin = container.findChild(QSpinBox, "time_max")
            
            like_checkbox = container.findChild(QCheckBox, "like_checkbox")
            subscribe_checkbox = container.findChild(QCheckBox, "subscribe_checkbox")
            random_checkbox = container.findChild(QCheckBox, "random_checkbox")
            
            if all([video_edit, comment_edit, chrome_path_edit, time_min_spin, time_max_spin, 
                   like_checkbox, subscribe_checkbox, random_checkbox]):
                additional_task = {
                    'video_links': video_edit.toPlainText().split('\n'),
                    'comments': comment_edit.toPlainText().split('\n'),
                    'browser_config': {
                        'type': 'chrome',
                        'profile': chrome_path_edit.text()
                    },
                    'options': {
                        'like': like_checkbox.isChecked(),
                        'subscribe': subscribe_checkbox.isChecked(),
                        'random': random_checkbox.isChecked(),
                        'time_range': (time_min_spin.value(), time_max_spin.value())
                    }
                }
                tasks.append(additional_task)
        
        if tasks:
            self.comment_manager.start_sequential_tasks(tasks)

    def create_browser_group(self, title):
        group = QGroupBox(title)
        layout = QVBoxLayout()
        
        # Browser selection
        browser_type = QButtonGroup()
        firefox_radio = QRadioButton("Firefox Profile")
        firefox_radio.setObjectName(f"firefox_radio_{title}")
        chrome_radio = QRadioButton("Chrome Portable")
        chrome_radio.setObjectName(f"chrome_radio_{title}")
        browser_type.addButton(firefox_radio)
        browser_type.addButton(chrome_radio)
        chrome_radio.setChecked(True)
        
        # Firefox frame
        firefox_frame = QFrame()
        firefox_frame.setObjectName(f"firefox_frame_{title}")
        firefox_layout = QVBoxLayout()
        profile_combo = QComboBox()
        profile_combo.setObjectName(f"profile_combo_{title}")
        firefox_layout.addWidget(profile_combo)
        firefox_frame.setLayout(firefox_layout)
        firefox_frame.hide()
        
        # Chrome frame  
        chrome_frame = QFrame()
        chrome_frame.setObjectName(f"chrome_frame_{title}")
        chrome_layout = QVBoxLayout()
        chrome_path = QLineEdit()
        chrome_path.setObjectName(f"chrome_path_{title}")
        chrome_btn = QPushButton("Chọn File Chrome")
        chrome_btn.setObjectName(f"chrome_btn_{title}")
        chrome_layout.addWidget(chrome_path)
        chrome_layout.addWidget(chrome_btn)
        chrome_frame.setLayout(chrome_layout)
        
        # Add components
        layout.addWidget(firefox_radio)
        layout.addWidget(firefox_frame) 
        layout.addWidget(chrome_radio)
        layout.addWidget(chrome_frame)
        layout.addWidget(QCheckBox("Like"))
        layout.addWidget(QCheckBox("Đăng ký"))
        layout.addWidget(QCheckBox("Random"))
        
        group.setLayout(layout)
        
        # Connect signals with unique identifiers
        firefox_radio.toggled.connect(
            lambda checked: self.toggle_frames_in_group(firefox_frame, chrome_frame, checked, profile_combo)
        )
        chrome_btn.clicked.connect(
            lambda: self.select_chrome_file_for_group(chrome_path)
        )
        
        return group

    def toggle_frames_in_group(self, firefox_frame, chrome_frame, show_firefox, profile_combo):
        firefox_frame.setVisible(show_firefox)
        chrome_frame.setVisible(not show_firefox)
        if show_firefox:
            self.load_firefox_profiles_for_group(profile_combo)

    def load_firefox_profiles_for_group(self, profile_combo):
        firefox_path = os.path.expanduser('~\\AppData\\Roaming\\Mozilla\\Firefox\\Profiles')
        if os.path.exists(firefox_path):
            profiles = [d for d in os.listdir(firefox_path) if os.path.isdir(os.path.join(firefox_path, d))]
            profile_combo.clear()
            profile_combo.addItems(profiles)

    def select_chrome_file_for_group(self, chrome_path_edit):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Chọn Chrome Portable",
            "",
            "Executable files (*.exe)"
        )
        if file_path:
            chrome_path_edit.setText(file_path)

    def get_group_count(self):
        count = 0
        right_layout = self.right_panel.layout()
        for i in range(right_layout.count()):
            item = right_layout.itemAt(i)
            if item and item.widget() and isinstance(item.widget(), QGroupBox):
                if "Browser Group" in item.widget().title():
                    count += 1
        return count

    def add_all_groups(self):
        new_group = self.create_complete_group()
        self.groups.append(new_group)
        
        scroll = self.findChild(QScrollArea)
        if scroll:
            container = scroll.widget()
            if container:
                container.layout().insertWidget(0, new_group)

    def toggle_frames_in_group(self, firefox_frame, chrome_frame, show_firefox):
        firefox_frame.setVisible(show_firefox)
        chrome_frame.setVisible(not show_firefox)

    def update_progress(self, value, message):
        # Cập nhật giá trị progress bar
        self.progress_bar.setValue(value)
        # Hiển thị message
        self.progress_bar.setFormat(f"{message} ({value}%)")

    def on_task_completed(self):
        self.progress_bar.setValue(100)
        self.progress_bar.setFormat("Hoàn thành!")
        QMessageBox.information(self, "Thành công", "Đã hoàn thành tất cả tác vụ!")

    def show_error(self, message):
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("Lỗi!")
        QMessageBox.critical(self, "Lỗi", message)

    def toggle_new_browser_frames(self, firefox_frame, chrome_frame, show_firefox):
        firefox_frame.setVisible(show_firefox)
        chrome_frame.setVisible(not show_firefox)

    def select_chrome_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Chọn Chrome Portable",
            "",
            "Executable files (*.exe)"
        )
        if file_path:
            self.chrome_path.setText(file_path)

    def create_complete_group(self):
        # Create container
        group_container = QWidget()
        group_container.setObjectName(f"group_{len(self.groups)}")  # Unique ID for container
        group_layout = QHBoxLayout()
        
        # Left side - Text boxes
        left_panel = QVBoxLayout()
        
        # Video Links
        video_group = QGroupBox("Danh sách link video")
        video_layout = QVBoxLayout()
        video_text = QTextEdit()
        video_text.setObjectName(f"video_links_{len(self.groups)}")  # Unique ID for video textbox
        video_text.setPlaceholderText("Nhập link video (mỗi video một dòng)")
        video_layout.addWidget(video_text)
        video_group.setLayout(video_layout)
        
        # Comments
        comment_group = QGroupBox("Nội dung comment")
        comment_layout = QVBoxLayout()
        comment_text = QTextEdit()
        comment_text.setObjectName(f"comments_{len(self.groups)}")  # Unique ID for comment textbox
        comment_text.setPlaceholderText("Nhập nội dung comment (phân cách bằng Enter)")
        comment_layout.addWidget(comment_text)
        comment_group.setLayout(comment_layout)
        
        left_panel.addWidget(video_group)
        left_panel.addWidget(comment_group)
        
        # Right side - Browser group
        right_panel = QVBoxLayout()
        browser_group = self.create_browser_group(f"Browser Group {len(self.groups) + 1}")
        right_panel.addWidget(browser_group)
        
        # Combine panels
        group_layout.addLayout(left_panel, stretch=50)
        group_layout.addLayout(right_panel, stretch=50)
        group_container.setLayout(group_layout)
        
        return group_container


class CommentManager(QObject):
    progress_updated = pyqtSignal(int, str)
    task_completed = pyqtSignal()
    error_occurred = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.is_running = False
        self.browser_manager = BrowserManager()

    def _setup_and_verify_browser(self, browser_config):
        try:
            if browser_config['type'] == 'firefox':
                self.driver = self.browser_manager.setup_firefox(browser_config['profile'])
            else:
                # Get Chrome Portable path
                chrome_path = browser_config['profile'].strip()
                
                # Validate Chrome path
                if not chrome_path:
                    raise Exception("Chrome path is empty. Please select Chrome executable file")
                if not os.path.exists(chrome_path):
                    raise Exception(f"Chrome file not found at: {chrome_path}")
                if not chrome_path.lower().endswith('.exe'):
                    raise Exception("Selected file must be an executable (.exe) file")
                    
                print(f"Starting Chrome Portable from: {chrome_path}")
                self.driver = self.browser_manager.setup_chrome(chrome_path)

            # Verify login
            wait = WebDriverWait(self.driver, 10)
            print('Đang khởi động trình duyệt')
            self.driver.get("https://studio.youtube.com")
            self.progress_updated.emit(10, "Đang khởi động trình duyệt...")
            
            try:
                avatar = wait.until(EC.visibility_of_element_located((By.XPATH, "//button[@id='avatar-btn']")))
                self.progress_updated.emit(20, "Đăng nhập thành công")
                print('đăng nhập thành công')
                time.sleep(2)
                return True
            except TimeoutException:
                self.error_occurred.emit("Chưa đăng nhập YouTube")
                return False

        except Exception as e:
            self.error_occurred.emit(f"Lỗi khởi tạo trình duyệt: {str(e)}")
            return False

    def _process_single_video(self, video_url, comments, options, time_range):
        try:
            self.driver.get(video_url)
            self.progress_updated.emit(50, "đang mở video ...")
            wait = WebDriverWait(self.driver, 10)
            
            # Wait for video to load
            wait.until(lambda driver: driver.execute_script("return document.readyState") == "complete")
            
            # Random watch time between min and max seconds
            watch_time = random.randint(time_range[0], time_range[1])
            print(f"Watching video for {watch_time} seconds")
            time.sleep(watch_time)

            # Improved scrolling to comment section
            def scroll_to_comments():
                last_height = self.driver.execute_script("return document.documentElement.scrollHeight")
                while True:
                    # Scroll down in smaller increments
                    for i in range(0, 1000, 200):
                        self.driver.execute_script(f"window.scrollTo(0, {i});")
                        time.sleep(0.5)
                    
                    # Check if comment section is visible
                    try:
                        comment_section = self.driver.find_element(By.ID, "comments")
                        if comment_section.is_displayed():
                            # Scroll comment section into view
                            self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", comment_section)
                            time.sleep(1)
                            return True
                    except:
                        pass
                    
                    new_height = self.driver.execute_script("return document.documentElement.scrollHeight")
                    if new_height == last_height:
                        break
                    last_height = new_height
                return False

            self.progress_updated.emit(75, "tìm kiếm comment ...")

            # Random order for actions if enabled
            actions = ['comment', 'like', 'subscribe']
            if options['random']:
                random.shuffle(actions)
            
            for action in actions:
                if not self.is_running:
                    break
                    
                if action == 'comment':
                    # Handle comment
                    try:
                        # First wait for page to be fully loaded
                        wait.until(lambda driver: driver.execute_script("return document.readyState") == "complete")
                        
                        # Scroll to comments section
                        self.driver.execute_script("window.scrollBy(0, 500);")
                        time.sleep(2)
                        
                        # Try multiple selector strategies
                        selectors = [
                            (By.CSS_SELECTOR, "#simplebox-placeholder"),
                            (By.CSS_SELECTOR, "ytd-comment-simplebox-renderer"),
                            (By.XPATH, "//div[@id='placeholder-area']"),
                            (By.CSS_SELECTOR, "#input-container")
                        ]
                        
                        comment_trigger = None
                        for selector in selectors:
                            try:
                                comment_trigger = wait.until(EC.element_to_be_clickable(selector))
                                print(f"Found element using selector: {selector}")
                                break
                            except:
                                continue
                                
                        if comment_trigger:
                            # Click to activate comment box
                            self.driver.execute_script("arguments[0].click();", comment_trigger)
                            time.sleep(2)
                            
                            # Now find the actual input field
                            comment_box = wait.until(EC.presence_of_element_located((
                                By.CSS_SELECTOR, 
                                "#contenteditable-root"
                            )))
                            
                            # Simulate natural keyboard typing
                            comment = random.choice(comments)

                            # Clear existing text first
                            comment_box.clear()

                            # Type each character with random delay
                            for char in comment:
                                comment_box.send_keys(char)
                                time.sleep(random.uniform(0.01, 0.2))  # Random delay between keystrokes

                            # Method 1: Using specific button class
                            submit_btn = wait.until(EC.element_to_be_clickable((
                                By.CSS_SELECTOR,
                                "button.yt-spec-button-shape-next--filled"
                            )))

                            # Method 2: Using the complete path
                            submit_btn = wait.until(EC.element_to_be_clickable((
                                By.CSS_SELECTOR,
                                "#submit-button yt-button-shape button"
                            )))

                            # Method 3: Using XPath with multiple attributes
                            submit_btn = wait.until(EC.element_to_be_clickable((
                                By.XPATH,
                                "//button[contains(@class, 'yt-spec-button-shape-next--filled') and contains(@class, 'yt-spec-button-shape-next--call-to-action')]"
                            )))
                            self.progress_updated.emit(90, "Comment xong ...")
                            # Add verification before clicking
                            if submit_btn.is_displayed() and submit_btn.is_enabled():
                                # Try multiple click methods
                                try:
                                    # Method 1: Direct click
                                    submit_btn.click()
                                except:
                                    try:
                                        # Method 2: JavaScript click
                                        self.driver.execute_script("arguments[0].click();", submit_btn)
                                    except:
                                        # Method 3: Action chains
                                        ActionChains(self.driver).move_to_element(submit_btn).click().perform()

                            # Add verification delay
                            time.sleep(2)


                            # Verify comment was posted
                            time.sleep(2)
                            print("Comment posted successfully!")
                            print("Successfully entered comment text")
                            
                    except Exception as e:
                        print(f"Detailed error: {str(e)}")
                        # Log the current URL for debugging
                        print(f"Current URL: {self.driver.current_url}")
                   
                elif action == 'like' and options['like']:
                    # Handle like
                    like_button = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "[class*='ytLikeButtonViewModelHost']")))
                    self.driver.execute_script("arguments[0].click();", like_button)
                    
                elif action == 'subscribe' and options['subscribe']:
                    # Handle subscribe
                    sub_button = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "#subscribe-button-shape")))
                    self.driver.execute_script("arguments[0].click();", sub_button)
            
            # Random delay between videos
            time.sleep(random.uniform(2, 4))
            
        except Exception as e:
            raise Exception(f"Lỗi xử lý video {video_url}: {str(e)}")

    def _comment_worker(self, video_links, comments, browser_config, options):
        try:
            if not self._setup_and_verify_browser(browser_config):
                return
                
            total_videos = len(video_links)
            for i, video in enumerate(video_links):
                if not self.is_running:
                    break
                    
                self.progress_updated.emit(
                    int((i + 1) * 100 / total_videos),
                    f"Đang xử lý video {i+1}/{total_videos}"
                )
                
                self._process_single_video(video, comments, options, time_range)
                
            self.task_completed.emit()
            
        except Exception as e:
            self.error_occurred.emit(str(e))
        finally:
            self.browser_manager.quit()
            self.is_running = False

    def start_comment_task(self, video_links, comments, browser_config, options):
        if self.is_running:
            return
            
        self.is_running = True
        
        # Start comment thread
        comment_thread = threading.Thread(
            target=self._comment_worker,
            args=(video_links, comments, browser_config, options)
        )
        comment_thread.daemon = True
        comment_thread.start()

    def stop_task(self):
        self.is_running = False

    def start_sequential_tasks(self, browser_groups):
        if self.is_running:
            return
            
        self.is_running = True
        
        def sequential_worker():
            try:
                total_groups = len(browser_groups)
                
                for i, group in enumerate(browser_groups):
                    if not self.is_running:
                        break
                        
                    print(f"Starting group {i+1}/{total_groups}")
                    print(f"Video links: {group['video_links']}")
                    print(f"Browser config: {group['browser_config']}")
                    
                    self.progress_updated.emit(
                        int((i) * 100 / total_groups),
                        f"Processing group {i+1}/{total_groups}"
                    )
                    
                    # Extract time_range from options
                    time_range = group['options'].get('time_range', (60, 120))
                    
                    # Process videos for this group
                    if self._setup_and_verify_browser(group['browser_config']):
                        for video_url in group['video_links']:
                            if not self.is_running:
                                break
                                
                            try:
                                self._process_single_video(
                                    video_url,
                                    group['comments'],
                                    group['options'],
                                    time_range
                                )
                            except Exception as e:
                                print(f"Error processing video {video_url}: {str(e)}")
                                continue
                    
                    # Clean up browser after each group
                    self.browser_manager.quit()
                    time.sleep(2)
                    
                self.task_completed.emit()
                
            except Exception as e:
                print(f"Sequential worker error: {str(e)}")
                self.error_occurred.emit(str(e))
            finally:
                self.is_running = False
                self.browser_manager.quit()
        
        sequential_thread = threading.Thread(target=sequential_worker)
        sequential_thread.daemon = True
        sequential_thread.start()
