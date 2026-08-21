"""Versioned public result models."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ValidationResult(BaseModel):
    outcome: Literal["permitted", "blocked"]
    normalized_sql: str | None = None
    sql_hash: str | None = None
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class QueryResult(BaseModel):
    version: Literal["v1"] = "v1"
    correlation_id: str
    query_id: str
    task_id: str
    source_alias: str
    columns: list[dict[str, str]]
    rows: list[list[Any]]
    truncated: bool
    normalized_sql: str
    sql_hash: str
    validation: ValidationResult
    duration_ms: int
    policy_outcome: Literal["permitted", "blocked"]
    explain_warnings: list[str] = Field(default_factory=list)
    result_checksum: str | None = None


class TaskResult(BaseModel):
    task_id: str
    status: Literal["active", "complete"]
    journal_path: str
