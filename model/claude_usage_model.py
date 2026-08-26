"""Costo y acumulación de consumo de Claude Haiku 4.5 en OCR.

Calcula el costo de una llamada a partir de los tokens reales que devuelve la
API y acumula el gasto del mes en curso en config.json. No importa PySide6 ni
el SDK `anthropic`: solo aritmética y persistencia vía `model/config_model.py`.
"""

from datetime import datetime

from model.config_model import load_config, save_claude_spend

HAIKU_INPUT_USD_PER_MTOK = 1.00
"""Pricing vigente de Claude Haiku 4.5 por millón de tokens de entrada. Valor
cacheado: puede cambiar si Anthropic actualiza el pricing del modelo."""

HAIKU_OUTPUT_USD_PER_MTOK = 5.00
"""Pricing vigente de Claude Haiku 4.5 por millón de tokens de salida. Valor
cacheado: puede cambiar si Anthropic actualiza el pricing del modelo."""


def call_cost_usd(input_tokens: int, output_tokens: int) -> float:
    """Calcula el costo exacto en USD de una llamada, según los tokens reales
    devueltos por la API (`response.usage`).
    """
    return (
        input_tokens / 1_000_000 * HAIKU_INPUT_USD_PER_MTOK
        + output_tokens / 1_000_000 * HAIKU_OUTPUT_USD_PER_MTOK
    )


def _current_month() -> str:
    """Devuelve el mes calendario actual en formato `"YYYY-MM"`."""
    return datetime.now().strftime("%Y-%m")


def load_spend() -> dict:
    """Devuelve el acumulador `claude_spend` del mes en curso, para pintar la
    barra de gasto al arrancar.

    Si el mes persistido en config.json no coincide con el mes actual, lo
    devuelve reiniciado en memoria (sin persistir el reinicio todavía).
    """
    spend = load_config().get("claude_spend", {})
    month = _current_month()
    if spend.get("month") != month:
        return {"month": month, "usd": 0.0, "calls": 0}
    return spend


def register_call(input_tokens: int, output_tokens: int) -> dict:
    """Registra una llamada a Claude en el acumulador de gasto mensual.

    Reinicia `claude_spend` si el mes persistido cambió, suma el costo de la
    llamada y una unidad a `calls`, persiste el resultado en config.json y lo
    devuelve.
    """
    spend = load_spend()
    spend["usd"] += call_cost_usd(input_tokens, output_tokens)
    spend["calls"] += 1
    save_claude_spend(spend)
    return spend
