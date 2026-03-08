"""Entry point for Video Generator Blaster."""

import logging
import sys

from PySide6.QtWidgets import QApplication

from app.ui_main import MainWindow


def main() -> None:
    """Launch the Video Generator Blaster application."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    app = QApplication(sys.argv)
    app.setApplicationName("Video Generator Blaster")
    app.setOrganizationName("VideoGenBlaster")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
