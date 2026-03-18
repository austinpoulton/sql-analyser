"""SQL Analyser - Domain model and analysis tools for SQL objects."""

from __future__ import annotations

from .domain import (
    AnalysisResult,
    ColumnClassification,
    ColumnUsage,
    ComplexityMetrics,
    DataModel,
    OutputColumn,
    QueriedColumn,
    QueriedTable,
    Relationship,
)

__version__ = "0.1.0"

__all__ = [
    "AnalysisResult",
    "ColumnClassification",
    "ColumnUsage",
    "ComplexityMetrics",
    "DataModel",
    "OutputColumn",
    "QueriedColumn",
    "QueriedTable",
    "Relationship",
]
