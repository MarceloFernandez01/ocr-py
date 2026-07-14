"""Overlay flotante para seleccionar el segmento de pantalla a capturar (OCR en vivo)."""

from __future__ import annotations

from PySide6.QtCore import QPoint, QRect, Qt, Signal
from PySide6.QtGui import QColor, QMouseEvent, QPainter, QPaintEvent, QPen
from PySide6.QtWidgets import QPushButton, QWidget

BORDER_WIDTH = 4
HANDLE_SIZE = 16
MIN_SIZE = 40
DEFAULT_SIZE = (500, 300)
ACCENT_COLOR = QColor(42, 130, 218)


class ScreenOverlay(QWidget):
    """Ventana top-level frameless, siempre-encima, semitransparente, con borde de
    acento y handles de redimensión en las esquinas. Arrastrable desde el área central.
    No contiene lógica de negocio ni de captura: solo geometría/dibujo y señales.
    """

    closed = Signal()
    geometry_changed = Signal()
    interaction_started = Signal()
    toggle_transcription_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        """Crea el overlay centrado en la pantalla con el tamaño default."""
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self._close_button = QPushButton("✕", self)
        self._close_button.setFixedSize(20, 20)
        self._close_button.setObjectName("overlayCloseButton")
        self._close_button.clicked.connect(self._on_close_clicked)

        self._toggle_button = QPushButton("▶", self)
        self._toggle_button.setFixedSize(20, 20)
        self._toggle_button.setObjectName("overlayToggleButton")
        self._toggle_button.clicked.connect(self.toggle_transcription_requested)

        self._drag_offset: QPoint | None = None
        self._resize_handle: str | None = None
        self._resize_start_geometry: QRect | None = None
        self._resize_start_pos: QPoint | None = None

        self._center_on_screen()

    def capture_geometry(self) -> QRect:
        """Devuelve el `QRect` (coordenadas globales de pantalla) del área interior
        a capturar, excluyendo el borde/handles dibujados por el propio overlay.
        """
        return QRect(
            self.geometry().x() + BORDER_WIDTH,
            self.geometry().y() + BORDER_WIDTH,
            self.geometry().width() - 2 * BORDER_WIDTH,
            self.geometry().height() - 2 * BORDER_WIDTH,
        )

    def _center_on_screen(self) -> None:
        """Posiciona el overlay centrado en la pantalla primaria con el tamaño default."""
        screen_geometry = self.screen().availableGeometry()
        width, height = DEFAULT_SIZE
        x = screen_geometry.x() + (screen_geometry.width() - width) // 2
        y = screen_geometry.y() + (screen_geometry.height() - height) // 2
        self.setGeometry(x, y, width, height)
        self._position_buttons()

    def _position_buttons(self) -> None:
        """Ubica el botón de pausa/reanudar y el de cierre en la esquina superior derecha."""
        self._close_button.move(self.width() - self._close_button.width() - BORDER_WIDTH, BORDER_WIDTH)
        self._toggle_button.move(
            self._close_button.x() - self._toggle_button.width() - 4,
            BORDER_WIDTH,
        )

    def set_running(self, running: bool) -> None:
        """Actualiza el ícono del botón de pausa/reanudar según si la transcripción corre."""
        self._toggle_button.setText("⏸" if running else "▶")

    def set_toggle_enabled(self, enabled: bool) -> None:
        """Habilita o deshabilita el botón de pausa/reanudar."""
        self._toggle_button.setEnabled(enabled)

    def _on_close_clicked(self) -> None:
        """Cierra el overlay y emite `closed`."""
        self.close()
        self.closed.emit()

    def resizeEvent(self, event) -> None:
        """Reposiciona los botones cuando cambia el tamaño del overlay."""
        super().resizeEvent(event)
        self._position_buttons()

    def paintEvent(self, event: QPaintEvent) -> None:
        """Dibuja el fondo semitransparente y el borde de acento con handles en las esquinas."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        painter.fillRect(self.rect(), QColor(0, 0, 0, 40))

        pen = QPen(ACCENT_COLOR, BORDER_WIDTH)
        painter.setPen(pen)
        painter.drawRect(self.rect().adjusted(BORDER_WIDTH // 2, BORDER_WIDTH // 2, -BORDER_WIDTH // 2, -BORDER_WIDTH // 2))

        painter.setBrush(ACCENT_COLOR)
        painter.setPen(Qt.NoPen)
        for handle_rect in self._handle_rects().values():
            painter.drawRect(handle_rect)

    def _handle_rects(self) -> dict[str, QRect]:
        """Devuelve el rectángulo de cada handle de redimensión, por esquina."""
        w, h = self.width(), self.height()
        return {
            "top_left": QRect(0, 0, HANDLE_SIZE, HANDLE_SIZE),
            "top_right": QRect(w - HANDLE_SIZE, 0, HANDLE_SIZE, HANDLE_SIZE),
            "bottom_left": QRect(0, h - HANDLE_SIZE, HANDLE_SIZE, HANDLE_SIZE),
            "bottom_right": QRect(w - HANDLE_SIZE, h - HANDLE_SIZE, HANDLE_SIZE, HANDLE_SIZE),
        }

    def _handle_at(self, pos: QPoint) -> str | None:
        """Devuelve el nombre del handle bajo `pos`, o None si no hay ninguno."""
        for name, rect in self._handle_rects().items():
            if rect.contains(pos):
                return name
        return None

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Inicia arrastre (mover) o redimensión según dónde se clickeó."""
        if event.button() != Qt.LeftButton:
            return

        handle = self._handle_at(event.pos())
        if handle is not None:
            self._resize_handle = handle
            self._resize_start_geometry = self.geometry()
            self._resize_start_pos = event.globalPosition().toPoint()
        else:
            self._drag_offset = event.globalPosition().toPoint() - self.pos()

        self.interaction_started.emit()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """Mueve o redimensiona el overlay mientras se arrastra el mouse."""
        if self._resize_handle is not None:
            self._resize_to(event.globalPosition().toPoint())
        elif self._drag_offset is not None:
            self.move(event.globalPosition().toPoint() - self._drag_offset)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """Finaliza el arrastre o la redimensión y emite `geometry_changed`."""
        if self._drag_offset is not None or self._resize_handle is not None:
            self.geometry_changed.emit()
        self._drag_offset = None
        self._resize_handle = None
        self._resize_start_geometry = None
        self._resize_start_pos = None

    def _resize_to(self, global_pos: QPoint) -> None:
        """Recalcula la geometría del overlay según el handle activo y `global_pos`."""
        delta = global_pos - self._resize_start_pos
        start = self._resize_start_geometry
        rect = QRect(start)

        if "left" in self._resize_handle:
            rect.setLeft(start.left() + delta.x())
        if "right" in self._resize_handle:
            rect.setRight(start.right() + delta.x())
        if "top" in self._resize_handle:
            rect.setTop(start.top() + delta.y())
        if "bottom" in self._resize_handle:
            rect.setBottom(start.bottom() + delta.y())

        if rect.width() < MIN_SIZE:
            if "left" in self._resize_handle:
                rect.setLeft(rect.right() - MIN_SIZE)
            else:
                rect.setRight(rect.left() + MIN_SIZE)
        if rect.height() < MIN_SIZE:
            if "top" in self._resize_handle:
                rect.setTop(rect.bottom() - MIN_SIZE)
            else:
                rect.setBottom(rect.top() + MIN_SIZE)

        self.setGeometry(rect)
