from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pandas as pd

from core.config import Settings
from core.utils import write_json


def _safe_rate(count: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return count / total


def _check_payload(
    name: str,
    dimension: str,
    passed: bool,
    value: Any,
    threshold: Any,
    details: str,
) -> dict[str, Any]:
    return {
        "name": name,
        "dimension": dimension,
        "passed": bool(passed),
        "value": value,
        "threshold": threshold,
        "details": details,
    }


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """
    Run simple data quality checks for cleaned Crossref dataset.

    Checks:
    1. Row count.
    2. paper_id non-null and unique.
    3. title non-null.
    4. summary length/completeness.
    5. freshness based on age_days.
    6. Write JSON report to data/quality/.
    """
    total_rows = int(len(df))
    checks: list[dict[str, Any]] = []

    required_columns = [
        "paper_id",
        "title",
        "summary",
        "published",
        "authors_joined",
        "categories_joined",
        "age_days",
        "text_for_embedding",
        "abs_url",
        "pdf_url",
    ]

    missing_columns = [col for col in required_columns if col not in df.columns]
    checks.append(
        _check_payload(
            name="required_columns_present",
            dimension="schema_validity",
            passed=len(missing_columns) == 0,
            value={"missing_columns": missing_columns},
            threshold="no missing required columns",
            details="Clean dataset must match the agreed contract.",
        )
    )

    checks.append(
        _check_payload(
            name="row_count_positive",
            dimension="completeness",
            passed=total_rows > 0,
            value=total_rows,
            threshold="> 0",
            details="Clean dataset should contain at least one record.",
        )
    )

    if "paper_id" in df.columns:
        paper_id_missing = int(df["paper_id"].isna().sum() + (df["paper_id"].astype(str).str.strip() == "").sum())
        paper_id_duplicate = int(df["paper_id"].duplicated().sum())
    else:
        paper_id_missing = total_rows
        paper_id_duplicate = 0

    checks.append(
        _check_payload(
            name="paper_id_not_null",
            dimension="validity",
            passed=paper_id_missing == 0,
            value={"missing_rows": paper_id_missing, "missing_rate": _safe_rate(paper_id_missing, total_rows)},
            threshold="0 missing paper_id",
            details="paper_id is required for retrieval hit-rate and evaluation matching.",
        )
    )

    checks.append(
        _check_payload(
            name="paper_id_unique",
            dimension="uniqueness",
            passed=paper_id_duplicate == 0,
            value={"duplicate_rows": paper_id_duplicate, "duplicate_rate": _safe_rate(paper_id_duplicate, total_rows)},
            threshold="0 duplicate paper_id",
            details="Each paper_id should identify exactly one cleaned document.",
        )
    )

    if "title" in df.columns:
        title_missing = int(df["title"].isna().sum() + (df["title"].astype(str).str.strip() == "").sum())
    else:
        title_missing = total_rows

    checks.append(
        _check_payload(
            name="title_not_null",
            dimension="completeness",
            passed=title_missing == 0,
            value={"missing_rows": title_missing, "missing_rate": _safe_rate(title_missing, total_rows)},
            threshold="0 missing title",
            details="Title is required for readable retrieval context and test-set generation.",
        )
    )

    if "summary" in df.columns:
        summary_text = df["summary"].fillna("").astype(str).str.strip()
        missing_summary = int((summary_text == "").sum())
        short_summary = int((summary_text.str.len() < 40).sum())
    else:
        missing_summary = total_rows
        short_summary = total_rows

    checks.append(
        _check_payload(
            name="summary_completeness",
            dimension="completeness",
            passed=_safe_rate(missing_summary, total_rows) <= 0.20,
            value={
                "missing_rows": missing_summary,
                "missing_rate": _safe_rate(missing_summary, total_rows),
                "short_summary_rows": short_summary,
                "short_summary_rate": _safe_rate(short_summary, total_rows),
            },
            threshold="missing summary rate <= 20%",
            details="Summary/abstract gives semantic content for embedding and RAG answers.",
        )
    )

    if "text_for_embedding" in df.columns:
        embedding_text = df["text_for_embedding"].fillna("").astype(str).str.strip()
        empty_embedding_text = int((embedding_text == "").sum())
        short_embedding_text = int((embedding_text.str.len() < 80).sum())
    else:
        empty_embedding_text = total_rows
        short_embedding_text = total_rows

    checks.append(
        _check_payload(
            name="text_for_embedding_ready",
            dimension="retrieval_readiness",
            passed=empty_embedding_text == 0 and _safe_rate(short_embedding_text, total_rows) <= 0.25,
            value={
                "empty_rows": empty_embedding_text,
                "empty_rate": _safe_rate(empty_embedding_text, total_rows),
                "short_rows": short_embedding_text,
                "short_rate": _safe_rate(short_embedding_text, total_rows),
            },
            threshold="0 empty text_for_embedding and short text rate <= 25%",
            details="Embedding quality depends directly on text_for_embedding.",
        )
    )

    if "age_days" in df.columns:
        age_values = pd.to_numeric(df["age_days"], errors="coerce")
        invalid_age = int(age_values.isna().sum())
        stale_rows = int((age_values > settings.freshness_threshold_days).sum())
    else:
        invalid_age = total_rows
        stale_rows = total_rows

    checks.append(
        _check_payload(
            name="freshness_age_days",
            dimension="freshness",
            passed=invalid_age == 0 and _safe_rate(stale_rows, total_rows) <= 0.50,
            value={
                "invalid_age_rows": invalid_age,
                "stale_rows": stale_rows,
                "stale_rate": _safe_rate(stale_rows, total_rows),
            },
            threshold=f"invalid age_days = 0 and stale rate <= 50%; threshold={settings.freshness_threshold_days} days",
            details="Freshness is computed from published date through age_days.",
        )
    )

    passed = all(check["passed"] for check in checks)
    report = {
        "report_name": report_name,
        "generated_at": datetime.now(UTC).isoformat(),
        "total_rows": total_rows,
        "passed": passed,
        "failed_checks": [check["name"] for check in checks if not check["passed"]],
        "checks": checks,
    }

    report_path = settings.paths.quality_dir / f"{report_name}.json"
    write_json(report_path, report)
    return report


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path) -> dict[str, Any]:
    """
    Build freshness report:
    - latest_published
    - oldest_published
    - stale_rows
    - total_rows
    - is_fresh
    """
    total_rows = int(len(df))

    if "published" in df.columns:
        published_dates = pd.to_datetime(df["published"], errors="coerce", utc=True)
        latest = published_dates.max()
        oldest = published_dates.min()
        invalid_published_rows = int(published_dates.isna().sum())
    else:
        published_dates = pd.Series([], dtype="datetime64[ns, UTC]")
        latest = pd.NaT
        oldest = pd.NaT
        invalid_published_rows = total_rows

    if "age_days" in df.columns:
        age_values = pd.to_numeric(df["age_days"], errors="coerce")
        stale_rows = int((age_values > settings.freshness_threshold_days).sum())
        invalid_age_rows = int(age_values.isna().sum())
    else:
        stale_rows = total_rows
        invalid_age_rows = total_rows

    stale_rate = _safe_rate(stale_rows, total_rows)
    is_fresh = total_rows > 0 and invalid_age_rows == 0 and stale_rate <= 0.50

    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "latest_published": None if pd.isna(latest) else latest.isoformat(),
        "oldest_published": None if pd.isna(oldest) else oldest.isoformat(),
        "freshness_threshold_days": settings.freshness_threshold_days,
        "stale_rows": stale_rows,
        "stale_rate": stale_rate,
        "invalid_age_rows": invalid_age_rows,
        "invalid_published_rows": invalid_published_rows,
        "total_rows": total_rows,
        "is_fresh": bool(is_fresh),
    }

    write_json(report_path, report)
    return report