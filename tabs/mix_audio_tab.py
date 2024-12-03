from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QPushButton, 
                           QLabel, QLineEdit, QFileDialog, QProgressBar, QComboBox, 
                           QFrame, QSizePolicy)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont
from pydub import AudioSegment
import os
import random
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QPushButton, 
                           QLabel, QLineEdit, QFileDialog, QProgressBar, QComboBox, 
                           QFrame, QSizePolicy, QMessageBox, QSlider)  # Added QMessageBox here

class DragDropList(QListWidget):
    file_dropped = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.setDragDropMode(QListWidget.DragDrop)
        self.setSelectionMode(QListWidget.ExtendedSelection)
        
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls() or event.mimeData().hasText():
            event.accept()
        else:
            event.ignore()
            
    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls() or event.mimeData().hasText():
            event.setDropAction(Qt.CopyAction)
            event.accept()
        else:
            event.ignore()
            
    def dropEvent(self, event):
        files = []
        if event.mimeData().hasUrls():
            files = [url.toLocalFile() for url in event.mimeData().urls()]
        elif event.mimeData().hasText():
            files = [file.strip('"') for file in event.mimeData().text().split('\n')]
            
        valid_files = []
        for file_path in files:
            # Remove quotes and normalize path
            clean_path = file_path.strip('"').strip("'").strip()
            if os.path.isfile(clean_path) and clean_path.lower().endswith(('.mp3', '.wav')):
                valid_files.append(clean_path)
                
        if valid_files:
            self.addItems(valid_files)
            self.file_dropped.emit()
            event.accept()
        else:
            event.ignore()

class BatchMixingWorker(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal()
    
    def __init__(self, main_files, mix1_files, mix2_files, output_path, 
                 filename_option, bitrate, mix_mode, main_volume, mix1_volume, mix2_volume):
        super().__init__()
        self.main_files = main_files
        self.mix1_files = mix1_files
        self.mix2_files = mix2_files
        self.output_path = output_path
        self.filename_option = filename_option
        self.bitrate = bitrate
        self.mix_mode = mix_mode
        self.main_volume = main_volume
        self.mix1_volume = mix1_volume
        self.mix2_volume = mix2_volume
    
    def run(self):
        total_files = len(self.main_files)
        for index, main_file in enumerate(self.main_files):
            base_progress = (index * 100) // total_files
            
            worker = MixingWorker(
                main_file,
                self.mix1_files,
                self.mix2_files,
                self.output_path,
                self.filename_option,
                self.bitrate,
                self.mix_mode,
                self.main_volume,    # Thêm volume values
                self.mix1_volume,
                self.mix2_volume
            )

            worker.progress.connect(
                lambda p, base=base_progress, total=total_files: 
                self.progress.emit(int(base + (p / total)))
            )
            
            worker.run()
            
        self.progress.emit(100)
        self.finished.emit()

class MixingWorker(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal()
    
    def __init__(self, main_file, mix1_files, mix2_files, output_path, 
                 filename_option, bitrate, mix_mode, main_volume, mix1_volume, mix2_volume):
        super().__init__()
        self.main_file = main_file
        self.mix1_files = mix1_files
        self.mix2_files = mix2_files
        self.output_path = output_path
        self.filename_option = filename_option
        self.bitrate = bitrate
        self.mix_mode = mix_mode
        self.main_volume = main_volume
        self.mix1_volume = mix1_volume
        self.mix2_volume = mix2_volume

    def run(self):
        main_audio = AudioSegment.from_file(self.main_file)
        main_audio = self.normalize_audio(main_audio)
        self.progress.emit(10)

        # Generate output filename
        if self.filename_option == "Use Main Audio name":
            self.output_name = os.path.splitext(os.path.basename(self.main_file))[0] + "_mixed.mp3"
        else:
            existing_files = os.listdir(self.output_path)
            counter = 1
            while f"audio_mix_{counter}.mp3" in existing_files:
                counter += 1
            self.output_name = f"audio_mix_{counter}.mp3"

        if self.mix_mode == "Standard Mix":
            self.standard_mix()
        else:
            self.dynamic_mix()

    def standard_mix(self):
        # Load và áp dụng volume cho main audio
        main_audio = AudioSegment.from_file(self.main_file)
        main_audio = main_audio + self.main_volume  # Áp dụng volume chính
        
        if self.mix1_files and self.mix2_files:
            # Load và áp dụng volume cho mix1
            mix1 = AudioSegment.from_file(random.choice(self.mix1_files))
            mix1 = self.adjust_audio_length(mix1, len(main_audio))
            mix1 = mix1 + self.mix1_volume  # Áp dụng volume mix1
            
            # Load và áp dụng volume cho mix2
            mix2 = AudioSegment.from_file(random.choice(self.mix2_files))
            mix2 = self.adjust_audio_length(mix2, len(main_audio))
            mix2 = mix2 + self.mix2_volume  # Áp dụng volume mix2
            
            # Mix các audio đã điều chỉnh volume
            final_mix = main_audio.overlay(mix1).overlay(mix2)
            
        elif self.mix1_files:
            mix1 = AudioSegment.from_file(random.choice(self.mix1_files))
            mix1 = self.adjust_audio_length(mix1, len(main_audio))
            mix1 = mix1 + self.mix1_volume  # Áp dụng volume mix1
            final_mix = main_audio.overlay(mix1)
        else:
            final_mix = main_audio
        
        output_path = os.path.join(self.output_path, self.output_name)
        final_mix.export(output_path, format="mp3", bitrate=self.bitrate.split()[0] + "k")


    def dynamic_mix(self):
        main_audio = AudioSegment.from_file(self.main_file)
        main_audio = self.normalize_audio(main_audio)
        
        if self.mix1_files and self.mix2_files:
            mix1 = AudioSegment.from_file(random.choice(self.mix1_files))
            mix2 = AudioSegment.from_file(random.choice(self.mix2_files))
            
            mix1 = self.adjust_audio_length(mix1, len(main_audio))
            mix2 = self.adjust_audio_length(mix2, len(main_audio))
            
            mix1 = self.normalize_audio(mix1)
            mix2 = self.normalize_audio(mix2)
            
            adjusted_mix1 = self.dynamic_volume_adjustment(main_audio, mix1)
            adjusted_mix2 = self.dynamic_volume_adjustment(main_audio, mix2)
            
            final_mix = main_audio.overlay(adjusted_mix1, gain_during_overlay=-6)
            final_mix = final_mix.overlay(adjusted_mix2, gain_during_overlay=-6)
            
            final_mix = self.normalize_audio(final_mix)
            
        elif self.mix1_files:
            mix1 = AudioSegment.from_file(random.choice(self.mix1_files))
            mix1 = self.adjust_audio_length(mix1, len(main_audio))
            mix1 = self.normalize_audio(mix1)
            
            adjusted_mix1 = self.dynamic_volume_adjustment(main_audio, mix1)
            final_mix = main_audio.overlay(adjusted_mix1, gain_during_overlay=-6)
            final_mix = self.normalize_audio(final_mix)
            
        else:
            final_mix = main_audio
        
        output_path = os.path.join(self.output_path, self.output_name)
        final_mix.export(output_path, format="mp3", bitrate=self.bitrate.split()[0] + "k")

    # Audio processing helper methods
    def normalize_audio(self, audio_segment, target_dbfs=-20.0):
        change_in_dbfs = target_dbfs - audio_segment.dBFS
        return audio_segment.apply_gain(change_in_dbfs)

    def calculate_audio_intensity(self, audio_segment, window_ms=100):
        chunks = [audio_segment[i:i+window_ms] for i in range(0, len(audio_segment), window_ms)]
        intensities = [chunk.dBFS for chunk in chunks if len(chunk) == window_ms]
        return intensities

    def dynamic_volume_adjustment(self, main_audio, mix_audio, window_ms=100):
        main_intensities = self.calculate_audio_intensity(main_audio, window_ms)
        avg_main_intensity = sum(main_intensities) / len(main_intensities)
        
        adjusted_mix = AudioSegment.empty()
        
        for i in range(len(main_intensities)):
            start_ms = i * window_ms
            end_ms = start_ms + window_ms
            
            mix_chunk = mix_audio[start_ms:end_ms]
            intensity_diff = main_intensities[i] - avg_main_intensity
            adjustment = -intensity_diff * 0.5
            adjustment = max(min(adjustment, 8), -8)
            
            adjusted_chunk = mix_chunk + adjustment
            adjusted_mix += adjusted_chunk
        
        return adjusted_mix

    def adjust_audio_length(self, audio, target_length):
        if len(audio) < target_length:
            repeats = (target_length // len(audio)) + 1
            crossfade_duration = min(1000, len(audio) // 10)
            combined = audio
            for _ in range(repeats - 1):
                combined = combined.append(audio, crossfade=crossfade_duration)
            return self.smooth_audio_transitions(combined[:target_length])
        return self.smooth_audio_transitions(audio[:target_length])

    def smooth_audio_transitions(self, audio_segment, fade_duration=100):
        return audio_segment.fade_in(fade_duration).fade_out(fade_duration)

class MixAudioTab(QWidget):
    def __init__(self):
        super().__init__()
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.default_font = QFont()
        self.default_font.setPointSize(11)
        self.setFont(self.default_font)
        self.setup_ui()
        
    def setup_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # Title
        title = QLabel("Audio Mixer")
        title.setFont(QFont("Arial", 14, QFont.Bold))
        main_layout.addWidget(title)

        # Lists Layout
        lists_layout = QHBoxLayout()
        
        # Main Audio List
        main_audio_layout = self.create_audio_list("Main Audio")
        self.main_audio_list = main_audio_layout.findChild(DragDropList)
        
        # Mix Audio 1 List
        mix1_audio_layout = self.create_audio_list("Mix Audio 1")
        self.mix1_audio_list = mix1_audio_layout.findChild(DragDropList)
        
        # Mix Audio 2 List
        mix2_audio_layout = self.create_audio_list("Mix Audio 2")
        self.mix2_audio_list = mix2_audio_layout.findChild(DragDropList)
        
        lists_layout.addWidget(main_audio_layout)
        lists_layout.addWidget(mix1_audio_layout)
        lists_layout.addWidget(mix2_audio_layout)
        
        main_layout.addLayout(lists_layout)

        # Options Layout
        options_layout = QVBoxLayout()

        # Output Path
        output_layout = QHBoxLayout()
        self.output_path = QLineEdit()
        self.output_path.setPlaceholderText("Select output folder...")
        self.output_browse = QPushButton("Browse")
        self.open_folder = QPushButton("Open Folder")
        self.reset_button = QPushButton("Reset")
        
        output_layout.addWidget(self.output_path)
        output_layout.addWidget(self.output_browse)
        output_layout.addWidget(self.open_folder)
        output_layout.addWidget(self.reset_button)
        options_layout.addLayout(output_layout)

        # Filename Option
        filename_layout = QHBoxLayout()
        self.filename_option = QComboBox()
        self.filename_option.addItems(["Use Main Audio name", "Auto-generate"])
        filename_layout.addWidget(QLabel("Output filename:"))
        filename_layout.addWidget(self.filename_option)
        options_layout.addLayout(filename_layout)

        # Bitrate Option
        bitrate_layout = QHBoxLayout()
        self.bitrate_option = QComboBox()
        self.bitrate_option.addItems(["320 kbps", "192 kbps", "128 kbps"])
        bitrate_layout.addWidget(QLabel("Output bitrate:"))
        bitrate_layout.addWidget(self.bitrate_option)
        options_layout.addLayout(bitrate_layout)

        # Mix Mode Option
        mix_mode_layout = QHBoxLayout()
        self.mix_mode_option = QComboBox()
        self.mix_mode_option.addItems(["Standard Mix", "Dynamic Mix"])
        mix_mode_layout.addWidget(QLabel("Mix Mode:"))
        mix_mode_layout.addWidget(self.mix_mode_option)
        options_layout.addLayout(mix_mode_layout)

        # Thêm options_layout vào main_layout (chỉ một lần)
        main_layout.addLayout(options_layout)

        # Progress Bar
        self.progress_bar = QProgressBar()
        main_layout.addWidget(self.progress_bar)

        # Mix Button
        self.mix_button = QPushButton("Mix Audio")
        self.mix_button.setMinimumHeight(40)
        main_layout.addWidget(self.mix_button)

        self.setLayout(main_layout)
        
        # Connect signals
        self.connect_signals()


    def create_audio_list(self, title):
        frame = QFrame()
        layout = QVBoxLayout(frame)
        
        # Title and Volume Layout
        title_volume_layout = QHBoxLayout()
        
        label = QLabel(f"{title} (0 files)")
        
        # Volume slider
        volume_layout = QHBoxLayout()
        volume_label = QLabel("Volume:")
        volume_slider = QSlider(Qt.Horizontal)
        volume_slider.setMinimum(-20)
        volume_slider.setMaximum(20)
        volume_slider.setValue(0)
        volume_slider.setTickPosition(QSlider.TicksBelow)
        volume_slider.setTickInterval(5)
        
        volume_value_label = QLabel("0 dB")
        volume_value_label.setMinimumWidth(50)
        
        volume_layout.addWidget(volume_label)
        volume_layout.addWidget(volume_slider)
        volume_layout.addWidget(volume_value_label)
        
        title_volume_layout.addWidget(label)
        title_volume_layout.addLayout(volume_layout)
        
        list_widget = DragDropList()
        
        buttons_layout = QHBoxLayout()
        add_btn = QPushButton("Add")
        edit_btn = QPushButton("Edit")
        remove_btn = QPushButton("Remove")
        
        buttons_layout.addWidget(add_btn)
        buttons_layout.addWidget(edit_btn)
        buttons_layout.addWidget(remove_btn)
        
        layout.addLayout(title_volume_layout)
        layout.addWidget(list_widget)
        layout.addLayout(buttons_layout)
        
        # Store references
        frame.label = label
        frame.list_widget = list_widget
        frame.add_btn = add_btn
        frame.edit_btn = edit_btn
        frame.remove_btn = remove_btn
        frame.volume_slider = volume_slider
        frame.volume_value_label = volume_value_label
        
        # Connect volume slider
        volume_slider.valueChanged.connect(
            lambda value: volume_value_label.setText(f"{value} dB")
        )
        
        return frame


    def connect_signals(self):
        # Connect all signals here
        self.output_browse.clicked.connect(self.select_output_folder)
        self.open_folder.clicked.connect(self.open_output_folder)
        self.mix_button.clicked.connect(self.mix_audio)
        self.reset_button.clicked.connect(self.reset_all)  # Thêm kết nối cho nút Reset

        # Connect list signals
        for list_frame in [self.main_audio_list, self.mix1_audio_list, self.mix2_audio_list]:
            list_frame.file_dropped.connect(self.update_file_counts)

    def reset_all(self):
        # Xóa các danh sách
        self.main_audio_list.clear()
        self.mix1_audio_list.clear()
        self.mix2_audio_list.clear()
        
        # Reset đường dẫn output
        self.output_path.clear()
        
        # Reset các combobox về giá trị mặc định
        self.filename_option.setCurrentIndex(0)
        self.bitrate_option.setCurrentIndex(0)
        self.mix_mode_option.setCurrentIndex(0)
        
        # Reset thanh progress
        self.progress_bar.setValue(0)
        
        # Reset các volume slider về 0
        self.main_audio_list.parent().volume_slider.setValue(0)
        self.mix1_audio_list.parent().volume_slider.setValue(0)
        self.mix2_audio_list.parent().volume_slider.setValue(0)
        
        # Cập nhật số lượng file
        self.update_file_counts()        
    def mix_audio(self):
        if not self.output_path.text():
            return
            
        main_audio = self.get_list_items(self.main_audio_list)
        mix1_audio = self.get_list_items(self.mix1_audio_list)
        mix2_audio = self.get_list_items(self.mix2_audio_list)
        
        if not main_audio:
            return
        
        self.mix_button.setEnabled(False)
        self.progress_bar.setValue(0)
        
        # Get volume values
        main_volume = self.main_audio_list.parent().volume_slider.value()
        mix1_volume = self.mix1_audio_list.parent().volume_slider.value()
        mix2_volume = self.mix2_audio_list.parent().volume_slider.value()
        
        self.batch_worker = BatchMixingWorker(
            main_audio,
            mix1_audio,
            mix2_audio,
            self.output_path.text(),
            self.filename_option.currentText(),
            self.bitrate_option.currentText(),
            self.mix_mode_option.currentText(),
            main_volume,
            mix1_volume,
            mix2_volume
        )
        
        self.batch_worker.progress.connect(self.progress_bar.setValue)
        self.batch_worker.finished.connect(self.mixing_finished)
        self.batch_worker.start()


    def mixing_finished(self):
        self.mix_button.setEnabled(True)
        QMessageBox.information(self, "Success", "Audio mixing completed!")

    def get_list_items(self, list_widget):
        return [list_widget.item(i).text() for i in range(list_widget.count())]

    def select_output_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if folder:
            self.output_path.setText(folder)
            
    def open_output_folder(self):
        if self.output_path.text():
            os.startfile(self.output_path.text())

    def update_file_counts(self):
        for list_frame in [self.main_audio_list, self.mix1_audio_list, self.mix2_audio_list]:
            count = list_frame.count()
            list_frame.parent().label.setText(f"{list_frame.parent().label.text().split('(')[0]}({count} files)")

    def add_audio(self, list_widget):
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Audio Files",
            "",
            "Audio Files (*.mp3 *.wav)"
        )
        if files:
            # Clean and add file paths
            clean_files = [file.strip('"').strip("'").strip() for file in files]
            list_widget.addItems(clean_files)
            self.update_file_counts()




