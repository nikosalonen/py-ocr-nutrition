import tkinter as tk
from tkinter import ttk, messagebox
from PIL import ImageGrab
import pyautogui

import easyocr
import re


def process_screenshot(image_path):
    # Create a reader
    reader = easyocr.Reader(['en'])

    # Perform OCR on the image
    result = reader.readtext(image_path, detail=0)
    text = ' '.join(result)

    # Information Extraction and Structuring
    nutrition_data = {}

    # Look for common nutrition label items
    patterns = {
        'calories': r'calories[:\s]+(\d+)',
        'fat': r'total fat[:\s]+(\d+)g',
        'carbohydrates': r'total carbohydrate[:\s]+(\d+)g',
        'protein': r'protein[:\s]+(\d+)g',
    }

    for key, pattern in patterns.items():
        match = re.search(pattern, text.lower())
        if match:
            nutrition_data[key] = match.group(1)

    return nutrition_data

class ScreenReaderApp:
    def __init__(self, master):
        self.master = master
        master.title("Screen Reader")
        master.attributes('-alpha', 0.3)  # Set window transparency
        master.attributes('-topmost', True)  # Keep window on top

        self.screen_width = master.winfo_screenwidth()
        self.screen_height = master.winfo_screenheight()

        # Set initial size and position
        self.hole_size = 200
        self.x = (self.screen_width - self.hole_size) // 2
        self.y = (self.screen_height - self.hole_size) // 2

        # Create canvas
        self.canvas = tk.Canvas(master, highlightthickness=0, cursor="arrow")
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # Create the "hole"
        self.hole = self.canvas.create_rectangle(self.x, self.y, self.x + self.hole_size, self.y + self.hole_size,
                                                 fill='', outline='red', width=2)

        # Create the mask
        self.mask = self.canvas.create_rectangle(0, 0, self.screen_width, self.screen_height,
                                                 fill='gray', stipple='gray50')
        self.canvas.tag_raise(self.hole, self.mask)

        # Bind events
        self.canvas.bind('<Configure>', self.on_resize)
        self.canvas.bind('<Motion>', self.on_motion)
        self.canvas.bind('<B1-Motion>', self.on_drag)
        self.canvas.bind('<ButtonPress-1>', self.on_press)
        self.canvas.bind('<ButtonRelease-1>', self.on_release)

        # Capture button
        self.capture_button = ttk.Button(master, text="Capture", command=self.capture_screen)
        self.capture_button.place(relx=1, rely=1, anchor='se')

        # Close button
        self.close_button = ttk.Button(master, text="Close", command=self.confirm_close)
        self.close_button.place(relx=1, rely=0, anchor='ne')

        # Result text
        self.result_text = tk.Text(master, height=3, width=30)
        self.result_text.place(relx=0, rely=1, anchor='sw')

        self.dragging = False
        self.resizing = False

    def on_resize(self, event):
        # Update the mask size
        self.canvas.coords(self.mask, 0, 0, event.width, event.height)

    def on_motion(self, event):
        x1, y1, x2, y2 = self.canvas.coords(self.hole)
        if abs(event.x - x2) < 10 and abs(event.y - y2) < 10:
            self.canvas.config(cursor="sizing")
        else:
            self.canvas.config(cursor="arrow")

    def on_press(self, event):
        x1, y1, x2, y2 = self.canvas.coords(self.hole)
        # Check if click is near the edge of the hole
        if abs(event.x - x2) < 10 and abs(event.y - y2) < 10:
            self.resizing = True
            self.canvas.config(cursor="sizing")
        else:
            self.dragging = True
            self.canvas.config(cursor="fleur")

    def on_drag(self, event):
        if self.dragging:
            x1, y1, x2, y2 = self.canvas.coords(self.hole)
            dx = event.x - (x1 + x2) / 2
            dy = event.y - (y1 + y2) / 2
            self.canvas.move(self.hole, dx, dy)
        elif self.resizing:
            x1, y1, _, _ = self.canvas.coords(self.hole)
            self.canvas.coords(self.hole, x1, y1, max(x1+10, event.x), max(y1+10, event.y))

    def on_release(self, event):
        self.dragging = False
        self.resizing = False
        self.canvas.config(cursor="arrow")

    def process_captured_image(self):
        nutrition_info = process_screenshot("screenshot.png")

        # Display results
        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(tk.END, "Extracted Nutrition Information:\n")
        for key, value in nutrition_info.items():
            self.result_text.insert(tk.END, f"{key.capitalize()}: {value}\n")

    def capture_screen(self):
        # Hide the main window
        self.master.withdraw()
        self.master.update()

        # Get the hole coordinates relative to the screen
        x1, y1, x2, y2 = self.canvas.coords(self.hole)
        screen_x = int(self.master.winfo_x() + x1)
        screen_y = int(self.master.winfo_y() + y1)
        capture_width = int(x2 - x1)
        capture_height = int(y2 - y1)

        # Capture the screen area
        screenshot = pyautogui.screenshot(region=(screen_x, screen_y, capture_width, capture_height))
        screenshot.save("screenshot.png")

        # Show the main window again
        self.master.deiconify()

        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(tk.END, f"Captured: {screen_x}, {screen_y}, {capture_width}x{capture_height}\n")
        self.result_text.insert(tk.END, "Saved as 'screenshot.png'")

        self.process_captured_image()

    def confirm_close(self):
        if messagebox.askyesno("Confirm Close", "Are you sure you want to close the application?"):
            self.master.quit()

root = tk.Tk()
root.attributes('-fullscreen', True)
app = ScreenReaderApp(root)
root.mainloop()
