from PyQt5.QtWidgets import QFileDialog, QInputDialog
from moviepy.editor import VideoFileClip, AudioFileClip
import os

class FileHandlers:
    def add_video_file(self, list_widget):
        files, _ = QFileDialog.getOpenFileNames(
            None,
            "Select Video Files",
            "",
            "Video Files (*.mp4 *.avi *.mkv *.mov)"
        )
        for file_path in files:
            try:
                with VideoFileClip(file_path) as video:
                    info = f"{file_path} | {video.size[0]}x{video.size[1]} | {video.fps:.2f}fps | {video.duration:.2f}s"
                    list_widget.addItem(info)
            except Exception as e:
                print(f"Error loading video: {e}")

    def add_audio_file(self, list_widget):
        files, _ = QFileDialog.getOpenFileNames(
            None,
            "Select Audio Files",
            "",
            "Audio Files (*.mp3 *.wav *.aac *.m4a)"
        )
        for file_path in files:
            try:
                with AudioFileClip(file_path) as audio:
                    info = f"{file_path} | {audio.fps}Hz | {audio.duration:.2f}s"
                    list_widget.addItem(info)
            except Exception as e:
                print(f"Error loading audio: {e}")

    def edit_file(self, list_widget):
        current_item = list_widget.currentItem()
        if current_item:
            old_text = current_item.text()
            new_text, ok = QInputDialog.getText(
                None,
                "Edit File Info",
                "Edit:",
                text=old_text
            )
            if ok and new_text:
                current_item.setText(new_text)

    def remove_file(self, list_widget):
        current_row = list_widget.currentRow()
        if current_row >= 0:
            list_widget.takeItem(current_row)
