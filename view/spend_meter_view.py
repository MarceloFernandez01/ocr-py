"""Barra inferior permanente con el medidor de gasto de Claude Haiku."""

from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QLabel, QProgressBar, QWidget

BAR_HEIGHT_PX = 28


class SpendMeterView(QWidget):
    """Franja horizontal con el progreso de gasto de Claude Haiku del mes en
    curso: barra de progreso contra el presupuesto configurado y un label de
    resumen ("Claude · 14 llamadas · $0.42 de $5.00"). Solo presentación: no
    lee config.json ni calcula costos, recibe los valores ya calculados por
    el controller.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        """Crea la barra de progreso y el label de resumen."""
        super().__init__(parent)
        self.setObjectName("spendMeter")
        self.setFixedHeight(BAR_HEIGHT_PX)

        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("spendMeterBar")
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setTextVisible(False)

        self.summary_label = QLabel()
        self.summary_label.setObjectName("spendMeterLabel")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(12)
        layout.addWidget(self.progress_bar, stretch=1)
        layout.addWidget(self.summary_label)

    def set_spend(self, usd: float, calls: int, budget_usd: float) -> None:
        """Actualiza el progreso y el texto de resumen del gasto del mes en curso."""
        percent = min(100, round(usd / budget_usd * 100)) if budget_usd > 0 else 100
        self.progress_bar.setValue(percent)
        self.summary_label.setText(f"Claude · {calls} llamadas · ${usd:.2f} de ${budget_usd:.2f}")

    def set_over_budget(self, over: bool) -> None:
        """Alterna el estado de alerta visual de la barra al superar el presupuesto."""
        self.progress_bar.setProperty("overBudget", over)
        self.progress_bar.style().unpolish(self.progress_bar)
        self.progress_bar.style().polish(self.progress_bar)
