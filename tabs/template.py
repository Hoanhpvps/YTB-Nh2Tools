from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel, QFileDialog, QSizePolicy
from PyQt5.QtGui import QFont

class TabNameTab(QWidget):
    def __init__(self):
        super().__init__()
        # Cho phép widget giãn theo cả hai chiều
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # Tăng font size cho các widget trong tab
        self.default_font = QFont()
        self.default_font.setPointSize(11)
        self.setFont(self.default_font)
        
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(10)  # Khoảng cách giữa các widget
        layout.setContentsMargins(20, 20, 20, 20)  # Lề cho layout
        
        # Tạo và tùy chỉnh các widget
        label = QLabel("Convert File Tab")
        label.setFont(self.default_font)
        
        select_btn = QPushButton("Select File")
        select_btn.setMinimumHeight(40)  # Tăng chiều cao nút
        select_btn.setFont(self.default_font)
        
        convert_btn = QPushButton("Convert")
        convert_btn.setMinimumHeight(40)
        convert_btn.setFont(self.default_font)
        
        # Thêm các widget vào layout
        layout.addWidget(label)
        layout.addWidget(select_btn)
        layout.addWidget(convert_btn)
        layout.addStretch()  # Thêm khoảng trống co giãn ở cuối
        
        self.setLayout(layout)