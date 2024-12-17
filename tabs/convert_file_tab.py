from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
                            QFileDialog, QSizePolicy, QListWidget, QComboBox, 
                            QRadioButton, QButtonGroup, QLineEdit, QProgressBar,
                            QSpinBox, QDoubleSpinBox, QMessageBox, QScrollArea)

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
import os
import subprocess
import os
from moviepy.editor import VideoFileClip
import time
from PyQt5.QtCore import QThread, pyqtSignal

class ConversionWorker(QThread):
    progress_updated = pyqtSignal(int, str, int)
    conversion_complete = pyqtSignal(int)
    
    def __init__(self, input_file, output_file, settings):
        super().__init__()
        self.input_file = input_file
        self.output_file = output_file
        self.settings = settings
        self.process = None
        self._is_running = True
        
    def stop(self):
        self._is_running = False
        if self.process:
            self.process.terminate()
        self.wait()
        
    def run(self):
        try:
            cmd = self.build_ffmpeg_command()
            print(f"Starting FFmpeg process with command: {' '.join(cmd)}")
            
            self.process = subprocess.Popen(
                ' '.join(cmd),
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            
            if not self._is_running:
                self.process.terminate()
                return
                
            stdout, stderr = self.process.communicate()
            
            if self.process.returncode == 0:
                print(f"Successfully converted: {self.output_file}")
                self.conversion_complete.emit(self.settings['row'])
            else:
                print(f"FFmpeg error: {stderr}")
                
        except Exception as e:
            print(f"Conversion error: {str(e)}")

    def build_ffmpeg_command(self):
        s = self.settings
        input_file = f'"{self.input_file}"'
        output_file = f'"{self.output_file}"'
        
        # Audio settings
        audio_setting = "-c:a aac -b:a 192k -ar 48000"
        
        # Video settings
        video_settings = (
            "-c:v libx264 "
            "-profile:v high "
            "-level:v 4.0 "
            "-pix_fmt yuv420p "
            "-preset slower "
            f"-r {s['fps']} "
            "-g 60 "
            "-keyint_min 30 "
            "-sc_threshold 0 "
            "-bf 2 "
            "-movflags +faststart "
            "-write_tmcd 0 "
        )
        
        # Scale filter based on resolution
        scale_filter = self.get_scale_filter(s['resolution'])
        filter_complex = f"-vf fps={s['fps']},{scale_filter}" if scale_filter else f"-vf fps={s['fps']}"
        
        # Build command based on mode
        if s['mode'] == 'manual':
            cmd = (f'ffmpeg -y -i {input_file} -threads 4 {audio_setting} '
                   f'{filter_complex} {video_settings} '
                   f'-b:v {s["bitrate"]}k -minrate {int(s["bitrate"])*0.9}k '
                   f'-maxrate {s["bitrate"]}k -bufsize {int(s["bitrate"])*2}k '
                   f'{output_file}')
        else:
            bitrate = self.get_youtube_bitrate(s['resolution'])
            cmd = (f'ffmpeg -y -i {input_file} -threads 4 {audio_setting} '
                   f'{filter_complex} {video_settings} '
                   f'-b:v {bitrate}k -minrate {int(bitrate)*0.9}k '
                   f'-maxrate {bitrate}k -bufsize {int(bitrate)*2}k '
                   f'{output_file}')
        
        return cmd.split()

    def get_scale_filter(self, resolution):
        scale_filters = {
            "4K (3840x2160)": "scale=3840:2160:force_original_aspect_ratio=decrease,pad=3840:2160:(ow-iw)/2:(oh-ih)/2",
            "2K (2560x1440)": "scale=2560:1440:force_original_aspect_ratio=decrease,pad=2560:1440:(ow-iw)/2:(oh-ih)/2",
            "1080p (1920x1080)": "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2",
            "720p (1280x720)": "scale=1280:720:force_original_aspect_ratio=decrease"
        }
        return scale_filters.get(resolution, "")

    def get_youtube_bitrate(self, resolution):
        youtube_bitrates = {
            "4K (3840x2160)": 45000,
            "2K (2560x1440)": 16000,
            "1080p (1920x1080)": 8000,
            "720p (1280x720)": 5000
        }
        return youtube_bitrates.get(resolution, 8000)

    def get_video_duration(self):
        clip = VideoFileClip(self.input_file)
        duration = clip.duration
        clip.close()
        return duration

    def parse_progress(self, output, duration):
        time_str = output.split('time=')[1].split()[0]
        current_time = sum(float(x) * 60 ** i for i, x in enumerate(reversed(time_str.split(':'))))
        progress = (current_time / duration) * 100
        time_info = f"{time_str}/{time.strftime('%H:%M:%S', time.gmtime(duration))}"
        self.progress_updated.emit(int(progress), time_info, self.settings['row'])

class CustomListWidget(QListWidget):
    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()
            
    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.setDropAction(Qt.CopyAction)
            event.accept()
        else:
            event.ignore()
            
    def dropEvent(self, event):
        files = [url.toLocalFile() for url in event.mimeData().urls()]
        valid_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.wmv']
        
        for file_path in files:
            file_path = file_path.strip('"')
            if any(file_path.lower().endswith(ext) for ext in valid_extensions):
                # Kiểm tra xem file đã tồn tại trong danh sách chưa
                existing_items = [self.item(i).text() for i in range(self.count())]
                if file_path not in existing_items:
                    self.addItem(file_path)

class ConvertFileTab(QWidget):
    def __init__(self):
        super().__init__()
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.default_font = QFont()
        self.default_font.setPointSize(11)
        self.setFont(self.default_font)
        
        self.processed_count = 0
        self.output_path = ""
        self.current_worker = None
        self.file_queue = []
        self.progress_bars = []
        self.workers = []  # Keep track of worker threads
        
        self.init_ui()
        
    def init_ui(self):
        main_layout = QHBoxLayout()
        
        # Left side - File List
        left_layout = QVBoxLayout()
        self.file_list = CustomListWidget()
        self.file_list.setMinimumWidth(400)
        
        file_controls = QHBoxLayout()
        add_btn = QPushButton("Add Files")
        add_btn.clicked.connect(self.add_files)
        remove_btn = QPushButton("Remove Selected")
        remove_btn.clicked.connect(self.remove_selected)
        
        file_controls.addWidget(add_btn)
        file_controls.addWidget(remove_btn)
        
        left_layout.addWidget(QLabel("Video Files:"))
        left_layout.addWidget(self.file_list)
        left_layout.addLayout(file_controls)
        
        # Right side - Controls
        right_layout = QVBoxLayout()
        
        # Progress counter
        self.progress_label = QLabel("Progress: 0/0")
        right_layout.addWidget(self.progress_label)
        
        # Conversion options
        self.youtube_radio = QRadioButton("YouTube Preset")
        self.manual_radio = QRadioButton("Manual Settings")
        self.youtube_radio.setChecked(True)
        
        button_group = QButtonGroup()
        button_group.addButton(self.youtube_radio)
        button_group.addButton(self.manual_radio)
        
        right_layout.addWidget(self.youtube_radio)
        right_layout.addWidget(self.manual_radio)
        
        # Create resolution combo
        self.resolution_combo = QComboBox()
        self.resolution_combo.addItems([
            "4K (3840x2160)", 
            "2K (2560x1440)", 
            "1080p (1920x1080)", 
            "720p (1280x720)"
        ])
        
        # Manual settings
        manual_settings = QVBoxLayout()
        
        # FPS Selection
        fps_layout = QHBoxLayout()
        fps_layout.addWidget(QLabel("FPS:"))
        self.fps_combo = QComboBox()
        self.fps_combo.addItems(["24", "30", "60", "100"])
        self.fps_combo.setCurrentText("30")
        fps_layout.addWidget(self.fps_combo)
        
        # Bitrate control
        self.bitrate_layout = QHBoxLayout()
        self.bitrate_layout.addWidget(QLabel("Bitrate (Mbps):"))
        self.bitrate_spin = QDoubleSpinBox()
        self.bitrate_spin.setRange(0.1, 100)
        self.bitrate_spin.setValue(8)
        self.bitrate_layout.addWidget(self.bitrate_spin)
        
        manual_settings.addLayout(fps_layout)
        manual_settings.addLayout(self.bitrate_layout)
        
        # Resolution selector
        resolution_layout = QHBoxLayout()
        resolution_layout.addWidget(QLabel("Resolution:"))
        resolution_layout.addWidget(self.resolution_combo)
        
        # Output path
        output_layout = QHBoxLayout()
        self.output_path_edit = QLineEdit()
        output_path_btn = QPushButton("Select Output")
        output_path_btn.clicked.connect(self.select_output_path)
        output_layout.addWidget(self.output_path_edit)
        output_layout.addWidget(output_path_btn)
        
        # Control buttons
        button_layout = QHBoxLayout()
        render_btn = QPushButton("Start Render")
        render_btn.clicked.connect(self.start_render)
        open_folder_btn = QPushButton("Open Output Folder")
        open_folder_btn.clicked.connect(self.open_output_folder)
        reset_btn = QPushButton("Reset All")
        reset_btn.clicked.connect(self.reset_all)
        
        button_layout.addWidget(render_btn)
        button_layout.addWidget(open_folder_btn)
        button_layout.addWidget(reset_btn)
        
        # Progress bars container with scroll area
        progress_container = QWidget()
        self.progress_layout = QVBoxLayout(progress_container)

        # Create scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(progress_container)
        scroll_area.setMinimumHeight(500)  # Set minimum height for scroll area
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        # Add all layouts to right side
        right_layout.addLayout(manual_settings)
        right_layout.addLayout(resolution_layout)
        right_layout.addLayout(output_layout)
        right_layout.addLayout(button_layout)
        right_layout.addWidget(scroll_area)  # Add scroll area instead of progress_layout
        right_layout.addStretch()

        right_layout.addStretch()
        
        # Combine left and right layouts
        main_layout.addLayout(left_layout)
        main_layout.addLayout(right_layout)
        
        self.setLayout(main_layout)
        
        # Connect signals
        self.youtube_radio.toggled.connect(self.toggle_manual_settings)
        self.manual_radio.toggled.connect(self.toggle_manual_settings)
        
        # Initialize UI state
        self.toggle_manual_settings()

    def toggle_manual_settings(self):
        manual_enabled = self.manual_radio.isChecked()
        self.bitrate_spin.setVisible(manual_enabled)
        self.bitrate_layout.itemAt(0).widget().setVisible(manual_enabled)
        
        if not manual_enabled:
            current_resolution = self.resolution_combo.currentText()
            youtube_bitrate = self.get_youtube_bitrate(current_resolution)
            self.bitrate_spin.setValue(youtube_bitrate)

    def create_resolution_combo(self):
        # Create resolution combo box
        self.resolution_combo = QComboBox()
        self.resolution_combo.addItems([
            "4K (3840x2160)", 
            "2K (2560x1440)", 
            "1080p (1920x1080)", 
            "720p (1280x720)"
        ])

    def create_manual_settings(self):
        # Create all manual settings controls
        self.fps_combo = QComboBox()
        self.fps_combo.addItems(["24", "30", "60", "100"])
        self.fps_combo.setCurrentText("30")
        
        self.bitrate_spin = QDoubleSpinBox()
        self.bitrate_spin.setRange(0.1, 100)
        self.bitrate_spin.setValue(8)
        

    def add_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select Videos", "",
            "Video Files (*.mp4 *.avi *.mov *.mkv *.wmv)")
        for file in files:
            if not self.file_list.findItems(file, Qt.MatchExactly):
                self.file_list.addItem(file)
                
    def remove_selected(self):
        for item in self.file_list.selectedItems():
            self.file_list.takeItem(self.file_list.row(item))
            
    def select_output_path(self):
        path = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if path:
            self.output_path = path
            self.output_path_edit.setText(path)
            
        
    def get_youtube_bitrate(self, resolution):
        # YouTube recommended bitrates
        bitrates = {
            "4K": 45,
            "2K": 16,
            "1080p": 8,
            "720p": 5
        }
        return bitrates.get(resolution.split()[0], 8)
        
    def start_render(self):
        if not self.output_path or not self.file_list.count():
            QMessageBox.warning(self, "Error", "Please select output directory and input files!")
            return

        # Clear previous progress bars
        for i in reversed(range(self.progress_layout.count())): 
            self.progress_layout.itemAt(i).widget().setParent(None)
        
        # Initialize progress bars
        self.progress_bars = []
        for i in range(self.file_list.count()):
            progress_bar = QProgressBar()
            progress_bar.setMaximum(100)
            progress_label = QLabel("Waiting...")
            progress_bar_layout = QHBoxLayout()
            progress_bar_layout.addWidget(progress_bar)
            progress_bar_layout.addWidget(progress_label)
            self.progress_layout.addLayout(progress_bar_layout)
            self.progress_bars.append((progress_bar, progress_label))

        # Prepare file queue
        self.file_queue = []
        for i in range(self.file_list.count()):
            input_file = self.file_list.item(i).text()
            output_file = os.path.join(self.output_path, f'convert_{os.path.basename(input_file)}')
            settings = {
                'mode': 'youtube' if self.youtube_radio.isChecked() else 'manual',
                'fps': int(self.fps_combo.currentText()),
                'bitrate': int(self.bitrate_spin.value() * 1000) if self.manual_radio.isChecked() else None,
                'resolution': self.resolution_combo.currentText(),
                'row': i
            }
            self.file_queue.append((input_file, output_file, settings))

        # Start processing first file
        self.process_next_file()

    def closeEvent(self, event):
        # Stop all running workers
        for worker in self.workers:
            worker.stop()
        super().closeEvent(event)

    def process_next_file(self):
        if not self.file_queue:
            QMessageBox.information(self, "Complete", "All conversions completed successfully!")
            return

        input_file, output_file, settings = self.file_queue.pop(0)
        worker = ConversionWorker(input_file, output_file, settings)
        worker.progress_updated.connect(self.update_progress)
        worker.conversion_complete.connect(self.file_completed)
        worker.finished.connect(lambda: self.cleanup_worker(worker))
        
        self.workers.append(worker)
        worker.start()

    def cleanup_worker(self, worker):
        if worker in self.workers:
            self.workers.remove(worker)
            worker.deleteLater()

    def update_progress(self, progress, time_info, row):
        progress_bar, label = self.progress_bars[row]
        progress_bar.setValue(progress)
        label.setText(f"Video {row + 1}: {progress}% ({time_info})")

    def file_completed(self, row):
        progress_bar, label = self.progress_bars[row]
        progress_bar.setValue(100)
        label.setText(f"Video {row + 1}: Complete")
        
        self.processed_count += 1
        self.progress_label.setText(f"Progress: {self.processed_count}/{self.file_list.count()}")
        
        # Process next file
        self.process_next_file()

        
    def open_output_folder(self):
        if self.output_path:
            os.startfile(self.output_path)
            
    def reset_all(self):
        self.file_list.clear()
        self.processed_count = 0
        self.progress_label.setText("Progress: 0/0")
        self.output_path = ""
        self.output_path_edit.clear()
        self.youtube_radio.setChecked(True)
        self.fps_combo.setCurrentText("30")
        self.bitrate_spin.setValue(8)
        self.resolution_combo.setCurrentIndex(0)
        
        # Clear progress bars - improved method
        while self.progress_layout.count():
            item = self.progress_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                # Clear nested layouts
                while item.layout().count():
                    child = item.layout().takeAt(0)
                    if child.widget():
                        child.widget().deleteLater()

