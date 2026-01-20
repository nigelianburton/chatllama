from __future__ import annotations

from pathlib import Path
from typing import Optional

from PyQt6 import QtGui, QtWidgets

from logger import get_logger


class Utilities:
    @staticmethod
    def log_screenshot(log_file: Path) -> Optional[Path]:
        logger = get_logger("Utilities")
        try:
            screen = QtWidgets.QApplication.primaryScreen()
            if screen is None:
                logger.error("No primary screen available for screenshot")
                return None

            base_name = log_file.stem
            target_dir = log_file.parent

            index = 1
            while True:
                candidate = target_dir / f"{base_name} ({index}).png"
                if not candidate.exists():
                    break
                index += 1

            pixmap = screen.grabWindow(0)
            if pixmap.isNull():
                logger.error("Screenshot capture returned empty pixmap")
                return None

            saved = pixmap.save(str(candidate), "PNG")
            if not saved:
                logger.error("Failed to save screenshot to %s", candidate)
                return None

            logger.info("Screenshot saved: %s", candidate)
            return candidate
        except Exception as exc:  # pragma: no cover
            logger.exception("Screenshot capture failed: %s", exc)
            return None
