import logging
from typing import Optional
from PyQt6 import QtCore, QtWidgets

logger = logging.getLogger(__name__)


class HardwareInfoPanel(QtWidgets.QWidget):
    """Hardware information widget for displaying GPU and token usage stats.
    
    This widget manages GPU monitoring and updates via a timer,
    displaying VRAM usage, GPU utilization, and token counts.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("HardwareInfoPanel")
        self.setFixedWidth(92)
        
        # GPU monitoring state
        self._gpu_samples: list[tuple[float, float]] = []  # (vram_used_mb, utilization_pct)
        self._gpu_timer: Optional[QtCore.QTimer] = None
        self._last_token_usage: dict = {}  # Track last token usage
        
        # UI components
        self.status_label: Optional[QtWidgets.QLabel] = None
        
        self._build_ui()
    
    def _build_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Status label for hardware info
        self.status_label = QtWidgets.QLabel("Ready")
        self.status_label.setFixedWidth(92)
        self.status_label.setWordWrap(True)
        self.status_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignTop)
        self.status_label.setStyleSheet("color: #aaaaaa; font-size: 10px; padding: 4px;")
        
        layout.addWidget(self.status_label)
        self.setLayout(layout)
    
    def start_monitoring(self) -> None:
        """Start polling GPU stats every second."""
        try:
            import GPUtil
            self._gpu_timer = QtCore.QTimer()
            self._gpu_timer.timeout.connect(self._update_gpu_stats)
            self._gpu_timer.start(1000)  # Poll every second
            logger.debug("GPU monitoring started")
        except ImportError:
            logger.debug("GPUtil not available; GPU monitoring disabled")
    
    def stop_monitoring(self) -> None:
        """Stop GPU monitoring."""
        if self._gpu_timer:
            self._gpu_timer.stop()
            self._gpu_timer = None
            logger.debug("GPU monitoring stopped")
    
    def update_token_usage(self, usage: dict) -> None:
        """Update token usage statistics.
        
        Args:
            usage: Dict with keys 'prompt_tokens', 'completion_tokens', 'total_tokens'
        """
        self._last_token_usage = {
            "prompt": usage.get("prompt_tokens", 0),
            "completion": usage.get("completion_tokens", 0),
            "total": usage.get("total_tokens", 0)
        }
        # Immediately update display with new token info
        self._update_status_display()
    
    def _update_gpu_stats(self) -> None:
        """Poll GPU and update display with rolling average."""
        try:
            import GPUtil
            gpus = GPUtil.getGPUs()
            if not gpus:
                return
            
            gpu = gpus[0]
            vram_used = gpu.memoryUsed  # MB
            utilization = gpu.load * 100  # Percent
            
            # Only add non-zero readings
            if vram_used > 0 or utilization > 0:
                self._gpu_samples.append((vram_used, utilization))
                # Keep only last 10 samples
                if len(self._gpu_samples) > 10:
                    self._gpu_samples.pop(0)
            
            # Update display
            self._update_status_display()
            
        except Exception as e:
            logger.debug(f"GPU stats update failed: {e}")
    
    def _update_status_display(self) -> None:
        """Update the status label with current GPU and token stats."""
        if not self.status_label:
            return
        
        status_msg = "Ready"
        
        # Add GPU stats if available
        if self._gpu_samples:
            avg_vram = sum(s[0] for s in self._gpu_samples) / len(self._gpu_samples)
            avg_util = sum(s[1] for s in self._gpu_samples) / len(self._gpu_samples)
            status_msg = f"GPU: {avg_vram:.0f} MB VRAM | {avg_util:.1f}% Util"
        
        # Append token usage if available
        if self._last_token_usage:
            prompt = self._last_token_usage.get("prompt", 0)
            completion = self._last_token_usage.get("completion", 0)
            total = self._last_token_usage.get("total", 0)
            if total > 0:
                status_msg += f" | Tokens: {total} ({prompt}+{completion})"
        
        self.status_label.setText(status_msg)
    
    def get_status_text(self) -> str:
        """Get the current status text."""
        return self.status_label.text() if self.status_label else "Ready"
    
    def set_ready_status(self, message: str = "Ready") -> None:
        """Set status to a simple message."""
        if self.status_label:
            self.status_label.setText(message)
            self._gpu_samples.clear()  # Reset GPU samples when status changes
