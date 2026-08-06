# Corruption, Repair and Comparison Report

Generated at: `2026-08-06T03:56:05.530476+00:00`

## 1. Metric Comparison

| Metric | Baseline | Corrupted | Repaired | Corruption delta | Repair delta |
|---|---:|---:|---:|---:|---:|
| `retrieval_hit_rate` | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 0.0000 |
| `mean_token_f1` | 0.2420 | 0.1802 | 0.2420 | -0.0618 | 0.0618 |
| `judge_accuracy` | 0.1250 | 0.1250 | 0.1250 | 0.0000 | 0.0000 |
| `mean_judge_score` | 1.2500 | 1.2500 | 1.2500 | 0.0000 | 0.0000 |

## 2. Corrupted Data Quality

Overall status: **FAIL**

| Check | Dimension | Passed | Value | Threshold |
|---|---|---:|---|---|
| required_columns_present | schema_validity | PASS | `{'missing_columns': []}` | no missing required columns |
| row_count_positive | completeness | PASS | `27` | > 0 |
| paper_id_not_null | validity | PASS | `{'missing_rows': 0, 'missing_rate': 0.0}` | 0 missing paper_id |
| paper_id_unique | uniqueness | FAIL | `{'duplicate_rows': 3, 'duplicate_rate': 0.1111111111111111}` | 0 duplicate paper_id |
| title_not_null | completeness | PASS | `{'missing_rows': 0, 'missing_rate': 0.0}` | 0 missing title |
| summary_completeness | completeness | FAIL | `{'missing_rows': 7, 'missing_rate': 0.25925925925925924, 'short_summary_rows': 7, 'short_summary_rate': 0.25925925925925924}` | missing summary rate <= 20% |
| text_for_embedding_ready | retrieval_readiness | PASS | `{'empty_rows': 0, 'empty_rate': 0.0, 'short_rows': 0, 'short_rate': 0.0}` | 0 empty text_for_embedding and short text rate <= 25% |
| freshness_age_days | freshness | PASS | `{'invalid_age_rows': 0, 'stale_rows': 4, 'stale_rate': 0.14814814814814814}` | invalid age_days = 0 and stale rate <= 50%; threshold=180 days |

## 3. Repaired Data Quality

Overall status: **PASS**

| Check | Dimension | Passed | Value | Threshold |
|---|---|---:|---|---|
| required_columns_present | schema_validity | PASS | `{'missing_columns': []}` | no missing required columns |
| row_count_positive | completeness | PASS | `24` | > 0 |
| paper_id_not_null | validity | PASS | `{'missing_rows': 0, 'missing_rate': 0.0}` | 0 missing paper_id |
| paper_id_unique | uniqueness | PASS | `{'duplicate_rows': 0, 'duplicate_rate': 0.0}` | 0 duplicate paper_id |
| title_not_null | completeness | PASS | `{'missing_rows': 0, 'missing_rate': 0.0}` | 0 missing title |
| summary_completeness | completeness | PASS | `{'missing_rows': 0, 'missing_rate': 0.0, 'short_summary_rows': 0, 'short_summary_rate': 0.0}` | missing summary rate <= 20% |
| text_for_embedding_ready | retrieval_readiness | PASS | `{'empty_rows': 0, 'empty_rate': 0.0, 'short_rows': 0, 'short_rate': 0.0}` | 0 empty text_for_embedding and short text rate <= 25% |
| freshness_age_days | freshness | PASS | `{'invalid_age_rows': 0, 'stale_rows': 0, 'stale_rate': 0.0}` | invalid age_days = 0 and stale rate <= 50%; threshold=180 days |

## 4. Freshness Comparison

| Signal | Corrupted | Repaired |
|---|---:|---:|
| Stale rows | 4 | 0 |
| Stale rate | 0.1481 | 0.0000 |
| Invalid age rows | 0 | 0 |
| Is fresh | True | True |

## 5. Causal Interpretation

1. Controlled corruption changes quality/freshness signals such as missing summary rate, duplicate paper IDs, stale rows, or short embedding text.
2. These data issues can reduce retrieval quality and answer quality because ChromaDB indexes weaker or noisier text.
3. Repair from raw records should improve quality/freshness signals and recover RAG metrics toward the baseline level.
