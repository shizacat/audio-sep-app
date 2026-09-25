"""Application entry point."""

import logging
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from audiosep_app.cli import configure_logging, parse_args
from audiosep_app.separation.job import make_separation_task
from audiosep_app.ui.main_window import MainWindow
from audiosep_app.ui.startup_error import show_startup_error, startup_error_message

logger = logging.getLogger(__name__)


def main() -> None:
    args, qt_args = parse_args()
    configure_logging(args.log_level)
    qt_app = QApplication([sys.argv[0], *qt_args])
    raise SystemExit(run_application(qt_app, args.separator, args.clap))


def run_application(
    qt_app: QApplication,
    separator_path: Path | None,
    clap_path: Path | None,
) -> int:
    message = startup_error_message(separator_path, clap_path)
    if message is not None:
        logger.error("%s", message)
        show_startup_error(message)
        return 1
    window = MainWindow(make_separation_task(separator_path, clap_path))
    window.show()
    return qt_app.exec()


if __name__ == "__main__":
    main()
