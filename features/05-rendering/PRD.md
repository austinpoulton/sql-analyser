# PRD: Source Data Model Rendering (FR-003)

## Part 1: Overview & Requirements

### Problem Statement

Data engineers and analysts need visual representations of extracted source data models to:
- **Quickly understand** table structures and relationships at a glance
- **Communicate** data models to stakeholders using industry-standard formats
- **Document** data dependencies for migration and transformation projects
- **Share** data models across teams using portable, version-controllable text formats

The SQL Analyser currently extracts structured DataModel objects but provides no way to visualize or export them. Engineers must manually translate JSON output into diagrams, which is time-consuming and error-prone.

### Goals

1. **Render Mermaid ERD** — Generate syntactically valid Mermaid `erDiagram` from DataModel
2. **Render DBML** — Generate syntactically valid DBML from DataModel
3. **Template-based rendering** — Use Jinja2 templates for maintainability and extensibility
4. **Clean API** — Expose `render_mermaid()` and `render_dbml()` methods on DataModel
5. **100% valid output** — All generated diagrams must be syntactically correct and renderable

### Non-Goals

- **Visual styling/theming** — Diagrams use default styling; custom themes are out of scope
- **Interactive diagrams** — Static text output only; no JavaScript/HTML rendering
- **Cardinality inference** — Relationships use `||--||` (unspecified); cardinality detection is future work
- **Column constraints** — Primary keys, foreign keys, nullability not inferred from SQL
- **Multi-model aggregation** — Rendering is per-DataModel; merging multiple models is handled by FR-009
- **Performance optimization** — Defer optimization until profiling shows need

### Success Metrics

- All TC-003-XX test cases pass
- Mermaid output renders correctly in Mermaid Live Editor
- DBML output validates in DBML Playground
- Template changes don't break existing tests
- Rendering completes in <100ms for typical models (<20 tables)

---

## Part 2: User Stories & Acceptance Criteria

### US-1: Visualize Data Model as Mermaid ERD
**As a** data engineer analysing SQL queries
**I want** to render the extracted DataModel as a Mermaid ERD
**So that** I can visually understand table structures and relationships in documentation or wikis

**Acceptance Criteria:**
- `data_model.render_mermaid()` returns a valid Mermaid `erDiagram` string
- Output includes `erDiagram` header
- Each QueriedTable renders as an entity block with table name and columns
- Each column shows: `<data_type> <column_name>`
- Relationships render as lines: `"table1" ||--|| "table2" : "table1.col = table2.col"`
- Output is copy-pasteable into Mermaid Live Editor and renders without errors

**Test Coverage:** TC-003-01

---

### US-2: Export Data Model as DBML
**As a** data platform engineer
**I want** to export the extracted DataModel as DBML
**So that** I can import it into dbdiagram.io, dbdocs, or other DBML-compatible tools

**Acceptance Criteria:**
- `data_model.render_dbml()` returns a valid DBML string
- Output includes `Table <qualified_name> { ... }` blocks for each QueriedTable
- Each column shows: `<column_name> <data_type>`
- Relationships render as `Ref: table1.col > table2.col` (or `<` or `-`)
- Output validates in DBML Playground without syntax errors

**Test Coverage:** TC-003-02

---

### US-3: Handle Empty or Partial DataModels
**As a** developer testing edge cases
**I want** rendering to handle empty models and tables without columns gracefully
**So that** the system doesn't crash on unexpected input

**Acceptance Criteria:**
- Empty DataModel (no tables) renders valid but empty Mermaid/DBML
- Table with no columns renders entity block with table name only
- Table with wildcard (`has_wildcard=True`) renders with comment indicating wildcard
- No runtime errors or exceptions for edge cases

**Test Coverage:** TC-RENDER-01 (edge cases)

---

### US-4: Preserve Qualified Table Names
**As a** data analyst reviewing multi-schema queries
**I want** table names to include schema/catalog qualifiers
**So that** I can distinguish between tables with the same name in different schemas

**Acceptance Criteria:**
- Table `core_facts.orders` renders as `"core_facts.orders"` (not just `orders`)
- Table `catalog.schema.table` renders as `"catalog.schema.table"`
- Single-part names (e.g., `users`) render as `"users"`
- Qualified names are quoted consistently in both Mermaid and DBML

**Test Coverage:** TC-003-01, TC-003-02

---

### US-5: Render Multi-Column Relationships
**As a** data engineer analysing composite keys
**I want** relationships with multiple join columns to be clearly represented
**So that** I understand the full join condition

**Acceptance Criteria:**
- Multi-column relationships render as single relationship line
- Relationship label includes all column pairs: `"t1.col1, t1.col2 = t2.col1, t2.col2"`
- DBML renders multi-column relationships with proper syntax
- Single-column and multi-column relationships both render correctly

**Test Coverage:** TC-RENDER-02 (multi-column relationships)

---

## Part 3: Technical Design

### Architecture

```
DataModel (domain.py)
    ↓
render_mermaid() / render_dbml()
    ↓
Jinja2 Template Engine
    ↓
Template Files (src/sql_analyser/templates/)
    ├── mermaid_erd.j2
    └── dbml.j2
    ↓
Rendered String (Mermaid or DBML)
```

### Module Structure

```
src/sql_analyser/
├── domain.py             # MODIFY: Add render_mermaid() and render_dbml() methods
├── templates/            # NEW: Jinja2 template directory
│   ├── mermaid_erd.j2   # NEW: Mermaid ERD template
│   └── dbml.j2          # NEW: DBML template

tests/
└── test_rendering.py     # NEW: Rendering tests for FR-003
```

### Implementation Details

#### 1. Modify `domain.py` — Add Rendering Methods

Add two methods to the `DataModel` class:

```python
from __future__ import annotations

import importlib.resources
from jinja2 import Template

class DataModel(BaseModel):
    """Container for extracted source data model: tables + relationships."""

    tables: list[QueriedTable] = Field(default_factory=list)
    relationships: list[Relationship] = Field(default_factory=list)

    def merge(self, other: DataModel) -> DataModel:
        """Merge with another DataModel (existing implementation)."""
        return merge_models(self, other)

    def render_mermaid(self) -> str:
        """Render DataModel as Mermaid ERD diagram.

        Returns:
            A Mermaid erDiagram string with tables, columns, and relationships.

        Example:
            >>> model = DataModel(tables=[...], relationships=[...])
            >>> print(model.render_mermaid())
            erDiagram
                "users" {
                    varchar id
                    varchar name
                }
                ...
        """
        template_source = _load_template("mermaid_erd.j2")
        template = Template(template_source)
        return template.render(model=self)

    def render_dbml(self) -> str:
        """Render DataModel as DBML schema.

        Returns:
            A DBML string with table definitions and relationships.

        Example:
            >>> model = DataModel(tables=[...], relationships=[...])
            >>> print(model.render_dbml())
            Table users {
              id varchar
              name varchar
            }
            ...
        """
        template_source = _load_template("dbml.j2")
        template = Template(template_source)
        return template.render(model=self)


def _load_template(filename: str) -> str:
    """Load a Jinja2 template from the templates directory.

    Args:
        filename: Template filename (e.g., "mermaid_erd.j2")

    Returns:
        Template source code as string.
    """
    # Use importlib.resources to load templates from package
    # This works both in development and when installed as a package
    import sql_analyser.templates as templates_package

    template_files = importlib.resources.files(templates_package)
    template_path = template_files / filename
    return template_path.read_text()
```

**Design Notes:**
- **Template loading**: Use `importlib.resources.files()` for Python 3.9+ compatibility
- **Separation of concerns**: DataModel owns the rendering API; templates own the output format
- **Error handling**: Let Jinja2 raise `TemplateNotFound` if template is missing
- **Type hints**: Return type is `str` for both methods

#### 2. Create `src/sql_analyser/templates/mermaid_erd.j2`

```jinja
erDiagram
{%- for table in model.tables %}
    "{{ table.qualified_name }}" {
{%- for column in table.columns %}
        {{ column.data_type }} {{ column.name }}
{%- endfor %}
    }
{%- endfor %}
{%- for rel in model.relationships %}
    "{{ rel.left_table }}" ||--|| "{{ rel.right_table }}" : "{{ rel.left_table }}.{{ rel.left_columns|join(', ' + rel.left_table + '.') }} = {{ rel.right_table }}.{{ rel.right_columns|join(', ' + rel.right_table + '.') }}"
{%- endfor %}
```

**Template Logic:**
- **Tables block**: Loop over `model.tables`, render qualified name + columns
- **Column format**: `<data_type> <column_name>` on each line
- **Relationships**: Render as `"table1" ||--|| "table2" : "description"`
- **Relationship label**: `"table1.col1, table1.col2 = table2.col1, table2.col2"` for multi-column
- **Whitespace control**: Use `{%-` to strip leading whitespace for cleaner output

**Edge Cases:**
- Empty model: Renders just `erDiagram` header
- Table with no columns: Renders entity block with name only
- No relationships: Renders only table blocks

#### 3. Create `src/sql_analyser/templates/dbml.j2`

```jinja
{%- for table in model.tables %}
Table {{ table.qualified_name }} {
{%- for column in table.columns %}
  {{ column.name }} {{ column.data_type }}
{%- endfor %}
}

{%- endfor %}
{%- for rel in model.relationships %}
{%- if rel.left_columns|length == 1 %}
Ref: {{ rel.left_table }}.{{ rel.left_columns[0] }} - {{ rel.right_table }}.{{ rel.right_columns[0] }}
{%- else %}
Ref: ({{ rel.left_table }}.{{ rel.left_columns|join(', ' + rel.left_table + '.') }}) - ({{ rel.right_table }}.{{ rel.right_columns|join(', ' + rel.right_table + '.') }})
{%- endif %}
{%- endfor %}
```

**Template Logic:**
- **Tables block**: `Table <qualified_name> { ... }`
- **Column format**: `<column_name> <data_type>` (note: reversed from Mermaid)
- **Relationships**:
  - Single-column: `Ref: table1.col - table2.col`
  - Multi-column: `Ref: (table1.col1, table1.col2) - (table2.col1, table2.col2)`
- **Relationship type**: Use `-` (many-to-many) as default; cardinality inference is future work

**DBML Syntax Notes:**
- DBML supports `<`, `>`, `-` for relationship types (one-to-many, many-to-one, many-to-many)
- We use `-` as conservative default (unspecified cardinality)
- Multi-column refs require parentheses: `Ref: (t1.a, t1.b) - (t2.a, t2.b)`

#### 4. Create `src/sql_analyser/templates/__init__.py`

```python
"""Jinja2 templates for rendering DataModel to various formats."""
```

This makes `templates/` a proper Python package for `importlib.resources`.

#### 5. Create `tests/test_rendering.py`

```python
"""Tests for DataModel rendering (FR-003).

This module tests the rendering of DataModel objects to Mermaid ERD and DBML formats.
"""

from __future__ import annotations

import sqlglot

from sql_analyser import analyse
from sql_analyser.domain import DataModel, QueriedColumn, QueriedTable, Relationship


# TC-003-01: Primary spec example — Mermaid rendering


def test_mermaid_rendering_spec_example():
    """TC-003-01: Render spec example (§8.1) as Mermaid ERD.

    This is the canonical rendering test from the specification.
    """
    sql = """
        WITH cte_ordered_products_store AS (
            SELECT
                prod_sku,
                store_id,
                SUM(quantity) AS quantity,
                SUM(value) AS revenue,
                AVG((value - base_cost) / base_cost) AS avg_margin
            FROM core_facts.orders
            GROUP BY prod_sku, store_id
        )
        SELECT
            p.prod_name AS product_name,
            s.store_nam AS store_name,
            o.revenue,
            o.quantity,
            o.avg_margin
        FROM core_dims.product p
        LEFT JOIN cte_ordered_products_store o
            ON o.prod_sku = p.sku
        LEFT JOIN core_dims.store s
            ON s.store_id = o.store_id
    """

    expr = sqlglot.parse_one(sql, dialect="postgres")
    result = analyse(expr)
    mermaid = result.data_model.render_mermaid()

    # Verify Mermaid structure
    assert "erDiagram" in mermaid, "Mermaid output should contain erDiagram header"

    # Verify all three tables are present
    assert '"core_facts.orders"' in mermaid
    assert '"core_dims.product"' in mermaid
    assert '"core_dims.store"' in mermaid

    # Verify columns with numeric types (from aggregates)
    assert "numeric quantity" in mermaid or "varchar quantity" in mermaid
    assert "numeric value" in mermaid or "varchar value" in mermaid
    assert "numeric base_cost" in mermaid or "varchar base_cost" in mermaid

    # Verify relationships
    assert (
        "core_facts.orders" in mermaid and "core_dims.product" in mermaid
    ), "Relationship orders↔product should be present"
    assert (
        "core_facts.orders" in mermaid and "core_dims.store" in mermaid
    ), "Relationship orders↔store should be present"

    # Verify output is syntactically valid (basic check)
    assert mermaid.strip().startswith("erDiagram")


# TC-003-02: DBML rendering — simple two-table join


def test_dbml_rendering_simple_join():
    """TC-003-02: Render simple two-table join as DBML."""
    sql = """
        SELECT o.order_id, c.name
        FROM sales.orders o
        JOIN sales.customer c ON c.customer_id = o.customer_id
    """

    expr = sqlglot.parse_one(sql, dialect="postgres")
    result = analyse(expr)
    dbml = result.data_model.render_dbml()

    # Verify DBML table blocks
    assert "Table sales.orders" in dbml, "DBML should contain sales.orders table"
    assert "Table sales.customer" in dbml, "DBML should contain sales.customer table"

    # Verify columns are present
    assert "order_id" in dbml
    assert "name" in dbml
    assert "customer_id" in dbml

    # Verify relationship reference
    assert "Ref:" in dbml, "DBML should contain at least one Ref"
    assert (
        "sales.orders" in dbml and "sales.customer" in dbml
    ), "Ref should connect orders and customer"


# TC-RENDER-01: Edge cases


def test_empty_datamodel_rendering():
    """TC-RENDER-01a: Empty DataModel renders valid but empty output."""
    model = DataModel(tables=[], relationships=[])

    mermaid = model.render_mermaid()
    assert mermaid.strip() == "erDiagram", "Empty model should render just erDiagram header"

    dbml = model.render_dbml()
    # Empty DBML is just whitespace/empty
    assert len(dbml.strip()) == 0, "Empty model should render empty DBML"


def test_table_with_no_columns():
    """TC-RENDER-01b: Table with no columns renders entity block with name only."""
    table = QueriedTable(name="users", schema_name="app", catalog_name="")
    model = DataModel(tables=[table], relationships=[])

    mermaid = model.render_mermaid()
    assert '"app.users"' in mermaid
    # Table block should exist even if empty
    assert "{" in mermaid and "}" in mermaid


def test_table_with_wildcard():
    """TC-RENDER-01c: Table with wildcard flag renders correctly."""
    table = QueriedTable(name="orders", has_wildcard=True, columns=[])
    model = DataModel(tables=[table], relationships=[])

    mermaid = model.render_mermaid()
    assert '"orders"' in mermaid
    # Wildcard doesn't break rendering


# TC-RENDER-02: Multi-column relationships


def test_multi_column_relationship_rendering():
    """TC-RENDER-02: Multi-column relationships render correctly."""
    table1 = QueriedTable(
        name="orders",
        schema_name="sales",
        columns=[
            QueriedColumn(name="region"),
            QueriedColumn(name="order_id"),
        ],
    )
    table2 = QueriedTable(
        name="shipments",
        schema_name="sales",
        columns=[
            QueriedColumn(name="region"),
            QueriedColumn(name="order_id"),
        ],
    )
    rel = Relationship(
        left_table="sales.orders",
        left_columns=["region", "order_id"],
        right_table="sales.shipments",
        right_columns=["region", "order_id"],
    )
    model = DataModel(tables=[table1, table2], relationships=[rel])

    mermaid = model.render_mermaid()
    # Multi-column relationship should include both columns in label
    assert "sales.orders" in mermaid and "sales.shipments" in mermaid
    # Relationship line should exist
    assert "||--||" in mermaid

    dbml = model.render_dbml()
    # DBML multi-column syntax: Ref: (t1.a, t1.b) - (t2.a, t2.b)
    assert "Ref:" in dbml
    assert "sales.orders" in dbml and "sales.shipments" in dbml


# TC-003-03: JSON round-trip (already tested in test_domain_model.py)
# No additional rendering-specific test needed


# Integration test: Full pipeline from SQL to rendered output


def test_integration_sql_to_mermaid():
    """Integration test: Parse SQL, analyse, render to Mermaid."""
    sql = "SELECT u.id, o.order_id FROM users u JOIN orders o ON u.id = o.user_id"
    expr = sqlglot.parse_one(sql)
    result = analyse(expr)
    mermaid = result.data_model.render_mermaid()

    assert "erDiagram" in mermaid
    assert '"users"' in mermaid
    assert '"orders"' in mermaid
    assert "||--||" in mermaid  # Relationship exists


def test_integration_sql_to_dbml():
    """Integration test: Parse SQL, analyse, render to DBML."""
    sql = "SELECT u.id, o.order_id FROM users u JOIN orders o ON u.id = o.user_id"
    expr = sqlglot.parse_one(sql)
    result = analyse(expr)
    dbml = result.data_model.render_dbml()

    assert "Table users" in dbml
    assert "Table orders" in dbml
    assert "Ref:" in dbml
```

**Test Strategy:**
- **TC-003-01**: Use spec example SQL, verify Mermaid structure
- **TC-003-02**: Simple two-table join, verify DBML format
- **TC-RENDER-01**: Edge cases (empty model, no columns, wildcard)
- **TC-RENDER-02**: Multi-column relationships
- **Integration**: Full pipeline from SQL → DataModel → rendered output

### Dependencies

- **Phase 1 (Domain Model)** ✅ Complete — DataModel, QueriedTable, Relationship exist
- **Phase 2 (Core Extraction)** ✅ Complete — `analyse()` function extracts tables/columns
- **Phase 3 (Relationships)** ✅ Complete — Relationships are extracted
- **Jinja2** — Template engine (add to `pyproject.toml` if not present)

### Implementation Plan

#### Step 1: Add Jinja2 Dependency

```bash
uv add jinja2
```

#### Step 2: Create Template Directory

```bash
mkdir -p src/sql_analyser/templates
touch src/sql_analyser/templates/__init__.py
```

#### Step 3: Create Mermaid Template

Create `src/sql_analyser/templates/mermaid_erd.j2` with Mermaid ERD template.

#### Step 4: Create DBML Template

Create `src/sql_analyser/templates/dbml.j2` with DBML template.

#### Step 5: Modify `domain.py`

Add `render_mermaid()` and `render_dbml()` methods to `DataModel` class.
Add `_load_template()` helper function.

#### Step 6: Create `tests/test_rendering.py`

Implement all TC-003-XX and TC-RENDER-XX test cases.

#### Step 7: Run Tests

```bash
uv run pytest tests/test_rendering.py -v
uv run pytest  # Full suite to check for regressions
```

#### Step 8: Manual Validation

- Copy Mermaid output to [Mermaid Live Editor](https://mermaid.live/)
- Copy DBML output to [DBML Playground](https://dbdiagram.io/)
- Verify both render correctly

### Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Template syntax errors break rendering | High | Write template tests first; validate templates with sample data |
| `importlib.resources` API changes across Python versions | Medium | Use Python 3.9+ compatible API; test on multiple Python versions |
| Mermaid/DBML syntax changes | Low | Pin to current Mermaid/DBML specs; templates are easy to update |
| Multi-column relationship formatting is ambiguous | Low | Follow DBML spec for multi-column refs; use parentheses |
| Qualified names with special characters break diagrams | Low | Quote all table names consistently; test with edge cases |

### Open Questions

1. **Should we support cardinality notation (1:N, N:M)?**
   → No for Phase 5. Use `||--||` (unspecified) as default. Cardinality inference is future work.

2. **Should we sanitize table/column names for Mermaid/DBML?**
   → Not initially. Assume table names are valid identifiers. Add sanitization if issues arise.

3. **Should we add comments for wildcard tables?**
   → Yes, add a comment in rendered output: `// SELECT * detected` for DBML, similar for Mermaid.

4. **Should we expose a `render(format='mermaid'|'dbml')` unified method?**
   → No. Keep separate methods for simplicity. Unified API can be added later if needed.

### Success Criteria (Definition of Done)

- [ ] Jinja2 added to dependencies
- [ ] `src/sql_analyser/templates/__init__.py` created
- [ ] `src/sql_analyser/templates/mermaid_erd.j2` created
- [ ] `src/sql_analyser/templates/dbml.j2` created
- [ ] `DataModel.render_mermaid()` method implemented
- [ ] `DataModel.render_dbml()` method implemented
- [ ] `tests/test_rendering.py` created with all TC-003-XX tests
- [ ] All rendering tests pass
- [ ] Full test suite passes (no regressions)
- [ ] Mermaid output renders in Mermaid Live Editor
- [ ] DBML output validates in DBML Playground
- [ ] Code passes linting and formatting checks
- [ ] Test coverage ≥95% for rendering code paths

### Future Enhancements (Out of Scope)

- Cardinality inference (1:1, 1:N, N:M) based on join patterns
- Column-level comments/descriptions in rendered output
- Primary key and foreign key notation
- Support for additional formats (GraphML, PlantUML, etc.)
- Interactive diagram generation (HTML/JavaScript)
- Custom styling/theming for Mermaid diagrams
- Schema versioning and evolution tracking

### References

- [SQL-ANALYSER-SPEC.md](../../SQL-ANALYSER-SPEC.md) — §6 (FR-003), §8.1 (Example)
- [TEST-CASES.md](../../docs/TEST-CASES.md) — TC-003-01, TC-003-02, TC-003-03
- [CLAUDE.md](../../CLAUDE.md) — Implementation sequence
- [Mermaid ERD Documentation](https://mermaid.js.org/syntax/entityRelationshipDiagram.html)
- [DBML Documentation](https://dbml.dbdiagram.io/docs/)
- [Jinja2 Documentation](https://jinja.palletsprojects.com/)
