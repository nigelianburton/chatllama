from __future__ import annotations

import sys
from pathlib import Path

from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtWebEngineWidgets import QWebEngineView


class HtmlWidgetWindow(QtWidgets.QMainWindow):
    def __init__(self, output_path: Path) -> None:
        super().__init__()
        self._output_path = output_path
        self.setWindowTitle("HTML Widget Test")
        self.resize(800, 600)

        container = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(container)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        header = QtWidgets.QLabel("Qt window with embedded HTML")
        header.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(header)

        self._frame = QtWidgets.QFrame()
        self._frame.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        self._frame.setStyleSheet("background-color: #ffffff; border: 1px solid #666;")
        frame_layout = QtWidgets.QVBoxLayout(self._frame)
        frame_layout.setContentsMargins(0, 0, 0, 0)
        frame_layout.setSpacing(0)

        self._web = QWebEngineView()
        frame_layout.addWidget(self._web)
        layout.addWidget(self._frame, 1)

        footer = QtWidgets.QLabel("Expected HTML content: Hello Nigel")
        footer.setStyleSheet("color: #444;")
        layout.addWidget(footer)

        self.setCentralWidget(container)

        html = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
          <meta charset="UTF-8" />
          <style>
            body {
              margin: 0;
              display: flex;
              align-items: center;
              justify-content: center;
              width: 100%;
              height: 100%;
              background: #f2f2f2;
              font-family: Arial, sans-serif;
            }
            .panel {
              padding: 24px 32px;
              border-radius: 12px;
              background: #ffffff;
              box-shadow: 0 6px 18px rgba(0,0,0,0.2);
              font-size: 28px;
              color: #1a1a1a;
              border: 2px solid #4a90e2;
            }
          </style>
        </head>
        <body>
          <div class="panel">Hello Nigel</div>
        </body>
        </html>
        """
        self._web.setHtml(html)
        self._web.loadFinished.connect(self._on_loaded)

    def _on_loaded(self, ok: bool) -> None:
        delay_ms = 1000 if ok else 1500
        QtCore.QTimer.singleShot(delay_ms, self._capture_and_exit)

    def _capture_and_exit(self) -> None:
        pixmap = self.grab()
        self._output_path.parent.mkdir(parents=True, exist_ok=True)
        pixmap.save(str(self._output_path))
        QtCore.QTimer.singleShot(200, QtWidgets.QApplication.instance().quit)


def main() -> None:
    output_path = Path(__file__).resolve().parent / "test_html_screencap.png"
    app = QtWidgets.QApplication(sys.argv)
    window = HtmlWidgetWindow(output_path)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
