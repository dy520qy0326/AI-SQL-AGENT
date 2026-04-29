import re

from app.parser.base import BaseParser
from app.parser.models import ParseResult


class PostgreSQLParser(BaseParser):
    """PostgreSQL dialect parser.

    Handles PostgreSQL-specific syntax:
    - SERIAL / BIGSERIAL pseudo-types (auto-increment)
    - " double-quote quoting (via sqlglot postgres dialect)
    - ::type cast syntax (handled by sqlglot, ignored)
    - PG-specific types: UUID, JSONB, TIMESTAMPTZ, BYTEA
    - COMMENT ON TABLE / COMMENT ON COLUMN (separate statements)
    """

    dialect = "postgresql"

    _SERIAL_MAP = {
        "serial": ("integer", True),
        "smallserial": ("smallint", True),
        "bigserial": ("bigint", True),
    }

    _SMALLSERIAL_RE = re.compile(r"\bSMALLSERIAL\b", re.IGNORECASE)

    def _parse_create_table(self, statement: str) -> "Table":
        """Parse a PostgreSQL CREATE TABLE, handling SERIAL pseudo-types.

        SERIAL and BIGSERIAL are recognized by sqlglot as custom types.
        SMALLSERIAL is not — we pre-process it to INT and track the column names.
        """
        smallserial_cols = self._find_smallserial_cols(statement)
        if smallserial_cols:
            statement = self._SMALLSERIAL_RE.sub("INT", statement)

        table = super()._parse_create_table(statement)

        for col in table.columns:
            lower_type = col.type.lower()
            if lower_type in self._SERIAL_MAP:
                mapped_type, auto_inc = self._SERIAL_MAP[lower_type]
                col.type = mapped_type
                col.auto_increment = auto_inc
            elif col.name.lower() in smallserial_cols:
                col.type = "smallint"
                col.auto_increment = True

        return table

    @staticmethod
    def _find_smallserial_cols(statement: str) -> set[str]:
        """Find column names declared as SMALLSERIAL."""
        cols: set[str] = set()
        for m in re.finditer(
            r'(?:(["`])([^"`]+)\1|(\w+))\s+SMALLSERIAL\b',
            statement,
            re.IGNORECASE,
        ):
            col_name = m.group(2) or m.group(3)
            if col_name:
                cols.add(col_name.lower())
        return cols

    def parse(self, sql_text: str) -> ParseResult:
        """Parse SQL text, including COMMENT ON statements."""
        result = super().parse(sql_text)

        if not sql_text or not sql_text.strip():
            return result

        self._apply_comments(sql_text, result)
        return result

    def _apply_comments(self, sql_text: str, result: ParseResult) -> None:
        """Apply COMMENT ON TABLE / COLUMN statements to parsed tables."""
        statements = self._parse_statements(sql_text)
        for stmt in statements:
            stripped = stmt.strip()
            upper = stripped.upper()
            if upper.startswith("COMMENT ON TABLE"):
                self._apply_table_comment(stripped, result)
            elif upper.startswith("COMMENT ON COLUMN"):
                self._apply_column_comment(stripped, result)

    @staticmethod
    def _apply_table_comment(stmt: str, result: ParseResult) -> None:
        """Apply COMMENT ON TABLE ... IS '...' to the matching table."""
        m = re.match(
            r"COMMENT\s+ON\s+TABLE\s+(.+?)\s+IS\s+'([^']*)'\s*$",
            stmt,
            re.IGNORECASE,
        )
        if not m:
            return
        raw_name = m.group(1).strip()
        comment = m.group(2)
        table_name = raw_name.strip('"')
        for table in result.tables:
            if table.name == table_name:
                table.comment = comment
                break

    @staticmethod
    def _apply_column_comment(stmt: str, result: ParseResult) -> None:
        """Apply COMMENT ON COLUMN table.col IS '...' to the matching column."""
        m = re.match(
            r"COMMENT\s+ON\s+COLUMN\s+(.+?)\s+IS\s+'([^']*)'\s*$",
            stmt,
            re.IGNORECASE,
        )
        if not m:
            return
        raw_ref = m.group(1).strip()
        comment = m.group(2)

        # Split by last dot to get table[.schema] and column
        parts = raw_ref.rsplit(".", 1)
        if len(parts) != 2:
            return
        table_name = parts[0].strip().strip('"')
        column_name = parts[1].strip().strip('"')

        for table in result.tables:
            if table.name == table_name:
                for col in table.columns:
                    if col.name == column_name:
                        col.comment = comment
                        return
