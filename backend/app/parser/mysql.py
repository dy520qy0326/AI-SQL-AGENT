from sqlglot import exp

from app.parser.base import BaseParser


class MySQLParser(BaseParser):
    """MySQL dialect parser.

    Handles MySQL-specific syntax:
    - `` ` `` backtick quoting  (via sqlglot MySQL dialect)
    - ``AUTO_INCREMENT`` column attribute  (via sqlglot MySQL dialect)
    - ``ENGINE=``, ``DEFAULT CHARSET`` etc. table options (ignored, not errors)
    - ``COMMENT 'xxx'`` column comment  (via sqlglot MySQL dialect)
    - ``COMMENT='xxx'`` table-level comment
    - MySQL-specific types: ``TINYINT``, ``BIGINT``, ``DATETIME``
    """

    dialect = "mysql"

    def _parse_create_table(self, statement: str) -> "Table":
        """Parse a MySQL CREATE TABLE statement, including table-level COMMENT."""
        # Let parent handle column/FK/index extraction
        table = super()._parse_create_table(statement)

        # Extract table-level COMMENT from MySQL properties
        parsed = self._parse_one(statement)
        if not parsed:
            return table

        comment = self._extract_table_comment(parsed)
        if comment:
            table.comment = comment

        return table

    def _parse_one(self, statement: str) -> exp.Create | None:
        """Parse a single statement with sqlglot."""
        import sqlglot

        try:
            parsed = sqlglot.parse_one(statement, dialect="mysql")
            if isinstance(parsed, exp.Create):
                return parsed
        except Exception:
            return None
        return None

    @staticmethod
    def _extract_table_comment(parsed: exp.Create) -> str:
        """Extract MySQL table-level COMMENT from CREATE TABLE properties."""
        props = parsed.args.get("properties")
        if not props:
            return ""
        for prop in props.expressions:
            if isinstance(prop, exp.SchemaCommentProperty):
                val = prop.args.get("this")
                if isinstance(val, exp.Literal):
                    return val.name
                return val.sql() if hasattr(val, "sql") else str(val)
        return ""
