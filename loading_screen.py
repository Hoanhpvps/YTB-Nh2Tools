from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QProgressBar, QPushButton, QApplication
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QMovie

class LoadingScreen(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedSize(280, 280)
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.CustomizeWindowHint)
        
        layout = QVBoxLayout()
        
        # Loading GIF
        self.loading_label = QLabel()
        self.movie = QMovie("loading.gif")
        self.loading_label.setMovie(self.movie)
        self.movie.start()
        
        # Status label
        self.status_label = QLabel("Đang kiểm tra hệ thống...")
        self.status_label.setAlignment(Qt.AlignCenter)
        
        # Progress bar
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        
        # OK button (ẩn mặc định)
        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.close_application)
        self.ok_button.hide()
        
        layout.addWidget(self.loading_label)
        layout.addWidget(self.status_label)
        layout.addWidget(self.progress)
        layout.addWidget(self.ok_button)
        
        self.setLayout(layout)

    def show_error(self, message):
        self.movie.stop()
        self.loading_label.hide()
        self.progress.hide()
        self.status_label.setText(message)
        self.ok_button.show()
    
    def close_application(self):
        QApplication.quit()
