import requests
from packaging import version
import webbrowser
import os
from PyQt5.QtWidgets import QMessageBox

class AutoUpdater:
    def __init__(self):
        self.current_version = "1.0.0"  # Version hiện tại
        self.github_repo = "Hoanhpvps/YTB-Nh2Tools"  # Thay thế bằng repo của bạn
        
    def check_update(self, parent_widget):
        try:
            response = requests.get(f"https://api.github.com/repos/{self.github_repo}/releases/latest")
            if response.status_code == 200:
                latest_release = response.json()
                latest_version = latest_release["tag_name"].strip("v")
                
                if version.parse(latest_version) > version.parse(self.current_version):
                    reply = QMessageBox.question(
                        parent_widget,
                        "Cập Nhật Mới",
                        f"Đã có phiên bản mới {latest_version}. Bạn có muốn cập nhật không?",
                        QMessageBox.Yes | QMessageBox.No
                    )
                    
                    if reply == QMessageBox.Yes:
                        download_url = latest_release["assets"][0]["browser_download_url"]
                        webbrowser.open(download_url)
                        return True, "Đang tải bản cập nhật..."
                    
            return False, "Ứng dụng đã là phiên bản mới nhất"
        except Exception as e:
            return False, f"Lỗi kiểm tra cập nhật: {str(e)}"
