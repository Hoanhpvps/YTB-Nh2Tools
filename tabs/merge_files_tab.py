from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                           QLabel, QFileDialog, QSizePolicy, QComboBox, 
                           QProgressBar, QListWidget, QSpinBox, QLineEdit,
                           QFrame, QRadioButton, QButtonGroup)
from PyQt5.QtCore import Qt, QMimeData
from PyQt5.QtGui import QFont, QDragEnterEvent, QDropEvent
import os
import json
import random
from datetime import datetime
import subprocess
import re
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QTextEdit, 
                           QPushButton, QLabel)
from moviepy.editor import VideoFileClip
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QApplication

class MergeFilesTab(QWidget):
    def __init__(self):
        super().__init__()
        self.files_list = []
        self.ffmpeg_path = "ffmpeg"
        self.setup_ui()
        self.load_ffmpeg_path()
        self.setAcceptDrops(True)

    def setup_ui(self):
        main_layout = QHBoxLayout()

        # Left panel - File list
        left_panel = self.create_left_panel()
        main_layout.addWidget(left_panel)

        # Right panel - Controls
        right_panel = self.create_right_panel()
        main_layout.addWidget(right_panel)

        self.setLayout(main_layout)

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

        # FFmpeg path selection
        ffmpeg_layout = QHBoxLayout()
        self.ffmpeg_path_edit = QLineEdit()
        self.ffmpeg_path_edit.setPlaceholderText("FFmpeg path (default: ffmpeg)")
        self.ffmpeg_btn = QPushButton("Select FFmpeg")
        self.ffmpeg_btn.clicked.connect(self.select_ffmpeg)
        ffmpeg_layout.addWidget(self.ffmpeg_path_edit)
        ffmpeg_layout.addWidget(self.ffmpeg_btn)

        # File type selection
        self.file_type_combo = QComboBox()
        self.file_type_combo.addItems(["Video", "Audio"])
        self.file_type_combo.currentTextChanged.connect(self.on_file_type_changed)

        # Effect options (for video only)
        self.effect_group = QButtonGroup()
        effect_layout = QHBoxLayout()
        self.no_effect_radio = QRadioButton("No Effect")
        self.with_effect_radio = QRadioButton("With Effect")
        self.effect_group.addButton(self.no_effect_radio)
        self.effect_group.addButton(self.with_effect_radio)
        effect_layout.addWidget(self.no_effect_radio)
        effect_layout.addWidget(self.with_effect_radio)
        self.no_effect_radio.setChecked(True)

        # Input/Output count
        count_layout = QHBoxLayout()
        self.output_count = QSpinBox()
        self.input_count = QSpinBox()
        self.output_count.setRange(1, 100)
        self.input_count.setRange(1, 100)
        count_layout.addWidget(QLabel("Output Files:"))
        count_layout.addWidget(self.output_count)
        count_layout.addWidget(QLabel("Input Files per Output:"))
        count_layout.addWidget(self.input_count)

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

        #Control buttons
        btn_layout = QHBoxLayout()
        self.render_btn = QPushButton("Start Render")
        self.open_folder_btn = QPushButton("Open Output Folder")
        self.reset_btn = QPushButton("Reset")

        # Add button connections
        self.render_btn.clicked.connect(self.start_render)
        self.open_folder_btn.clicked.connect(self.open_output_folder)
        self.reset_btn.clicked.connect(self.reset_ui)

        btn_layout.addWidget(self.render_btn)
        btn_layout.addWidget(self.open_folder_btn)
        btn_layout.addWidget(self.reset_btn)

        # Progress area
        self.progress_area = QVBoxLayout()
        
        # Add all elements to layout
        layout.addLayout(ffmpeg_layout)
        layout.addWidget(self.file_type_combo)
        layout.addLayout(effect_layout)
        layout.addLayout(count_layout)
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
            file_type = self.file_type_combo.currentText()
            urls = event.mimeData().urls()
            
            # Check if all dragged files match the selected type
            valid_files = all(
                url.toLocalFile().lower().endswith('.mp4') if file_type == "Video"
                else url.toLocalFile().lower().endswith(('.mp3', '.wav', '.ogg', '.flac'))
                for url in urls
            )
            
            if valid_files:
                event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        files = [url.toLocalFile() for url in event.mimeData().urls()]
        self.add_files_to_list(files)

    def add_files_to_list(self, files):
        for file_path in files:
            # Handle spaces in path
            safe_path = file_path.replace('"', '').strip()
            if self.is_valid_file(safe_path):
                self.files_list.append(safe_path)
                self.file_list.addItem(safe_path)
        self.update_file_count()

    def is_valid_file(self, file_path):
        file_type = self.file_type_combo.currentText()
        if file_type == "Video":
            return file_path.lower().endswith('.mp4')
        return file_path.lower().endswith(('.mp3', '.wav', '.ogg', '.flac'))

    def open_output_folder(self):
        """Open the output folder in file explorer"""
        output_path = self.output_path_edit.text()
        if output_path and os.path.exists(output_path):
            os.startfile(output_path)
        else:
            self.show_error("Output folder does not exist")

    def reset_ui(self):
        """Reset all UI elements to default state"""
        # Clear file list
        self.clear_list()
        
        # Reset path fields
        self.output_path_edit.clear()
        self.ffmpeg_path_edit.setText("ffmpeg")
        
        # Reset combo boxes and radio buttons
        self.file_type_combo.setCurrentIndex(0)
        self.no_effect_radio.setChecked(True)
        
        # Reset spinboxes (make sure we're using the widget, not the value)
        self.output_count.setValue(1)
        self.input_count.setValue(1)
        
        # Reset naming options
        self.naming_combo.setCurrentIndex(0)
        
        # Clear SEO keywords if they exist
        if hasattr(self, 'seo_keywords'):
            del self.seo_keywords
            
        # Clear progress area
        self.clear_progress_area()
        
        # Reset any stored values
        self.ffmpeg_path = "ffmpeg"

    def select_ffmpeg(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select FFmpeg Executable", "",
            "Executable files (*.exe);;All files (*.*)"
        )
        if file_path:
            self.ffmpeg_path = file_path
            self.ffmpeg_path_edit.setText(file_path)
            self.save_ffmpeg_path()

    def save_ffmpeg_path(self):
        config_path = os.path.join(os.path.dirname(__file__), 'config.json')
        with open(config_path, 'w') as f:
            json.dump({'ffmpeg_path': self.ffmpeg_path}, f)

    def load_ffmpeg_path(self):
        config_path = os.path.join(os.path.dirname(__file__), 'config.json')
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
                self.ffmpeg_path = config.get('ffmpeg_path', 'ffmpeg')
                self.ffmpeg_path_edit.setText(self.ffmpeg_path)
        except (FileNotFoundError, json.JSONDecodeError):
            pass

    def select_output_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if folder:
            self.output_path_edit.setText(folder)

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
            # Replace other special characters
            invalid_chars = '<>:"/\\|?*'
            for char in invalid_chars:
                title = title.replace(char, '')
                
            return title
        return f"Video_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    def generate_output_filename(self, index):
        base_name = self.generate_seo_title() if self.naming_combo.currentText() == "SEO Title" else f"File_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        output_dir = self.output_path_edit.text()
        extension = ".mp3" if self.file_type_combo.currentText() == "Audio" else ".mp4"
        
        # Ensure the filename is safe for FFmpeg
        safe_name = base_name.strip().replace(' ', '_')
        return os.path.join(output_dir, f"{safe_name}_{index}{extension}")

    def create_progress_bar(self, index):
        progress_frame = QFrame()
        layout = QHBoxLayout()
        
        label = QLabel(f"File {index + 1}:")
        progress = QProgressBar()
        percentage = QLabel("0%")
        
        layout.addWidget(label)
        layout.addWidget(progress)
        layout.addWidget(percentage)
        
        progress_frame.setLayout(layout)
        self.progress_area.addWidget(progress_frame)
        
        return progress, percentage

    def start_render(self):
        if not self.validate_inputs():
            return

        self.clear_progress_area()
        self.render_btn.setEnabled(False)
        
        # Store rendering parameters correctly
        self.output_count_value = self.output_count.value()
        self.input_count_value = self.input_count.value()
        self.use_effects = self.with_effect_radio.isChecked() if self.file_type_combo.currentText() == "Video" else False
        self.current_file_index = 0
        
        # Create progress bars for all files
        self.progress_bars = []
        self.percentage_labels = []
        for i in range(self.output_count_value):
            progress_bar, percentage_label = self.create_progress_bar(i)
            self.progress_bars.append(progress_bar)
            self.percentage_labels.append(percentage_label)
        
        # Start rendering the first file
        self.render_next_file()

    def render_next_file(self):
        if self.current_file_index >= self.output_count.value():  # Get the value from QSpinBox
            self.render_btn.setEnabled(True)
            QMessageBox.information(self, "Success", "All files have been rendered!")
            return
        
        output_file = self.generate_output_filename(self.current_file_index)
        temp_list = self.create_temp_file_list(self.input_count.value())  # Get the value from QSpinBox
        
        # Get current progress bar and label
        progress_bar = self.progress_bars[self.current_file_index]
        percentage_label = self.percentage_labels[self.current_file_index]
        
        # Start rendering process
        success = self.render_file(temp_list, output_file, progress_bar, percentage_label, self.use_effects)
        
        # Cleanup temp files
        if os.path.exists(temp_list):
            os.remove(temp_list)
        
        if success:
            self.current_file_index += 1
            # Use QTimer to prevent UI blocking
            QTimer.singleShot(100, self.render_next_file)
        else:
            self.render_btn.setEnabled(True)

    def get_video_dimensions(self, video_path):
        """Get video width and height"""
        clip = VideoFileClip(video_path)
        width, height = clip.size
        clip.close()
        return width, height

    def check_video_compatibility(self, video_files):
        """Check if all videos have same dimensions"""
        if not video_files:
            return True
            
        reference_width, reference_height = self.get_video_dimensions(video_files[0])
        incompatible_files = []
        
        for video in video_files[1:]:
            width, height = self.get_video_dimensions(video)
            if width != reference_width or height != reference_height:
                incompatible_files.append(video)
        
        if incompatible_files:
            message = "Some videos have different dimensions. This may cause errors.\n"
            message += "Do you want to continue anyway?\n\n"
            message += "Incompatible files:\n" + "\n".join(incompatible_files)
            
            reply = QMessageBox.question(self, 'Warning', message, 
                                       QMessageBox.Yes | QMessageBox.No)
            
            return reply == QMessageBox.Yes
        
        return True

    def render_file(self, input_list, output_file, progress_bar, percentage_label, use_effects):
        try:
            with open(input_list, 'r', encoding='utf-8') as f:
                files = [line.strip().split("'")[1] for line in f if "file" in line]
            
            # Define is_video variable at the start
            is_video = self.file_type_combo.currentText() == "Video"
            
            cmd = self.build_ffmpeg_command(input_list, output_file, use_effects)
            print(f"Executing command: {cmd}")  # Debug output
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                shell=True
            )

            # Calculate total duration based on file type
            if is_video:
                total_duration = sum(VideoFileClip(f).duration for f in files)
            else:
                total_duration = len(files) * 180  # Assuming average 3 minutes per file
            
            while True:
                line = process.stderr.readline()
                if not line and process.poll() is not None:
                    break
                
                time_match = re.search(r'time=(\d{2}:\d{2}:\d{2}\.\d{2})', line)
                if time_match:
                    current_time = self.duration_to_seconds(time_match.group(1))
                    progress = min((current_time / total_duration) * 100, 99)
                    progress_bar.setValue(int(progress))
                    percentage_label.setText(f"{int(progress)}%")
                    QApplication.processEvents()

            if process.returncode == 0:
                progress_bar.setValue(100)
                percentage_label.setText("100%")
                QApplication.processEvents()
                self.add_metadata(output_file)
                return True
            
            return False

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Rendering failed: {str(e)}")
            return False

    def build_ffmpeg_command(self, input_list, output_file, use_effects):
        # Properly quote paths for shell execution
        quoted_input = f'"{input_list}"'
        quoted_output = f'"{output_file}"'

        if self.file_type_combo.currentText() == "Audio":
            cmd = [
                self.ffmpeg_path, '-y',
                '-f', 'concat',
                '-safe', '0',
                '-i', quoted_input,
                '-c:a', 'copy',
                quoted_output
            ]
            return ' '.join(cmd)
        else:
            TRANSITION_EFFECTS = [
                "fade", "fadeblack", "fadewhite", "distance",
                "smoothleft", "smoothright", "smoothup", "smoothdown",
                "circleclose", "circleopen", "horzclose", "horzopen", 
                "vertclose", "vertopen", "diagbl", "diagbr", "diagtl", 
                "diagtr", "hlslice", "hrslice", "vuslice", "vdslice",
                "dissolve", "hblur", "hlwind", "hrwind", "vuwind", "vdwind"
            ]

            if use_effects:
                with open(input_list, 'r', encoding='utf-8') as f:
                    video_files = [line.strip().split("'")[1] for line in f if "file" in line]
                
                video_files = [f'"{path.replace("\\", "/")}"' for path in video_files]
                quoted_output = quoted_output.replace("\\", "/")
                
                filter_complex = []
                cumulative_duration = 0
                
                for i in range(len(video_files)-1):
                    effect = random.choice(TRANSITION_EFFECTS)
                    duration = 1
                    
                    if i == 0:
                        offset = self.get_video_duration(video_files[0].strip('"')) - duration
                        cumulative_duration = offset
                        filter_complex.append(f"[0][1]xfade=transition={effect}:duration={duration}:offset={offset}[v1]")
                    else:
                        cumulative_duration += self.get_video_duration(video_files[i].strip('"')) - duration
                        filter_complex.append(f"[v{i}][{i+1}]xfade=transition={effect}:duration={duration}:offset={cumulative_duration}[v{i+1}]")

                cmd = [self.ffmpeg_path, '-y']
                for video in video_files:
                    cmd.extend(['-i', video])
                
                cmd.extend([
                    '-filter_complex', f'"{";".join(filter_complex)}"',
                    '-map', f'[v{len(video_files)-1}]',
                    '-pix_fmt', 'yuv420p',
                    '-colorspace', 'bt709',
                    '-color_primaries', 'bt709',
                    '-color_trc', 'bt709',
                    quoted_output
                ])
                return ' '.join(cmd)
            else:
                cmd = [
                    self.ffmpeg_path, '-y',
                    '-f', 'concat',
                    '-safe', '0',
                    '-i', quoted_input,
                    '-c:v', 'copy',
                    '-c:a', 'copy',
                    quoted_output
                ]
                return ' '.join(cmd)

    def duration_to_seconds(self, time_str):
        h, m, s = time_str.split(':')
        return float(h) * 3600 + float(m) * 60 + float(s)

    def get_video_duration(self, video_path):
        clip = VideoFileClip(video_path)
        duration = clip.duration
        clip.close()
        return duration

    def add_metadata(self, output_file):
        if self.naming_combo.currentText() == "SEO Title":
            metadata = {
                'title': os.path.splitext(os.path.basename(output_file))[0],
                'comment': ','.join(self.seo_keywords),
                'keywords': ','.join(self.seo_keywords),
                'rating': '5.0'
            }
            
            metadata_args = []
            for key, value in metadata.items():
                metadata_args.extend(['-metadata', f'{key}={value}'])

            temp_file = output_file + '.temp'
            os.rename(output_file, temp_file)
            
            cmd = [
                self.ffmpeg_path,
                '-i', temp_file
            ] + metadata_args + [
                '-codec', 'copy',
                output_file
            ]
            
            subprocess.run(cmd)
            os.remove(temp_file)

    def validate_inputs(self):
        if not self.files_list:
            self.show_error("Please add some files first")
            return False
            
        if not self.output_path_edit.text():
            self.show_error("Please select an output folder")
            return False
            
        if self.naming_combo.currentText() == "SEO Title" and not hasattr(self, 'seo_keywords'):
            self.show_error("Please set SEO keywords first")
            return False
            
        return True

    def show_error(self, message):
        from PyQt5.QtWidgets import QMessageBox
        QMessageBox.critical(self, "Error", message)

    def clear_progress_area(self):
        while self.progress_area.count():
            item = self.progress_area.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def add_files(self):
        """Handle adding files through button click"""
        file_type = self.file_type_combo.currentText()
        if file_type == "Video":
            files, _ = QFileDialog.getOpenFileNames(
                self,
                "Select Video Files",
                "",
                "Video Files (*.mp4)"
            )
        else:
            files, _ = QFileDialog.getOpenFileNames(
                self,
                "Select Audio Files",
                "",
                "Audio Files (*.mp3 *.wav *.ogg *.flac)"
            )
        
        self.add_files_to_list(files)

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

    def on_file_type_changed(self, file_type):
        """Handle file type combo box changes"""
        # Enable/disable effect options for video
        self.no_effect_radio.setEnabled(file_type == "Video")
        self.with_effect_radio.setEnabled(file_type == "Video")
        
        # Clear existing files as they might not be compatible
        self.clear_list()

    def create_temp_file_list(self, input_count):
        """Create temporary file list for FFmpeg"""
        selected_files = random.sample(self.files_list, min(input_count, len(self.files_list)))
        temp_list_path = os.path.join(self.output_path_edit.text(), 'temp_list.txt')
        
        with open(temp_list_path, 'w', encoding='utf-8') as f:
            for file_path in selected_files:
                f.write(f"file '{file_path}'\n")
        
        return temp_list_path

    def parse_progress(self, line):
        """Parse FFmpeg output for progress information"""
        time_match = re.search(r'time=(\d{2}:\d{2}:\d{2}\.\d{2})', line)
        if time_match:
            time_str = time_match.group(1)
            h, m, s = map(float, time_str.split(':'))
            current_seconds = h * 3600 + m * 60 + s
            # Assuming average video length of 3 minutes
            progress = min(int((current_seconds / 180) * 100), 100)
            return progress
        return None

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

