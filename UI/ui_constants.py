"""
Qt controls/widgets used in UI:
- QtWidgets.QApplication
- QtWidgets.QButtonGroup
- QtWidgets.QComboBox
- QtWidgets.QFileDialog
- QtWidgets.QFrame
- QtWidgets.QGridLayout
- QtWidgets.QHBoxLayout
- QtWidgets.QLabel
- QtWidgets.QLineEdit
- QtWidgets.QMainWindow
- QtWidgets.QPlainTextEdit
- QtWidgets.QProgressBar
- QtWidgets.QPushButton
- QtWidgets.QScrollArea
- QtWidgets.QSplitter
- QtWidgets.QTextEdit
- QtWidgets.QToolBar
- QtWidgets.QToolButton
- QtWidgets.QVBoxLayout
- QtWidgets.QWidget

Other Qt classes referenced in UI:
- QtCore.QEvent
- QtCore.QMetaObject
- QtCore.QObject
- QtCore.QSize
- QtCore.QThread
- QtCore.QTimer
- QtCore.Q_ARG
- QtCore.pyqtSignal
- QtGui.QDragEnterEvent
- QtGui.QDropEvent
- QtGui.QKeyEvent
- QtGui.QPixmap
- QtGui.QResizeEvent
- QtGui.QShowEvent
- QtGui.QTextCursor
"""

# Dark/cool palette (style_color) with suggested usage
darkcool_midnight = "rgb(15, 18, 26)"  # App/page background
darkcool_slate = "rgb(22, 26, 38)"  # Panels/cards/sections
darkcool_slate_alt = "rgb(28, 34, 48)"  # Hover/secondary panels
darkcool_steel = "rgb(52, 63, 84)"  # Borders/dividers
darkcool_ice = "rgb(220, 230, 245)"  # Primary text
darkcool_mist = "rgb(150, 165, 190)"  # Secondary text
darkcool_azure = "rgb(98, 140, 255)"  # Accent buttons/links
darkcool_azure_light = "rgb(118, 160, 255)"  # Accent hover
darkcool_mint = "rgb(73, 201, 150)"  # Success states
darkcool_amber = "rgb(245, 196, 90)"  # Warnings
darkcool_rose = "rgb(239, 95, 118)"  # Errors
darkcool_ocean = "rgb(54, 82, 120)"  # Selection highlight

# Professional palette: University of Miami (UofM)
uofm_orange = "rgb(244, 115, 33)"  # Primary brand accent (CTAs/highlights)
uofm_green = "rgb(0, 80, 48)"  # Primary brand base (headers/primary panels)

# Font suggestions per style
darkcool_font_windows = "Segoe UI"  # Clean, modern Windows UI font
darkcool_font_web = "Inter"  # Web-friendly sans (Google Fonts)
uofm_font_windows = "Book Antiqua"  # UofM Windows preference
uofm_font_web = "Libre Baskerville"  # Classic serif web fallback

# Global font sizes (pt)
FONT_SIZE_SMALL = 8  # Small text
FONT_SIZE_NORMAL = 12  # Default text
FONT_SIZE_LARGE = 16  # Large text

# Text/foreground colors
TEXT_COLOR_BLACK = "rgb(0, 0, 0)"  # Black text
TEXT_COLOR_WHITE = "rgb(255, 255, 255)"  # White text
TEXT_COLOR_GRAY = "rgb(128, 128, 128)"  # Gray text
TEXT_COLOR_RED = "rgb(220, 20, 60)"  # Red text

# Sizing
TOOLBAR_HEIGHT = 64  # Main toolbar height (px)

# Derived UI constants (Darkcool defaults)
TOGGLE_ON_COLOR = darkcool_azure  # Toggle/checkbox on
TOGGLE_OFF_COLOR = darkcool_slate  # Toggle/checkbox off
TOGGLE_DISABLED_COLOR = darkcool_slate_alt  # Disabled controls
HEADER_COLOR_READY = darkcool_mint  # Ready header color
HEADER_COLOR_LOADING = darkcool_amber  # Loading header color
HEADER_COLOR_FAULT = darkcool_rose  # Fault header color
COLUMN_SETTINGS_BG = darkcool_slate  # Settings column background
COLUMN_CHAT_BG = darkcool_slate_alt  # Chat column background
COLUMN_CARDS_BG = darkcool_slate  # Cards column background
MAIN_PAGE_BG = darkcool_midnight  # Main page background
TOOLBAR_BG_COLOR = darkcool_mist  # Toolbar background
CURRENT_FONT_WINDOWS = darkcool_font_windows  # Active Windows font
ACCORDION_EXPANDED_TEXT_COLOR = TEXT_COLOR_BLACK  # Expanded header text
ACCORDION_EXPANDED_BG_COLOR = darkcool_slate  # Expanded header background
ACCORDION_COLLAPSED_TEXT_COLOR = TEXT_COLOR_WHITE  # Collapsed header text
ACCORDION_COLLAPSED_BG_COLOR = darkcool_midnight  # Collapsed header background
