# R6 label and local-only 6×6 audit — 2026-08-13

## Decision

The previous 6×6 result was not admissible: it evaluated models on their own
training parquet, reused overlapping target-test samples, and was built on
mislabelled source ingestion. The pipeline was repaired and one local-only
6×6 run was completed. No federated aggregation was applied.

## Corrections made

1. `SRC_03` ModSecurity entries are now classified from CRS rule IDs/tags:
   930 → PathTrav, 941 → XSS, 942 → SQLi; protocol/PHP/other rules are
   quarantined as `other` instead of being forced to SQLi.
2. `SRC_06` no longer treats a numeric feature column as payload. Explicit
   SQLi/XSS/Normal columns are decoded, and `norm`/`goodqueries` text files are
   benign rather than SQLi.
3. The generic XSS regex no longer treats every `<img src>` as an attack.
   Explicitly labelled sources retain their labels; uncertain inferred labels
   are quarantined.
4. Exact payload collisions created by augmentation are unioned before split.
   Client test partitions are now disjoint and label-stratified rather than six
   overlapping samples from one global test table.
5. `other` is excluded from the preregistered four-class training target.

## Data checkpoints

| Stage | benign | XSS | SQLi | PathTrav | other | total |
|---|---:|---:|---:|---:|---:|---:|
| raw unified | 2,316,994 | 1,290,570 | 321,498 | 157,750 | 565,560 | 4,652,372 |
| dedup lineage seeds | 38,022 | 23,269 | 29,990 | 2,260 | 35,187 | 128,728 |
| trainable after local augmentation | 25,000 | 23,269 | 25,000 | 11,606 | 35,187 | 120,062 |

The `other` quarantine is deliberately not counted as one of the four attack
families. PathTrav has 3,054 independent seeds and 16,504 trainable rows after
augmentation; the 16,504 figure must not be described as 16,504 independent
examples.

## Split and leakage gates

- Client training is family-disjoint: C1/C2=XSS, C3/C4=SQLi, C5/C6=PathTrav,
  each with benign.
- Global train/test lineage overlap: **0**.
- Exact sanitized payload train/test overlap: **0**.
- Client-test lineage overlap: **0**.
- Client-test exact payload overlap: **0**.
- Local train rows: C1 7,721; C2 7,719; C3 8,192; C4 8,190; C5 4,811;
  C6 4,900.

## Local-only 6×6 result

The run used CharCNN, seed 42, three epochs, standard CrossEntropy, CUDA.
Model `i` was trained only on `client_i_train`; every matrix cell was computed
on `client_j_test`. Full metrics are in
[`local_only_6x6_repaired.json`](../data/reporting/local_only_6x6_repaired.json).

The four-class macro-F1 matrix is approximately 0.354–0.374 (diagonal mean
0.364). This is expected
for a family-disjoint model evaluated on all four families: each local model
learns its own attack family and benign, while unseen families receive zero
recall. The decisive result is not the diagonal macro-F1 but the unseen-family
recall:

| trained client family | unseen-family recall (mean/max) |
|---|---:|
| XSS (C1/C2) | 0.0 / 0.0 |
| SQLi (C3/C4) | 0.0 / 0.0 |
| PathTrav (C5/C6) | 0.0 / 0.0 |

Known-family holdout recalls are high (XSS ≈0.983–0.998, SQLi ≈0.994–0.998,
PathTrav ≈0.985–1.000), while the two locally unseen attack families are never
claimed as learned. This is a valid baseline for the next FL experiment: FL
must be judged by whether aggregation raises unseen-family recall without
reintroducing leakage.

## Next gate

Do not reuse the old `client_cross_evaluation_matrix.json` or any old R4/R5
headline table. The next experiment may run FedAvg/FedProx/proposed only after
the same split manifest and leakage assertions are preserved; this local-only
artifact is the new baseline.
