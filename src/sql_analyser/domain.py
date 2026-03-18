"""Domain model for SQL Analyser.

This module contains the core domain model classes for representing SQL objects
including schemas, tables, columns, views, and their relationships.
"""

from __future__ import annotations

import warnings
from enum import StrEnum

from pydantic import BaseModel, Field


class ColumnUsage(StrEnum):
    """SQL clause where a column was referenced."""

    SELECT = "select"
    WHERE = "where"
    HAVING = "having"
    ORDER_BY = "order_by"
    GROUP_BY = "group_by"
    JOIN_ON = "join_on"


class ColumnClassification(StrEnum):
    """Business classification of an output column."""

    MEASURE = "measure"
    DIMENSION = "dimension"
    ATTRIBUTE = "attribute"


class QueriedColumn(BaseModel):
    """A column extracted from SQL, with inferred type and usage tracking.

    Attributes:
        name: The column name.
        data_type: The inferred data type (defaults to 'varchar').
        usages: Set of SQL clauses where this column was referenced.
    """

    name: str
    data_type: str = "varchar"
    usages: set[ColumnUsage] = Field(default_factory=set)


class QueriedTable(BaseModel):
    """A base table extracted from SQL with its referenced columns.

    Attributes:
        name: The table name.
        schema_name: The schema name (empty if not specified).
        catalog_name: The catalog name (empty if not specified).
        columns: List of columns referenced from this table.
        has_wildcard: True if SELECT * was used on this table.
    """

    name: str
    schema_name: str = ""
    catalog_name: str = ""
    columns: list[QueriedColumn] = Field(default_factory=list)
    has_wildcard: bool = False

    @property
    def qualified_name(self) -> str:
        """Fully-qualified table name: catalog.schema.name (omits empty parts)."""
        parts = [p for p in [self.catalog_name, self.schema_name, self.name] if p]
        return ".".join(parts)


class Relationship(BaseModel):
    """A relationship between two tables on specific columns.

    Attributes:
        left_table: Qualified name of the left table.
        left_columns: List of column names on the left side.
        right_table: Qualified name of the right table.
        right_columns: List of column names on the right side.
    """

    left_table: str
    left_columns: list[str]
    right_table: str
    right_columns: list[str]

    @property
    def canonical_key(self) -> tuple:
        """Normalised key for symmetric deduplication.

        Returns a tuple that is identical for relationships (A→B) and (B→A),
        enabling deduplication of symmetric relationships.
        """
        left = (self.left_table, tuple(sorted(self.left_columns)))
        right = (self.right_table, tuple(sorted(self.right_columns)))
        return tuple(sorted([left, right]))


class DataModel(BaseModel):
    """Container for extracted source data model: tables + relationships.

    Attributes:
        tables: List of queried tables.
        relationships: List of relationships between tables.
    """

    tables: list[QueriedTable] = Field(default_factory=list)
    relationships: list[Relationship] = Field(default_factory=list)

    def merge(self, other: DataModel) -> DataModel:
        """Merge with another DataModel.

        Args:
            other: The DataModel to merge with this one.

        Returns:
            A new DataModel containing the merged result.
        """
        return merge_models(self, other)


class OutputColumn(BaseModel):
    """Lineage and classification for a SELECT output column.

    Attributes:
        alias: The output column alias.
        source_table: Qualified name of the source table (if applicable).
        source_column: Name of the source column (if applicable).
        transforms: List of transformation descriptions applied.
        classification: Business classification of this column.
    """

    alias: str
    source_table: str | None = None
    source_column: str | None = None
    transforms: list[str] = Field(default_factory=list)
    classification: ColumnClassification = ColumnClassification.ATTRIBUTE


class ComplexityMetrics(BaseModel):
    """AST complexity metrics.

    Attributes:
        node_count: Number of AST nodes.
        scope_count: Number of semantic scopes.
        scope_types: List of scope type names.
    """

    node_count: int
    scope_count: int
    scope_types: list[str] = Field(default_factory=list)


class AnalysisResult(BaseModel):
    """Top-level wrapper for complete analysis output.

    Attributes:
        data_model: The extracted source data model.
        output_columns: List of output columns with lineage.
        metrics: Complexity metrics (optional).
    """

    data_model: DataModel
    output_columns: list[OutputColumn] = Field(default_factory=list)
    metrics: ComplexityMetrics | None = None


def merge_columns(left: QueriedColumn, right: QueriedColumn) -> QueriedColumn:
    """Merge two QueriedColumn instances with type specificity rules.

    Args:
        left: The left-hand column.
        right: The right-hand column.

    Returns:
        A new QueriedColumn with merged usages and resolved data type.

    Raises:
        ValueError: If column names do not match.
    """
    if left.name != right.name:
        raise ValueError(
            f"Cannot merge columns with different names: {left.name} vs {right.name}"
        )

    usages = left.usages | right.usages

    if left.data_type == right.data_type:
        data_type = left.data_type
    elif left.data_type == "varchar":
        data_type = right.data_type
    elif right.data_type == "varchar":
        data_type = left.data_type
    else:
        warnings.warn(
            f"Column {left.name}: conflicting types {left.data_type} vs "
            f"{right.data_type}, using {left.data_type}",
            stacklevel=2,
        )
        data_type = left.data_type

    return QueriedColumn(name=left.name, data_type=data_type, usages=usages)


def merge_tables(left: QueriedTable, right: QueriedTable) -> QueriedTable:
    """Merge two QueriedTable instances with column union and wildcard OR.

    Args:
        left: The left-hand table.
        right: The right-hand table.

    Returns:
        A new QueriedTable with merged columns and combined wildcard flag.

    Raises:
        ValueError: If qualified names do not match.
    """
    if left.qualified_name != right.qualified_name:
        raise ValueError(
            f"Cannot merge tables with different qualified names: "
            f"{left.qualified_name} vs {right.qualified_name}"
        )

    # Build column index by name
    merged_cols: dict[str, QueriedColumn] = {}
    for col in left.columns:
        merged_cols[col.name] = col
    for col in right.columns:
        if col.name in merged_cols:
            merged_cols[col.name] = merge_columns(merged_cols[col.name], col)
        else:
            merged_cols[col.name] = col

    return QueriedTable(
        name=left.name,
        schema_name=left.schema_name,
        catalog_name=left.catalog_name,
        columns=list(merged_cols.values()),
        has_wildcard=left.has_wildcard or right.has_wildcard,
    )


def merge_models(left: DataModel, right: DataModel) -> DataModel:
    """Merge two DataModel instances with table and relationship union.

    Args:
        left: The left-hand DataModel.
        right: The right-hand DataModel.

    Returns:
        A new DataModel with merged tables and deduplicated relationships.
    """
    # Merge tables
    table_index: dict[str, QueriedTable] = {}
    for table in left.tables:
        table_index[table.qualified_name] = table
    for table in right.tables:
        qn = table.qualified_name
        if qn in table_index:
            table_index[qn] = merge_tables(table_index[qn], table)
        else:
            table_index[qn] = table

    # Deduplicate relationships
    rel_set: set[tuple] = set()
    merged_rels: list[Relationship] = []
    for rel in left.relationships + right.relationships:
        key = rel.canonical_key
        if key not in rel_set:
            rel_set.add(key)
            merged_rels.append(rel)

    return DataModel(tables=list(table_index.values()), relationships=merged_rels)
