# SQL Analyser — Test Cases

Test cases are organised by Functional Requirement (FR). Each case includes the input SQL, the key assertions to make, and a concise rationale explaining what behaviour is exercised and why it is non-trivial.

Where a test case exercises multiple FRs, it is listed under its primary FR and cross-referenced.

---

## FR-001 — Source Table & Column Extraction

### TC-001-01 · Simple SELECT with WHERE filter

**SQL:**
```sql
SELECT customer_id, full_name
FROM sales.customer
WHERE region = 'EMEA'
```

**Key assertions:**
- `sales.customer` is extracted as a `QueriedTable`.
- Columns: `customer_id`, `full_name`, `region`.
- `region` is present even though it appears only in `WHERE`, not in `SELECT`.

**Rationale:** Verifies that columns referenced outside the `SELECT` list — the most common omission — are still captured in the source model.

---

### TC-001-02 · All clause types in one query

**SQL:**
```sql
SELECT
    department_id,
    SUM(salary) AS total_salary
FROM hr.employee
WHERE status = 'ACTIVE'
GROUP BY department_id
HAVING SUM(salary) > 100000
ORDER BY total_salary DESC
```

**Key assertions:**
- Single table `hr.employee`.
- Columns present: `department_id`, `salary`, `status`.
- `status` sourced from `WHERE`; `salary` sourced from `SELECT` aggregate and `HAVING`; `department_id` sourced from `SELECT` and `GROUP BY`.

**Rationale:** Confirms every clause (`SELECT`, `WHERE`, `GROUP BY`, `HAVING`, `ORDER BY`) contributes columns to the source model.

---

### TC-001-03 · CTE resolved to base table

**SQL:**
```sql
WITH active_orders AS (
    SELECT order_id, customer_id, amount
    FROM sales.orders
    WHERE status = 'ACTIVE'
)
SELECT o.order_id, c.name
FROM active_orders o
JOIN sales.customer c ON c.customer_id = o.customer_id
```

**Key assertions:**
- `sales.orders` is extracted; `active_orders` CTE alias does **not** appear.
- `sales.customer` is extracted.
- Columns for `sales.orders`: `order_id`, `customer_id`, `amount`, `status`.

**Rationale:** Core requirement — CTE aliases must be resolved to their underlying base tables; the CTE name must never appear in the domain model.

---

### TC-001-04 · Nested CTEs (CTE referencing another CTE)

**SQL:**
```sql
WITH base AS (
    SELECT product_id, cost
    FROM warehouse.stock
),
enriched AS (
    SELECT b.product_id, b.cost, p.category
    FROM base b
    JOIN catalogue.product p ON p.product_id = b.product_id
)
SELECT product_id, category, cost
FROM enriched
```

**Key assertions:**
- Both `warehouse.stock` and `catalogue.product` are extracted.
- Neither `base` nor `enriched` appears as a table in the model.
- Columns for `warehouse.stock`: `product_id`, `cost`.
- Columns for `catalogue.product`: `product_id`, `category`.

**Rationale:** Multi-level CTE chains require recursive resolution. A naïve implementation resolves one level and stops, producing false CTE-alias table entries.

---

### TC-001-05 · Subquery in FROM clause

**SQL:**
```sql
SELECT sub.region, sub.total
FROM (
    SELECT region, SUM(revenue) AS total
    FROM finance.sales_fact
    GROUP BY region
) sub
WHERE sub.total > 50000
```

**Key assertions:**
- `finance.sales_fact` is extracted; the anonymous subquery alias `sub` does not appear.
- Columns: `region`, `revenue`.

**Rationale:** Inline subqueries in `FROM` are a distinct scope type from CTEs; the resolver must handle both.

---

### TC-001-06 · UNION ALL across two branches

**SQL:**
```sql
SELECT employee_id, name, 'FT' AS employment_type
FROM hr.full_time_employee
WHERE active = 1
UNION ALL
SELECT contractor_id, name, 'CT'
FROM hr.contractor
WHERE active = 1
```

**Key assertions:**
- Both `hr.full_time_employee` and `hr.contractor` are extracted.
- `employee_id`, `name`, `active` on `hr.full_time_employee`.
- `contractor_id`, `name`, `active` on `hr.contractor`.

**Rationale:** Each `UNION ALL` branch is a separate scope. The analyser must enumerate all branches and not stop after the first.

---

### TC-001-07 · Correlated subquery in WHERE

**SQL:**
```sql
SELECT o.order_id, o.total
FROM sales.orders o
WHERE o.total > (
    SELECT AVG(total)
    FROM sales.orders
    WHERE customer_id = o.customer_id
)
```

**Key assertions:**
- `sales.orders` is the single extracted table.
- Columns: `order_id`, `total`, `customer_id`.
- `total` is captured from both the outer query and the correlated subquery context.

**Rationale:** Correlated subqueries reference columns from an outer scope. The analyser must associate those columns with the correct base table and not duplicate the table entry.

---

### TC-001-08 · EXISTS subquery

**SQL:**
```sql
SELECT p.product_id, p.name
FROM catalogue.product p
WHERE EXISTS (
    SELECT 1
    FROM sales.order_line ol
    WHERE ol.product_id = p.product_id
    AND ol.returned = 0
)
```

**Key assertions:**
- `catalogue.product` extracted with columns `product_id`, `name`.
- `sales.order_line` extracted with columns `product_id`, `returned`.

**Rationale:** `EXISTS` subqueries are often overlooked. Tables and columns inside the `EXISTS` clause are genuine source dependencies.

---

### TC-001-09 · Window function with PARTITION BY and ORDER BY

**SQL:**
```sql
SELECT
    employee_id,
    department_id,
    salary,
    RANK() OVER (PARTITION BY department_id ORDER BY salary DESC) AS salary_rank
FROM hr.employee
```

**Key assertions:**
- `hr.employee` extracted.
- Columns: `employee_id`, `department_id`, `salary`.
- `department_id` and `salary` captured from window function spec.

**Rationale:** Column references inside `OVER (PARTITION BY ... ORDER BY ...)` are part of the query's source dependency but are easy to miss when only scanning the `SELECT` projection.

---

### TC-001-10 · ORDER BY column not in SELECT

**SQL:**
```sql
SELECT customer_id, total_spend
FROM sales.customer_summary
ORDER BY last_order_date DESC
```

**Key assertions:**
- `sales.customer_summary` extracted.
- Columns include `customer_id`, `total_spend`, **and** `last_order_date`.

**Rationale:** A column that appears only in `ORDER BY` is a real source dependency even though it is not projected. It must not be silently dropped.

---

## FR-002 — Relationship Extraction

### TC-002-01 · Explicit INNER JOIN

**SQL:**
```sql
SELECT o.order_id, c.name
FROM sales.orders o
INNER JOIN sales.customer c ON c.customer_id = o.customer_id
```

**Key assertions:**
- One relationship between `sales.orders` and `sales.customer`.
- Join columns: `orders.customer_id` ↔ `customer.customer_id`.

**Rationale:** Baseline for explicit join extraction — the most common relationship source.

---

### TC-002-02 · Multiple explicit JOINs

**SQL:**
```sql
SELECT o.order_id, c.name, p.product_name
FROM sales.orders o
JOIN sales.customer c ON c.customer_id = o.customer_id
JOIN catalogue.product p ON p.product_id = o.product_id
```

**Key assertions:**
- Two relationships: `orders` ↔ `customer` and `orders` ↔ `product`.
- Correct join columns for each.

**Rationale:** Verifies the extractor handles multiple JOIN clauses in a single query and produces one `Relationship` per `ON` predicate.

---

### TC-002-03 · Implicit join (comma-separated FROM with WHERE predicate)

**SQL:**
```sql
SELECT o.order_id, c.name
FROM sales.orders o, sales.customer c
WHERE c.customer_id = o.customer_id
AND o.status = 'SHIPPED'
```

**Key assertions:**
- Relationship between `sales.orders` and `sales.customer` is extracted from the `WHERE` clause.
- `status` also captured as a column on `sales.orders`.
- Relationship is equivalent to the explicit JOIN in TC-002-01.

**Rationale:** Implicit joins are common in legacy SQL. Without specific `WHERE`-clause scanning, no relationship would be detected even though the semantic join is identical to an explicit `JOIN`.

---

### TC-002-04 · Self-join

**SQL:**
```sql
SELECT e.employee_id, e.name, m.name AS manager_name
FROM hr.employee e
JOIN hr.employee m ON m.employee_id = e.manager_id
```

**Key assertions:**
- `hr.employee` appears exactly **once** in the model (not duplicated).
- One relationship exists: `hr.employee` to `hr.employee`.
- Join columns: `employee.employee_id` ↔ `employee.manager_id`.

**Rationale:** Self-joins must not produce a duplicate table entry. The relationship references the same fully-qualified name on both sides.

---

### TC-002-05 · JOIN via CTE (relationship resolved to base table)

**SQL:**
```sql
WITH shipped AS (
    SELECT order_id, customer_id
    FROM sales.orders
    WHERE status = 'SHIPPED'
)
SELECT s.order_id, c.name
FROM shipped s
JOIN sales.customer c ON c.customer_id = s.customer_id
```

**Key assertions:**
- Relationship is between `sales.orders` and `sales.customer`, **not** between `shipped` and `sales.customer`.
- Join columns properly resolved: `orders.customer_id` ↔ `customer.customer_id`.

**Rationale:** When a CTE is used on one side of a JOIN, the relationship must reference the underlying base table, not the CTE alias.

---

### TC-002-06 · Multi-column JOIN predicate

**SQL:**
```sql
SELECT i.quantity, p.price
FROM warehouse.inventory i
JOIN catalogue.product p
    ON p.product_id = i.product_id
    AND p.warehouse_code = i.warehouse_code
```

**Key assertions:**
- One relationship with two join column pairs: `product_id` and `warehouse_code`.

**Rationale:** Composite join keys must be captured as a single relationship with multiple column references, not as two separate relationships.

---

### TC-002-07 · LEFT JOIN preserves relationship

**SQL:**
```sql
SELECT c.customer_id, o.order_id
FROM sales.customer c
LEFT JOIN sales.orders o ON o.customer_id = c.customer_id
```

**Key assertions:**
- Relationship between `sales.customer` and `sales.orders` is extracted.
- Join direction/type is recorded (or at minimum the relationship is present).

**Rationale:** JOIN cardinality and direction should not affect whether a relationship is extracted.

---

## FR-003 — Rendering (Mermaid ERD & DBML)

### TC-003-01 · Primary spec example — CTE with aggregations (Mermaid)

This is the canonical test case from §8.1 of the specification.

**SQL:**
```sql
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
```

**Key assertions:**
- Mermaid output contains `erDiagram`.
- All three base tables appear as entity blocks.
- `core_facts.orders` entity includes `numeric` types for `quantity`, `value`, `base_cost`.
- Relationship lines render for `orders`↔`product` and `orders`↔`store`.
- Output is syntactically valid Mermaid.

**Rationale:** The spec provides expected Mermaid output for this query, making it the primary regression anchor for the rendering pipeline.

---

### TC-003-02 · DBML rendering — simple two-table join

**SQL:**
```sql
SELECT o.order_id, c.name
FROM sales.orders o
JOIN sales.customer c ON c.customer_id = o.customer_id
```

**Key assertions:**
- DBML output contains `Table sales.orders` and `Table sales.customer` blocks.
- A `Ref` line is present connecting `orders.customer_id` to `customer.customer_id`.
- Output is syntactically valid DBML.

**Rationale:** Confirms the DBML template produces well-formed output containing the correct tables and relationship reference.

---

### TC-003-03 · JSON serialisation round-trip

**SQL:** (reuse TC-001-02 SQL)

**Key assertions:**
- `DataModel.model_dump()` serialises without error.
- `DataModel.model_validate(serialised)` reconstructs an equal object.
- All `QueriedTable`, `QueriedColumn`, and `Relationship` instances survive the round-trip intact.

**Rationale:** JSON serialisation is an explicit functional requirement (FR-003). Round-trip integrity ensures no data is silently lost during serialisation.

---

## FR-004 — Complexity Metrics

### TC-004-01 · Simple single-table query metric baseline

**SQL:**
```sql
SELECT id, name FROM app.users WHERE active = 1
```

**Key assertions:**
- `ast_node_count` is a non-zero positive integer.
- `scope_count` equals 1 (root scope only).
- Scope types list contains exactly one root scope.

**Rationale:** Establishes a baseline. Metrics on a trivial query must not be zero and scope count must equal exactly 1.

---

### TC-004-02 · CTE increases scope count

**SQL:**
```sql
WITH cte AS (SELECT id FROM app.users)
SELECT id FROM cte
```

**Key assertions:**
- `scope_count` equals 2 (one CTE scope + one root scope).
- Scope types include both a CTE scope and a root scope.

**Rationale:** Each CTE introduces a new scope. The metric must count it separately from the root.

---

### TC-004-03 · Nested CTE and subquery scope count

**SQL:**
```sql
WITH base AS (
    SELECT id FROM app.users
),
enriched AS (
    SELECT b.id, (SELECT MAX(score) FROM app.scores s WHERE s.user_id = b.id) AS top_score
    FROM base b
)
SELECT id, top_score FROM enriched
```

**Key assertions:**
- `scope_count` equals 4 (root, `base` CTE, `enriched` CTE, correlated subquery).
- AST node count is higher than TC-004-01.

**Rationale:** Validates that nested scopes (CTEs + correlated subquery inside a CTE) are each counted individually.

---

### TC-004-04 · UNION ALL scope count

**SQL:**
```sql
SELECT id FROM app.table_a
UNION ALL
SELECT id FROM app.table_b
```

**Key assertions:**
- `scope_count` is at least 2, reflecting both UNION branches as separate scopes.

**Rationale:** Each branch of a `UNION`/`UNION ALL` is its own scope in sqlglot's scope model.

---

## FR-005 — Type Inference

### TC-005-01 · Default type is varchar

**SQL:**
```sql
SELECT customer_id, region FROM sales.customer
```

**Key assertions:**
- `customer_id.data_type == 'varchar'`
- `region.data_type == 'varchar'`

**Rationale:** In the absence of any type cues, every column must default to `varchar`.

---

### TC-005-02 · Aggregate function infers numeric

**SQL:**
```sql
SELECT SUM(amount) AS total, AVG(amount) AS avg_amount, COUNT(order_id) AS order_count
FROM sales.orders
```

**Key assertions:**
- `amount.data_type == 'numeric'` (sourced from `SUM` and `AVG`).
- `order_id.data_type == 'numeric'` (sourced from `COUNT`).

**Rationale:** Columns inside aggregate functions (`SUM`, `AVG`, `COUNT`, `MIN`, `MAX`) are unambiguously numeric and must be typed accordingly.

---

### TC-005-03 · Explicit CAST honoured

**SQL:**
```sql
SELECT CAST(order_date AS DATE) AS order_date, CAST(price AS DECIMAL(10,2)) AS price
FROM sales.orders
```

**Key assertions:**
- `order_date.data_type == 'date'` (or `'DATE'`).
- `price.data_type == 'decimal'` (or equivalent numeric/decimal).

**Rationale:** An explicit `CAST` is the strongest available type cue and must override the `varchar` default.

---

### TC-005-04 · Mixed: same column inferred both ways picks numeric

**SQL:**
```sql
SELECT amount, SUM(amount) AS total
FROM sales.orders
GROUP BY amount
```

**Key assertions:**
- `amount` appears in both a plain `SELECT` reference (would default to `varchar`) and inside `SUM` (infers `numeric`).
- Resolved type for `amount` is `numeric` — the more specific inference wins.

**Rationale:** When heuristics from different clauses conflict, the more specific type must take precedence.

---

## FR-006 — Output Column Classification

### TC-006-01 · Measure, dimension, attribute classification

**SQL:**
```sql
SELECT
    region,
    category,
    SUM(revenue) AS total_revenue,
    COUNT(order_id) AS order_count,
    status
FROM sales.fact_orders
GROUP BY region, category, status
```

**Key assertions:**
- `total_revenue` and `order_count` classified as **measure** (inside aggregate).
- `region`, `category`, `status` classified as **dimension** (in `GROUP BY`).
- No attributes if all non-aggregates are in `GROUP BY`.

**Rationale:** The three-way classification (measure/dimension/attribute) is the spec's primary output enrichment for BI/analytics use cases.

---

### TC-006-02 · Attribute classification (no GROUP BY)

**SQL:**
```sql
SELECT customer_id, name, email
FROM sales.customer
WHERE active = 1
```

**Key assertions:**
- `customer_id`, `name`, `email` all classified as **attribute** (no aggregation, no `GROUP BY`).

**Rationale:** In the absence of any aggregation or grouping, all output columns are plain attributes.

---

### TC-006-03 · Window function output is attribute (not measure)

**SQL:**
```sql
SELECT
    employee_id,
    salary,
    RANK() OVER (PARTITION BY department_id ORDER BY salary DESC) AS salary_rank
FROM hr.employee
```

**Key assertions:**
- `salary_rank` is classified as **attribute** (window functions do not collapse rows like aggregates).
- `employee_id` and `salary` are also **attribute**.

**Rationale:** Window functions superficially resemble aggregates but do not reduce the row set — they must not be misclassified as measures.

---

## FR-007 — Column Lineage

### TC-007-01 · Direct column pass-through with alias

**SQL:**
```sql
SELECT customer_id AS cust_id, full_name AS name
FROM sales.customer
```

**Key assertions:**
- `cust_id` lineage: source `sales.customer.customer_id`, no transform.
- `name` lineage: source `sales.customer.full_name`, no transform.

**Rationale:** Simplest lineage case — a renamed column with no transformation applied.

---

### TC-007-02 · Aggregate transform in lineage

**SQL:**
```sql
SELECT department_id, SUM(salary) AS total_salary
FROM hr.employee
GROUP BY department_id
```

**Key assertions:**
- `total_salary` lineage: source `hr.employee.salary`, transform recorded as `SUM`.
- `department_id` lineage: source `hr.employee.department_id`, no transform.

**Rationale:** Aggregation is the most common transform. Lineage must capture both the source column and the aggregate operator applied.

---

### TC-007-03 · Multi-table lineage from JOIN

**SQL:**
```sql
SELECT o.order_id, c.name AS customer_name
FROM sales.orders o
JOIN sales.customer c ON c.customer_id = o.customer_id
```

**Key assertions:**
- `order_id` traces to `sales.orders.order_id`.
- `customer_name` traces to `sales.customer.name`.

**Rationale:** When output columns originate from different source tables, lineage must correctly attribute each to its actual source table, not the first table in the `FROM` clause.

---

### TC-007-04 · CTE output lineage resolved to base table

**SQL:**
```sql
WITH summary AS (
    SELECT region, SUM(revenue) AS total
    FROM finance.sales_fact
    GROUP BY region
)
SELECT region AS sales_region, total AS total_revenue
FROM summary
```

**Key assertions:**
- `sales_region` traces back to `finance.sales_fact.region`.
- `total_revenue` traces back to `finance.sales_fact.revenue` with `SUM` transform.

**Rationale:** Lineage must pass through CTE boundaries — output aliases in the outer query must trace to the original base table columns, not the CTE's intermediate aliases.

---

## FR-008 — SELECT * Wildcard Handling

### TC-008-01 · Simple SELECT *

**SQL:**
```sql
SELECT *
FROM sales.customer
```

**Key assertions:**
- `sales.customer` is extracted.
- `has_wildcard` flag is `True` on the `QueriedTable`.
- No columns are invented or populated in the model.

**Rationale:** Without a catalog, column names cannot be resolved from `SELECT *`. The flag warns downstream consumers without fabricating data.

---

### TC-008-02 · Qualified wildcard (table.*)

**SQL:**
```sql
SELECT o.*, c.name
FROM sales.orders o
JOIN sales.customer c ON c.customer_id = o.customer_id
```

**Key assertions:**
- `sales.orders` has `has_wildcard = True`.
- `sales.customer` has `has_wildcard = False` and column `name` is present.

**Rationale:** Qualified wildcards (`table.*`) must be flagged on the specific table they reference, while explicitly named columns from other tables are still captured normally.

---

### TC-008-03 · SELECT * inside CTE

**SQL:**
```sql
WITH raw AS (
    SELECT * FROM staging.raw_events
)
SELECT event_id, event_type FROM raw
```

**Key assertions:**
- `staging.raw_events` has `has_wildcard = True`.
- `event_id` and `event_type` are **not** added as columns (they cannot be confirmed without catalog resolution).

**Rationale:** A wildcard inside a CTE propagates unresolvability to the outer query. The analyser must flag and not fabricate columns for downstream references.

---

## FR-009 — DataModel Merging

### TC-009-01 · Non-overlapping tables merged by union

**Models:**
- Model A: table `sales.orders` with columns `[order_id (varchar), amount (numeric)]`
- Model B: table `sales.customer` with columns `[customer_id (varchar), name (varchar)]`

**Key assertions:**
- Merged model contains both `sales.orders` and `sales.customer`.
- All columns intact and unmodified.

**Rationale:** Merging two entirely disjoint models is the simplest case — a pure union with no resolution logic needed.

---

### TC-009-02 · Overlapping table — column union with type specificity

**Models:**
- Model A: `sales.orders` with `[order_id (varchar), amount (varchar)]` (amount inferred as varchar elsewhere)
- Model B: `sales.orders` with `[amount (numeric), status (varchar)]`

**Key assertions:**
- Merged model has `sales.orders` with columns `order_id (varchar)`, `amount (numeric)`, `status (varchar)`.
- `numeric` wins over `varchar` for `amount`.

**Rationale:** Type-specificity resolution is the core merge rule. This is the case where two queries observe the same column but with different type inferences; the richer type must win.

---

### TC-009-03 · Overlapping table — conflicting non-varchar types warn, left wins

**Models:**
- Model A: `sales.orders` with `[order_date (date)]`
- Model B: `sales.orders` with `[order_date (timestamp)]`

**Key assertions:**
- Merged model retains `order_date` with type `date` (left-hand operand).
- A warning is emitted (or recorded) about the type conflict.

**Rationale:** When both sides have specific but incompatible types, the spec requires the left operand to win and a warning to be raised. Silent corruption of type information must be prevented.

---

### TC-009-04 · Relationship deduplication on merge

**Models:**
- Model A: relationship `sales.orders.customer_id = sales.customer.customer_id`
- Model B: same relationship

**Key assertions:**
- Merged model contains exactly **one** relationship between `sales.orders` and `sales.customer`.

**Rationale:** The same relationship inferred from two different queries must not produce duplicates in the merged model.

---

### TC-009-05 · Wildcard flag preserved on merge

**Models:**
- Model A: `sales.orders` with `has_wildcard = True`, no columns
- Model B: `sales.orders` with `has_wildcard = False`, column `order_id (varchar)`

**Key assertions:**
- Merged `sales.orders` has `has_wildcard = True`.
- `order_id` is present.

**Rationale:** Once a wildcard is flagged on a table, that flag must be preserved through a merge — seeing `SELECT *` in any analysed query means the column list is incomplete.

---

## Cross-cutting / Integration Test Cases

### TC-INT-01 · Full pipeline — CTE + aggregate + multiple JOINs (spec §8.1)

This is the primary integration test from the specification. See TC-003-01 for the SQL and Mermaid assertions.

**Additional assertions beyond rendering:**
- Source model contains exactly three base tables.
- Relationships: two (orders↔product, orders↔store).
- Type inference: `quantity`, `value`, `base_cost` typed `numeric`.
- Lineage: `product_name → core_dims.product.prod_name`, `store_name → core_dims.store.store_nam`, `revenue/quantity/avg_margin → core_facts.orders`.

**Rationale:** The spec's own example is the canonical end-to-end regression test covering extraction, type inference, relationships, lineage, and rendering together.

---

### TC-INT-02 · Deeply nested subquery and CTE combination

**SQL:**
```sql
WITH regional_totals AS (
    SELECT
        r.region_name,
        SUM(o.amount) AS total_amount
    FROM sales.orders o
    JOIN (
        SELECT customer_id, region_name
        FROM sales.customer
        WHERE active = 1
    ) r ON r.customer_id = o.customer_id
    GROUP BY r.region_name
)
SELECT region_name, total_amount
FROM regional_totals
ORDER BY total_amount DESC
```

**Key assertions:**
- Tables extracted: `sales.orders`, `sales.customer` (inline subquery resolved).
- No CTE or subquery aliases in the model.
- Relationship: `sales.orders.customer_id` ↔ `sales.customer.customer_id`.
- `amount` typed `numeric` (from `SUM`).
- `total_amount DESC` sourced from `ORDER BY` contributes `total_amount` to lineage.

**Rationale:** Combines CTEs, an inline subquery within the CTE, a JOIN, an aggregate, and an `ORDER BY` on a derived column. This stress-tests the scope resolver, type inferencer, and lineage tracker together.

---

### TC-INT-03 · UNION with mixed column references

**SQL:**
```sql
SELECT 'active' AS segment, customer_id, revenue
FROM sales.active_customers
WHERE revenue > 1000
UNION ALL
SELECT 'lapsed' AS segment, customer_id, last_revenue AS revenue
FROM sales.lapsed_customers
ORDER BY revenue DESC
```

**Key assertions:**
- Two distinct tables: `sales.active_customers`, `sales.lapsed_customers`.
- `revenue` on `sales.active_customers`; `last_revenue` on `sales.lapsed_customers`.
- `customer_id` and filter columns captured on each table respectively.
- `ORDER BY revenue` does not invent a column on either table beyond what is already projected.

**Rationale:** UNION queries with different column names mapping to the same output alias test both scope enumeration and lineage disambiguation across branches.

---

## Edge Cases

### TC-EDGE-01 · Literal-only SELECT (no table columns)

**SQL:**
```sql
SELECT 1 AS one, 'hello' AS greeting
```

**Key assertions:**
- No tables extracted.
- No relationships.
- Model is valid but empty.

**Rationale:** The analyser must handle a SELECT with no FROM clause gracefully and return an empty but valid `DataModel`.

---

### TC-EDGE-02 · Subquery in SELECT list (scalar subquery)

**SQL:**
```sql
SELECT
    c.customer_id,
    (SELECT COUNT(*) FROM sales.orders o WHERE o.customer_id = c.customer_id) AS order_count
FROM sales.customer c
```

**Key assertions:**
- Both `sales.customer` and `sales.orders` are extracted.
- `order_count` lineage traces to `sales.orders` with `COUNT` transform.

**Rationale:** Scalar subqueries in the `SELECT` list introduce a separate scope with its own table references, which must be included in the source model.

---

### TC-EDGE-03 · Table alias without schema prefix

**SQL:**
```sql
SELECT e.id, e.name
FROM employee e
WHERE e.department = 'Engineering'
```

**Key assertions:**
- Table `employee` (no schema prefix) is extracted.
- Columns: `id`, `name`, `department`.

**Rationale:** Schema-less table references are common in single-schema environments. The analyser must handle them without error.

---

### TC-EDGE-04 · CASE expression column references

**SQL:**
```sql
SELECT
    order_id,
    CASE
        WHEN status = 'SHIPPED' THEN delivery_date
        WHEN status = 'PENDING' THEN estimated_date
        ELSE NULL
    END AS resolved_date
FROM sales.orders
```

**Key assertions:**
- Columns extracted: `order_id`, `status`, `delivery_date`, `estimated_date`.
- All columns from inside the `CASE` expression branches are captured.

**Rationale:** `CASE` expressions reference columns in `WHEN` and `THEN` clauses that are not surfaced at the top level of the `SELECT`. They represent real source dependencies.

---

### TC-EDGE-05 · Arithmetic expression columns

**SQL:**
```sql
SELECT
    price * quantity AS line_total,
    price * quantity * (1 - discount_rate) AS discounted_total
FROM sales.order_line
```

**Key assertions:**
- Columns extracted: `price`, `quantity`, `discount_rate`.

**Rationale:** Columns inside arithmetic expressions must be walked and captured. An expression walker that only visits top-level AST nodes will miss them.
