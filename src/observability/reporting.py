from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from core.utils import write_text


def _fmt(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.4f}"
    if value is None:
        return "N/A"
    return str(value)


def _metric_table(metrics: dict[str, Any]) -> str:
    keys = [
        "samples",
        "retrieval_hit_rate",
        "mean_token_f1",
        "judge_accuracy",
        "mean_judge_score",
    ]
    lines = [
        "| Metric | Value |",
        "|---|---:|",
    ]
    for key in keys:
        lines.append(f"| `{key}` | {_fmt(metrics.get(key, 'N/A'))} |")
    return "\n".join(lines)


def _quality_table(quality: dict[str, Any]) -> str:
    lines = [
        "| Check | Dimension | Passed | Value | Threshold |",
        "|---|---|---:|---|---|",
    ]

    for check in quality.get("checks", []):
        lines.append(
            "| {name} | {dimension} | {passed} | `{value}` | {threshold} |".format(
                name=check.get("name", "unknown"),
                dimension=check.get("dimension", "unknown"),
                passed="PASS" if check.get("passed") else "FAIL",
                value=check.get("value"),
                threshold=check.get("threshold", ""),
            )
        )

    if len(lines) == 2:
        lines.append("| N/A | N/A | N/A | N/A | N/A |")

    return "\n".join(lines)


def generate_phase1_report(
    report_path,
    source_summary: dict[str, Any],
    metrics: dict[str, Any],
    quality: dict[str, Any],
    freshness: dict[str, Any],
) -> None:
    """Write markdown report for baseline phase."""
    text = f"""# Phase 1 Baseline Report

Generated at: `{datetime.now(UTC).isoformat()}`

## 1. Source Summary

| Field | Value |
|---|---|
| Source API | {source_summary.get("source_api", "Crossref REST API")} |
| Query | {source_summary.get("source_query", "N/A")} |
| Filter | {source_summary.get("source_filter", "N/A")} |
| Max results | {source_summary.get("max_results", "N/A")} |
| Raw records | {source_summary.get("raw_records", "N/A")} |
| Clean records | {source_summary.get("clean_records", "N/A")} |

## 2. Baseline Evaluation Metrics

{_metric_table(metrics)}

## 3. Data Quality Checks

Overall status: **{"PASS" if quality.get("passed") else "FAIL"}**

{_quality_table(quality)}

## 4. Freshness Report

| Field | Value |
|---|---|
| Latest published | {freshness.get("latest_published", "N/A")} |
| Oldest published | {freshness.get("oldest_published", "N/A")} |
| Freshness threshold days | {freshness.get("freshness_threshold_days", "N/A")} |
| Stale rows | {freshness.get("stale_rows", "N/A")} |
| Stale rate | {_fmt(freshness.get("stale_rate"))} |
| Invalid age rows | {freshness.get("invalid_age_rows", "N/A")} |
| Is fresh | {freshness.get("is_fresh", "N/A")} |

## 5. Interpretation

This baseline is the clean-data reference point for later comparison. 
The retrieval hit rate mainly reflects whether embedding and ChromaDB retrieval can find the ground-truth paper in top-k results. 
Token F1 measures lexical overlap between the generated answer and the ground truth, so it may be below 1.0 even when the retrieved document is correct.
"""
    write_text(report_path, text)


def _comparison_table(
    baseline_metrics: dict[str, Any],
    corrupted_metrics: dict[str, Any],
    repaired_metrics: dict[str, Any],
) -> str:
    metric_names = [
        "retrieval_hit_rate",
        "mean_token_f1",
        "judge_accuracy",
        "mean_judge_score",
    ]
    lines = [
        "| Metric | Baseline | Corrupted | Repaired | Corruption delta | Repair delta |",
        "|---|---:|---:|---:|---:|---:|",
    ]

    for name in metric_names:
        base = baseline_metrics.get(name)
        corrupt = corrupted_metrics.get(name)
        repaired = repaired_metrics.get(name)

        corruption_delta = None
        repair_delta = None

        if isinstance(base, (int, float)) and isinstance(corrupt, (int, float)):
            corruption_delta = corrupt - base
        if isinstance(corrupt, (int, float)) and isinstance(repaired, (int, float)):
            repair_delta = repaired - corrupt

        lines.append(
            f"| `{name}` | {_fmt(base)} | {_fmt(corrupt)} | {_fmt(repaired)} | {_fmt(corruption_delta)} | {_fmt(repair_delta)} |"
        )

    return "\n".join(lines)


def generate_corruption_report(
    report_path,
    baseline_metrics: dict[str, Any],
    corrupted_metrics: dict[str, Any],
    repaired_metrics: dict[str, Any],
    corrupted_quality: dict[str, Any],
    repaired_quality: dict[str, Any],
    corrupted_freshness: dict[str, Any],
    repaired_freshness: dict[str, Any],
) -> None:
    """Write markdown report comparing baseline/corrupted/repaired."""
    text = f"""# Corruption, Repair and Comparison Report

Generated at: `{datetime.now(UTC).isoformat()}`

## 1. Metric Comparison

{_comparison_table(baseline_metrics, corrupted_metrics, repaired_metrics)}

## 2. Corrupted Data Quality

Overall status: **{"PASS" if corrupted_quality.get("passed") else "FAIL"}**

{_quality_table(corrupted_quality)}

## 3. Repaired Data Quality

Overall status: **{"PASS" if repaired_quality.get("passed") else "FAIL"}**

{_quality_table(repaired_quality)}

## 4. Freshness Comparison

| Signal | Corrupted | Repaired |
|---|---:|---:|
| Stale rows | {corrupted_freshness.get("stale_rows", "N/A")} | {repaired_freshness.get("stale_rows", "N/A")} |
| Stale rate | {_fmt(corrupted_freshness.get("stale_rate"))} | {_fmt(repaired_freshness.get("stale_rate"))} |
| Invalid age rows | {corrupted_freshness.get("invalid_age_rows", "N/A")} | {repaired_freshness.get("invalid_age_rows", "N/A")} |
| Is fresh | {corrupted_freshness.get("is_fresh", "N/A")} | {repaired_freshness.get("is_fresh", "N/A")} |

## 5. Causal Interpretation

1. Controlled corruption changes quality/freshness signals such as missing summary rate, duplicate paper IDs, stale rows, or short embedding text.
2. These data issues can reduce retrieval quality and answer quality because ChromaDB indexes weaker or noisier text.
3. Repair from raw records should improve quality/freshness signals and recover RAG metrics toward the baseline level.
"""
    write_text(report_path, text)