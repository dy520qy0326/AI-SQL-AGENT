"""MySQL parser integration test — employees DDL sample.

Based on the classic MySQL employees database schema.
Verifies that all 8 tables are correctly parsed with accurate types and FKs.
"""

import pytest
from app.parser.mysql import MySQLParser

# ── Sample DDL ────────────────────────────────────────────────────────────────
# Based on the MySQL employees sample database (6 core tables) plus 2 additional
# practical tables for comprehensive coverage.

SAMPLE_DDL = """
CREATE TABLE employees (
    emp_no      INT             NOT NULL,
    birth_date  DATE            NOT NULL,
    first_name  VARCHAR(14)     NOT NULL,
    last_name   VARCHAR(16)     NOT NULL,
    gender      ENUM('M','F')   NOT NULL,
    hire_date   DATE            NOT NULL,
    PRIMARY KEY (emp_no)
);

CREATE TABLE departments (
    dept_no     CHAR(4)         NOT NULL,
    dept_name   VARCHAR(40)     NOT NULL,
    PRIMARY KEY (dept_no),
    UNIQUE KEY dept_name (dept_name)
);

CREATE TABLE dept_manager (
    emp_no       INT             NOT NULL,
    dept_no      CHAR(4)         NOT NULL,
    from_date    DATE            NOT NULL,
    to_date      DATE            NOT NULL,
    FOREIGN KEY (emp_no)  REFERENCES employees (emp_no),
    FOREIGN KEY (dept_no) REFERENCES departments (dept_no),
    PRIMARY KEY (emp_no, dept_no)
);

CREATE TABLE dept_emp (
    emp_no      INT             NOT NULL,
    dept_no     CHAR(4)         NOT NULL,
    from_date   DATE            NOT NULL,
    to_date     DATE            NOT NULL,
    FOREIGN KEY (emp_no)  REFERENCES employees   (emp_no),
    FOREIGN KEY (dept_no) REFERENCES departments (dept_no),
    PRIMARY KEY (emp_no, dept_no)
);

CREATE TABLE titles (
    emp_no      INT             NOT NULL,
    title       VARCHAR(50)     NOT NULL,
    from_date   DATE            NOT NULL,
    to_date     DATE,
    FOREIGN KEY (emp_no) REFERENCES employees (emp_no),
    PRIMARY KEY (emp_no, title, from_date)
);

CREATE TABLE salaries (
    emp_no      INT             NOT NULL,
    salary      INT             NOT NULL,
    from_date   DATE            NOT NULL,
    to_date     DATE            NOT NULL,
    FOREIGN KEY (emp_no) REFERENCES employees (emp_no),
    PRIMARY KEY (emp_no, from_date)
);

CREATE TABLE projects (
    project_id   INT             NOT NULL AUTO_INCREMENT,
    project_name VARCHAR(100)   NOT NULL,
    start_date   DATE,
    budget       DECIMAL(12,2)  DEFAULT 0.00,
    PRIMARY KEY (project_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE project_members (
    project_id  INT          NOT NULL,
    emp_no      INT          NOT NULL,
    role        VARCHAR(50)  DEFAULT 'member',
    FOREIGN KEY (project_id) REFERENCES projects(project_id),
    FOREIGN KEY (emp_no) REFERENCES employees(emp_no),
    PRIMARY KEY (project_id, emp_no)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""


@pytest.fixture(scope="module")
def sample_result():
    parser = MySQLParser()
    return parser.parse(SAMPLE_DDL)


# ── Test data ─────────────────────────────────────────────────────────────────

# Each entry: (name, schema_, col_count, fk_count, expected_columns)
# expected_columns is a dict: col_name -> {attr: value, ...}

TABLE_EXPECTATIONS = [
    (
        "employees", "",
        6, 0,
        {
            "emp_no": {"type": "int", "nullable": False, "primary_key": True, "length": None, "default": None},
            "birth_date": {"type": "date", "nullable": False, "primary_key": False},
            "first_name": {"type": "varchar", "length": 14, "nullable": False},
            "last_name": {"type": "varchar", "length": 16, "nullable": False},
            "gender": {"type": "enum", "nullable": False},
            "hire_date": {"type": "date", "nullable": False},
        },
    ),
    (
        "departments", "",
        2, 0,
        {
            "dept_no": {"type": "char", "length": 4, "nullable": False, "primary_key": True},
            "dept_name": {"type": "varchar", "length": 40, "nullable": False},
        },
    ),
    (
        "dept_manager", "",
        4, 2,
        {
            "emp_no": {"type": "int", "nullable": False, "primary_key": True},
            "dept_no": {"type": "char", "length": 4, "nullable": False, "primary_key": True},
            "from_date": {"type": "date", "nullable": False},
            "to_date": {"type": "date", "nullable": False},
        },
    ),
    (
        "dept_emp", "",
        4, 2,
        {
            "emp_no": {"type": "int", "nullable": False, "primary_key": True},
            "dept_no": {"type": "char", "length": 4, "nullable": False, "primary_key": True},
            "from_date": {"type": "date", "nullable": False},
            "to_date": {"type": "date", "nullable": False},
        },
    ),
    (
        "titles", "",
        4, 1,
        {
            "emp_no": {"type": "int", "nullable": False, "primary_key": True},
            "title": {"type": "varchar", "length": 50, "nullable": False, "primary_key": True},
            "from_date": {"type": "date", "nullable": False, "primary_key": True},
            "to_date": {"type": "date", "nullable": True, "primary_key": False},
        },
    ),
    (
        "salaries", "",
        4, 1,
        {
            "emp_no": {"type": "int", "nullable": False, "primary_key": True},
            "salary": {"type": "int", "nullable": False},
            "from_date": {"type": "date", "nullable": False, "primary_key": True},
            "to_date": {"type": "date", "nullable": False},
        },
    ),
    (
        "projects", "",
        4, 0,
        {
            "project_id": {"type": "int", "nullable": False, "primary_key": True, "auto_increment": True},
            "project_name": {"type": "varchar", "length": 100, "nullable": False},
            "start_date": {"type": "date", "nullable": True},
            "budget": {"type": "decimal", "length": 12, "nullable": True, "default": "0.00"},
        },
    ),
    (
        "project_members", "",
        3, 2,
        {
            "project_id": {"type": "int", "nullable": False, "primary_key": True},
            "emp_no": {"type": "int", "nullable": False, "primary_key": True},
            "role": {"type": "varchar", "length": 50, "nullable": True, "default": "member"},
        },
    ),
]

FK_EXPECTATIONS = {
    "dept_manager": [
        {"columns": ["emp_no"], "ref_table": "employees", "ref_columns": ["emp_no"]},
        {"columns": ["dept_no"], "ref_table": "departments", "ref_columns": ["dept_no"]},
    ],
    "dept_emp": [
        {"columns": ["emp_no"], "ref_table": "employees", "ref_columns": ["emp_no"]},
        {"columns": ["dept_no"], "ref_table": "departments", "ref_columns": ["dept_no"]},
    ],
    "titles": [
        {"columns": ["emp_no"], "ref_table": "employees", "ref_columns": ["emp_no"]},
    ],
    "salaries": [
        {"columns": ["emp_no"], "ref_table": "employees", "ref_columns": ["emp_no"]},
    ],
    "project_members": [
        {"columns": ["project_id"], "ref_table": "projects", "ref_columns": ["project_id"]},
        {"columns": ["emp_no"], "ref_table": "employees", "ref_columns": ["emp_no"]},
    ],
}


# ── Table Count ────────────────────────────────────────────────────────────────


class TestTableCount:
    def test_exactly_8_tables(self, sample_result):
        assert len(sample_result.tables) == 8

    def test_no_errors(self, sample_result):
        assert sample_result.errors == []


# ── Parameterized Table Tests ─────────────────────────────────────────────────


class TestTableStructure:
    @pytest.mark.parametrize(
        "name,schema,col_count,fk_count,expected_cols",
        TABLE_EXPECTATIONS,
        ids=[e[0] for e in TABLE_EXPECTATIONS],
    )
    def test_table_metadata(
        self, sample_result, name, schema, col_count, fk_count, expected_cols
    ):
        tables = {t.name: t for t in sample_result.tables}
        assert name in tables, f"Table '{name}' not found in parse result"
        table = tables[name]

        assert table.schema_ == schema
        assert len(table.columns) == col_count
        assert len(table.foreign_keys) == fk_count

    @pytest.mark.parametrize(
        "name,schema,col_count,fk_count,expected_cols",
        TABLE_EXPECTATIONS,
        ids=[e[0] for e in TABLE_EXPECTATIONS],
    )
    def test_column_types_and_constraints(
        self, sample_result, name, schema, col_count, fk_count, expected_cols
    ):
        tables = {t.name: t for t in sample_result.tables}
        table = tables[name]
        cols = {c.name: c for c in table.columns}

        for col_name, expected in expected_cols.items():
            assert col_name in cols, f"Column '{col_name}' missing in {name}"
            col = cols[col_name]
            for attr, value in expected.items():
                actual = getattr(col, attr)
                assert actual == value, (
                    f"{name}.{col_name}.{attr}: expected {value!r}, got {actual!r}"
                )

    @pytest.mark.parametrize(
        "table_name,expected_fks",
        [
            (name, fks)
            for name, fks in FK_EXPECTATIONS.items()
        ],
        ids=list(FK_EXPECTATIONS.keys()),
    )
    def test_foreign_keys(self, sample_result, table_name, expected_fks):
        tables = {t.name: t for t in sample_result.tables}
        table = tables[table_name]
        assert len(table.foreign_keys) == len(expected_fks)

        for actual, expected in zip(table.foreign_keys, expected_fks):
            assert actual.columns == expected["columns"]
            assert actual.ref_table == expected["ref_table"]
            assert actual.ref_columns == expected["ref_columns"]


# ── Tables Without FKs ────────────────────────────────────────────────────────


class TestTablesWithoutFKs:
    @pytest.mark.parametrize("name", ["employees", "departments", "projects"])
    def test_no_foreign_keys(self, sample_result, name):
        tables = {t.name: t for t in sample_result.tables}
        assert tables[name].foreign_keys == []


# ── Performance ────────────────────────────────────────────────────────────────


class TestPerformance:
    def test_parsing_under_500ms(self):
        """500 lines of DDL should parse in under 500ms."""
        # Repeat the sample to create ~500 lines
        many_ddls = "\n\n".join([SAMPLE_DDL] * 20)
        line_count = many_ddls.count("\n") + 1
        assert line_count > 500, (
            f"Only {line_count} lines, add more repetitions"
        )

        import time
        parser = MySQLParser()
        start = time.perf_counter()
        result = parser.parse(many_ddls)
        elapsed = (time.perf_counter() - start) * 1000  # ms

        assert elapsed < 500, f"Parsing {line_count} lines took {elapsed:.1f}ms"
        assert len(result.tables) > 0
        assert result.errors == []
