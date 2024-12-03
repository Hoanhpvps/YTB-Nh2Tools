from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
                           QFileDialog, QSizePolicy, QListWidget, QComboBox, QSpinBox,
                           QLineEdit, QFrame, QProgressBar, QRadioButton, QButtonGroup)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QDragEnterEvent, QDropEvent
import os
import random
from datetime import datetime
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
                           QFileDialog, QSizePolicy, QListWidget, QComboBox, QSpinBox,
                           QLineEdit, QFrame, QProgressBar, QRadioButton, QButtonGroup,
                           QDialog, QTextEdit, QMessageBox)
from moviepy.editor import VideoFileClip, AudioFileClip
import math
import subprocess
import re
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QApplication

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

class CreateShortTab(QWidget):
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

    def open_seo_dialog(self):
        """Open SEO keywords dialog and store keywords"""
        dialog = SEODialog(self)
        if dialog.exec_():
            self.seo_keywords = dialog.get_keywords()

    def create_left_panel(self):
        panel = QFrame()
        layout = QVBoxLayout()

        # Title
        title = QLabel("Create Short Videos (1080x1920)")
        title.setFont(QFont("Arial", 14, QFont.Bold))
        layout.addWidget(title)

        # File list
        self.file_list = QListWidget()
        self.file_list.setAcceptDrops(True)

        # File controls
        btn_layout = QHBoxLayout()
        self.add_btn = QPushButton("Add Videos")
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

        # Start time input
        start_time_layout = QHBoxLayout()
        start_time_label = QLabel("Start Time (HH:MM:SS):")
        self.start_time_edit = QLineEdit()
        self.start_time_edit.setPlaceholderText("00:00:30")
        start_time_layout.addWidget(start_time_label)
        start_time_layout.addWidget(self.start_time_edit)

        # Duration range input
        duration_layout = QHBoxLayout()
        duration_label = QLabel("Duration Range (seconds):")
        self.min_duration_edit = QLineEdit()
        self.min_duration_edit.setPlaceholderText("30")
        self.max_duration_edit = QLineEdit()
        self.max_duration_edit.setPlaceholderText("50")
        duration_layout.addWidget(duration_label)
        duration_layout.addWidget(self.min_duration_edit)
        duration_layout.addWidget(self.max_duration_edit)

        # Output folder selection
        output_layout = QHBoxLayout()
        self.output_path_edit = QLineEdit()
        self.output_path_btn = QPushButton("Select Output Folder")
        self.output_path_btn.clicked.connect(self.select_output_folder)
        output_layout.addWidget(self.output_path_edit)
        output_layout.addWidget(self.output_path_btn)

        # Naming options
        self.naming_combo = QComboBox()
        self.naming_combo.addItems(["Auto Name", "SEO Title"])
        self.seo_keywords_btn = QPushButton("SEO Keywords")
        self.seo_keywords_btn.clicked.connect(self.open_seo_dialog)

        # Control buttons
        btn_layout = QHBoxLayout()
        self.render_btn = QPushButton("Create Short Videos")
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
        layout.addLayout(start_time_layout)
        layout.addLayout(duration_layout)
        layout.addLayout(output_layout)
        layout.addWidget(self.naming_combo)
        layout.addWidget(self.seo_keywords_btn)
        layout.addLayout(btn_layout)
        layout.addLayout(self.progress_area)
        layout.addStretch()

        panel.setLayout(layout)
        return panel

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            valid_files = all(
                url.toLocalFile().lower().endswith('.mp4')
                for url in urls
            )
            if valid_files:
                event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        files = [url.toLocalFile() for url in event.mimeData().urls()]
        self.add_files_to_list(files)

    def add_files_to_list(self, files):
        for file_path in files:
            if file_path.lower().endswith('.mp4'):
                self.files_list.append(file_path)
                self.file_list.addItem(file_path)
        self.update_file_count()

    def add_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Videos",
            "",
            "MP4 Files (*.mp4)"
        )
        self.add_files_to_list(files)

    def create_progress_bar(self, index):
        progress_frame = QFrame()
        layout = QHBoxLayout()
        
        label = QLabel(f"Video {index + 1}:")
        progress = QProgressBar()
        progress.setMinimum(0)
        progress.setMaximum(100)
        percentage = QLabel("0%")
        percentage.setMinimumWidth(50)
        
        layout.addWidget(label)
        layout.addWidget(progress)
        layout.addWidget(percentage)
        
        progress_frame.setLayout(layout)
        self.progress_area.addWidget(progress_frame)
        
        return progress, percentage

    def process_file(self, input_file, output_file, progress_bar, percentage_label):
        try:
            # Get parameters
            start_time = self.start_time_edit.text() or "00:00:30"
            min_duration = int(self.min_duration_edit.text() or "30")
            max_duration = int(self.max_duration_edit.text() or "50")
            random_duration = random.randint(min_duration, max_duration)
            
            # Create filter complex options
            filter_complex_options = [
                f'[0:v]scale=3413:1920,setpts=PTS-STARTPTS[v];color=black:1080x1920:d=30[s];[s][v]overlay=x=\'-min(t*1920/30,1080)\':y=0:eof_action=pass[out]',
                f'[0:v]scale=3413:1920,setpts=PTS-STARTPTS[v];color=black:1080x1920:d={random_duration}[s];[s][v]overlay=x=\'-min(t*1920/{random_duration},1080)\':y=0:eof_action=pass[out]',
                f'[0:v]setpts=PTS-STARTPTS[v];color=black:1080x1920:d=30[s];[s][v]overlay=x=\'-min(t*1920/30,1080)\':y=\'(1920-h)/2\':eof_action=pass[out]',
                f'[0:v]setpts=PTS-STARTPTS[v];color=black:1080x1920:d={random_duration}[s];[s][v]overlay=x=\'-min(t*1920/{random_duration},1080)\':y=\'(1920-h)/2\':eof_action=pass[out]'
            ]
            
            selected_filter = random.choice(filter_complex_options)
            
            # Build FFmpeg command
            cmd = f'ffmpeg -hide_banner -y -ss {start_time} -i "{input_file}" -ss {start_time} -t {random_duration} -i "{input_file}" -filter_complex "{selected_filter}" -map [out] -map 1:a -c:v libx264 -c:a copy "{output_file}"'
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                shell=True
            )
            
            self.monitor_progress(process, random_duration, progress_bar, percentage_label)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def start_processing(self):
        if not self.validate_inputs():
            return
            
        self.clear_progress_area()
        self.render_btn.setEnabled(False)
        
        for i, video_path in enumerate(self.files_list):
            progress_bar, percentage_label = self.create_progress_bar(i)
            output_file = self.generate_output_filename(video_path, i)
            self.process_file(video_path, output_file, progress_bar, percentage_label)
        
        self.render_btn.setEnabled(True)
        QMessageBox.information(self, "Complete", "All videos have been processed successfully!")

    def validate_inputs(self):
        if not self.files_list:
            QMessageBox.warning(self, "Validation Error", "Please select at least one video file.")
            return False
        
        if not self.output_path_edit.text():
            QMessageBox.warning(self, "Validation Error", "Please select an output folder.")
            return False
            
        try:
            min_duration = int(self.min_duration_edit.text() or "30")
            max_duration = int(self.max_duration_edit.text() or "50")
            if min_duration <= 0 or max_duration <= 0 or min_duration > max_duration:
                raise ValueError
        except ValueError:
            QMessageBox.warning(self, "Validation Error", "Please enter valid duration range values.")
            return False
            
        return True

    def remove_selected(self):
        """Remove selected items from the list"""
        selected_items = self.file_list.selectedItems()
        for item in selected_items:
            row = self.file_list.row(item)
            self.file_list.takeItem(row)
            self.files_list.pop(row)
        self.update_file_count()

    def clear_list(self):
        """Clear all items from the list"""
        self.file_list.clear()
        self.files_list.clear()
        self.update_file_count()

    def update_file_count(self):
        """Update the file count label"""
        count = len(self.files_list)
        self.file_count_label.setText(f"Files: {count}")

    def select_output_folder(self):
        """Open dialog to select output folder"""
        folder = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if folder:
            self.output_path_edit.setText(folder)

    def open_output_folder(self):
        """Open the output folder in file explorer"""
        output_path = self.output_path_edit.text()
        if output_path and os.path.exists(output_path):
            os.startfile(output_path)

    def reset_ui(self):
        """Reset all UI elements to default state"""
        self.clear_list()
        self.output_path_edit.clear()
        self.start_time_edit.setText("00:00:30")
        self.min_duration_edit.setText("30")
        self.max_duration_edit.setText("50")
        self.naming_combo.setCurrentIndex(0)
        self.clear_progress_area()

    def clear_progress_area(self):
        """Clear all progress bars"""
        while self.progress_area.count():
            item = self.progress_area.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def generate_output_filename(self, input_path, index):
        """Generate output filename based on naming option"""
        output_dir = self.output_path_edit.text()
        base_name = os.path.splitext(os.path.basename(input_path))[0]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return os.path.join(output_dir, f'Short_{base_name}_{timestamp}_{index}.mp4')

    def monitor_progress(self, process, total_duration, progress_bar, percentage_label):
        """Monitor FFmpeg progress and update UI"""
        import re
        from PyQt5.QtWidgets import QApplication
        
        while process.poll() is None:
            line = process.stderr.readline()
            time_match = re.search(r'time=(\d{2}:\d{2}:\d{2}\.\d{2})', line)
            
            if time_match:
                current_time = self.duration_to_seconds(time_match.group(1))
                progress = min(100, (current_time / total_duration) * 100)
                progress_bar.setValue(int(progress))
                percentage_label.setText(f"{int(progress)}%")
                QApplication.processEvents()

    def duration_to_seconds(self, time_str):
        """Convert time string (HH:MM:SS.ms) to seconds"""
        h, m, s = time_str.split(':')
        s, ms = s.split('.') if '.' in s else (s, '0')
        total_seconds = int(h) * 3600 + int(m) * 60 + int(s) + float(f"0.{ms}")
        return total_seconds
