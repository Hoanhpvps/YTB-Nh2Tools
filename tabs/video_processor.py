import os
import re
import subprocess
from moviepy.editor import VideoFileClip, AudioFileClip, concatenate_videoclips
import random
from datetime import datetime
from PyQt5.QtCore import QThread, pyqtSignal
import shutil
import math
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QCheckBox, QPushButton, QScrollArea, QWidget, QLabel, QDialog
from PyQt5.QtCore import Qt

class EffectSelectorDialog(QDialog):
    def __init__(self, effects, parent=None):
        super().__init__(parent)
        self.effects = effects
        self.selected_effects = []
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Select Transition Effects')
        self.setMinimumWidth(300)
        layout = QVBoxLayout()

        # Add link to FFmpeg xfade documentation
        doc_label = QLabel('View effects examples: <a href="https://trac.ffmpeg.org/wiki/Xfade">FFmpeg Xfade Documentation</a>')
        doc_label.setOpenExternalLinks(True)
        layout.addWidget(doc_label)

        # Create scrollable area
        scroll = QScrollArea()
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout()

        # Add checkboxes for each effect
        self.checkboxes = {}
        for effect in self.effects:
            cb = QCheckBox(effect)
            cb.setChecked(True)  # Default all selected
            self.checkboxes[effect] = cb
            scroll_layout.addWidget(cb)

        scroll_widget.setLayout(scroll_layout)
        scroll.setWidget(scroll_widget)
        scroll.setWidgetResizable(True)
        layout.addWidget(scroll)

        # Add Select All/None buttons
        btn_layout = QVBoxLayout()
        select_all = QPushButton('Select All')
        select_none = QPushButton('Select None')
        select_all.clicked.connect(self.select_all_effects)
        select_none.clicked.connect(self.select_no_effects)
        btn_layout.addWidget(select_all)
        btn_layout.addWidget(select_none)
        layout.addLayout(btn_layout)

        # Add OK/Cancel buttons
        buttons = QVBoxLayout()
        ok_button = QPushButton('OK')
        cancel_button = QPushButton('Cancel')
        ok_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)
        buttons.addWidget(ok_button)
        buttons.addWidget(cancel_button)
        layout.addLayout(buttons)

        self.setLayout(layout)

    def select_all_effects(self):
        for cb in self.checkboxes.values():
            cb.setChecked(True)

    def select_no_effects(self):
        for cb in self.checkboxes.values():
            cb.setChecked(False)

    def get_selected_effects(self):
        return [effect for effect, cb in self.checkboxes.items() if cb.isChecked()]

class VideoProcessor:
    def __init__(self, progress_callback=None):
        self.progress_callback = progress_callback
        self.TRANSITION_EFFECTS = [
            "fade", "fadeblack", "fadewhite", "distance",
            "smoothleft", "smoothright", "smoothup", "smoothdown", 
            "circleclose", "circleopen", "horzclose", "horzopen",
            "vertclose", "vertopen", "diagbl", "diagbr", "diagtl",
            "diagtr", "hlslice", "hrslice", "vuslice", "vdslice",
            "dissolve", "hblur", "hlwind", "hrwind", "vuwind", "vdwind"
        ]

    def set_selected_effects(self, effects):
        if effects:
            self.selected_effects = effects
        else:
            self.selected_effects = self.TRANSITION_EFFECTS.copy()
            
    def update_progress(self, message, percentage=None):
        if self.progress_callback:
            self.progress_callback(message, percentage)

    def get_video_duration(self, video_path):
        """Get duration of video file using ffprobe"""
        cmd = [
            'ffprobe',
            '-v', 'error',
            '-select_streams', 'v:0',
            '-show_entries', 'format=duration',  # Thay đổi từ stream sang format
            '-of', 'default=noprint_wrappers=1:nokey=1',
            f'{video_path}'
        ]
        
        try:
            result = subprocess.run(
                ' '.join(cmd),
                shell=True,
                capture_output=True,
                text=True
            )
            duration = result.stdout.strip()
            
            if duration:
                return float(duration)
            else:
                # Sử dụng phương thức dự phòng nếu ffprobe không trả về duration
                cmd_backup = [
                    'ffprobe',
                    '-v', 'error',
                    '-show_entries', 'stream=duration',
                    '-of', 'default=noprint_wrappers=1:nokey=1',
                    f'{video_path}'
                ]
                result_backup = subprocess.run(
                    ' '.join(cmd_backup),
                    shell=True,
                    capture_output=True,
                    text=True
                )
                return float(result_backup.stdout.strip() or 0)
        except (ValueError, subprocess.CalledProcessError):
            # Trả về giá trị mặc định nếu không thể đọc duration
            return 0



    def merge_videos_with_effects(self, video_paths, temp_dir):
        """Merge videos with transition effects using FFmpeg"""
        print("Starting merge with effects...")
        print(f"Number of videos: {len(video_paths)}")

        # Convert paths to proper format
        video_paths = [f'"{path.encode("utf-8", errors="ignore").decode("utf-8").replace("\\", "/")}"' for path in video_paths]
        temp_video = os.path.join(temp_dir, 'temp_merged.mp4').replace("\\", "/")
        
        # Build FFmpeg command
        cmd_merge = ['ffmpeg', '-y', '-hwaccel', 'auto']
        
        # Add input videos
        for path in video_paths:
            cmd_merge.extend(['-i', path])
            print(f"Added input: {path}")

        # Build filter complex
        filter_complex = []
        cumulative_duration = 0
        
        # Get durations for all videos
        durations = []
        for path in video_paths:
            duration = self.get_video_duration(path.strip('"'))
            durations.append(duration)
            print(f"Duration for {path}: {duration}")

        # Build transition effects
        for i in range(len(video_paths)-1):
            effect = random.choice(getattr(self, 'selected_effects', self.TRANSITION_EFFECTS))
            duration = 1  # Fixed transition duration
            
            if i == 0:
                offset = durations[0] - duration
                cumulative_duration = offset
                filter_complex.append(
                    f"[0][1]xfade=transition={effect}:duration={duration}:offset={offset}[v1]"
                )
            else:
                cumulative_duration += durations[i] - duration
                filter_complex.append(
                    f"[v{i}][{i+1}]xfade=transition={effect}:duration={duration}:offset={cumulative_duration}[v{i+1}]"
                )
            
            print(f"Added filter: {filter_complex[-1]}")

        # Complete command with output options
        cmd_merge.extend([
            '-filter_complex', f'"{";".join(filter_complex)}"',
            '-map', f'[v{len(video_paths)-1}]',
            '-pix_fmt', 'yuv420p',
            '-colorspace', 'bt709',
            '-color_primaries', 'bt709', 
            '-color_trc', 'bt709',
            '-preset', 'veryfast',
            '-c:v', 'libx264',
            '-crf', '23',
            '-max_muxing_queue_size', '1024',
            f'"{temp_video}"'
        ])

        try:
            # Execute command
            result = subprocess.run(
                ' '.join(cmd_merge),
                shell=True,
                check=True,
                capture_output=True,
                text=True
            )
            print("FFmpeg command completed successfully")
            return temp_video

        except subprocess.CalledProcessError as e:
            print(f"FFmpeg Command: {' '.join(cmd_merge)}")
            print(f"FFmpeg stderr: {e.stderr}")
            print(f"FFmpeg stdout: {e.stdout}")
            
            # Fallback to simple concatenation if effects fail
            print("Falling back to simple concatenation...")
            concat_file = os.path.join(temp_dir, 'concat.txt')
            with open(concat_file, 'w', encoding='utf-8', errors='ignore') as f:
                for path in video_paths:
                    f.write(f"file {path}\n")
                    
            fallback_cmd = [
                'ffmpeg', '-y',
                '-f', 'concat',
                '-safe', '0', 
                '-i', f'"{concat_file}"',
                '-c:v', 'copy',
                '-c:a', 'copy',
                f'"{temp_video}"'
            ]
            
            subprocess.run(' '.join(fallback_cmd), shell=True, check=True)
            return temp_video

    def merge_videos(self, video_paths, count, use_effect=False):
        """Step 1: Merge selected videos with/without effects"""
        self.update_progress("Starting video merge...", 0)
        selected_videos = random.sample(video_paths, min(count, len(video_paths)))
        temp_dir = 'temp'
        os.makedirs(temp_dir, exist_ok=True)
        
        if use_effect:
            return self.merge_videos_with_effects(selected_videos, temp_dir)
        else:
            # Simple concatenation without effects
            concat_file = os.path.join(temp_dir, 'concat.txt')
            with open(concat_file, 'w', encoding='utf-8', errors='ignore') as f:
                for path in selected_videos:
                    f.write(f"file '{path}'\n")
                    
            output_path = os.path.join(temp_dir, 'merged_base.mp4')
            cmd = [
                'ffmpeg', '-y',
                '-f', 'concat',
                '-safe', '0',
                '-i', f'"{concat_file}"',
                '-c:v', 'copy',
                '-an',  # Remove any audio
                f'"{output_path}"'
            ]
            
            subprocess.run(' '.join(cmd), shell=True, check=True)
            self.update_progress("Video merge complete", 100)
            return output_path

    def get_audio_duration(self, audio_path):
        """Get duration of audio file in seconds"""
        cmd = [
            'ffprobe',
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            f'"{audio_path}"'
        ]
        
        result = subprocess.run(
            ' '.join(cmd),
            shell=True,
            capture_output=True,
            text=True
        )
        
        return float(result.stdout.strip())

    def merge_audio(self, audio_paths, count):
        """Step 2: Merge selected audio files"""
        self.update_progress("Starting audio merge...", 0)
        selected_audio = random.sample(audio_paths, min(count, len(audio_paths)))
        temp_dir = 'temp'
        os.makedirs(temp_dir, exist_ok=True)
        
        # Create concat file with absolute paths
        concat_file = os.path.join(temp_dir, 'audio_concat.txt')
        with open(concat_file, 'w', encoding='utf-8', errors='ignore') as f:
            for path in selected_audio:
                f.write(f"file '{os.path.abspath(path)}'\n")
                
        output_path = os.path.join(temp_dir, 'merged_audio.m4a')
        
        # Updated FFmpeg command with proper audio encoding settings
        cmd = [
            'ffmpeg', '-y',
            '-f', 'concat',
            '-safe', '0',
            '-i', f'"{concat_file}"',
            '-c:a', 'aac',
            '-b:a', '192k',
            '-ar', '44100',
            '-ac', '2',
            f'"{output_path}"'
        ]
        
        subprocess.run(' '.join(cmd), shell=True, check=True)
        self.update_progress("Audio merge complete", 100)
        return output_path
    
    def build_effect_filter(self, video_paths):
        """Build FFmpeg filter complex string for video effects"""
        filter_complex = []
        cumulative_duration = 0
        
        # Get durations for all videos
        durations = []
        for path in video_paths:
            duration = self.get_video_duration(path.strip('"'))
            durations.append(duration)
        
        # Build transition effects chain
        for i in range(len(video_paths)-1):
            effect = random.choice(self.TRANSITION_EFFECTS)
            duration = 1  # Fixed transition duration
            
            if i == 0:
                offset = durations[0] - duration
                cumulative_duration = offset
                filter_complex.append(
                    f"[0][1]xfade=transition={effect}:duration={duration}:offset={offset}[v1]"
                )
            else:
                cumulative_duration += durations[i] - duration
                filter_complex.append(
                    f"[v{i}][{i+1}]{effect}:duration={duration}:offset={cumulative_duration}[v{i+1}]"
                )
        
        return ";".join(filter_complex)

    def loop_video(self, video_path, mode, **kwargs):
        """Loop video using concat demuxer for faster processing"""
        temp_dir = os.path.abspath('temp')
        output_path = os.path.join(temp_dir, 'final_looped.mp4')
        concat_file = os.path.join(temp_dir, 'loop_concat.txt')
        
        # Get source video duration
        video_duration = self.get_video_duration(video_path)
        
        # Calculate number of loops needed
        if mode == 'count':
            loop_count = kwargs.get('count', 1)
        elif mode == 'duration':
            target_duration = kwargs.get('duration', 0)
            loop_count = math.ceil(target_duration / video_duration)
        else:  # random duration
            target_duration = random.uniform(
                kwargs.get('min_duration', 60),
                kwargs.get('max_duration', 180)
            )
            loop_count = math.ceil(target_duration / video_duration)
        
        # Create concat file
        with open(concat_file, 'w', encoding='utf-8', errors='ignore') as f:
            for _ in range(loop_count):
                f.write(f"file '{os.path.abspath(video_path)}'\n")
        
        # Fast concatenation using concat demuxer
        cmd = [
            'ffmpeg', '-y',
            '-f', 'concat',
            '-safe', '0',
            '-i', f'"{concat_file}"'
        ]
        
        # Add duration limit for duration/random modes
        if mode in ('duration', 'random'):
            cmd.extend(['-t', str(target_duration)])
        
        # Output settings
        cmd.extend([
            '-c', 'copy',  # Stream copy for fastest processing
            f'"{output_path}"'
        ])
        
        subprocess.run(' '.join(cmd), shell=True, check=True)
        return output_path

    def process_final_video(self, video_path, audio_path, loop_params):
        # Add duration validation
        video_duration = self.get_video_duration(video_path)
        if video_duration <= 0:
            video_duration = 1  # Set minimum duration to prevent division by zero
        temp_dir = os.path.abspath('temp')
        
        # Step 1-2: Create temp_AV1 by combining video and audio
        temp_av1 = os.path.join(temp_dir, 'temp_AV1.mp4')
        cmd_combine = [
            'ffmpeg', '-y',
            '-stream_loop', '-1',
            '-i', f'"{video_path}"',
            '-i', f'"{audio_path}"',
            '-c:v', 'copy',
            '-c:a', 'aac',
            f'"{temp_av1}"'
        ]
        subprocess.run(' '.join(cmd_combine), shell=True, check=True)
        
        # Step 3: Loop temp_AV1 based on specified mode
        mode = loop_params['mode']
        if mode == 'count':
            return self.loop_video(temp_av1, 'count', count=loop_params['count'])
        elif mode == 'duration':
            return self.loop_video(temp_av1, 'duration', duration=loop_params['duration'])
        else:  # random duration
            return self.loop_video(temp_av1, 'random', 
                                 min_duration=loop_params['min_duration'],
                                 max_duration=loop_params['max_duration'])

    def loop_final_video(self, input_video, target_duration, output_name):
        """Create final looped video with exact duration"""
        temp_dir = os.path.abspath('temp')
        output_path = os.path.join(temp_dir, f'loop_{output_name}.mp4')
        
        # Calculate number of loops needed with validation
        video_duration = self.get_video_duration(input_video)
        if video_duration <= 0:
            video_duration = 1  # Set minimum duration
        
        # Ensure target_duration is valid
        if target_duration <= 0:
            target_duration = video_duration
        
        loop_count = math.ceil(target_duration / video_duration)
        
        # Ensure at least one loop
        loop_count = max(1, loop_count)
        
        # Create concat file
        concat_file = os.path.join(temp_dir, 'final_loop.txt')
        with open(concat_file, 'w', encoding='utf-8', errors='ignore') as f:
            for _ in range(loop_count):
                f.write(f"file '{os.path.abspath(input_video)}'\n")
        
        # Final render with exact duration
        cmd = [
            'ffmpeg', '-y',
            '-f', 'concat',
            '-safe', '0',
            '-i', f'"{concat_file}"',
            '-t', str(target_duration),
            '-c', 'copy',
            f'"{output_path}"'
        ]
        
        subprocess.run(' '.join(cmd), shell=True, check=True)
        return output_path


    def combine_video_audio(self, video_path, audio_path):
        """Step 3: Combine video with looping to match audio duration"""
        temp_dir = os.path.abspath('temp')
        os.makedirs(temp_dir, exist_ok=True)
        
        # Get audio duration
        audio_duration = self.get_audio_duration(audio_path)
        
        output_path = os.path.join(temp_dir, 'combined_base.mp4')
        
        # Use stream_loop for video to ensure it loops enough to match audio
        cmd = [
            'ffmpeg', '-y',
            '-stream_loop', '-1',  # Infinite loop for input video
            '-i', f'"{video_path}"',
            '-i', f'"{audio_path}"',
            '-map', '0:v',  # Take video from first input
            '-map', '1:a',  # Take audio from second input
            '-c:v', 'copy',
            '-c:a', 'aac',
            '-shortest',    # Cut when shortest input ends (audio)
            '-t', str(audio_duration),  # Explicitly set duration to audio length
            f'"{output_path}"'
        ]
        
        subprocess.run(' '.join(cmd), shell=True, check=True)
        return output_path

    def get_ffmpeg_progress(self, duration, line):
        if "out_time_ms" in line and duration > 0:  # Add check for duration > 0
            try:
                time_ms = int(line.split('=')[1])
                time_s = time_ms / 1000000.0
                progress = min(int((time_s / float(duration)) * 100), 100)
                self.update_progress(f"Processing: {progress}%", progress)
            except (ValueError, IndexError):
                self.update_progress("Processing...", 50)  # Default progress value

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
            # Process each video in a separate thread
            for i in range(self.params['output_count']):
                self.process_single_video(i)
            self.finished.emit()
            
        except Exception as e:
            self.error.emit(str(e))
            
    def process_single_video(self, index):
        try:
            self.progress_updated.emit(f"Starting video {index+1}", 0)
            
            # Step 1: Merge videos
            self.progress_updated.emit("Merging videos...", 20)
            merged_video = self.video_processor.merge_videos(
                self.params['video_paths'],
                self.params['video_count'],
                self.params['use_effect']
            )
            
            # Step 2: Merge audio
            self.progress_updated.emit("Merging audio...", 40)
            merged_audio = self.video_processor.merge_audio(
                self.params['audio_paths'],
                self.params['audio_count']
            )
            
            # Step 3: Combine video and audio (video will loop to match audio)
            self.progress_updated.emit("Combining video and audio...", 60)
            combined_video = self.video_processor.combine_video_audio(
                merged_video,
                merged_audio
            )
            
            # Step 4: Create final looped version
            self.progress_updated.emit("Creating final loop...", 80)
            
            # Calculate target duration based on mode
            if self.params['loop_mode'] == 'count':
                base_duration = self.video_processor.get_video_duration(combined_video)
                target_duration = base_duration * self.params['loop_count']
            elif self.params['loop_mode'] == 'duration':
                target_duration = self.params['loop_duration']
            else:  # random duration
                target_duration = random.uniform(
                    self.params['min_duration'],
                    self.params['max_duration']
                )
            
            # Create final looped video
            output_name = self.params['generate_output_name'](index)
            final_video = self.video_processor.loop_final_video(
                combined_video,
                target_duration,
                output_name
            )
            
            # Move to final destination
            final_path = os.path.join(self.params['output_path'], f"{output_name}.mp4")
            shutil.move(final_video, final_path)
            
            self.progress_updated.emit(f"Completed video {index+1}", 100)
            
        except Exception as e:
            self.error.emit(str(e))
