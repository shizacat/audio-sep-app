"""Main window of the application."""

from PySide6.QtWidgets import QLabel, QMainWindow, QVBoxLayout, QWidget


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("AudioSep")
        self.resize(800, 480)

        message = QLabel("Откройте аудиофайл и опишите звук, который нужно отделить.")
        message.setWordWrap(True)
        layout = QVBoxLayout()
        layout.addWidget(message)

        central = QWidget()
        central.setLayout(layout)
        self.setCentralWidget(central)
