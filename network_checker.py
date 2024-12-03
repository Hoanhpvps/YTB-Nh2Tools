import socket
import google.generativeai as genai
from google.api_core import exceptions

class NetworkChecker:
    # API key được định nghĩa sẵn
    GEMINI_API_KEY = "AIzaSyD2ZqiJvuBAxJqLPX78IvTvauldWACa55M"  # Thay thế bằng API key thật của bạn

    @staticmethod
    def check_internet():
        try:
            socket.create_connection(("8.8.8.8", 53), timeout=3)
            return True, "Kết nối internet OK"
        except OSError:
            return False, "Không có kết nối internet"

    @staticmethod
    def check_gemini_api():
        try:
            genai.configure(api_key=NetworkChecker.GEMINI_API_KEY)
            model = genai.GenerativeModel('gemini-pro')
            response = model.generate_content("Test connection")
            return True, "API Gemini hoạt động tốt"
        except exceptions.PermissionDenied:
            return False, "API key không hợp lệ"
        except exceptions.QuotaExceeded:
            return False, "API key đã hết hạn mức sử dụng"
        except Exception as e:
            return False, f"Lỗi kết nối API: {str(e)}"

