import re
from abc import ABC
from typing import Optional

import sqlglot
from sqlglot import exp

from app.parser.models import ParseResult, ParseError, Table, Column, ForeignKey as FKModel
from app.parser.dialect import detect_dialect


class BaseParser(ABC):
    """Abstract base parser for SQL DDL parsing.

    Subclasses override extraction methods to handle dialect-specific syntax.
    parse() is a template method defining the parsing workflow.
    """

    dialect: str = ""

    # Maps user-facing dialect names to sqlglot dialect names
    _SQLGLOT_DIALECTS = {
        "postgresql": "postgres",
        "postgres": "postgres",
        "mysql": "mysql",
    }

    def parse(self, sql_text: str) -> ParseResult:
        """Template method: detect dialect -> split statements -> parse each."""
        if not sql_text or not sql_text.strip():
            return ParseResult(dialect=self.dialect or "mysql")

        self.dialect = self._detect_dialect(sql_text)

        statements = self._parse_statements(sql_text)

        tables = []
        errors: list[ParseError] = []

        for i, stmt in enumerate(statements):
            stmt = stmt.strip()
            if not stmt:
                continue
            try:
                upper = stmt.upper().strip()
                if upper.startswith("CREATE TABLE"):
                    table = self._parse_create_table(stmt)
                    tables.append(table)
            except Exception as e:
                errors.append(
                    ParseError(
                        statement_index=i,
                        line=self._guess_line(sql_text, stmt),
                        message=str(e),
                    )
                )

        return ParseResult(dialect=self.dialect, tables=tables, errors=errors)

    def _parse_statements(self, sql_text: str) -> list[str]:
        """Split SQL text into individual statements.

        Strategy:
        1. Remove comments (-- and /* */)
        2. Split by semicolons (standard delimiter)
        3. For segments still containing multiple CREATE statements
           (missing semicolons), split by CREATE keyword boundaries
        """
        cleaned = self._remove_comments(sql_text)

        parts = [p.strip() for p in cleaned.split(";") if p.strip()]

        result: list[str] = []
        for part in parts:
            creates = self._find_create_positions(part)
            if len(creates) > 1:
                for i, start in enumerate(creates):
                    end = creates[i + 1] if i + 1 < len(creates) else len(part)
                    sub = part[start:end].strip()
                    if sub:
                        result.append(sub)
            else:
                result.append(part)

        return result

    @property
    def _sqlglot_dialect(self) -> str:
        """Map the parser's dialect to a sqlglot-compatible dialect name."""
        return self._SQLGLOT_DIALECTS.get(self.dialect, self.dialect)

    def _parse_create_table(self, statement: str) -> Table:
        """Parse a single CREATE TABLE statement into a Table model."""
        parsed = sqlglot.parse_one(statement, dialect=self._sqlglot_dialect)

        if not isinstance(parsed, exp.Create):
            raise ValueError("Statement is not a CREATE TABLE")

        schema = parsed.this
        if not isinstance(schema, exp.Schema):
            raise ValueError("CREATE TABLE missing schema definition")

        # Table name and schema
        table_node = schema.this
        table_name = table_node.name if hasattr(table_node, "name") else str(table_node)
        schema_name = ""
        if isinstance(table_node, exp.Table):
            db = table_node.args.get("db")
            if isinstance(db, exp.Identifier):
                schema_name = db.name

        # Extract columns, foreign keys, and apply table-level constraints
        columns: list[Column] = []
        foreign_keys: list[FKModel] = []

        for expr in schema.args.get("expressions") or []:
            if isinstance(expr, exp.ColumnDef):
                columns.append(self._extract_column(expr))
                fk = self._extract_column_ref(expr)
                if fk:
                    foreign_keys.append(fk)
            elif isinstance(expr, exp.PrimaryKey):
                self._apply_composite_pk(expr, columns)
            elif isinstance(expr, exp.ForeignKey):
                fk = self._extract_table_fk(expr)
                if fk:
                    foreign_keys.append(fk)

        return Table(
            name=table_name,
            schema_=schema_name,
            columns=columns,
            foreign_keys=foreign_keys,
        )

    def _extract_column(self, column_def: exp.ColumnDef) -> Column:
        """Extract a Column model from a sqlglot ColumnDef expression."""
        name = column_def.this.name

        # Data type
        data_type = column_def.args.get("kind")
        type_name = data_type.this.name.lower() if data_type else ""

        # Length / precision
        length: Optional[int] = None
        if data_type and data_type.args.get("expressions"):
            try:
                length = int(data_type.expressions[0].name)
            except (ValueError, AttributeError, IndexError):
                pass

        nullable = True
        primary_key = False
        default: Optional[str] = None
        comment = ""
        auto_increment = False

        for constraint in column_def.args.get("constraints") or []:
            kind = constraint.args.get("kind")
            if isinstance(kind, exp.NotNullColumnConstraint):
                nullable = False
            elif isinstance(kind, exp.PrimaryKeyColumnConstraint):
                primary_key = True
            elif isinstance(kind, exp.DefaultColumnConstraint):
                default = self._format_default(kind)
            elif isinstance(kind, exp.AutoIncrementColumnConstraint):
                auto_increment = True
            elif isinstance(kind, exp.CommentColumnConstraint):
                comment = self._format_comment(kind)
            elif isinstance(kind, exp.Reference):
                pass  # handled by _extract_column_ref after column extraction

        # PRIMARY KEY implies NOT NULL
        if primary_key:
            nullable = False

        return Column(
            name=name,
            type=type_name,
            length=length,
            nullable=nullable,
            default=default,
            primary_key=primary_key,
            auto_increment=auto_increment,
            comment=comment,
        )

    @staticmethod
    def _apply_composite_pk(pk: exp.PrimaryKey, columns: list[Column]) -> None:
        """Mark columns referenced by a table-level PRIMARY KEY constraint."""
        for expr in pk.args.get("expressions") or []:
            col_name = expr.name if isinstance(expr, exp.Identifier) else str(expr)
            for col in columns:
                if col.name == col_name:
                    col.primary_key = True
                    break

    @staticmethod
    def _extract_column_ref(column_def: exp.ColumnDef) -> FKModel | None:
        """Extract a column-level REFERENCES constraint as a ForeignKey model."""
        for constraint in column_def.args.get("constraints") or []:
            kind = constraint.args.get("kind")
            if isinstance(kind, exp.Reference):
                schema = kind.this
                ref_table = schema.this.name
                ref_columns = [
                    e.name for e in (schema.args.get("expressions") or [])
                ]
                return FKModel(
                    columns=[column_def.this.name],
                    ref_table=ref_table,
                    ref_columns=ref_columns,
                )
        return None

    @staticmethod
    def _extract_table_fk(fk_node: exp.ForeignKey) -> FKModel | None:
        """Extract a table-level FOREIGN KEY constraint as a ForeignKey model."""
        columns = [e.name for e in (fk_node.args.get("expressions") or [])]
        ref = fk_node.args.get("reference")
        if not ref:
            return None
        schema = ref.this
        ref_table = schema.this.name
        ref_columns = [e.name for e in (schema.args.get("expressions") or [])]
        return FKModel(
            columns=columns,
            ref_table=ref_table,
            ref_columns=ref_columns,
        )

    @staticmethod
    def _format_default(constraint: exp.DefaultColumnConstraint) -> str:
        """Format the DEFAULT value as a string."""
        val = constraint.this
        if isinstance(val, exp.Literal):
            return val.name
        if isinstance(val, exp.Null):
            return "NULL"
        if isinstance(val, exp.Boolean):
            return "true" if val.this else "false"
        return val.sql() if hasattr(val, "sql") else str(val)

    @staticmethod
    def _format_comment(constraint: exp.CommentColumnConstraint) -> str:
        """Extract the comment string from a COMMENT constraint."""
        val = constraint.this
        if isinstance(val, exp.Literal):
            return val.name
        return val.sql() if hasattr(val, "sql") else str(val)

    def _detect_dialect(self, sql_text: str) -> str:
        return detect_dialect(sql_text)

    def _guess_line(self, full_text: str, statement: str) -> int:
        """Estimate the line number where a statement starts in the original text."""
        idx = full_text.find(statement[: min(80, len(statement))])
        if idx == -1:
            return 0
        return full_text[:idx].count("\n") + 1

    @staticmethod
    def _remove_comments(sql_text: str) -> str:
        """Remove SQL single-line and block comments."""
        lines = sql_text.split("\n")
        cleaned_lines: list[str] = []
        for line in lines:
            in_string = False
            in_single_quote = False
            clean_chars: list[str] = []
            i = 0
            while i < len(line):
                ch = line[i]
                # Track string context to avoid stripping -- inside strings
                if ch == "'" and (i == 0 or line[i - 1] != "\\"):
                    in_single_quote = not in_single_quote
                if ch == '"' and (i == 0 or line[i - 1] != "\\"):
                    in_string = not in_string

                if not in_single_quote and not in_string:
                    if ch == "-" and i + 1 < len(line) and line[i + 1] == "-":
                        break
                clean_chars.append(ch)
                i += 1
            cleaned_lines.append("".join(clean_chars))
        result = "\n".join(cleaned_lines)

        result = re.sub(r"/\*.*?\*/", "", result, flags=re.DOTALL)
        return result

    @staticmethod
    def _find_create_positions(text: str) -> list[int]:
        """Find start positions of all CREATE statements in text."""
        upper = text.upper()
        positions: list[int] = []
        start = 0
        while True:
            pos = upper.find("CREATE ", start)
            if pos == -1:
                pos = upper.find("CREATE\n", start)
            if pos == -1:
                pos = upper.find("CREATE\t", start)
            if pos == -1:
                break
            positions.append(pos)
            start = pos + 7
        return positions
