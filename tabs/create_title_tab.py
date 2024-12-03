from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
                           QSizePolicy, QListWidget, QTextEdit, QRadioButton, 
                           QButtonGroup, QGroupBox, QMessageBox, QFrame)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
import google.generativeai as genai
from openai import OpenAI
import random

class CreateTitleTab(QWidget):
    def __init__(self):
        super().__init__()
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.default_font = QFont()
        self.default_font.setPointSize(11)
        self.setFont(self.default_font)
        
        # API Keys
        self.API_GEMINI = [
            "AIzaSyBBd8INtemzKrMfoQ_gVWZh9bZ-LlwV8t0",
            "AIzaSyCX_sunzjmd1SdIJ21j96uLxj5HNzdemTA",
            # Add your other Gemini API keys here
        ]
        
        self.API_OPENAI = [
            "sk-your-openai-key-1",
            "sk-your-openai-key-2",
            # Add your OpenAI API keys here
        ]
        
        self.setup_ui()

    def setup_ui(self):
        main_layout = QHBoxLayout()
        
        # Left Panel - Results List
        left_panel = self.create_left_panel()
        main_layout.addWidget(left_panel)
        
        # Right Panel - Controls
        right_panel = self.create_right_panel()
        main_layout.addWidget(right_panel)
        
        self.setLayout(main_layout)

    def create_left_panel(self):
        panel = QFrame()
        layout = QVBoxLayout()
        
        # Title
        title = QLabel("AI Content Generator")
        title.setFont(QFont("Arial", 14, QFont.Bold))
        layout.addWidget(title)
        
        # Results list
        self.results_list = QListWidget()
        self.results_list.setFont(QFont("Arial", 11))
        layout.addWidget(self.results_list)
        
        panel.setLayout(layout)
        return panel

    def create_right_panel(self):
        panel = QFrame()
        layout = QVBoxLayout()
        
        # AI Selection
        ai_group = QGroupBox("Select AI Model")
        ai_layout = QHBoxLayout()
        
        self.ai_group = QButtonGroup()
        self.gemini_radio = QRadioButton("Gemini AI")
        self.openai_radio = QRadioButton("ChatGPT")
        self.gemini_radio.setChecked(True)
        
        self.ai_group.addButton(self.gemini_radio)
        self.ai_group.addButton(self.openai_radio)
        
        ai_layout.addWidget(self.gemini_radio)
        ai_layout.addWidget(self.openai_radio)
        ai_group.setLayout(ai_layout)
        layout.addWidget(ai_group)
        
        # Custom Prompt Input
        layout.addWidget(QLabel("Enter Your Question:"))
        self.prompt_input = QTextEdit()
        self.prompt_input.setPlaceholderText("Enter your custom prompt here...")
        self.prompt_input.setMaximumHeight(100)
        layout.addWidget(self.prompt_input)
        
        # Keywords Input
        layout.addWidget(QLabel("Additional Keywords (Optional):"))
        self.keywords_input = QTextEdit()
        self.keywords_input.setPlaceholderText("Enter keywords separated by commas...")
        self.keywords_input.setMaximumHeight(100)
        layout.addWidget(self.keywords_input)
        
        # Control Buttons
        btn_layout = QHBoxLayout()
        
        self.generate_btn = QPushButton("Generate Content")
        self.copy_btn = QPushButton("Copy Selected")
        self.reset_btn = QPushButton("Reset All")
        
        self.generate_btn.clicked.connect(self.generate_content)
        self.copy_btn.clicked.connect(self.copy_selected)
        self.reset_btn.clicked.connect(self.reset_ui)
        
        btn_layout.addWidget(self.generate_btn)
        btn_layout.addWidget(self.copy_btn)
        btn_layout.addWidget(self.reset_btn)
        
        layout.addLayout(btn_layout)
        layout.addStretch()
        
        panel.setLayout(layout)
        return panel

    def generate_content(self):
        prompt = self.prompt_input.toPlainText().strip()
        keywords = self.keywords_input.toPlainText().strip()
        
        if not prompt and not keywords:
            QMessageBox.warning(self, "Warning", "Please enter either a question or keywords")
            return
            
        # Construct the question
        if prompt and keywords:
            question = f"{prompt} with the following keywords: {keywords}"
        elif prompt:
            question = prompt
        else:
            question = f"Write 6 English titles and descriptions for YouTube videos using these keywords: {keywords}"
            
        # Generate response based on selected AI
        if self.gemini_radio.isChecked():
            api_key = random.choice(self.API_GEMINI)
            response = self.generate_gemini_response(api_key, question)
        else:
            api_key = random.choice(self.API_OPENAI)
            response = self.generate_openai_response(api_key, question)
            
        if response:
            self.results_list.clear()
            for line in response.split('\n'):
                if line.strip():
                    self.results_list.addItem(line.strip())

    def generate_gemini_response(self, api_key, question, model_name='gemini-1.5-flash'):
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(question)
            return response.text
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Gemini API Error: {str(e)}")
            return ""

    def generate_openai_response(self, api_key, question):
        try:
            client = OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": question}]
            )
            return response.choices[0].message.content
        except Exception as e:
            QMessageBox.critical(self, "Error", f"OpenAI API Error: {str(e)}")
            return ""

    def copy_selected(self):
        current_item = self.results_list.currentItem()
        if current_item:
            from PyQt5.QtWidgets import QApplication
            QApplication.clipboard().setText(current_item.text())
            QMessageBox.information(self, "Success", "Content copied to clipboard!")
        else:
            QMessageBox.warning(self, "Warning", "Please select content to copy")

    def reset_ui(self):
        self.results_list.clear()
        self.prompt_input.clear()
        self.keywords_input.clear()
        self.gemini_radio.setChecked(True)
