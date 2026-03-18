"""Tests for domain model classes and merge logic."""

from __future__ import annotations

import warnings

import pytest

from sql_analyser.domain import (
    AnalysisResult,
    ColumnClassification,
    ColumnUsage,
    ComplexityMetrics,
    DataModel,
    OutputColumn,
    QueriedColumn,
    QueriedTable,
    Relationship,
    merge_columns,
    merge_models,
    merge_tables,
)


class TestEnums:
    """Test enum construction and serialization."""

    def test_column_usage_enum(self):
        """TC-DOMAIN-01: ColumnUsage enum values."""
        assert ColumnUsage.SELECT == "select"
        assert ColumnUsage.WHERE == "where"
        assert ColumnUsage.HAVING == "having"
        assert ColumnUsage.ORDER_BY == "order_by"
        assert ColumnUsage.GROUP_BY == "group_by"
        assert ColumnUsage.JOIN_ON == "join_on"

    def test_column_classification_enum(self):
        """TC-DOMAIN-01: ColumnClassification enum values."""
        assert ColumnClassification.MEASURE == "measure"
        assert ColumnClassification.DIMENSION == "dimension"
        assert ColumnClassification.ATTRIBUTE == "attribute"


class TestQueriedColumn:
    """Test QueriedColumn construction and defaults."""

    def test_construction_with_defaults(self):
        """TC-DOMAIN-01: QueriedColumn with default values."""
        col = QueriedColumn(name="id")
        assert col.name == "id"
        assert col.data_type == "varchar"
        assert col.usages == set()

    def test_construction_with_values(self):
        """TC-DOMAIN-01: QueriedColumn with explicit values."""
        col = QueriedColumn(
            name="quantity",
            data_type="numeric",
            usages={ColumnUsage.SELECT, ColumnUsage.WHERE},
        )
        assert col.name == "quantity"
        assert col.data_type == "numeric"
        assert col.usages == {ColumnUsage.SELECT, ColumnUsage.WHERE}

    def test_usages_is_mutable_set(self):
        """Verify usages can be modified after construction."""
        col = QueriedColumn(name="id")
        col.usages.add(ColumnUsage.JOIN_ON)
        assert ColumnUsage.JOIN_ON in col.usages


class TestQueriedTable:
    """Test QueriedTable and qualified_name property."""

    def test_qualified_name_full(self):
        """TC-DOMAIN-04: catalog.schema.name."""
        table = QueriedTable(
            name="orders",
            schema_name="core_facts",
            catalog_name="my_catalog",
        )
        assert table.qualified_name == "my_catalog.core_facts.orders"

    def test_qualified_name_schema_and_name(self):
        """TC-DOMAIN-05: schema.name."""
        table = QueriedTable(name="orders", schema_name="core_facts")
        assert table.qualified_name == "core_facts.orders"

    def test_qualified_name_name_only(self):
        """TC-DOMAIN-05: name only."""
        table = QueriedTable(name="orders")
        assert table.qualified_name == "orders"

    def test_qualified_name_with_empty_strings(self):
        """TC-DOMAIN-05: Empty strings are omitted."""
        table = QueriedTable(
            name="orders",
            schema_name="",
            catalog_name="",
        )
        assert table.qualified_name == "orders"

    def test_construction_with_defaults(self):
        """TC-DOMAIN-01: QueriedTable with defaults."""
        table = QueriedTable(name="orders")
        assert table.name == "orders"
        assert table.schema_name == ""
        assert table.catalog_name == ""
        assert table.columns == []
        assert table.has_wildcard is False

    def test_construction_with_columns(self):
        """TC-DOMAIN-01: QueriedTable with columns."""
        cols = [
            QueriedColumn(name="id", data_type="int"),
            QueriedColumn(name="quantity"),
        ]
        table = QueriedTable(
            name="orders",
            schema_name="core_facts",
            columns=cols,
            has_wildcard=True,
        )
        assert len(table.columns) == 2
        assert table.has_wildcard is True


class TestRelationship:
    """Test Relationship and canonical_key property."""

    def test_construction(self):
        """TC-DOMAIN-01: Relationship construction."""
        rel = Relationship(
            left_table="core_dims.product",
            left_columns=["sku"],
            right_table="core_facts.orders",
            right_columns=["prod_sku"],
        )
        assert rel.left_table == "core_dims.product"
        assert rel.left_columns == ["sku"]
        assert rel.right_table == "core_facts.orders"
        assert rel.right_columns == ["prod_sku"]

    def test_canonical_key_symmetry(self):
        """TC-DOMAIN-06: (A→B) == (B→A)."""
        rel1 = Relationship(
            left_table="A",
            left_columns=["id"],
            right_table="B",
            right_columns=["a_id"],
        )
        rel2 = Relationship(
            left_table="B",
            left_columns=["a_id"],
            right_table="A",
            right_columns=["id"],
        )
        assert rel1.canonical_key == rel2.canonical_key

    def test_canonical_key_multi_column_sort(self):
        """TC-DOMAIN-07: Multi-column joins are sorted."""
        rel1 = Relationship(
            left_table="A",
            left_columns=["col2", "col1"],
            right_table="B",
            right_columns=["b_col1", "b_col2"],
        )
        rel2 = Relationship(
            left_table="A",
            left_columns=["col1", "col2"],
            right_table="B",
            right_columns=["b_col2", "b_col1"],
        )
        # Column lists are sorted within each side
        assert rel1.canonical_key == rel2.canonical_key


class TestOtherDomainClasses:
    """Test OutputColumn, ComplexityMetrics, AnalysisResult, DataModel."""

    def test_output_column_construction(self):
        """TC-DOMAIN-01: OutputColumn with defaults."""
        col = OutputColumn(alias="product_name")
        assert col.alias == "product_name"
        assert col.source_table is None
        assert col.source_column is None
        assert col.transforms == []
        assert col.classification == ColumnClassification.ATTRIBUTE

    def test_output_column_with_lineage(self):
        """TC-DOMAIN-01: OutputColumn with lineage."""
        col = OutputColumn(
            alias="total_revenue",
            source_table="core_facts.orders",
            source_column="revenue",
            transforms=["SUM"],
            classification=ColumnClassification.MEASURE,
        )
        assert col.source_table == "core_facts.orders"
        assert col.source_column == "revenue"
        assert col.transforms == ["SUM"]
        assert col.classification == ColumnClassification.MEASURE

    def test_complexity_metrics_construction(self):
        """TC-DOMAIN-01: ComplexityMetrics construction."""
        metrics = ComplexityMetrics(
            node_count=42,
            scope_count=3,
            scope_types=["ROOT", "CTE", "SUBQUERY"],
        )
        assert metrics.node_count == 42
        assert metrics.scope_count == 3
        assert metrics.scope_types == ["ROOT", "CTE", "SUBQUERY"]

    def test_data_model_construction(self):
        """TC-DOMAIN-01: DataModel with defaults."""
        model = DataModel()
        assert model.tables == []
        assert model.relationships == []

    def test_analysis_result_construction(self):
        """TC-DOMAIN-01: AnalysisResult construction."""
        model = DataModel()
        result = AnalysisResult(data_model=model)
        assert result.data_model == model
        assert result.output_columns == []
        assert result.metrics is None


class TestJSONSerialisation:
    """Test JSON serialization round-trip."""

    def test_queried_column_dict_round_trip(self):
        """TC-DOMAIN-02: QueriedColumn model → dict → model."""
        col = QueriedColumn(
            name="quantity",
            data_type="numeric",
            usages={ColumnUsage.SELECT, ColumnUsage.WHERE},
        )
        data = col.model_dump()
        restored = QueriedColumn.model_validate(data)
        assert restored.name == col.name
        assert restored.data_type == col.data_type
        assert restored.usages == col.usages

    def test_queried_column_json_string_round_trip(self):
        """TC-DOMAIN-03: QueriedColumn model → JSON string → model."""
        col = QueriedColumn(
            name="quantity",
            data_type="numeric",
            usages={ColumnUsage.SELECT, ColumnUsage.WHERE},
        )
        json_str = col.model_dump_json()
        restored = QueriedColumn.model_validate_json(json_str)
        assert restored.name == col.name
        assert restored.data_type == col.data_type
        assert restored.usages == col.usages

    def test_data_model_full_round_trip(self):
        """TC-DOMAIN-02, TC-DOMAIN-03: Full DataModel serialization."""
        table1 = QueriedTable(
            name="orders",
            schema_name="core_facts",
            columns=[
                QueriedColumn(name="id", data_type="int", usages={ColumnUsage.SELECT}),
                QueriedColumn(name="quantity", data_type="numeric"),
            ],
            has_wildcard=False,
        )
        table2 = QueriedTable(
            name="product",
            schema_name="core_dims",
            columns=[QueriedColumn(name="sku")],
        )
        rel = Relationship(
            left_table="core_facts.orders",
            left_columns=["prod_sku"],
            right_table="core_dims.product",
            right_columns=["sku"],
        )
        model = DataModel(tables=[table1, table2], relationships=[rel])

        # Dict round-trip
        data = model.model_dump()
        restored = DataModel.model_validate(data)
        assert len(restored.tables) == 2
        assert len(restored.relationships) == 1
        assert restored.tables[0].qualified_name == "core_facts.orders"
        assert len(restored.tables[0].columns) == 2

        # JSON string round-trip
        json_str = model.model_dump_json()
        restored_json = DataModel.model_validate_json(json_str)
        assert len(restored_json.tables) == 2
        assert len(restored_json.relationships) == 1

    def test_analysis_result_round_trip(self):
        """TC-DOMAIN-02: AnalysisResult serialization."""
        model = DataModel(
            tables=[QueriedTable(name="orders")],
        )
        output_cols = [
            OutputColumn(
                alias="product_name",
                source_table="core_dims.product",
                source_column="name",
                classification=ColumnClassification.DIMENSION,
            )
        ]
        metrics = ComplexityMetrics(
            node_count=10, scope_count=1, scope_types=["ROOT"]
        )
        result = AnalysisResult(
            data_model=model, output_columns=output_cols, metrics=metrics
        )

        data = result.model_dump()
        restored = AnalysisResult.model_validate(data)
        assert len(restored.data_model.tables) == 1
        assert len(restored.output_columns) == 1
        assert restored.metrics is not None
        assert restored.metrics.node_count == 10


class TestMergeColumns:
    """Test merge_columns function."""

    def test_merge_same_type(self):
        """Merge columns with same data type."""
        col1 = QueriedColumn(name="id", data_type="int", usages={ColumnUsage.SELECT})
        col2 = QueriedColumn(name="id", data_type="int", usages={ColumnUsage.WHERE})
        result = merge_columns(col1, col2)
        assert result.name == "id"
        assert result.data_type == "int"
        assert result.usages == {ColumnUsage.SELECT, ColumnUsage.WHERE}

    def test_merge_varchar_with_specific_type(self):
        """TC-009-03: Non-varchar beats varchar."""
        col1 = QueriedColumn(name="quantity", data_type="varchar")
        col2 = QueriedColumn(name="quantity", data_type="numeric")
        result = merge_columns(col1, col2)
        assert result.data_type == "numeric"

        # Test reverse order
        result2 = merge_columns(col2, col1)
        assert result2.data_type == "numeric"

    def test_merge_conflicting_non_varchar_types(self):
        """TC-009-04: Conflicting non-varchar types warn and prefer left."""
        col1 = QueriedColumn(name="value", data_type="int")
        col2 = QueriedColumn(name="value", data_type="decimal")

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = merge_columns(col1, col2)
            assert len(w) == 1
            assert "conflicting types" in str(w[0].message).lower()
            assert result.data_type == "int"

    def test_merge_usage_union(self):
        """TC-DOMAIN-08: Usage sets are unioned."""
        col1 = QueriedColumn(
            name="id", usages={ColumnUsage.SELECT, ColumnUsage.WHERE}
        )
        col2 = QueriedColumn(
            name="id", usages={ColumnUsage.WHERE, ColumnUsage.JOIN_ON}
        )
        result = merge_columns(col1, col2)
        assert result.usages == {
            ColumnUsage.SELECT,
            ColumnUsage.WHERE,
            ColumnUsage.JOIN_ON,
        }

    def test_merge_different_names_raises_error(self):
        """Merge columns with different names should raise ValueError."""
        col1 = QueriedColumn(name="id")
        col2 = QueriedColumn(name="sku")
        with pytest.raises(ValueError, match="different names"):
            merge_columns(col1, col2)


class TestMergeTables:
    """Test merge_tables function."""

    def test_merge_disjoint_columns(self):
        """TC-009-02: Columns are unioned."""
        table1 = QueriedTable(
            name="orders",
            schema_name="core_facts",
            columns=[QueriedColumn(name="id"), QueriedColumn(name="quantity")],
        )
        table2 = QueriedTable(
            name="orders",
            schema_name="core_facts",
            columns=[QueriedColumn(name="revenue"), QueriedColumn(name="date")],
        )
        result = merge_tables(table1, table2)
        assert result.qualified_name == "core_facts.orders"
        assert len(result.columns) == 4
        col_names = {col.name for col in result.columns}
        assert col_names == {"id", "quantity", "revenue", "date"}

    def test_merge_overlapping_columns(self):
        """TC-009-02: Overlapping columns are merged."""
        table1 = QueriedTable(
            name="orders",
            columns=[
                QueriedColumn(name="id", data_type="varchar"),
                QueriedColumn(name="quantity"),
            ],
        )
        table2 = QueriedTable(
            name="orders",
            columns=[
                QueriedColumn(name="id", data_type="int"),
                QueriedColumn(name="revenue"),
            ],
        )
        result = merge_tables(table1, table2)
        assert len(result.columns) == 3
        id_col = next(col for col in result.columns if col.name == "id")
        assert id_col.data_type == "int"  # Non-varchar wins

    def test_merge_wildcard_or(self):
        """TC-DOMAIN-09: Wildcard flags are OR'd."""
        table1 = QueriedTable(name="orders", has_wildcard=False)
        table2 = QueriedTable(name="orders", has_wildcard=True)
        result = merge_tables(table1, table2)
        assert result.has_wildcard is True

        # Test both false
        table3 = QueriedTable(name="orders", has_wildcard=False)
        table4 = QueriedTable(name="orders", has_wildcard=False)
        result2 = merge_tables(table3, table4)
        assert result2.has_wildcard is False

    def test_merge_different_qualified_names_raises_error(self):
        """Merge tables with different qualified names should raise ValueError."""
        table1 = QueriedTable(name="orders", schema_name="core_facts")
        table2 = QueriedTable(name="orders", schema_name="other_schema")
        with pytest.raises(ValueError, match="different qualified names"):
            merge_tables(table1, table2)

    def test_merge_preserves_namespace(self):
        """Merged table preserves namespace parts from left operand."""
        table1 = QueriedTable(
            name="orders",
            schema_name="core_facts",
            catalog_name="my_catalog",
            columns=[QueriedColumn(name="id")],
        )
        table2 = QueriedTable(
            name="orders",
            schema_name="core_facts",
            catalog_name="my_catalog",
            columns=[QueriedColumn(name="quantity")],
        )
        result = merge_tables(table1, table2)
        assert result.name == "orders"
        assert result.schema_name == "core_facts"
        assert result.catalog_name == "my_catalog"


class TestMergeModels:
    """Test merge_models function and DataModel.merge() method."""

    def test_merge_disjoint_models(self):
        """TC-009-01: Union of disjoint tables and relationships."""
        model1 = DataModel(
            tables=[QueriedTable(name="orders", schema_name="core_facts")],
            relationships=[
                Relationship(
                    left_table="core_facts.orders",
                    left_columns=["prod_id"],
                    right_table="core_dims.product",
                    right_columns=["id"],
                )
            ],
        )
        model2 = DataModel(
            tables=[QueriedTable(name="customer", schema_name="core_dims")],
            relationships=[
                Relationship(
                    left_table="core_facts.orders",
                    left_columns=["cust_id"],
                    right_table="core_dims.customer",
                    right_columns=["id"],
                )
            ],
        )
        result = merge_models(model1, model2)
        assert len(result.tables) == 2
        assert len(result.relationships) == 2

    def test_merge_overlapping_tables(self):
        """TC-009-02: Overlapping tables are merged."""
        model1 = DataModel(
            tables=[
                QueriedTable(
                    name="orders",
                    schema_name="core_facts",
                    columns=[QueriedColumn(name="id")],
                )
            ],
        )
        model2 = DataModel(
            tables=[
                QueriedTable(
                    name="orders",
                    schema_name="core_facts",
                    columns=[QueriedColumn(name="quantity")],
                )
            ],
        )
        result = merge_models(model1, model2)
        assert len(result.tables) == 1
        assert result.tables[0].qualified_name == "core_facts.orders"
        assert len(result.tables[0].columns) == 2

    def test_merge_relationship_deduplication(self):
        """TC-009-05: Symmetric relationships are deduplicated."""
        rel1 = Relationship(
            left_table="A",
            left_columns=["id"],
            right_table="B",
            right_columns=["a_id"],
        )
        rel2 = Relationship(
            left_table="B",
            left_columns=["a_id"],
            right_table="A",
            right_columns=["id"],
        )
        model1 = DataModel(relationships=[rel1])
        model2 = DataModel(relationships=[rel2])
        result = merge_models(model1, model2)
        assert len(result.relationships) == 1

    def test_merge_exact_duplicate_relationships(self):
        """Exact duplicate relationships are deduplicated."""
        rel1 = Relationship(
            left_table="A",
            left_columns=["id"],
            right_table="B",
            right_columns=["a_id"],
        )
        rel2 = Relationship(
            left_table="A",
            left_columns=["id"],
            right_table="B",
            right_columns=["a_id"],
        )
        model1 = DataModel(relationships=[rel1])
        model2 = DataModel(relationships=[rel2])
        result = merge_models(model1, model2)
        assert len(result.relationships) == 1

    def test_data_model_merge_method(self):
        """DataModel.merge() delegates to merge_models()."""
        model1 = DataModel(tables=[QueriedTable(name="orders")])
        model2 = DataModel(tables=[QueriedTable(name="product")])
        result = model1.merge(model2)
        assert len(result.tables) == 2

    def test_merge_complex_scenario(self):
        """Complex merge: overlapping tables, symmetric relationships, type resolution."""
        model1 = DataModel(
            tables=[
                QueriedTable(
                    name="orders",
                    schema_name="core_facts",
                    columns=[
                        QueriedColumn(name="id", data_type="varchar"),
                        QueriedColumn(name="quantity", data_type="numeric"),
                    ],
                ),
                QueriedTable(name="product", schema_name="core_dims"),
            ],
            relationships=[
                Relationship(
                    left_table="core_facts.orders",
                    left_columns=["prod_id"],
                    right_table="core_dims.product",
                    right_columns=["id"],
                )
            ],
        )
        model2 = DataModel(
            tables=[
                QueriedTable(
                    name="orders",
                    schema_name="core_facts",
                    columns=[
                        QueriedColumn(name="id", data_type="int"),  # More specific type
                        QueriedColumn(name="revenue", data_type="numeric"),
                    ],
                ),
                QueriedTable(name="customer", schema_name="core_dims"),
            ],
            relationships=[
                Relationship(
                    left_table="core_dims.product",  # Symmetric relationship
                    left_columns=["id"],
                    right_table="core_facts.orders",
                    right_columns=["prod_id"],
                )
            ],
        )
        result = merge_models(model1, model2)

        # Check tables
        assert len(result.tables) == 3  # orders, product, customer
        orders = next(t for t in result.tables if t.name == "orders")
        assert len(orders.columns) == 3  # id, quantity, revenue
        id_col = next(col for col in orders.columns if col.name == "id")
        assert id_col.data_type == "int"  # Non-varchar wins

        # Check relationships
        assert len(result.relationships) == 1  # Symmetric relationship deduplicated
