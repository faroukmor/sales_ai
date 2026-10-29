# core/formatting.py


def format_number(value: float) -> str:
    """16.0 -> '16' و 1.5 -> '1.5'. (لا نستخدم :g لأنه يحوّل 1000000 إلى 1e+06)."""
    value = float(value)
    if value.is_integer():
        return str(int(value))
    return f"{value:.2f}".rstrip("0").rstrip(".")
