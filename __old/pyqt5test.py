import sys
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QVBoxLayout

def on_button_click():
    print("Button clicked!")

# Main application class
def main():
    app = QApplication(sys.argv)

    # Create the main window
    window = QWidget()
    window.setWindowTitle("PyQt5 Test")
    window.setGeometry(100, 100, 300, 200)  # x, y, width, height

    # Create a button
    button = QPushButton("Click Me")
    button.clicked.connect(on_button_click)  # Connect button click to function

    # Set up the layout
    layout = QVBoxLayout()
    layout.addWidget(button)
    window.setLayout(layout)

    # Show the window
    window.show()

    # Execute the application
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
