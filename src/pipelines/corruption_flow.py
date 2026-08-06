from __future__ import annotations

from datetime import UTC, datetime

import pandas as pd

from core.config import load_settings, require_llm_credentials
from core.utils import read_json, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_corruption_report
from retrieval.index import LocalEmbeddingIndex


def _load_clean_dataset(settings) -> pd.DataFrame:
    if not settings.paths.clean_csv.exists():
        raise FileNotFoundError(
            f"Missing clean dataset: {settings.paths.clean_csv}. "
            "Run baseline first: python script/run_phase1.py"
        )
    return pd.read_csv(settings.paths.clean_csv)


def _require_baseline_artifacts(settings) -> dict:
    missing = []

    for path in [
        settings.paths.baseline_metrics,
        settings.paths.baseline_answers,
        settings.paths.eval_testset,
        settings.paths.raw_records_json,
        settings.paths.clean_csv,
    ]:
        if not path.exists():
            missing.append(str(path))

    if missing:
        raise FileNotFoundError(
            "Missing baseline artifacts. Run python script/run_phase1.py first.\n"
            + "\n".join(missing)
        )

    return read_json(settings.paths.baseline_metrics)


def _save_dataframe(df: pd.DataFrame, csv_path, json_path) -> None:
    write_csv(df, csv_path)
    write_json(json_path, df.to_dict(orient="records"))


def _build_index_and_evaluate(
    *,
    df: pd.DataFrame,
    settings,
    embeddings_output_path,
    metrics_output_path,
    answers_output_path,
):
    index = LocalEmbeddingIndex.build(
        df=df,
        settings=settings,
        embeddings_output_path=embeddings_output_path,
    )

    return evaluate_pipeline(
        settings=settings,
        index=index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=metrics_output_path,
        answers_output_path=answers_output_path,
    )


def main() -> None:
    """
    Corruption flow end-to-end.

    Steps:
    1. Load baseline metrics and clean dataset.
    2. Create corrupted dataframe.
    3. Save corrupted artifacts.
    4. Rebuild index and evaluate corrupted data.
    5. Run quality/freshness on corrupted data.
    6. Repair from saved raw records.
    7. Evaluate repaired dataset.
    8. Create comparison report.
    """
    settings = load_settings()
    require_llm_credentials(settings)

    print("[corruption_flow] Step 1/8: load baseline artifacts")
    baseline_metrics = _require_baseline_artifacts(settings)
    clean_df = _load_clean_dataset(settings)

    print("[corruption_flow] Step 2/8: create corrupted dataframe")
    corrupted_df = corrupt_clean_dataframe(
        df=clean_df,
        output_log_path=settings.paths.corruption_log,
    )

    print("[corruption_flow] Step 3/8: save corrupted artifacts")
    _save_dataframe(
        corrupted_df,
        settings.paths.corrupted_clean_csv,
        settings.paths.corrupted_clean_json,
    )

    print("[corruption_flow] Step 4/8: rebuild corrupted index and evaluate")
    corrupted_eval = _build_index_and_evaluate(
        df=corrupted_df,
        settings=settings,
        embeddings_output_path=settings.paths.corrupted_embeddings_json,
        metrics_output_path=settings.paths.corrupted_metrics,
        answers_output_path=settings.paths.corrupted_answers,
    )

    print("[corruption_flow] Step 5/8: quality/freshness on corrupted data")
    corrupted_quality = run_data_quality_checks(
        df=corrupted_df,
        settings=settings,
        report_name="corrupted_quality_report",
    )
    corrupted_freshness = build_freshness_report(
        df=corrupted_df,
        settings=settings,
        report_path=settings.paths.quality_dir / "corrupted_freshness_report.json",
    )

    print("[corruption_flow] Step 6/8: repair from raw records")
    raw_records = load_raw_records(settings.paths.raw_records_json)
    repaired_df = build_clean_dataframe(
        records=raw_records,
        run_date=datetime.now(UTC),
    )

    if repaired_df.empty:
        raise RuntimeError("Repaired dataframe is empty. Check raw records and cleaning pipeline.")

    _save_dataframe(
        repaired_df,
        settings.paths.repaired_clean_csv,
        settings.paths.repaired_clean_json,
    )

    print("[corruption_flow] Step 7/8: rebuild repaired index and evaluate")
    repaired_eval = _build_index_and_evaluate(
        df=repaired_df,
        settings=settings,
        embeddings_output_path=settings.paths.repaired_embeddings_json,
        metrics_output_path=settings.paths.repaired_metrics,
        answers_output_path=settings.paths.repaired_answers,
    )

    repaired_quality = run_data_quality_checks(
        df=repaired_df,
        settings=settings,
        report_name="repaired_quality_report",
    )
    repaired_freshness = build_freshness_report(
        df=repaired_df,
        settings=settings,
        report_path=settings.paths.quality_dir / "repaired_freshness_report.json",
    )

    print("[corruption_flow] Step 8/8: generate comparison report")
    generate_corruption_report(
        report_path=settings.paths.comparison_report,
        baseline_metrics=baseline_metrics,
        corrupted_metrics=corrupted_eval.summary,
        repaired_metrics=repaired_eval.summary,
        corrupted_quality=corrupted_quality,
        repaired_quality=repaired_quality,
        corrupted_freshness=corrupted_freshness,
        repaired_freshness=repaired_freshness,
    )

    print("\n[corruption_flow] Corruption flow completed.")
    print(f"[corruption_flow] Corruption log: {settings.paths.corruption_log}")
    print(f"[corruption_flow] Corrupted metrics: {settings.paths.corrupted_metrics}")
    print(f"[corruption_flow] Repaired metrics: {settings.paths.repaired_metrics}")
    print(f"[corruption_flow] Comparison report: {settings.paths.comparison_report}")