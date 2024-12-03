# PyQt5 GUI imports
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QFileDialog, QSizePolicy, QListWidget, QComboBox, QSpinBox,
    QLineEdit, QFrame, QProgressBar, QRadioButton, QButtonGroup,
    QDialog, QTextEdit, QMessageBox, QApplication
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QDragEnterEvent, QDropEvent

# System and utility imports
import os
import re
import math
import random
import subprocess
from datetime import datetime

# Media processing imports
from moviepy.editor import VideoFileClip, AudioFileClip

class SEODialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        
    def setup_ui(self):
        self.setWindowTitle("SEO Keywords")
        layout = QVBoxLayout()
        
        label = QLabel("Enter keywords (one per line):")
        self.keywords_edit = QTextEdit()
        
        ok_button = QPushButton("OK")
        ok_button.clicked.connect(self.accept)
        
        layout.addWidget(label)
        layout.addWidget(self.keywords_edit)
        layout.addWidget(ok_button)
        
        self.setLayout(layout)
        
    def get_keywords(self):
        text = self.keywords_edit.toPlainText()
        return [keyword.strip() for keyword in text.split('\n') if keyword.strip()]

class LoopVideoTab(QWidget):
    def __init__(self):
        super().__init__()
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.default_font = QFont()
        self.default_font.setPointSize(11)
        self.setFont(self.default_font)
        self.files_list = []
        self.setup_ui()
        self.setAcceptDrops(True)

    def setup_ui(self):
        main_layout = QHBoxLayout()

        # Left Panel - File List
        left_panel = self.create_left_panel()
        main_layout.addWidget(left_panel)

        # Right Panel - Controls
        right_panel = self.create_right_panel()
        main_layout.addWidget(right_panel)

        self.setLayout(main_layout)

    def get_media_duration(self, file_path):
        """Get the duration of a media file in seconds"""
        try:
            if file_path.lower().endswith(('.mp3', '.wav')):
                clip = AudioFileClip(file_path)
            else:
                clip = VideoFileClip(file_path)
            
            duration = clip.duration
            clip.close()
            return duration
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not get duration of file: {file_path}\nError: {str(e)}")
            return 0

    def duration_to_seconds(self, time_str):
        """Convert time string (HH:MM:SS.ms) to seconds"""
        h, m, s = time_str.split(':')
        s, ms = s.split('.') if '.' in s else (s, '0')
        total_seconds = int(h) * 3600 + int(m) * 60 + int(s) + float(f"0.{ms}")
        return total_seconds


    def create_left_panel(self):
        panel = QFrame()
        layout = QVBoxLayout()

        # File list
        self.file_list = QListWidget()
        self.file_list.setAcceptDrops(True)

        # File controls
        btn_layout = QHBoxLayout()
        self.add_btn = QPushButton("Add Files")
        self.remove_btn = QPushButton("Remove Selected")
        self.clear_btn = QPushButton("Clear All")

        self.add_btn.clicked.connect(self.add_files)
        self.remove_btn.clicked.connect(self.remove_selected)
        self.clear_btn.clicked.connect(self.clear_list)

        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.remove_btn)
        btn_layout.addWidget(self.clear_btn)

        # File count label
        self.file_count_label = QLabel("Files: 0")

        layout.addWidget(self.file_list)
        layout.addLayout(btn_layout)
        layout.addWidget(self.file_count_label)

        panel.setLayout(layout)
        return panel

    def create_right_panel(self):
        panel = QFrame()
        layout = QVBoxLayout()

        # Loop Options
        loop_group = QButtonGroup()
        self.loop_count_radio = QRadioButton("Loop by Count")
        self.loop_time_radio = QRadioButton("Loop by Time")
        self.loop_random_radio = QRadioButton("Random Time Loop")
        
        loop_group.addButton(self.loop_count_radio)
        loop_group.addButton(self.loop_time_radio)
        loop_group.addButton(self.loop_random_radio)
        self.loop_count_radio.setChecked(True)

        # Loop parameters
        # Loop parameters
        self.loop_value = QLineEdit()
        self.loop_value.setPlaceholderText("00:00:00")
        
        # Connect radio buttons to update UI
        self.loop_count_radio.toggled.connect(self.update_ui_based_on_loop_option)
        self.loop_time_radio.toggled.connect(self.update_ui_based_on_loop_option)
        self.loop_random_radio.toggled.connect(self.update_ui_based_on_loop_option)

        # Naming options
        self.naming_combo = QComboBox()
        self.naming_combo.addItems(["Auto Name", "SEO Title"])
        self.seo_keywords_btn = QPushButton("SEO Keywords")
        self.seo_keywords_btn.clicked.connect(self.open_seo_dialog)

        # Output folder selection
        output_layout = QHBoxLayout()
        self.output_path_edit = QLineEdit()
        self.output_path_btn = QPushButton("Select Output Folder")
        self.output_path_btn.clicked.connect(self.select_output_folder)
        output_layout.addWidget(self.output_path_edit)
        output_layout.addWidget(self.output_path_btn)

        # Control buttons
        btn_layout = QHBoxLayout()
        self.render_btn = QPushButton("Start Processing")
        self.open_folder_btn = QPushButton("Open Output Folder")
        self.reset_btn = QPushButton("Reset")

        self.render_btn.clicked.connect(self.start_processing)
        self.open_folder_btn.clicked.connect(self.open_output_folder)
        self.reset_btn.clicked.connect(self.reset_ui)

        btn_layout.addWidget(self.render_btn)
        btn_layout.addWidget(self.open_folder_btn)
        btn_layout.addWidget(self.reset_btn)

        # Progress area
        self.progress_area = QVBoxLayout()

        # Add all elements to layout
        layout.addWidget(self.loop_count_radio)
        layout.addWidget(self.loop_time_radio)
        layout.addWidget(self.loop_random_radio)
        layout.addWidget(self.loop_value)
        layout.addWidget(self.naming_combo)
        layout.addWidget(self.seo_keywords_btn)
        layout.addLayout(output_layout)
        layout.addLayout(btn_layout)
        layout.addLayout(self.progress_area)
        layout.addStretch()

        panel.setLayout(layout)
        return panel

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            valid_files = all(
                url.toLocalFile().lower().endswith(('.mp4', '.mp3', '.wav'))
                for url in urls
            )
            if valid_files:
                event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        files = [url.toLocalFile() for url in event.mimeData().urls()]
        self.add_files_to_list(files)

    def add_files_to_list(self, files):
        for file_path in files:
            if self.is_valid_file(file_path):
                self.files_list.append(file_path)
                self.file_list.addItem(file_path)
        self.update_file_count()

    def is_valid_file(self, file_path):
        return file_path.lower().endswith(('.mp4', '.mp3', '.wav'))

    def add_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Files",
            "",
            "Media Files (*.mp4 *.mp3 *.wav)"
        )
        self.add_files_to_list(files)

    def remove_selected(self):
        selected_items = self.file_list.selectedItems()
        for item in selected_items:
            row = self.file_list.row(item)
            self.file_list.takeItem(row)
            self.files_list.pop(row)
        self.update_file_count()

    def clear_list(self):
        self.file_list.clear()
        self.files_list.clear()
        self.update_file_count()

    def update_file_count(self):
        count = len(self.files_list)
        self.file_count_label.setText(f"Files: {count}")

    def select_output_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if folder:
            self.output_path_edit.setText(folder)

    def open_output_folder(self):
        output_path = self.output_path_edit.text()
        if output_path and os.path.exists(output_path):
            os.startfile(output_path)

    def reset_ui(self):
        self.clear_list()
        self.output_path_edit.clear()
        self.loop_count_radio.setChecked(True)
        self.loop_value.clear()  # Clear the QLineEdit instead of setValue
        self.loop_value.setPlaceholderText("Enter number (e.g., 10)")  # Reset placeholder text
        self.naming_combo.setCurrentIndex(0)
        self.clear_progress_area()


    def clear_progress_area(self):
        while self.progress_area.count():
            item = self.progress_area.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def update_ui_based_on_loop_option(self):
        """Update UI elements based on selected loop option"""
        self.loop_value.clear()
        
        if self.loop_count_radio.isChecked():
            self.loop_value.setPlaceholderText("Enter number (e.g., 10)")
        elif self.loop_time_radio.isChecked():
            self.loop_value.setPlaceholderText("HH:MM:SS (e.g., 01:30:00)")
        elif self.loop_random_radio.isChecked():
            self.loop_value.setPlaceholderText("HH:MM:SS-HH:MM:SS (e.g., 01:00:00-02:00:00)")


    def generate_output_filename(self, media_path, index):
        """Generate output filename based on selected naming option"""
        output_dir = self.output_path_edit.text()
        base_name = os.path.splitext(os.path.basename(media_path))[0]
        extension = os.path.splitext(media_path)[1]
        
        if self.naming_combo.currentText() == "Auto Name":
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            return os.path.join(output_dir, f'Loop_{timestamp}_{index}{extension}')
        else:  # SEO Title
            if hasattr(self, 'seo_keywords'):
                title = self.generate_seo_title()
                return os.path.join(output_dir, f'{title}_{index}{extension}')
        
        return os.path.join(output_dir, f'Loop_{base_name}_{index}{extension}')

    def start_processing(self):
        """Start processing the files"""
        if not self.validate_inputs():
            return

        self.clear_progress_area()
        self.render_btn.setEnabled(False)
        
        for i, media_path in enumerate(self.files_list):
            progress_bar, percentage_label = self.create_progress_bar(i)
            output_file = self.generate_output_filename(media_path, i)
            
            # Start processing in a separate thread
            self.process_file(media_path, output_file, progress_bar, percentage_label)

    def create_progress_bar(self, index):
        """Create and return a progress bar with percentage label for file processing"""
        progress_frame = QFrame()
        layout = QHBoxLayout()
        
        # Create label for file name
        label = QLabel(f"File {index + 1}:")
        
        # Create progress bar
        progress = QProgressBar()
        progress.setMinimum(0)
        progress.setMaximum(100)
        progress.setValue(0)
        
        # Create percentage label
        percentage = QLabel("0%")
        percentage.setMinimumWidth(50)
        
        # Add widgets to layout
        layout.addWidget(label)
        layout.addWidget(progress)
        layout.addWidget(percentage)
        
        # Set layout for frame
        progress_frame.setLayout(layout)
        
        # Add frame to progress area
        self.progress_area.addWidget(progress_frame)
        
        return progress, percentage


    def validate_inputs(self):
        """Validate all required inputs before processing"""
        # Check if files are selected
        if not self.files_list:
            QMessageBox.warning(self, "Validation Error", "Please select at least one file to process.")
            return False
        
        # Check if output folder is selected
        if not self.output_path_edit.text():
            QMessageBox.warning(self, "Validation Error", "Please select an output folder.")
            return False
        
        # Check if output folder exists
        if not os.path.exists(self.output_path_edit.text()):
            QMessageBox.warning(self, "Validation Error", "Selected output folder does not exist.")
            return False
        
        # Validate input based on selected mode
        value = self.loop_value.text().strip()
        if not value:
            QMessageBox.warning(self, "Validation Error", "Please enter a value.")
            return False
            
        if self.loop_count_radio.isChecked():
            try:
                count = int(value)
                if count <= 0:
                    raise ValueError
            except ValueError:
                QMessageBox.warning(self, "Validation Error", "Please enter a valid positive number for loop count.")
                return False
                
        elif self.loop_time_radio.isChecked():
            if not self.is_valid_time_format(value):
                QMessageBox.warning(self, "Validation Error", "Please enter time in HH:MM:SS format.")
                return False
                
        elif self.loop_random_radio.isChecked():
            try:
                start_time, end_time = value.split('-')
                if not (self.is_valid_time_format(start_time.strip()) and self.is_valid_time_format(end_time.strip())):
                    raise ValueError
            except:
                QMessageBox.warning(self, "Validation Error", "Please enter time range in HH:MM:SS-HH:MM:SS format.")
                return False
        
        return True



    def process_file(self, input_file, output_file, progress_bar, percentage_label):
        """Process individual file with FFmpeg"""
        try:
            duration = self.get_media_duration(input_file)
            loop_time = self.calculate_loop_time(duration)
            
            # Create temporary file list
            temp_list = self.create_temp_file_list(input_file, loop_time, duration)
            
            cmd = self.build_ffmpeg_command(temp_list, output_file, loop_time)
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                shell=True
            )
            
            self.monitor_progress(process, loop_time, progress_bar, percentage_label)
            
            # Cleanup
            if os.path.exists(temp_list):
                os.remove(temp_list)
                
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def build_ffmpeg_command(self, input_list, output_file, duration):
        """Build FFmpeg command for looping media with optimized settings"""
        return f'ffmpeg -y -safe 0 -f concat -i "{input_list}" -c copy -avoid_negative_ts 1 -t {duration} -movflags +faststart "{output_file}"'

    def calculate_loop_time(self, media_duration):
        """Calculate total loop time based on selected option"""
        value = self.loop_value.text().strip()
        
        if self.loop_count_radio.isChecked():
            try:
                count = int(value)
                return media_duration * count
            except ValueError:
                QMessageBox.warning(self, "Input Error", "Please enter a valid number for loop count")
                return 0
                
        elif self.loop_time_radio.isChecked():
            if not self.is_valid_time_format(value):
                QMessageBox.warning(self, "Input Error", "Please enter time in HH:MM:SS format")
                return 0
            return self.time_to_seconds(value)
            
        else:  # Random Time Loop
            try:
                start_time, end_time = value.split('-')
                if not (self.is_valid_time_format(start_time) and self.is_valid_time_format(end_time)):
                    raise ValueError
                start_seconds = self.time_to_seconds(start_time.strip())
                end_seconds = self.time_to_seconds(end_time.strip())
                return random.uniform(start_seconds, end_seconds)
            except:
                QMessageBox.warning(self, "Input Error", "Please enter time range in HH:MM:SS-HH:MM:SS format")
                return 0

    def is_valid_time_format(self, time_str):
        """Check if string matches HH:MM:SS format"""
        pattern = r'^\d{2}:\d{2}:\d{2}$'
        return bool(re.match(pattern, time_str.strip()))

    def time_to_seconds(self, time_str):
        """Convert HH:MM:SS to seconds"""
        h, m, s = map(int, time_str.strip().split(':'))
        return h * 3600 + m * 60 + s


    def create_temp_file_list(self, input_file, total_time, duration):
        """Create temporary file list for FFmpeg concat"""
        num_loops = math.ceil(total_time / duration)
        temp_list = os.path.join(self.output_path_edit.text(), 'temp_list.txt')
        
        with open(temp_list, 'w', encoding='utf-8') as f:
            for _ in range(num_loops):
                f.write(f"file '{input_file}'\n")
        
        return temp_list

    def monitor_progress(self, process, total_duration, progress_bar, percentage_label):
        """Monitor FFmpeg progress and update UI"""
        while process.poll() is None:
            line = process.stderr.readline()
            time_match = re.search(r'time=(\d{2}:\d{2}:\d{2}\.\d{2})', line)
            
            if time_match:
                current_time = self.duration_to_seconds(time_match.group(1))
                progress = min(100, (current_time / total_duration) * 100)
                progress_bar.setValue(int(progress))
                percentage_label.setText(f"{int(progress)}%")
                QApplication.processEvents()

    def open_seo_dialog(self):
        dialog = SEODialog(self)
        if dialog.exec_():
            self.seo_keywords = dialog.get_keywords()

    def generate_seo_title(self):
        if hasattr(self, 'seo_keywords') and self.seo_keywords:
            # Select up to 3 keywords and join them
            words = random.sample(self.seo_keywords, min(3, len(self.seo_keywords)))
            title = ' '.join(words)
            
            # Limit title length to 80 characters
            if len(title) > 80:
                title = title[:77] + "..."
                
            # Replace problematic characters
            title = title.replace(',', '').replace('  ', ' ')
            invalid_chars = '<>:"/\\|?*'
            for char in invalid_chars:
                title = title.replace(char, '')
                
            return title
        return f"Video_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
