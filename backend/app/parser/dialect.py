from typing import Optional


def detect_dialect(sql_text: str, explicit: Optional[str] = None) -> str:
    """Auto-detect SQL dialect from text content.

    Detection priority:
    1. Explicit specification (user-provided)
    2. AUTO_INCREMENT -> MySQL
    3. SERIAL / BIGSERIAL / :: type cast -> PostgreSQL
    4. Backtick quoted identifiers -> MySQL
    5. Default -> mysql
    """
    if explicit:
        return explicit.lower()

    if not sql_text or not sql_text.strip():
        return "mysql"

    upper = sql_text.upper()

    # AUTO_INCREMENT is MySQL-specific
    if "AUTO_INCREMENT" in upper:
        return "mysql"

    # SERIAL and BIGSERIAL are PostgreSQL-specific
    if " SERIAL" in upper or "BIGSERIAL" in upper or upper.startswith("SERIAL"):
        return "postgresql"

    # :: type cast is PostgreSQL-specific
    if "::" in sql_text:
        return "postgresql"

    # Backtick identifiers indicate MySQL
    if "`" in sql_text:
        return "mysql"

    return "mysql"
