from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
                            QFileDialog, QSizePolicy, QListWidget, QComboBox, QLineEdit, 
                            QProgressBar, QRadioButton, QButtonGroup, QTextEdit, QSpinBox,
                            QGroupBox, QDialog)
from PyQt5.QtCore import Qt, QMimeData
from PyQt5.QtGui import QFont, QDragEnterEvent, QDropEvent
import os
import random
from moviepy.editor import VideoFileClip, AudioFileClip
from datetime import datetime
# Import từ cùng thư mục tabs
from .file_handlers import FileHandlers
from .video_processor import VideoProcessor
from PyQt5.QtCore import QThread, pyqtSignal
import shutil
from PyQt5.QtWidgets import QApplication
import google.generativeai as genai
import subprocess
from PyQt5.QtWidgets import QMenu, QWidgetAction
from .video_processor import EffectSelectorDialog

class DragDropList(QListWidget):
    def __init__(self, is_video=True):
        super().__init__()
        self.setAcceptDrops(True)
        self.setDragDropMode(QListWidget.DragDrop)
        self.is_video = is_video
        self.file_info = {}  # Store file info separately
        
    def dragEnterEvent(self, event: QDragEnterEvent):
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
            
    def dropEvent(self, event: QDropEvent):
        files = [url.toLocalFile() for url in event.mimeData().urls()]
        for file_path in files:
            # Only validate extension
            ext = os.path.splitext(file_path)[1].lower()
            valid_video_ext = ['.mp4', '.avi', '.mkv', '.mov']
            valid_audio_ext = ['.mp3', '.wav', '.aac', '.m4a']
            
            if self.is_video and ext not in valid_video_ext:
                continue
            if not self.is_video and ext not in valid_audio_ext:
                continue
                
            # Just add file path initially
            self.addItem(file_path)
            
        event.accept()

    def load_file_info(self, progress_callback=None):
        """Load detailed file information for all items"""
        total = self.count()
        for i in range(total):
            if progress_callback:
                progress_callback(f"Loading info for file {i+1}/{total}", (i+1)*100//total)
                
            file_path = self.item(i).text()
            try:
                if self.is_video:
                    with VideoFileClip(file_path) as video:
                        self.file_info[file_path] = {
                            'size': f"{video.size[0]}x{video.size[1]}",
                            'fps': f"{video.fps:.2f}",
                            'duration': f"{video.duration:.2f}"
                        }
                else:
                    with AudioFileClip(file_path) as audio:
                        self.file_info[file_path] = {
                            'fps': str(audio.fps),
                            'duration': f"{audio.duration:.2f}"
                        }
                        
                # Update item text with info
                self.update_item_display(i)
                
            except Exception as e:
                print(f"Error loading info for {file_path}: {e}")
                
    def update_item_display(self, index):
        """Update list item to show file info if available"""
        item = self.item(index)
        file_path = item.text()
        
        if file_path in self.file_info:
            info = self.file_info[file_path]
            if self.is_video:
                display = f"{file_path} | {info['size']} | {info['fps']}fps | {info['duration']}s"
            else:
                display = f"{file_path} | {info['fps']}Hz | {info['duration']}s"
            item.setText(display)


class VideoRenderThread(QThread):
    progress_updated = pyqtSignal(str, int)
    finished = pyqtSignal()
    error = pyqtSignal(str)
    
    def __init__(self, video_processor, params):
        super().__init__()
        self.video_processor = video_processor
        self.params = params

    def run(self):
        try:
            def progress_callback(message, percentage):
                self.progress_updated.emit(message, percentage)
                
            self.video_processor.progress_callback = progress_callback
            
            # Get total number of outputs to create
            output_count = self.params.get('output_count', 1)
            
            for i in range(output_count):
                self.progress_updated.emit(f"Starting video {i+1}/{output_count}...", 0)
                
                # Generate unique output path for each video
                base_output_path = self.params['output_path']
                output_name = self.params['generate_output_name'](i)
                final_output_path = os.path.join(base_output_path, f"{output_name}.mp4")
                
                # Process current video
                merged_video = self.video_processor.merge_videos(
                    self.params['video_paths'],
                    self.params['video_count'],
                    self.params['use_effect']
                )
                
                merged_audio = self.video_processor.merge_audio(
                    self.params['audio_paths'],
                    self.params['audio_count']
                )
                
                # Combine video and audio
                combined_video = self.video_processor.combine_video_audio(
                    merged_video,
                    merged_audio
                )
                
                # Loop the final video based on parameters
                self.progress_updated.emit("Creating final loop...", 80)
                
                if self.params['loop_mode'] == 'count':
                    target_duration = self.video_processor.get_video_duration(combined_video) * self.params['loop_count']
                elif self.params['loop_mode'] == 'duration':
                    target_duration = self.params['loop_duration']
                else:  # random duration
                    target_duration = random.uniform(
                        self.params['min_duration'],
                        self.params['max_duration']
                    )
                
                final_video = self.video_processor.loop_final_video(
                    combined_video,
                    target_duration,
                    output_name
                )
                
                # Move to final destination
                shutil.move(final_video, final_output_path)
                
                overall_progress = ((i + 1) * 100) // output_count
                self.progress_updated.emit(f"Completed video {i+1}/{output_count}", overall_progress)
                
            self.progress_updated.emit("All renders complete!", 100)
            self.finished.emit()
            
        except Exception as e:
            self.error.emit(str(e))



class CreateLongVideoTab(QWidget):
    def __init__(self):
        super().__init__()
        
        # Initialize all controls first
        self.duration_min = QLineEdit()
        self.duration_min.setPlaceholderText("00:00:00")
        self.duration_min.setInputMask("99:99:99")
        self.duration_min.setText("01:30:00")  # Set default minimum duration
        
        self.duration_max = QLineEdit()
        self.duration_max.setPlaceholderText("00:00:00")
        self.duration_max.setInputMask("99:99:99")
        self.duration_max.setText("03:30:00")  # Set default maximum duration

        self.loop_count = QSpinBox()
        self.loop_count.setRange(1, 100)
        self.loop_count.setValue(1)
        self.loop_count.setPrefix("× ")
        
        self.output_count = QSpinBox()
        self.output_count.setMinimum(1)
        self.output_count.setValue(1)
        
        # Then initialize other components
        self.API_GEMINI = [
            "AIzaSyBBd8INtemzKrMfoQ_gVWZh9bZ-LlwV8t0",
            "AIzaSyCX_sunzjmd1SdIJ21j96uLxj5HNzdemTA",
        ]
        self.file_handlers = FileHandlers()
        self.video_processor = VideoProcessor()
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        self.default_font = QFont()
        self.default_font.setPointSize(11)
        self.setFont(self.default_font)
        self.video_processor = VideoProcessor(progress_callback=self.update_progress)
        
        # Finally call init_ui()
        self.init_ui()
        self.render_thread = None

    def create_options_menu(self):
        options_menu = QMenu(self)
        
        # Duration submenu
        duration_menu = QMenu("Duration Settings", self)
        
        duration_widget = QWidget()
        duration_layout = QHBoxLayout()
        duration_layout.addWidget(QLabel("Min:"))
        duration_layout.addWidget(self.duration_min)
        duration_layout.addWidget(QLabel("Max:"))
        duration_layout.addWidget(self.duration_max)
        duration_widget.setLayout(duration_layout)
        
        duration_action = QWidgetAction(self)
        duration_action.setDefaultWidget(duration_widget)
        duration_menu.addAction(duration_action)
        
        # Loop count submenu 
        loop_menu = QMenu("Loop Settings", self)
        
        loop_widget = QWidget()
        loop_layout = QHBoxLayout()
        loop_layout.addWidget(QLabel("Loop Count:"))
        loop_layout.addWidget(self.loop_count)
        loop_widget.setLayout(loop_layout)
        
        loop_action = QWidgetAction(self)
        loop_action.setDefaultWidget(loop_widget)
        loop_menu.addAction(loop_action)
        
        # Add submenus to main menu
        options_menu.addMenu(duration_menu)
        options_menu.addMenu(loop_menu)
        
        return options_menu

    def init_ui(self):
        # Main layout
        main_layout = QVBoxLayout()
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # Control layout initialization
        control_layout = QHBoxLayout()
        
        # First Row: Lists Section
        lists_layout = QHBoxLayout()
        
        # Video Files Section
        video_group = QGroupBox("Video Files")
        video_layout = QVBoxLayout()
        self.video_list = DragDropList(is_video=True)
        video_buttons = QHBoxLayout()
        self.add_video_btn = QPushButton("Add")
        self.edit_video_btn = QPushButton("Edit")
        self.remove_video_btn = QPushButton("Remove")
        # Add "Load Info" buttons
        video_info_btn = QPushButton("Load Video Info")       
        video_buttons.addWidget(video_info_btn)

        video_buttons.addWidget(self.add_video_btn)
        video_buttons.addWidget(self.edit_video_btn)
        video_buttons.addWidget(self.remove_video_btn)
        video_layout.addWidget(self.video_list)
        video_layout.addLayout(video_buttons)
        video_group.setLayout(video_layout)

        # Audio Files Section
        audio_group = QGroupBox("Audio Files")
        audio_layout = QVBoxLayout()
        self.audio_list = DragDropList(is_video=False)
        audio_buttons = QHBoxLayout()
        self.add_audio_btn = QPushButton("Add")
        self.edit_audio_btn = QPushButton("Edit")
        self.remove_audio_btn = QPushButton("Remove")
        audio_info_btn = QPushButton("Load Audio Info")
        audio_buttons.addWidget(audio_info_btn)

        audio_buttons.addWidget(self.add_audio_btn)
        audio_buttons.addWidget(self.edit_audio_btn)
        audio_buttons.addWidget(self.remove_audio_btn)
        audio_layout.addWidget(self.audio_list)
        audio_layout.addLayout(audio_buttons)
        audio_group.setLayout(audio_layout)

        # Connect buttons
        video_info_btn.clicked.connect(lambda: self.load_file_info(self.video_list))
        audio_info_btn.clicked.connect(lambda: self.load_file_info(self.audio_list))
        # Progress Section
        progress_group = QGroupBox("Render Progress")
        progress_layout = QVBoxLayout()
        self.progress_list = QListWidget()
        self.progress_bar = QProgressBar()
        progress_layout.addWidget(self.progress_list)
        progress_layout.addWidget(self.progress_bar)
        progress_group.setLayout(progress_layout)

        # Add groups to lists layout
        lists_layout.addWidget(video_group)
        lists_layout.addWidget(audio_group)
        lists_layout.addWidget(progress_group)

        # Second Row: Options Section
        options_row_layout = QHBoxLayout()
        
        # Options Section
        options_group = QGroupBox("Options")
        options_layout = QVBoxLayout()
        
        # Video and Audio options
        merge_options = QHBoxLayout()
        self.video_count = QSpinBox()
        self.video_count.setMinimum(1)
        self.effect_combo = QComboBox()
        self.effect_combo.addItems(["No Effect", "Effect"])
        self.audio_count = QSpinBox()
        self.audio_count.setMinimum(1)
        
        merge_options.addWidget(QLabel("Videos to merge:"))
        merge_options.addWidget(self.video_count)
        merge_options.addWidget(QLabel("Effect:"))
        merge_options.addWidget(self.effect_combo)
        self.select_effects_btn = QPushButton("Select Effects")
        self.select_effects_btn.clicked.connect(self.open_effect_selector)
        merge_options.addWidget(self.select_effects_btn)  # Add this line
        merge_options.addWidget(QLabel("Audios to merge:"))
        merge_options.addWidget(self.audio_count)

        # Output options
        output_options = QHBoxLayout()
        self.output_path = QLineEdit()
        self.browse_btn = QPushButton("Browse")
        
        output_options.addWidget(QLabel("Output count:"))
        output_options.addWidget(self.output_count)
        output_options.addWidget(self.output_path)
        output_options.addWidget(self.browse_btn)
        
        options_layout.addLayout(merge_options)
        options_layout.addLayout(output_options)
        options_group.setLayout(options_layout)

        # Loop Settings Section
        loop_group = QGroupBox("Loop Settings")
        loop_layout = QVBoxLayout()

        # Radio buttons for loop type
        loop_type_layout = QHBoxLayout()
        self.loop_type_group = QButtonGroup()
        self.loop_by_count = QRadioButton("Loop by Count")
        self.loop_by_duration = QRadioButton("Loop by Duration")
        self.loop_by_count.setChecked(True)
        self.loop_type_group.addButton(self.loop_by_count)
        self.loop_type_group.addButton(self.loop_by_duration)
        loop_type_layout.addWidget(self.loop_by_count)
        loop_type_layout.addWidget(self.loop_by_duration)

        # In CreateLongVideoTab.init_ui(), update the loop settings section:

        # Loop Settings Section
        loop_group = QGroupBox("Loop Settings")
        loop_layout = QVBoxLayout()

        # Radio buttons for loop type
        loop_type_layout = QHBoxLayout()
        self.loop_type_group = QButtonGroup()
        self.loop_by_count = QRadioButton("Loop by Count")
        self.loop_by_duration = QRadioButton("Loop by Duration")
        self.loop_by_random = QRadioButton("Random Duration")
        self.loop_by_count.setChecked(True)
        self.loop_type_group.addButton(self.loop_by_count)
        self.loop_type_group.addButton(self.loop_by_duration)
        self.loop_type_group.addButton(self.loop_by_random)
        loop_type_layout.addWidget(self.loop_by_count)
        loop_type_layout.addWidget(self.loop_by_duration)
        loop_type_layout.addWidget(self.loop_by_random)

        # Loop count input
        loop_count_layout = QHBoxLayout()
        loop_count_layout.addWidget(QLabel("Loop Count:"))
        self.loop_count = QSpinBox()
        self.loop_count.setRange(1, 100)
        self.loop_count.setValue(1)
        loop_count_layout.addWidget(self.loop_count)

        # Fixed duration input
        loop_duration_layout = QHBoxLayout()
        loop_duration_layout.addWidget(QLabel("Duration (HH:MM:SS):"))
        self.loop_duration = QLineEdit()
        self.loop_duration.setInputMask("99:99:99")
        self.loop_duration.setText("00:30:00")
        self.loop_duration.setEnabled(False)
        loop_duration_layout.addWidget(self.loop_duration)

        # Random duration range inputs
        random_duration_layout = QHBoxLayout()
        random_duration_layout.addWidget(QLabel("Random Range:"))
        self.random_min = QLineEdit()
        self.random_min.setInputMask("99:99:99")
        self.random_min.setText("00:30:00")
        self.random_min.setEnabled(False)
        random_duration_layout.addWidget(self.random_min)
        random_duration_layout.addWidget(QLabel("-"))
        self.random_max = QLineEdit()
        self.random_max.setInputMask("99:99:99")
        self.random_max.setText("01:30:00")
        self.random_max.setEnabled(False)
        random_duration_layout.addWidget(self.random_max)

        # Add all to loop layout
        loop_layout.addLayout(loop_type_layout)
        loop_layout.addLayout(loop_count_layout)
        loop_layout.addLayout(loop_duration_layout)
        loop_layout.addLayout(random_duration_layout)
        loop_group.setLayout(loop_layout)

        # Add loop group to options_row_layout
        options_row_layout.addWidget(loop_group)

        # Naming Section
        naming_group = QGroupBox("Output Naming")
        naming_layout = QVBoxLayout()
        
        naming_options = QHBoxLayout()
        self.naming_options = QButtonGroup()
        auto_name = QRadioButton("Auto Name")
        user_list = QRadioButton("User List")
        ai_title = QRadioButton("AI Title")
        auto_name.setChecked(True)
        
        self.naming_options.addButton(auto_name)
        self.naming_options.addButton(user_list)
        self.naming_options.addButton(ai_title)
        
        naming_options.addWidget(auto_name)
        naming_options.addWidget(user_list)
        naming_options.addWidget(ai_title)
        
        self.title_list = QTextEdit()
        self.title_list.setPlaceholderText(
            "For User List: Enter one title per line\n\n"
            "For AI Title:\n"
            "First line: Language (e.g., English, Vietnamese)\n"
            "Following lines: Keywords"
        )
        
        naming_layout.addLayout(naming_options)
        naming_layout.addWidget(self.title_list)
        naming_group.setLayout(naming_layout)

        # SEO Options Section
        seo_group = QGroupBox("SEO Options")
        main_seo_layout = QVBoxLayout()
        
        radio_layout = QHBoxLayout()
        self.enable_seo = QRadioButton("Enable SEO")
        self.disable_seo = QRadioButton("Disable SEO")
        self.disable_seo.setChecked(True)
        radio_layout.addWidget(self.enable_seo)
        radio_layout.addWidget(self.disable_seo)
        
        self.seo_inputs = QWidget()
        inputs_layout = QVBoxLayout()
        
        self.tags_input = QTextEdit()
        self.tags_input.setPlaceholderText("Enter tags (one per line)")
        self.tags_input.setMaximumHeight(100)
        
        self.comments_input = QTextEdit()
        self.comments_input.setPlaceholderText("Enter comments (one per line)")
        self.comments_input.setMaximumHeight(100)
        
        inputs_layout.addWidget(QLabel("Tags:"))
        inputs_layout.addWidget(self.tags_input)
        inputs_layout.addWidget(QLabel("Comments:"))
        inputs_layout.addWidget(self.comments_input)
        
        self.seo_inputs.setLayout(inputs_layout)
        self.seo_inputs.setVisible(False)
        
        main_seo_layout.addLayout(radio_layout)
        main_seo_layout.addWidget(self.seo_inputs)
        seo_group.setLayout(main_seo_layout)

        # Add sections to options row
        options_row_layout.addWidget(options_group)
        options_row_layout.addWidget(naming_group)
        options_row_layout.addWidget(seo_group)

        # Add control buttons
        self.start_btn = QPushButton("Start Render")
        self.open_folder_btn = QPushButton("Open Output Folder")
        self.reset_btn = QPushButton("Reset")
        
        control_layout.addWidget(self.start_btn)
        control_layout.addWidget(self.open_folder_btn)
        control_layout.addWidget(self.reset_btn)

        # Add all layouts to main layout
        main_layout.addLayout(lists_layout)
        main_layout.addLayout(options_row_layout)
        main_layout.addLayout(control_layout)

        self.setLayout(main_layout)
        
        # Connect signals
        self.connect_signals()
    
    def get_random_duration(self):
        try:
            min_seconds = self.parse_duration(self.duration_min.text())
            max_seconds = self.parse_duration(self.duration_max.text())
            
            if min_seconds > max_seconds:
                min_seconds, max_seconds = max_seconds, min_seconds
                
            random_seconds = random.uniform(min_seconds, max_seconds)
            return random_seconds
            
        except ValueError as e:
            self.progress_list.addItem(f"Duration Error: {str(e)}")
            return 60 # Default 1 minute if error

    def open_effect_selector(self):
        dialog = EffectSelectorDialog(self.video_processor.TRANSITION_EFFECTS, self)
        if dialog.exec_() == QDialog.Accepted:  # Now QDialog should be defined
            selected_effects = dialog.get_selected_effects()
            self.video_processor.set_selected_effects(selected_effects)
        else:
            print("Error: VideoProcessor not initialized")

    def load_file_info(self, list_widget):
        """Handle loading file information with progress updates"""
        # Disable buttons during loading
        self.toggle_controls(False)
        
        # Show loading in progress list
        self.progress_list.addItem("Loading file information...")
        
        # Load info with progress updates
        list_widget.load_file_info(self.update_progress)
        
        # Re-enable controls
        self.toggle_controls(True)
        self.progress_list.addItem("File information loaded")

    def connect_signals(self):
        # File handling connections
        self.add_video_btn.clicked.connect(lambda: self.file_handlers.add_video_file(self.video_list))
        self.add_audio_btn.clicked.connect(lambda: self.file_handlers.add_audio_file(self.audio_list))
        self.edit_video_btn.clicked.connect(lambda: self.file_handlers.edit_file(self.video_list))
        self.edit_audio_btn.clicked.connect(lambda: self.file_handlers.edit_file(self.audio_list))
        self.remove_video_btn.clicked.connect(lambda: self.file_handlers.remove_file(self.video_list))
        self.remove_audio_btn.clicked.connect(lambda: self.file_handlers.remove_file(self.audio_list))
        
        # Other connections
        self.browse_btn.clicked.connect(self.browse_output_folder)
        self.reset_btn.clicked.connect(self.reset_tab)
        self.start_btn.clicked.connect(self.start_render)
        self.open_folder_btn.clicked.connect(self.open_output_folder)
        self.video_count.valueChanged.connect(self.update_effect_combo)

        # Connect loop type radio buttons
        self.loop_by_count.toggled.connect(self.toggle_loop_inputs)
        self.loop_by_duration.toggled.connect(self.toggle_loop_inputs)

        # Connect naming radio buttons to text area enable/disable
        for button in self.naming_options.buttons():
            button.toggled.connect(self.toggle_title_input)
            
        # Connect SEO radio buttons
        self.enable_seo.toggled.connect(self.toggle_seo_options)

    def toggle_loop_inputs(self):
        is_count = self.loop_by_count.isChecked()
        is_duration = self.loop_by_duration.isChecked()
        is_random = self.loop_by_random.isChecked()
        
        self.loop_count.setEnabled(is_count)
        self.loop_duration.setEnabled(is_duration)
        self.random_min.setEnabled(is_random)
        self.random_max.setEnabled(is_random)

    def toggle_title_input(self):
        """Enable/disable title input based on selected naming option"""
        selected = self.naming_options.checkedButton().text()
        
        if selected == "Auto Name":
            self.title_list.setEnabled(False)
            self.title_list.setPlaceholderText("Title input disabled for Auto Name")
        else:
            self.title_list.setEnabled(True)
            if selected == "User List":
                self.title_list.setPlaceholderText("Enter one title per line")
            else:  # AI Title
                self.title_list.setPlaceholderText(
                    "First line: Language (e.g., English, Vietnamese)\n"
                    "Following lines: Keywords"
                )

    def toggle_seo_options(self, enabled):
        """Show/hide SEO input fields"""
        if enabled:
            self.seo_inputs.setVisible(True)
        else:
            self.seo_inputs.setVisible(False)
      
    # Add this method to CreateLongVideoTab class
    def sanitize_filename(self, filename):
        # Remove invalid Windows filename characters
        invalid_chars = r'<>:"/\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        # Remove control characters
        filename = "".join(char for char in filename if ord(char) >= 32)
        # Limit length to avoid path length issues
        return filename[:200]

    # Update the generate_output_name method

    def browse_output_folder(self):
        """Open folder dialog to select output directory"""
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Output Folder",
            os.path.expanduser("~")  # Start from user's home directory
        )
        if folder:
            self.output_path.setText(folder)

    def generate_output_name(self, index):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if self.naming_options.checkedButton().text() == "Auto Name":
            base_name = f"output_{timestamp}_{index+1}"
        elif self.naming_options.checkedButton().text() == "User List":
            titles = self.title_list.toPlainText().splitlines()
            if titles:
                if not hasattr(self, 'used_titles'):
                    self.used_titles = set()
                available_titles = [t for t in titles if t not in self.used_titles]
                if not available_titles:
                    self.used_titles.clear()
                    available_titles = titles
                title = random.choice(available_titles)
                self.used_titles.add(title)
                base_name = f"{title}_{timestamp}"
            else:
                base_name = f"output_{timestamp}_{index+1}"
        else:  # AI Title
            try:
                if not hasattr(self, 'ai_titles'):
                    lines = self.title_list.toPlainText().splitlines()
                    language = lines[0].strip()
                    keywords = ", ".join(lines[1:])
                    prompt = f"Create {self.output_count.value()} YouTube video titles in {language} using these keywords: {keywords}"
                    self.ai_titles = self.get_ai_titles(prompt)
                
                if self.ai_titles:
                    title = self.ai_titles[index % len(self.ai_titles)]
                    base_name = f"{title}_{timestamp}"
                else:
                    base_name = f"ai_generated_{timestamp}_{index+1}"
            except Exception as e:
                self.progress_list.addItem(f"AI Title Error: {str(e)}")
                base_name = f"ai_generated_{timestamp}_{index+1}"
        
        return self.sanitize_filename(base_name)

    def get_ai_titles(self, prompt):
        """Get titles from AI using CreateTitleTab logic"""
        try:
            # Initialize AI generator
            api_key = random.choice(self.API_GEMINI)
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            # Generate response
            response = model.generate_content(prompt)
            
            # Parse response into list of titles
            titles = [line.strip() for line in response.text.split('\n') 
                     if line.strip() and not line.startswith(('#', '-', '*'))]
            
            return titles
            
        except Exception as e:
            self.progress_list.addItem(f"AI Generation Error: {str(e)}")
            return []


    def add_seo_metadata(self, video_path, title):
        if not self.enable_seo.isChecked():
            return
            
        try:
            tags = self.tags_input.toPlainText().splitlines()
            comments = self.comments_input.toPlainText().splitlines()
            
            # Tạo temporary file path
            temp_output = os.path.join(os.path.dirname(video_path), "temp_" + os.path.basename(video_path))
            
            # Chuẩn bị metadata arguments
            metadata_args = [
                '-metadata', f'title={title}',
                '-metadata', f'description={" | ".join(comments)}', 
                '-metadata', f'keywords={",".join(tags)}',
                '-metadata', 'rating=5.0',
                '-metadata', 'handler_name=Sourcegraph Video Handler'
            ]
            
            # Construct ffmpeg command
            cmd = [
                'ffmpeg', '-i', video_path,
                '-c', 'copy'
            ] + metadata_args + [temp_output]
            
            # Run ffmpeg
            subprocess.run(cmd, check=True, capture_output=True)
            
            # Replace original with temp file
            os.replace(temp_output, video_path)
            
        except Exception as e:
            self.progress_list.addItem(f"SEO Metadata Error: {str(e)}")



    def update_progress(self, message, percentage):
        # Ensure UI updates happen in the main thread
        self.progress_list.addItem(message)
        self.progress_list.scrollToBottom()  # Auto-scroll to latest message
        self.progress_bar.setValue(percentage)
        # Process events to keep UI responsive
        QApplication.processEvents()

    def reset_tab(self):
        self.video_list.clear()
        self.audio_list.clear()
        self.progress_list.clear()
        self.progress_bar.setValue(0)
        self.video_count.setValue(1)
        self.audio_count.setValue(1)
        self.output_count.setValue(1)
        self.duration_min.setText("01:30:00")  # Reset to default value
        self.duration_max.setText("03:30:00")  # Reset to default value
        self.output_path.clear()
        self.title_list.clear()
        self.disable_seo.setChecked(True)
        self.loop_count.setValue(1)
        self.loop_duration.setText("00:30:00")
        self.random_min.setText("00:30:00") 
        self.random_max.setText("01:30:00")
        self.loop_by_count.setChecked(True)
        self.effect_combo.setCurrentIndex(0)
     
    def start_render(self):
        # Validate inputs
        if not self.validate_inputs():
            return
            
        # Get render parameters
        params = self.get_render_params()
        
        # Create and start render thread
        self.render_thread = VideoRenderThread(self.video_processor, params)
        self.render_thread.progress_updated.connect(self.update_progress)
        self.render_thread.finished.connect(self.render_finished)
        self.render_thread.error.connect(self.render_error)
        
        # Disable controls during render
        self.toggle_controls(False)
        
        # Start rendering
        self.render_thread.start()
    
    def validate_inputs(self):
        # Check output path and set default if empty
        if not self.output_path.text():
            default_path = os.path.join(os.path.expanduser("~"), "Videos", "Rendered")
            os.makedirs(default_path, exist_ok=True)
            self.output_path.setText(default_path)
            self.update_progress(f"Using default output path: {default_path}", 0)
        
        # Continue with other validations
        if not os.path.exists(self.output_path.text()):
            os.makedirs(self.output_path.text())
            
        if self.video_list.count() == 0:
            self.update_progress("Error: No video files selected", 0)
            return False
            
        if self.audio_list.count() == 0:
            self.update_progress("Error: No audio files selected", 0)
            return False
            
        return True


    def get_render_params(self):
        params = {
            'video_paths': [self.video_list.item(i).text().split('|')[0].strip() 
                           for i in range(self.video_list.count())],
            'audio_paths': [self.audio_list.item(i).text().split('|')[0].strip() 
                           for i in range(self.audio_list.count())],
            'video_count': self.video_count.value(),
            'audio_count': self.audio_count.value(),
            'use_effect': self.effect_combo.currentText() == "Effect",
            'output_path': self.output_path.text(),
            'output_count': self.output_count.value(),
            'generate_output_name': self.generate_output_name
        }
        
        # Add loop parameters based on selected mode
        if self.loop_by_count.isChecked():
            params['loop_mode'] = 'count'
            params['loop_count'] = self.loop_count.value()
        elif self.loop_by_duration.isChecked():
            params['loop_mode'] = 'duration'
            params['loop_duration'] = self.parse_duration(self.loop_duration.text())
        else:  # Random duration
            params['loop_mode'] = 'random'
            params['min_duration'] = self.parse_duration(self.random_min.text())
            params['max_duration'] = self.parse_duration(self.random_max.text())
        
        return params

    def toggle_controls(self, enabled):
        """Enable/disable UI controls during rendering"""
        controls = [
            self.start_btn, self.reset_btn, self.video_count,
            self.audio_count, self.effect_combo, self.output_path,
            self.browse_btn
        ]
        for control in controls:
            control.setEnabled(enabled)
            
    def update_progress(self, message, percentage):
        self.progress_list.addItem(message)
        self.progress_bar.setValue(percentage)
        
    def render_finished(self):
        self.toggle_controls(True)
        self.progress_list.addItem("Rendering completed successfully!")
        
    def render_error(self, error_message):
        self.toggle_controls(True)
        self.progress_list.addItem(f"Error: {error_message}")
     
    def open_output_folder(self):
        if self.output_path.text():
            os.startfile(self.output_path.text())
            
    def update_effect_combo(self, value):
        self.effect_combo.setEnabled(value > 1)

    def parse_duration(self, duration_str):
        """Convert duration string (HH:MM:SS) to seconds"""
        try:
            # Split time components
            h, m, s = map(int, duration_str.split(':'))
            # Convert to total seconds
            return h * 3600 + m * 60 + s
        except ValueError:
            raise ValueError("Invalid duration format. Please use HH:MM:SS")
