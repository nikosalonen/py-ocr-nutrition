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
    QFrame,
    QPushButton,
    QVBoxLayout,
)
from PyQt6.QtCore import Qt, QRect, QPoint, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QScreen
import pyautogui
import easyocr
import re


class DraggableButton(QPushButton):
    clicked_signal = pyqtSignal()  # Custom signal for click events

    def __init__(self, title, parent):
        super().__init__(title, parent)
        self.dragging = False
        self.offset = QPoint()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = True
            self.offset = event.pos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.dragging:
            self.move(self.mapToParent(event.pos() - self.offset))
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.dragging:
            self.dragging = False
        else:
            # Emit our custom signal if it wasn't a drag
            self.clicked_signal.emit()
        super().mouseReleaseEvent(event)


def process_screenshot(image_path):
    reader = easyocr.Reader(["en"])
    result = reader.readtext(image_path, detail=0)
    text = " ".join(result)

    print("Extracted text:")
    print(text)

    nutrition_data = {}
    patterns = {
        "calories/energy": r"(?:calories|energy)[:\s]+(?:(\d+(?:\.\d+)?)(?:\s*kcal)?[,\s/]*(?:\d+(?:\.\d+)?\s*kJ)?|(\d+(?:\.\d+)?)\s*kJ[,\s/]*(\d+(?:\.\d+)?)\s*kcal)",
        "fat": r"(?:total\s+)?fat[:\s]+(\d+(?:\.\d+)?)\s*g",
        "carbohydrates": r"(?:total\s+)?carbohydrates?[:\s]+(\d+(?:\.\d+)?)\s*g",
        "protein": r"protein[:\s]+(\d+(?:\.\d+)?)\s*g",
    }

    for key, pattern in patterns.items():
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            if key == "calories/energy":
                kcal_value = match.group(1) or match.group(3)
                kj_value = match.group(2)
                if kcal_value:
                    nutrition_data[key] = f"{kcal_value} kcal"
                elif kj_value:
                    nutrition_data[key] = f"{kj_value} kJ"
            else:
                nutrition_data[key] = f"{match.group(1)}g"
            print(f"Matched {key}: {match.group(0)}")
        else:
            print(f"No match found for {key}")
            # If no match, try to find any number near the keyword
            keyword = key.split("/")[0]  # Use 'calories' instead of 'calories/energy'
            keyword_match = re.search(
                rf"{keyword}.*?(\d+(?:\.\d+)?)", text, re.IGNORECASE
            )
            if keyword_match:
                nutrition_data[key] = f"{keyword_match.group(1)}g"
                print(f"Found nearby number for {key}: {keyword_match.group(0)}")

    print("Extracted nutrition data:")
    print(nutrition_data)

    return nutrition_data


class ScreenReaderApp(QFrame):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.selection_rect = QRect()
        self.dragging = False
        self.background = None
        self.screenshot_mode = False
        self.drag_position = None
        self.screenshot_overlay = None

    def initUI(self):
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setGeometry(100, 100, 300, 220)
        self.setWindowTitle("Screen Reader")

        self.setStyleSheet(
            """
            ScreenReaderApp {
                background-color: #f0f0f0;
                border: 2px solid #c0c0c0;
                border-radius: 10px;
            }
            QLabel {
                color: black;  /* Set label color to black */
            }
            QTextEdit {
                color: #fff;
            }
            QPushButton {
                background-color: #4a90e2;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #3a80d2;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """
        )

        layout = QVBoxLayout(self)

        self.label = QLabel('Click "Screenshot Mode" to start')
        layout.addWidget(self.label)

        button_layout = QHBoxLayout()

        self.screenshot_mode_button = QPushButton("Screenshot Mode")
        self.screenshot_mode_button.clicked.connect(self.toggle_screenshot_mode)
        button_layout.addWidget(self.screenshot_mode_button)

        self.capture_button = QPushButton("Capture")
        self.capture_button.clicked.connect(self.capture_screen)
        self.capture_button.setEnabled(False)
        button_layout.addWidget(self.capture_button)

        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.close_app)
        button_layout.addWidget(self.close_button)

        layout.addLayout(button_layout)

        self.result_text = QTextEdit()
        self.result_text.setFixedHeight(100)
        layout.addWidget(self.result_text)

    def toggle_screenshot_mode(self):
        print("Toggling screenshot mode")
        self.screenshot_mode = not self.screenshot_mode
        if self.screenshot_mode:
            print("Entering screenshot mode")
            if not self.screenshot_overlay:
                print("Creating screenshot overlay")
                self.screenshot_overlay = ScreenshotOverlay()
                self.screenshot_overlay.capture_requested.connect(self.capture_screen)
            print("Showing screenshot overlay")
            self.screenshot_overlay.show()
            self.hide()  # Hide main window after showing overlay
        else:
            print("Exiting screenshot mode")
            if self.screenshot_overlay:
                print("Hiding screenshot overlay")
                self.screenshot_overlay.hide()
            print("Showing main window")
            self.show()
        self.capture_button.setEnabled(self.screenshot_mode)
        self.label.setText(
            'Drag to select the screen area and click "Capture"'
            if self.screenshot_mode
            else 'Click "Screenshot Mode" to start'
        )

    def capture_screen(self):
        if self.screenshot_overlay:
            x, y, width, height = self.screenshot_overlay.get_selection()
            if width > 0 and height > 0:
                screenshot = pyautogui.screenshot(region=(x, y, width, height))
                screenshot.save("screenshot.png")
                self.result_text.setPlainText(
                    f"Captured: {x}, {y}, {width}x{height}\nSaved as 'screenshot.png'"
                )
                self.process_captured_image()
                self.toggle_screenshot_mode()  # Exit screenshot mode after capturing
            else:
                self.result_text.setPlainText("Please select an area before capturing.")
        self.show()  # Ensure the main window is visible after capture

    def process_captured_image(self):
        nutrition_info = process_screenshot("screenshot.png")
        output = "Extracted Nutrition Information:\n"
        if nutrition_info:
            for key, value in nutrition_info.items():
                output += f"{key.capitalize()}: {value}\n"
        else:
            output += "No nutrition information extracted. Please try again with a clearer image."
        self.result_text.setPlainText(output)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = (
                event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            )
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()

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


class ScreenshotOverlay(QWidget):
    capture_requested = pyqtSignal()  # Signal to inform parent of capture request

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.setGeometry(QApplication.primaryScreen().geometry())
        self.selection_rect = QRect()
        self.dragging = False

        # Add draggable Capture button
        self.capture_button = DraggableButton("Capture", self)
        self.capture_button.setStyleSheet(
            """
            QPushButton {
                background-color: #4a90e2;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #3a80d2;
            }
        """
        )
        self.capture_button.move(100, 100)  # Initial position
        self.capture_button.clicked.connect(self.capture_clicked)

    def capture_clicked(self):
        # This method will be connected to the parent's capture_screen method
        self.capture_requested.emit()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 100))
        if not self.selection_rect.isEmpty():
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
            painter.fillRect(self.selection_rect, Qt.GlobalColor.transparent)
            painter.setCompositionMode(
                QPainter.CompositionMode.CompositionMode_SourceOver
            )
            painter.setPen(QColor(255, 0, 0))
            painter.drawRect(self.selection_rect)

    def mousePressEvent(self, event):
        if (
            event.button() == Qt.MouseButton.LeftButton
            and not self.capture_button.geometry().contains(event.pos())
        ):
            self.dragging = True
            self.selection_rect.setTopLeft(event.pos())
            self.selection_rect.setBottomRight(event.pos())
            self.update()

    def mouseMoveEvent(self, event):
        if self.dragging:
            self.selection_rect.setBottomRight(event.pos())
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = False

    def get_selection(self):
        return (
            self.selection_rect.x(),
            self.selection_rect.y(),
            self.selection_rect.width(),
            self.selection_rect.height(),
        )


if __name__ == "__main__":
    app = QApplication(sys.argv)
    ex = ScreenReaderApp()
    ex.show()
    sys.exit(app.exec())
