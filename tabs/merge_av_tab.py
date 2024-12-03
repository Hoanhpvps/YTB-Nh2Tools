from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
                            QFileDialog, QSizePolicy, QRadioButton, QButtonGroup, 
                            QLineEdit, QListWidget, QProgressBar, QDialog, QTextEdit,
                            QComboBox, QMessageBox, QFrame)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont
import os, random, subprocess
from moviepy.editor import VideoFileClip, AudioFileClip
import nltk
from nltk.tokenize import word_tokenize
from nltk.tag import pos_tag
import re
import random
from itertools import combinations
#import resource

class TitleManager:
    def __init__(self):
        self.used_titles = set()
        self.title_templates = [
            "{adj} {noun} {action}",
            "{noun} {action} {adj}",
            "The {adj} {noun}",
            "{adj} {noun} {time}",
            "Best {noun} {action}"
        ]
        
        self.adjectives = ["Amazing", "Beautiful", "Creative", "Dynamic", "Exciting", 
                          "Fantastic", "Great", "Happy", "Incredible", "Joyful"]
        self.nouns = ["Adventure", "Journey", "Story", "Moment", "Experience",
                     "Discovery", "Creation", "Memory", "Dream", "Vision"]
        self.actions = ["Guide", "Tutorial", "Review", "Showcase", "Highlights",
                       "Experience", "Journey", "Adventure", "Exploration"]
        self.time_refs = ["2024", "Today", "Now", "Special", "Ultimate"]

    def generate_unique_title(self):
        max_attempts = 50
        attempts = 0
        
        while attempts < max_attempts:
            template = random.choice(self.title_templates)
            title = template.format(
                adj=random.choice(self.adjectives),
                noun=random.choice(self.nouns),
                action=random.choice(self.actions),
                time=random.choice(self.time_refs)
            )
            
            if title not in self.used_titles:
                self.used_titles.add(title)
                return title
            attempts += 1
            
        # If no unique title found, append timestamp
        return f"{title}_{int(time.time())}"

    def get_random_keywords(self, num_keywords=5):
        all_words = self.adjectives + self.nouns + self.actions
        selected = random.sample(all_words, min(num_keywords, len(all_words)))
        return selected

class CustomAVListWidget(QListWidget):
    def __init__(self, accepted_formats):
        super().__init__()
        self.accepted_formats = accepted_formats
        self.setAcceptDrops(True)
        self.setDragDropMode(QListWidget.DragDrop)
        
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if any(url.toLocalFile().lower().endswith(ext) for ext in self.accepted_formats):
                    event.accept()
                    return
        event.ignore()
            
    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.setDropAction(Qt.CopyAction)
            event.accept()
        else:
            event.ignore()
            
    def dropEvent(self, event):
        files = [url.toLocalFile() for url in event.mimeData().urls()]
        valid_files = []
        
        for file_path in files:
            clean_path = file_path.replace('"', '').strip()
            if any(clean_path.lower().endswith(ext) for ext in self.accepted_formats):
                if not self.findItems(clean_path, Qt.MatchExactly):
                    valid_files.append(clean_path)
                    
        if valid_files:
            self.addItems(valid_files)
            event.accept()
        else:
            event.ignore()

class KeywordsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("SEO Keywords")
        self.setModal(True)
        layout = QVBoxLayout()
        
        self.keywords_edit = QTextEdit()
        self.keywords_edit.setPlaceholderText("Enter keywords (one per line)")
        
        save_btn = QPushButton("Save Keywords")
        save_btn.clicked.connect(self.accept)
        
        layout.addWidget(QLabel("Enter SEO Keywords:"))
        layout.addWidget(self.keywords_edit)
        layout.addWidget(save_btn)
        
        self.setLayout(layout)

class MergeAVWorker(QThread):
    progress_updated = pyqtSignal(int, str, int)
    merge_complete = pyqtSignal(int)
    
    def __init__(self, video_path, audio_path, output_path, settings):
        super().__init__()
        self.video_path = video_path
        self.audio_path = audio_path
        self.output_path = output_path
        self.settings = settings

    def run(self):
        try:
            # Implementation of merge logic here
            # This will vary based on live/public option
            pass
        except Exception as e:
            print(f"Conversion error: {str(e)}")
class MergeAVTab(QWidget):
    def __init__(self):
        super().__init__()
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.default_font = QFont()
        self.default_font.setPointSize(11)
        self.setFont(self.default_font)
        
        self.keywords_list = []
        self.output_path = ""
        self.processed_count = 0
        self.progress_bars = []
        self.current_worker = None  # Chỉ theo dõi 1 worker
        # Thêm queue manager
        self.merge_queue = []
        self.is_processing = False
        self.max_concurrent = 1  # Số lượng xử lý đồng thời
        try:
            nltk.data.find('tokenizers/punkt')
        except LookupError:
            nltk.download('punkt')
            nltk.download('averaged_perceptron_tagger')
            # Add this line after other initializations
        self.title_manager = TitleManager()
        self.init_merge_ui()
        self.workers = [] # Track active workers
    
    def closeEvent(self, event):
        if self.current_worker and self.current_worker.isRunning():
            self.current_worker.stop()
        super().closeEvent(event)

    def init_merge_ui(self):
        main_layout = QVBoxLayout()
        
        # Create options layout with frames
        options_layout = QHBoxLayout()
        
        # Merge type frame
        merge_frame = QFrame()
        merge_frame.setFrameStyle(QFrame.StyledPanel)
        merge_layout = QHBoxLayout(merge_frame)
        merge_layout.addWidget(QLabel("Merge Type:"))
        self.few_radio = QRadioButton("Ghép theo số ít")
        self.many_radio = QRadioButton("Ghép theo số nhiều")
        self.few_radio.setChecked(True)
        merge_group = QButtonGroup()
        merge_group.addButton(self.few_radio)
        merge_group.addButton(self.many_radio)
        merge_layout.addWidget(self.few_radio)
        merge_layout.addWidget(self.many_radio)
        
        # Render type frame
        render_frame = QFrame()
        render_frame.setFrameStyle(QFrame.StyledPanel)
        render_layout = QHBoxLayout(render_frame)
        render_layout.addWidget(QLabel("Render Type:"))
        self.live_radio = QRadioButton("Live Video")
        self.public_radio = QRadioButton("Public Video")
        self.live_radio.setChecked(True)
        render_group = QButtonGroup()
        render_group.addButton(self.live_radio)
        render_group.addButton(self.public_radio)
        render_layout.addWidget(self.live_radio)
        render_layout.addWidget(self.public_radio)
        
        options_layout.addWidget(merge_frame)
        options_layout.addWidget(render_frame)
        
        # File lists section
        lists_layout = QHBoxLayout()
        
        # Video list
        video_layout = QVBoxLayout()
        self.video_list = CustomAVListWidget(['.mp4', '.avi', '.mov', '.mkv'])
        video_controls = QHBoxLayout()
        add_video_btn = QPushButton("Add Videos")
        remove_video_btn = QPushButton("Remove Selected")
        video_controls.addWidget(add_video_btn)
        video_controls.addWidget(remove_video_btn)
        
        self.video_count_label = QLabel("Videos: 0")
        video_layout.addWidget(QLabel("Video Files:"))
        video_layout.addWidget(self.video_list)
        video_layout.addLayout(video_controls)
        video_layout.addWidget(self.video_count_label)
        
        # Audio list
        audio_layout = QVBoxLayout()
        self.audio_list = CustomAVListWidget(['.mp3', '.wav', '.aac', '.m4a'])
        audio_controls = QHBoxLayout()
        add_audio_btn = QPushButton("Add Audio")
        remove_audio_btn = QPushButton("Remove Selected")
        audio_controls.addWidget(add_audio_btn)
        audio_controls.addWidget(remove_audio_btn)
        
        self.audio_count_label = QLabel("Audio: 0")
        audio_layout.addWidget(QLabel("Audio Files:"))
        audio_layout.addWidget(self.audio_list)
        audio_layout.addLayout(audio_controls)
        audio_layout.addWidget(self.audio_count_label)
        
        lists_layout.addLayout(video_layout)
        lists_layout.addLayout(audio_layout)
        
        # Output settings
        output_layout = QHBoxLayout()
        self.output_path_edit = QLineEdit()
        output_path_btn = QPushButton("Select Output Folder")
        output_layout.addWidget(self.output_path_edit)
        output_layout.addWidget(output_path_btn)
        
        # Output naming options
        naming_layout = QHBoxLayout()
        self.naming_combo = QComboBox()
        self.naming_combo.addItems(["Audio Name", "Video Name", "Auto Generate", "SEO Title"])
        self.seo_btn = QPushButton("SEO Settings")
        naming_layout.addWidget(QLabel("Output Naming:"))
        naming_layout.addWidget(self.naming_combo)
        naming_layout.addWidget(self.seo_btn)
        
        # Control buttons
        controls_layout = QHBoxLayout()
        render_btn = QPushButton("Start Render")
        open_folder_btn = QPushButton("Open Output Folder")
        reset_btn = QPushButton("Reset All")
        controls_layout.addWidget(render_btn)
        controls_layout.addWidget(open_folder_btn)
        controls_layout.addWidget(reset_btn)
        
        # Progress area
        self.progress_layout = QVBoxLayout()
        
        # Add all layouts to main layout
        main_layout.addLayout(options_layout)
        main_layout.addLayout(lists_layout)
        main_layout.addLayout(output_layout)
        main_layout.addLayout(naming_layout)
        main_layout.addLayout(controls_layout)
        main_layout.addLayout(self.progress_layout)
        
        self.setLayout(main_layout)
        
        # Connect signals
        add_video_btn.clicked.connect(self.add_videos)
        remove_video_btn.clicked.connect(lambda: self.remove_selected(self.video_list))
        add_audio_btn.clicked.connect(self.add_audio)
        remove_audio_btn.clicked.connect(lambda: self.remove_selected(self.audio_list))
        output_path_btn.clicked.connect(self.select_output_path)
        self.seo_btn.clicked.connect(self.show_seo_dialog)
        render_btn.clicked.connect(self.start_render)
        open_folder_btn.clicked.connect(self.open_output_folder)
        reset_btn.clicked.connect(self.reset_all)
        
        # Connect list change signals
        self.video_list.model().rowsInserted.connect(lambda: self.update_count_label(self.video_list, self.video_count_label, "Videos"))
        self.video_list.model().rowsRemoved.connect(lambda: self.update_count_label(self.video_list, self.video_count_label, "Videos"))
        self.audio_list.model().rowsInserted.connect(lambda: self.update_count_label(self.audio_list, self.audio_count_label, "Audio"))
        self.audio_list.model().rowsRemoved.connect(lambda: self.update_count_label(self.audio_list, self.audio_count_label, "Audio"))


    def add_videos(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select Video Files", "",
            "Video Files (*.mp4 *.avi *.mov *.mkv)"
        )
        for file in files:
            clean_path = file.replace('"', '')
            if not self.video_list.findItems(clean_path, Qt.MatchExactly):
                self.video_list.addItem(clean_path)

    def add_audio(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select Audio Files", "",
            "Audio Files (*.mp3 *.wav *.aac *.m4a)"
        )
        for file in files:
            clean_path = file.replace('"', '')
            if not self.audio_list.findItems(clean_path, Qt.MatchExactly):
                self.audio_list.addItem(clean_path)

    def remove_selected(self, list_widget):
        for item in list_widget.selectedItems():
            list_widget.takeItem(list_widget.row(item))

    def update_count_label(self, list_widget, label, prefix):
        count = list_widget.count()
        if count > 0:
            label.setText(f"{prefix} ({count} files)")
        else:
            label.setText(f"{prefix}: 0")

    def select_output_path(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if folder:
            self.output_path = folder
            self.output_path_edit.setText(folder)

    def show_seo_dialog(self):
        dialog = KeywordsDialog(self)
        if dialog.exec_():
            self.keywords_list = dialog.keywords_edit.toPlainText().split('\n')
            self.keywords_list = [k.strip() for k in self.keywords_list if k.strip()]

    def generate_seo_title(self, keywords):
        # Create meaningful phrases from keywords
        words = []
        for keyword in keywords[:5]:  # Use only first 5 keywords
            words.extend(word_tokenize(keyword))
        
        # Tag parts of speech
        tagged = pos_tag(words)
        
        # Prioritize nouns and adjectives
        important_words = [word for word, tag in tagged if tag.startswith(('NN', 'JJ'))]
        
        # Take first 4-5 important words
        title_words = important_words[:4]
        
        # Join words and clean the title
        raw_title = " ".join(title_words)
        
        # Clean special characters and spaces
        clean_title = self.clean_filename(raw_title)
        
        return clean_title

    def clean_filename(self, filename):
        # Remove or replace invalid characters
        clean = re.sub(r'[<>:"/\\|?*]', '', filename)
        # Replace multiple spaces with single space
        clean = re.sub(r'\s+', ' ', clean)
        # Trim length
        clean = clean[:50]  # Limit length to 50 characters
        # Remove trailing spaces and periods
        clean = clean.strip('. ')
        return clean

    def generate_output_filename(self, video_path, audio_path):
        naming_mode = self.naming_combo.currentText()
        base_name = ""
        
        if naming_mode == "SEO Title":
            # Generate unique title and keywords
            title = self.title_manager.generate_unique_title()
            if not self.keywords_list:
                self.keywords_list = self.title_manager.get_random_keywords()
            base_name = f"{title}_{'-'.join(random.sample(self.keywords_list, min(3, len(self.keywords_list))))}"
        elif naming_mode == "Auto Generate":
            base_name = f"video_{self.title_manager.generate_unique_title()}"
        else:
            # Original logic for Audio/Video name
            base_name = os.path.splitext(os.path.basename(audio_path if naming_mode == "Audio Name" else video_path))[0]
        
        clean_base = self.clean_filename(base_name)
        return f"{clean_base}_merged.mp4"

    def start_render(self):
        if not self.output_path:
            QMessageBox.warning(self, "Error", "Please select output directory!")
            return
            
        if self.video_list.count() == 0 or self.audio_list.count() == 0:
            QMessageBox.warning(self, "Error", "Please add both video and audio files!")
            return

        # Get files first
        video_files = [self.video_list.item(i).text() for i in range(self.video_list.count())]
        audio_files = [self.audio_list.item(i).text() for i in range(self.audio_list.count())]
        merge_pairs = self.generate_merge_pairs(video_files, audio_files)

        # Clear old progress bars
        while self.progress_layout.count():
            item = self.progress_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                while item.layout().count():
                    child = item.layout().takeAt(0)
                    if child.widget():
                        child.widget().deleteLater()

        # Create new progress bars
        self.progress_bars = []
        for i in range(len(merge_pairs)):
            progress_bar = QProgressBar()
            progress_bar.setMaximum(100)
            progress_label = QLabel("Waiting...")
            progress_bar_layout = QHBoxLayout()
            progress_bar_layout.addWidget(progress_bar)
            progress_bar_layout.addWidget(progress_label)
            self.progress_layout.addLayout(progress_bar_layout)
            self.progress_bars.append((progress_bar, progress_label))

        # Start processing
        self.process_merge_pairs(merge_pairs)


    def on_merge_type_changed(self, button):
        # Xử lý khi thay đổi chế độ ghép
        print(f"Merge type selected: {button.text()}")
        
        # Đảm bảo các radio button luôn hiển thị và hoạt động
        self.few_radio.setVisible(True)
        self.many_radio.setVisible(True)
        self.few_radio.setEnabled(True)
        self.many_radio.setEnabled(True)

    def on_render_type_changed(self, button):
        # Xử lý khi thay đổi chế độ render
        print(f"Render type selected: {button.text()}")
        
        # Đảm bảo các radio button luôn hiển thị và hoạt động
        self.live_radio.setVisible(True)
        self.public_radio.setVisible(True)
        self.live_radio.setEnabled(True)
        self.public_radio.setEnabled(True)

    def generate_merge_pairs(self, video_files, audio_files):
        video_count = len(video_files)
        audio_count = len(audio_files)
        
        available_videos = video_files.copy()
        available_audios = audio_files.copy()
        pairs = []

        # Using few_radio for "Ghép theo số ít"
        if self.few_radio.isChecked():
            # Logic for "số ít" - pair minimum number
            if video_count > audio_count:
                random.shuffle(available_videos)
                for audio in audio_files:
                    video = available_videos.pop(0)
                    pairs.append((video, audio))
            else:
                random.shuffle(available_audios)
                for video in video_files:
                    audio = available_audios.pop(0)
                    pairs.append((video, audio))
        else:
            # Logic for "số nhiều" - maximum pairs
            if video_count < audio_count:
                while available_audios:
                    if not available_videos:
                        available_videos = video_files.copy()
                    video = random.choice(available_videos)
                    audio = available_audios.pop(0)
                    pairs.append((video, audio))
            else:
                while available_videos:
                    if not available_audios:
                        available_audios = audio_files.copy()
                    audio = random.choice(available_audios)
                    video = available_videos.pop(0)
                    pairs.append((video, audio))

        return pairs

    def process_next_merge(self):
        if not self.is_processing or not self.merge_queue:
            self.is_processing = False
            QMessageBox.information(self, "Complete", "All merges completed successfully!")
            return

        video_path, audio_path = self.merge_queue.pop(0)
        output_name = self.generate_output_filename(video_path, audio_path)
        output_path = os.path.join(self.output_path, output_name)
        
        settings = {
            'is_live': self.live_radio.isChecked(),
            'keywords': self.keywords_list if self.naming_combo.currentText() == "SEO Title" else [],
            'row': self.processed_count
        }
        
        worker = MergeAVWorker(video_path, audio_path, output_path, settings)
        worker.progress_updated.connect(self.update_progress)
        worker.merge_complete.connect(self.on_merge_complete)
        worker.finished.connect(lambda: self.cleanup_worker(worker))
        
        self.workers.append(worker)
        self.current_worker = worker
        worker.start()

    def cleanup_worker(self, worker):
        if worker in self.workers:
            self.workers.remove(worker)
            worker.deleteLater()
            
        # Tiếp tục xử lý file tiếp theo nếu còn
        if self.merge_queue:
            self.process_next_merge()


    def process_merge_pairs(self, merge_pairs):
        self.merge_queue = merge_pairs
        self.processed_count = 0
        self.is_processing = True
        
        # Khởi chạy các worker theo số lượng cho phép
        for _ in range(min(self.max_concurrent, len(self.merge_queue))):
            self.process_next_merge()

    def on_merge_complete(self, row):
        progress_bar, label = self.progress_bars[row]
        progress_bar.setValue(100)
        label.setText(f"Merge {row + 1}: Complete")
        
        self.processed_count += 1
        self.process_next_merge()  # Process next pair automatically


    def merge_completed(self, row):
        progress_bar, label = self.progress_bars[row]
        progress_bar.setValue(100)
        label.setText(f"Merge {row + 1}: Complete")
        
        self.processed_count += 1
        # Process next file in queue
        self.process_next_merge()

    def update_progress(self, progress, time_info, row):
        progress_bar, label = self.progress_bars[row]
        progress_bar.setValue(progress)
        label.setText(f"Merge {row + 1}: {progress}% ({time_info})")

    def merge_completed(self, row):
        progress_bar, label = self.progress_bars[row]
        progress_bar.setValue(100)
        label.setText(f"Merge {row + 1}: Complete")
        
        self.processed_count += 1
        if self.processed_count == len(self.progress_bars):
            QMessageBox.information(self, "Complete", "All merges completed successfully!")

    def open_output_folder(self):
        if self.output_path and os.path.exists(self.output_path):
            os.startfile(self.output_path)
        else:
            QMessageBox.warning(self, "Error", "Output folder not found!")

    def reset_all(self):
        # Stop any running workers
        if self.current_worker:
            self.current_worker.stop()
            self.current_worker = None
        self.merge_queue.clear()

        for worker in self.workers:
            worker.stop()
        self.workers.clear()
        self.video_list.clear()
        self.audio_list.clear()
        self.output_path = ""
        self.output_path_edit.clear()
        self.keywords_list = []
        self.processed_count = 0
        self.few_radio.setChecked(True)
        self.live_radio.setChecked(True)
        self.naming_combo.setCurrentIndex(0)
        
        # Clear progress bars safely
        while self.progress_layout.count():
            item = self.progress_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                while item.layout().count():
                    child = item.layout().takeAt(0)
                    if child.widget():
                        child.widget().deleteLater()


class MergeAVWorker(QThread):
    progress_updated = pyqtSignal(int, str, int)
    merge_complete = pyqtSignal(int)
    
    def __init__(self, video_path, audio_path, output_path, settings):
        super().__init__()
        self.video_path = video_path
        self.audio_path = audio_path 
        self.output_path = output_path
        self.settings = settings
        self.temp_files = []
        self.is_running = True
        self.process = None

    def stop(self):
        self.is_running = False
        self.wait() # Wait for thread to finish
      
    def run(self):
        try:
            # Giới hạn memory usage
            max_memory = 1024 * 1024 * 1024  # 1GB
            resource.setrlimit(resource.RLIMIT_AS, (max_memory, max_memory))
            
            # Xử lý theo chunks để tránh memory leak
            chunk_size = 1024 * 1024  # 1MB chunks
            
            while self.is_running:
                # Process data in chunks
                if not data_chunk:
                    break
                    
                # Emit progress
                self.progress_updated.emit(progress, time_info, row)
                
        except Exception as e:
            print(f"Error: {e}")
            
        finally:
            self.cleanup()
        try:
            if not self.is_running:
                return
                
            audio = AudioFileClip(self.audio_path)
            audio_duration = audio.duration
            audio.close()

            if self.settings['is_live']:
                cmd = self.build_live_command(audio_duration)
            else:
                cmd = self.build_public_command(audio_duration)

            process = subprocess.Popen(
                cmd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )

            while process.poll() is None and self.is_running:
                output = process.stderr.readline()
                if output == '':
                    break
                    
                if 'time=' in output:
                    try:
                        current_time = self.parse_time(output)
                        progress = min((current_time / audio_duration) * 100, 100)
                        time_info = f"{self.format_time(current_time)}/{self.format_time(audio_duration)}"
                        self.progress_updated.emit(int(progress), time_info, self.settings['row'])
                    except ValueError:
                        continue

            if not self.is_running:
                process.terminate()
                return

            if self.settings['keywords']:
                self.add_metadata()

            # Clean up temporary files
            for temp_file in self.temp_files:
                if os.path.exists(temp_file):
                    os.remove(temp_file)

            self.merge_complete.emit(self.settings['row'])

        except Exception as e:
            print(f"Merge error: {str(e)}")
        finally:
            self.is_running = False

    
    def cleanup(self):
        for temp_file in self.temp_files:
            if os.path.exists(temp_file):
                os.remove(temp_file)

    def build_live_command(self, audio_duration):
        return (
            f'ffmpeg -y -stream_loop -1 -i "{self.video_path}"  -i "{self.audio_path}" '
            '-map 0:v -map 1:a '
            f'-t {audio_duration} '
            '-c:v libx264 -preset veryfast '
            '-b:v 6000k -maxrate 6000k -bufsize 12000k '
            '-g 50 -keyint_min 25 '
            '-sc_threshold 0 '
            '-c:a aac -b:a 320k -ar 44100 '
            f'"{self.output_path}"'
        )

    def build_public_command(self, audio_duration):
        video = VideoFileClip(self.video_path)
        video_duration = video.duration
        video.close()
        
        concat_file = self.create_concat_file(audio_duration, video_duration)
        
        cmd = (
            f'ffmpeg -y -hwaccel auto -f concat -safe 0 -i "{concat_file}" '
            f'-i "{self.audio_path}" '
            '-map 0:v -map 1:a '
            '-c copy -bsf:v h264_mp4toannexb '  # Copy video stream directly
            '-shortest '
            '-avoid_negative_ts make_zero '
            '-fflags +shortest '
            '-max_interleave_delta 0 '
            '-vsync 0 '
            f'"{self.output_path}"'
        )
    
        self.temp_files.append(concat_file)
        return cmd


    def create_concat_file(self, target_duration, video_duration):
        # Tính số lần lặp cần thiết và thêm dư 1 để đảm bảo đủ độ dài
        repeat_count = int(target_duration / video_duration) + 1
        concat_content = f"file '{self.video_path}'\n" * repeat_count
        concat_file = os.path.splitext(self.output_path)[0] + "_concat.txt"
        
        with open(concat_file, 'w', encoding='utf-8') as f:
            f.write(concat_content)
        return concat_file
        
    def add_metadata(self):
        keywords = self.settings['keywords']
        comment = " ".join(random.sample(keywords, min(5, len(keywords))))
        
        metadata_cmd = (
            f'ffmpeg -i "{self.output_path}" -c copy '
            f'-metadata title="{" ".join(keywords[:3])}" '
            f'-metadata artist="Auto Generated" '
            f'-metadata comment="{comment}" '
            f'-metadata description="{" ".join(keywords)}" '
            f'-metadata rating="5" '
            f'-metadata tags="{",".join(keywords)}" '
            f'"{self.output_path}_temp.mp4"'
        )
        
        subprocess.run(metadata_cmd, shell=True)
        os.replace(f"{self.output_path}_temp.mp4", self.output_path)
        
    def parse_time(self, output):
        time_str = output.split('time=')[1].split()[0]
        h, m, s = map(float, time_str.split(':'))
        return h * 3600 + m * 60 + s
        
    def format_time(self, seconds):
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        return f"{h:02d}:{m:02d}:{s:02d}"
