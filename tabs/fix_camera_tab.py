from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
                           QFileDialog, QSizePolicy, QListWidget, QProgressBar, 
                           QCheckBox, QFrame, QSpinBox, QMessageBox)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont
import cv2
import os
import numpy as np
from moviepy.editor import VideoFileClip, concatenate_videoclips


# For creating video from frames, we'll use OpenCV's VideoWriter
import cv2

class VideoProcessingThread(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal()
    error = pyqtSignal(str)
    
    def __init__(self, input_path, output_path, min_duration, stabilize, use_transition, transition_frames):
        super().__init__()
        self.input_path = input_path
        self.output_path = output_path
        self.min_duration = min_duration
        self.stabilize = stabilize
        self.use_transition = use_transition
        self.transition_frames = transition_frames

    def create_transition(self, second_half, first_half, num_frames):
        try:
            # Get frames directly from clips
            last_frame = None
            first_frame = None
            
            # Get last frame from second_half
            frames_second = list(second_half.iter_frames())
            if frames_second:
                last_frame = frames_second[-1]
                
            # Get first frame from first_half
            frames_first = list(first_half.iter_frames())
            if frames_first:
                first_frame = frames_first[0]
                
            if last_frame is None or first_frame is None:
                return None
                
            transition_frames = []
            for i in range(num_frames):
                alpha = i / num_frames
                # Create blend
                blended = cv2.addWeighted(last_frame, 1 - alpha, first_frame, alpha, 0)
                transition_frames.append(blended)
                
            return transition_frames
            
        except Exception as e:
            print(f"Transition creation error: {str(e)}")
            return None

    def run(self):
        temp_files = []  # List to track temporary files
        try:
            # Find similar frames
            pos1, pos2 = self.find_similar_frames()
            self.progress.emit(30)

            # Load video and create segments
            video = VideoFileClip(self.input_path)
            t1 = pos1 / video.fps
            t2 = pos2 / video.fps
            
            video_segment = video.subclip(t1, t2)
            mid_time = (t2 - t1) / 2
            
            first_half = video_segment.subclip(0, mid_time)
            second_half = video_segment.subclip(mid_time)
            
            self.progress.emit(50)

            # Apply stabilization if requested
            if self.stabilize:
                first_half = self.stabilize_video(first_half)
                second_half = self.stabilize_video(second_half)
                self.progress.emit(70)

            # Add transition if requested
            if self.use_transition:
                transition_frames = self.create_transition(second_half, first_half, self.transition_frames)
                if transition_frames:
                    # Create transition clip from frames
                    from moviepy.video.io.ImageSequenceClip import ImageSequenceClip
                    transition_clip = ImageSequenceClip(transition_frames, fps=video.fps)
                    final_video = concatenate_videoclips([second_half, transition_clip, first_half])
                else:
                    final_video = concatenate_videoclips([second_half, first_half])
            else:
                final_video = concatenate_videoclips([second_half, first_half])

            # Write output video
            final_video.write_videofile(
                self.output_path,
                codec='libx264',
                audio_codec='aac',
                bitrate='4000k',
                preset='faster',
                threads=4
            )

            # Cleanup
            video.close()
            first_half.close()
            second_half.close()
            final_video.close()

            # Store temp file paths
            if self.stabilize:
                temp_files.extend([temp_avi, temp_mp4])
            
            # After processing is complete
            self.progress.emit(100)
            self.finished.emit()
            
        except Exception as e:
            self.error.emit(str(e))
            
        finally:
            # Clean up all temp files
            for temp_file in temp_files:
                try:
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                except:
                    continue
                    
            # Clean up temp directory if empty
            try:
                temp_dir = os.path.dirname(temp_files[0])
                if os.path.exists(temp_dir) and not os.listdir(temp_dir):
                    os.rmdir(temp_dir)
            except:
                pass

    def find_similar_frames(self):
        cap = cv2.VideoCapture(self.input_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        min_frame_gap = int(fps * self.min_duration)
        
        # Optimization: Reduce frame sampling rate
        frame_sampling_rate = 5  # Process every 5th frame
        
        frames = []
        frame_positions = []
        
        frame_count = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break
                
            # Only process every nth frame
            if frame_count % frame_sampling_rate == 0:
                # Reduce resolution for faster processing
                frame = cv2.resize(frame, (160, 120))
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                frame = cv2.GaussianBlur(frame, (3,3), 0)
                
                frames.append(frame)
                frame_positions.append(frame_count)
            
            frame_count += 1
            
            if frame_count % 100 == 0:
                progress = (frame_count / total_frames) * 50
                self.progress.emit(progress)
        
        # Find best matching frames
        best_similarity = -1
        best_positions = (0, 0)
        
        for i in range(len(frames)):
            start_j = i + (min_frame_gap // frame_sampling_rate)
            if start_j >= len(frames):
                continue
                
            current_frame = frames[i]
            comparison_frames = frames[start_j:]
            
            # Vectorized similarity calculation
            ssims = np.array([cv2.matchTemplate(current_frame, frame, cv2.TM_CCOEFF_NORMED)[0][0] 
                             for frame in comparison_frames])
            diffs = np.array([np.mean(cv2.absdiff(current_frame, frame)) 
                             for frame in comparison_frames])
            
            similarities = (ssims + (1 - diffs/255)) / 2
            
            max_similarity_idx = np.argmax(similarities)
            if similarities[max_similarity_idx] > best_similarity:
                best_similarity = similarities[max_similarity_idx]
                best_positions = (frame_positions[i], 
                                frame_positions[start_j + max_similarity_idx])
            
            progress = 50 + ((i+1) / len(frames)) * 50
            self.progress.emit(progress)
        
        cap.release()
        return best_positions

    def stabilize_video(self, clip):
        import time
        from pathlib import Path
        
        # Create unique filenames with timestamp and random suffix
        timestamp = int(time.time())
        random_suffix = np.random.randint(1000, 9999)
        temp_dir = Path(os.path.dirname(self.output_path)) / "temp"
        temp_dir.mkdir(exist_ok=True)
        
        temp_avi = temp_dir / f"stabilized_{timestamp}_{random_suffix}.avi"
        temp_mp4 = temp_dir / f"stabilized_{timestamp}_{random_suffix}.mp4"
        
        try:
            # Get video properties
            fps = clip.fps
            width = int(clip.size[0])
            height = int(clip.size[1])
            
            # Use XVID codec for intermediate file
            fourcc = cv2.VideoWriter_fourcc(*'XVID')
            out = cv2.VideoWriter(str(temp_avi), fourcc, fps, (width, height))
            
            frames = list(clip.iter_frames())
            prev_gray = cv2.cvtColor(frames[0], cv2.COLOR_RGB2GRAY)
            out.write(cv2.cvtColor(frames[0], cv2.COLOR_RGB2BGR))
            
            for i in range(1, len(frames)):
                curr_frame = frames[i]
                curr_gray = cv2.cvtColor(curr_frame, cv2.COLOR_RGB2GRAY)
                
                prev_pts = cv2.goodFeaturesToTrack(
                    prev_gray,
                    maxCorners=200,
                    qualityLevel=0.01,
                    minDistance=30,
                    blockSize=3
                )
                
                if prev_pts is not None:
                    next_pts, status, _ = cv2.calcOpticalFlowPyrLK(
                        prev_gray,
                        curr_gray,
                        prev_pts,
                        None
                    )
                    
                    good_prev = prev_pts[status == 1]
                    good_next = next_pts[status == 1]
                    
                    if len(good_prev) >= 4 and len(good_next) >= 4:
                        transform = cv2.estimateAffinePartial2D(good_prev, good_next)[0]
                        
                        if transform is not None:
                            stabilized = cv2.warpAffine(curr_frame, transform, (width, height))
                            out.write(cv2.cvtColor(stabilized, cv2.COLOR_RGB2BGR))
                        else:
                            out.write(cv2.cvtColor(curr_frame, cv2.COLOR_RGB2BGR))
                    else:
                        out.write(cv2.cvtColor(curr_frame, cv2.COLOR_RGB2BGR))
                else:
                    out.write(cv2.cvtColor(curr_frame, cv2.COLOR_RGB2BGR))
                
                prev_gray = curr_gray
                self.progress.emit((i / len(frames)) * 100)
            
            # Ensure writer is released before conversion
            out.release()
            del out
            
            # Convert AVI to MP4
            temp_clip = VideoFileClip(str(temp_avi))
            temp_clip.write_videofile(
                str(temp_mp4),
                codec='libx264',
                audio=False,
                preset='ultrafast'
            )
            temp_clip.close()
            
            # Return stabilized clip
            return VideoFileClip(str(temp_mp4))
            
        finally:
            # Clean up resources
            if 'temp_clip' in locals():
                temp_clip.close()
            
            # Wait for file handles to be released
            time.sleep(0.5)
            
            # Remove temporary files
            for temp_file in [temp_avi, temp_mp4]:
                try:
                    if temp_file.exists():
                        temp_file.unlink()
                except:
                    pass
            
            # Try to remove temp directory if empty
            try:
                temp_dir.rmdir()
            except:
                pass

class FixCameraTab(QWidget):
    def __init__(self):
        super().__init__()
        # Add this line to store thread references
        self.processing_threads = []
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.default_font = QFont()
        self.default_font.setPointSize(11)
        self.setFont(self.default_font)
        self.init_ui()
        
    def init_ui(self):
        layout = QHBoxLayout()
        
        # Left Panel
        left_panel = QFrame()
        left_layout = QVBoxLayout(left_panel)
        
        # Video List
        list_label = QLabel("Videos to Process:")
        self.video_list = QListWidget()
        self.video_list.setAcceptDrops(True)
        self.video_list.setDragDropMode(QListWidget.DragDrop)
        
        # Buttons
        buttons_layout = QHBoxLayout()
        self.add_btn = QPushButton("Add Videos")
        self.remove_btn = QPushButton("Remove Selected")
        buttons_layout.addWidget(self.add_btn)
        buttons_layout.addWidget(self.remove_btn)
        
        # Options Frame
        options_frame = QFrame()
        options_frame.setFrameStyle(QFrame.StyledPanel)
        options_layout = QVBoxLayout(options_frame)
        
        # Duration Setting
        duration_layout = QHBoxLayout()
        duration_label = QLabel("Minimum Duration (seconds):")
        self.duration_spin = QSpinBox()
        self.duration_spin.setRange(1, 3600)
        self.duration_spin.setValue(10)
        duration_layout.addWidget(duration_label)
        duration_layout.addWidget(self.duration_spin)
        
        # Checkboxes
        self.stabilize_check = QCheckBox("Stabilize Output Video")
        self.transition_check = QCheckBox("Use Blend Transition")
        
        # Transition Frames
        transition_layout = QHBoxLayout()
        transition_label = QLabel("Transition Frames:")
        self.transition_spin = QSpinBox()
        self.transition_spin.setRange(2, 60)
        self.transition_spin.setValue(6)
        transition_layout.addWidget(transition_label)
        transition_layout.addWidget(self.transition_spin)
        
        # Output Directory
        output_layout = QHBoxLayout()
        self.output_path = QLabel("Output Directory: Not Selected")
        self.browse_btn = QPushButton("Browse")
        output_layout.addWidget(self.output_path)
        output_layout.addWidget(self.browse_btn)
        
        # Process Button
        self.process_btn = QPushButton("Process Videos")
        self.process_btn.setMinimumHeight(40)
        
        # Add all to options layout
        options_layout.addLayout(duration_layout)
        options_layout.addWidget(self.stabilize_check)
        options_layout.addWidget(self.transition_check)
        options_layout.addLayout(transition_layout)
        options_layout.addLayout(output_layout)
        options_layout.addWidget(self.process_btn)
        
        # Add everything to left layout
        left_layout.addWidget(list_label)
        left_layout.addWidget(self.video_list)
        left_layout.addLayout(buttons_layout)
        left_layout.addWidget(options_frame)
        # Enable drag & drop for video_list
        self.video_list.setAcceptDrops(True)
        self.video_list.dragEnterEvent = self.dragEnterEvent
        self.video_list.dragMoveEvent = self.dragMoveEvent
        self.video_list.dropEvent = self.dropEvent
        # Right Panel (Progress)
        right_panel = QFrame()
        right_layout = QVBoxLayout(right_panel)
        
        progress_label = QLabel("Processing Progress")
        self.progress_list = QListWidget()
        self.overall_progress = QProgressBar()
        
        right_layout.addWidget(progress_label)
        right_layout.addWidget(self.progress_list)
        right_layout.addWidget(self.overall_progress)
        
        # Add panels to main layout
        layout.addWidget(left_panel, 2)  # 2/3 width
        layout.addWidget(right_panel, 1)  # 1/3 width
        
        self.setLayout(layout)
        
        # Connect signals
        self.connect_signals()
    
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
        files = []
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if file_path.lower().endswith(('.mp4', '.avi', '.mkv')):
                # Handle paths with spaces correctly
                normalized_path = os.path.normpath(file_path)
                if normalized_path not in [self.video_list.item(i).text() for i in range(self.video_list.count())]:
                    files.append(normalized_path)

        if files:
            self.video_list.addItems(files)

    def connect_signals(self):
        self.add_btn.clicked.connect(self.add_videos)
        self.remove_btn.clicked.connect(self.remove_selected)
        self.browse_btn.clicked.connect(self.select_output_dir)
        self.process_btn.clicked.connect(self.start_processing)
        
    # Add your video processing methods here
    def add_videos(self):
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Videos",
            "",
            "Video Files (*.mp4 *.avi *.mkv)"
        )
        if files:
            self.video_list.addItems(files)
            
    def remove_selected(self):
        for item in self.video_list.selectedItems():
            self.video_list.takeItem(self.video_list.row(item))
            
    def select_output_dir(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if directory:
            self.output_path.setText(f"Output Directory: {directory}")
            # Add this line to store the actual directory path
            self.output_directory = directory
            
    def start_processing(self):
        # Change this check to look at the actual text
        if self.output_path.text() == "Output Directory: Not Selected":
            QMessageBox.warning(self, "Warning", "Please select output directory first")
            return
            
        if self.video_list.count() == 0:
            QMessageBox.warning(self, "Warning", "Please add videos to process")
            return

        # Disable UI elements during processing
        self.process_btn.setEnabled(False)
        self.add_btn.setEnabled(False)
        self.remove_btn.setEnabled(False)
        self.progress_list.clear()
        self.overall_progress.setValue(0)

        # Get processing parameters
        min_duration = self.duration_spin.value()
        stabilize = self.stabilize_check.isChecked()
        use_transition = self.transition_check.isChecked()
        transition_frames = self.transition_spin.value()

        # Process each video
        total_videos = self.video_list.count()
        for i in range(total_videos):
            input_path = self.video_list.item(i).text()
            output_name = f"processed_{os.path.basename(input_path)}"
            output_path = os.path.join(self.output_directory, output_name)
            self.progress_list.addItem(f"Processing: {os.path.basename(input_path)}")
            
            # Create thread
            processing_thread = VideoProcessingThread(
                input_path, output_path, min_duration,
                stabilize, use_transition, transition_frames
            )
            
            # Store thread reference
            self.processing_threads.append(processing_thread)
            
            processing_thread.progress.connect(
                lambda p, idx=i: self.update_progress(p, idx, total_videos)
            )
            processing_thread.finished.connect(
                lambda idx=i: self.on_video_complete(idx, total_videos)
            )
            processing_thread.error.connect(self.on_processing_error)
            
            processing_thread.start()

    def update_progress(self, progress, current_video, total_videos):
        self.overall_progress.setValue(
            int((current_video * 100 + progress) / total_videos)
        )
        current_item = self.progress_list.item(self.progress_list.count() - 1)
        current_item.setText(f"Processing: {progress}%")

    def on_video_complete(self, current_video, total_videos):
        if current_video == total_videos - 1:
            # Clean up finished threads
            for thread in self.processing_threads:
                thread.wait()
                thread.deleteLater()
            self.processing_threads.clear()
            
            self.process_btn.setEnabled(True)
            self.add_btn.setEnabled(True)
            self.remove_btn.setEnabled(True)
            QMessageBox.information(self, "Success", "All videos processed successfully!")

    # Add cleanup method
    def closeEvent(self, event):
        for thread in self.processing_threads:
            thread.wait()
        super().closeEvent(event)

    def on_processing_error(self, error_msg):
        QMessageBox.critical(self, "Error", f"Error processing video: {error_msg}")
        self.process_btn.setEnabled(True)
        self.add_btn.setEnabled(True)
        self.remove_btn.setEnabled(True)

