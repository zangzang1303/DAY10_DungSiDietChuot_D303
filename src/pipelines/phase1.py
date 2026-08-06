from __future__ import annotations

from datetime import UTC, datetime

import pandas as pd

from core.config import load_settings, require_llm_credentials
from core.utils import read_json, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import build_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import fetch_source_records, load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_phase1_report
from retrieval.index import LocalEmbeddingIndex


def _load_or_fetch_raw_records(settings):
    """
    Load raw records from saved snapshot when available.
    Fetch from Crossref only when snapshot is missing or REFRESH_SOURCE=true.
    """
    if settings.paths.raw_records_json.exists() and not settings.refresh_source:
        print(f"[phase1] Loading raw records from {settings.paths.raw_records_json}")
        return load_raw_records(settings.paths.raw_records_json)

    print("[phase1] Fetching records from Crossref API...")
    return fetch_source_records(settings)


def _load_or_build_test_set(df: pd.DataFrame, settings) -> list[dict]:
    """
    Freeze evaluation set.
    Reuse data/eval/test_set.json unless REFRESH_TEST_SET=true.
    """
    if settings.paths.eval_testset.exists() and not settings.refresh_test_set:
        print(f"[phase1] Loading frozen test set from {settings.paths.eval_testset}")
        return read_json(settings.paths.eval_testset)

    print("[phase1] Building and freezing evaluation test set...")
    return build_test_set(df, settings.paths.eval_testset)


def _source_summary(settings, raw_records_count: int, clean_records_count: int) -> dict:
    return {
        "source_api": settings.source_api,
        "source_query": settings.source_query,
        "source_filter": settings.source_filter,
        "max_results": settings.max_results,
        "raw_records": raw_records_count,
        "clean_records": clean_records_count,
        "generated_at": datetime.now(UTC).isoformat(),
    }


def main() -> None:
    """
    Baseline pipeline end-to-end.

    Steps:
    1. Load settings.
    2. Load or fetch raw records.
    3. Clean data.
    4. Save clean CSV/JSON.
    5. Build Chroma index.
    6. Create or load frozen evaluation set.
    7. Evaluate RAG pipeline.
    8. Run quality/freshness checks.
    9. Write baseline markdown report.
    """
    settings = load_settings()

    # Check LLM credentials early. If LLM judge/agent is unavailable,
    # evaluation.metrics still has fallback judge, but answer generation needs provider config.
    require_llm_credentials(settings)

    print("[phase1] Step 1/9: load or fetch raw records")
    records = _load_or_fetch_raw_records(settings)

    print("[phase1] Step 2/9: clean records")
    run_date = datetime.now(UTC)
    clean_df = build_clean_dataframe(records, run_date=run_date)

    if clean_df.empty:
        raise RuntimeError("Clean dataframe is empty. Check Crossref ingestion and cleaning rules.")

    print("[phase1] Step 3/9: save clean dataset")
    write_csv(clean_df, settings.paths.clean_csv)
    write_json(settings.paths.clean_json, clean_df.to_dict(orient="records"))

    print("[phase1] Step 4/9: build ChromaDB index")
    index = LocalEmbeddingIndex.build(
        df=clean_df,
        settings=settings,
        embeddings_output_path=settings.paths.embeddings_json,
    )

    print("[phase1] Step 5/9: create or load frozen evaluation test set")
    test_set = _load_or_build_test_set(clean_df, settings)

    if not test_set:
        raise RuntimeError("Evaluation test set is empty. Check evaluation/testset.py.")

    print("[phase1] Step 6/9: evaluate baseline RAG")
    evaluation = evaluate_pipeline(
        settings=settings,
        index=index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.baseline_metrics,
        answers_output_path=settings.paths.baseline_answers,
    )

    print("[phase1] Step 7/9: run data quality checks")
    quality = run_data_quality_checks(
        df=clean_df,
        settings=settings,
        report_name="baseline_quality_report",
    )

    print("[phase1] Step 8/9: build freshness report")
    freshness = build_freshness_report(
        df=clean_df,
        settings=settings,
        report_path=settings.paths.freshness_report,
    )

    print("[phase1] Step 9/9: generate markdown report")
    source_summary = _source_summary(
        settings=settings,
        raw_records_count=len(records),
        clean_records_count=len(clean_df),
    )

    generate_phase1_report(
        report_path=settings.paths.baseline_report,
        source_summary=source_summary,
        metrics=evaluation.summary,
        quality=quality,
        freshness=freshness,
    )

    print("\n[phase1] Baseline pipeline completed.")
    print(f"[phase1] Clean CSV: {settings.paths.clean_csv}")
    print(f"[phase1] Test set: {settings.paths.eval_testset}")
    print(f"[phase1] Metrics: {settings.paths.baseline_metrics}")
    print(f"[phase1] Answers: {settings.paths.baseline_answers}")
    print(f"[phase1] Quality: {settings.paths.quality_dir / 'baseline_quality_report.json'}")
    print(f"[phase1] Freshness: {settings.paths.freshness_report}")
    print(f"[phase1] Report: {settings.paths.baseline_report}")