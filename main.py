import sys
from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QLabel,
    QMessageBox,
    QHBoxLayout,
)
from PyQt6.QtCore import Qt, QRect
from PyQt6.QtGui import QPainter, QColor, QScreen
import pyautogui
import easyocr
import re


def process_screenshot(image_path):
    reader = easyocr.Reader(["en"])
    result = reader.readtext(image_path, detail=0)
    text = " ".join(result)

    # Debug: Print the extracted text
    print("Extracted text:")
    print(text)

    nutrition_data = {}
    patterns = {
        "calories": r"(?:calories|energy)[:\s]+(?:(\d+)(?:\s*kcal)?[,\s/]*(?:\d+\s*kJ)?|(\d+)\s*kJ[,\s/]*(\d+)\s*kcal)",
        "fat": r"(?:total\s+)?fat[:\s]+(\d+(?:\.\d+)?)g",
        "carbohydrates": r"(?:total\s+)?carbohydrates?[:\s]+(\d+(?:\.\d+)?)g",
        "protein": r"protein[:\s]+(\d+(?:\.\d+)?)g",
        "sodium": r"(?:sodium|salt)[:\s]+(\d+(?:\.\d+)?)mg",
    }

    for key, pattern in patterns.items():
        match = re.search(pattern, text.lower())
        if match:
            if key == "calories":
                kcal_value = match.group(1) or match.group(3)
                kj_value = match.group(2)
                if kcal_value:
                    nutrition_data[key] = f"{kcal_value} kcal"
                elif kj_value:
                    nutrition_data[key] = f"{kj_value} kJ"
            nutrition_data[key] = match.group(1)
        else:
            # Debug: Print when a pattern doesn't match
            print(f"No match found for {key}")

    # Debug: Print the extracted nutrition data
    print("Extracted nutrition data:")
    print(nutrition_data)

    return nutrition_data


class ScreenReaderApp(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.selection_rect = QRect()
        self.dragging = False
        self.background = None

    def initUI(self):
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        screen = QApplication.primaryScreen().size()
        self.setGeometry(0, 0, screen.width(), screen.height())
        self.setWindowTitle("Screen Reader")

        # Create a central widget for controls
        self.control_widget = QWidget(self)
        self.control_widget.setStyleSheet("background-color: rgba(0, 0, 0, 150);")
        control_layout = QVBoxLayout(self.control_widget)

        self.label = QLabel('Drag to select the screen area and click "Capture"')
        self.label.setStyleSheet("color: white;")
        control_layout.addWidget(self.label)

        button_layout = QHBoxLayout()
        self.capture_button = QPushButton("Capture")
        self.capture_button.clicked.connect(self.capture_screen)
        button_layout.addWidget(self.capture_button)

        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.close_app)
        button_layout.addWidget(self.close_button)

        control_layout.addLayout(button_layout)

        self.result_text = QTextEdit()
        self.result_text.setFixedHeight(100)  # Limit the height of the text area
        control_layout.addWidget(self.result_text)

        # Position the control widget at the bottom of the screen
        self.control_widget.setGeometry(0, screen.height() - 200, screen.width(), 200)

    def showEvent(self, event):
        self.background = QApplication.primaryScreen().grabWindow(0).toImage()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.drawImage(0, 0, self.background)

        # Draw semi-transparent overlay
        overlay = QColor(0, 0, 0, 100)
        painter.fillRect(self.rect(), overlay)

        # Draw the "hole"
        if not self.selection_rect.isEmpty():
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
            painter.fillRect(self.selection_rect, Qt.GlobalColor.transparent)

            # Draw red border around the hole
            painter.setCompositionMode(
                QPainter.CompositionMode.CompositionMode_SourceOver
            )
            pen = painter.pen()
            pen.setColor(QColor(255, 0, 0))
            pen.setWidth(2)
            painter.setPen(pen)
            painter.drawRect(self.selection_rect)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = True
            self.selection_rect.setTopLeft(event.position().toPoint())
            self.selection_rect.setBottomRight(event.position().toPoint())
            self.update()

    def mouseMoveEvent(self, event):
        if self.dragging:
            self.selection_rect.setBottomRight(event.position().toPoint())
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = False
            self.selection_rect.setBottomRight(event.position().toPoint())
            self.update()

    def capture_screen(self):
        x = min(self.selection_rect.left(), self.selection_rect.right())
        y = min(self.selection_rect.top(), self.selection_rect.bottom())
        width = abs(self.selection_rect.width())
        height = abs(self.selection_rect.height())

        screenshot = pyautogui.screenshot(region=(x, y, width, height))
        screenshot.save("screenshot.png")
        self.result_text.setPlainText(
            f"Captured: {x}, {y}, {width}x{height}\nSaved as 'screenshot.png'"
        )
        self.process_captured_image()

    def process_captured_image(self):
        nutrition_info = process_screenshot("screenshot.png")
        output = "Extracted Nutrition Information:\n"
        if nutrition_info:
            for key, value in nutrition_info.items():
                output += f"{key.capitalize()}: {value}\n"
        else:
            output += "No nutrition information extracted. Please try again with a clearer image."
        self.result_text.setPlainText(output)

    def close_app(self):
        reply = QMessageBox.question(
            self,
            "Confirm Close",
            "Are you sure you want to close the application?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.close()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    ex = ScreenReaderApp()
    ex.show()
    sys.exit(app.exec())
