"""Application entry point."""

import sys

from PySide6.QtWidgets import QApplication

from audiosep_app.cli import configure_logging, parse_args
from audiosep_app.ui.main_window import MainWindow


def main() -> None:
    args, qt_args = parse_args()
    configure_logging(args.log_level)
    qt_app = QApplication([sys.argv[0], *qt_args])
    window = MainWindow()
    window.show()
    raise SystemExit(qt_app.exec())


if __name__ == "__main__":
    main()
