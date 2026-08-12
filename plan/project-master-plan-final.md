# Project Master Plan — Federated Payload Web Attack Detection
**Consolidated charter · v-final · 20 July 2026**
**One reference document for the whole project. If anything below conflicts with a later decision made with the professor, the professor's decision wins.**

---

## PART 1 — WHAT THIS PROJECT IS

### Official topic (as assigned, unchanged)
> **Federated Hybrid Payload-based Detection for Web Attacks**

### Conference paper (SCIN-2026 slice)
> **Diversity-Aware Federated Learning for Resilient Multi-Family Web Payload Detection under Non-IID Distributions**

### Journal extension (after SCIN)
> **Federated Open-World Web Payload Detection under Cross-Organization and Obfuscation Shifts** — adds open-set rejection, dual-view raw/canonical representation, FedLoRA communication efficiency, obfuscation robustness, and a privacy audit.

### Contribution type
Empirical benchmark study + a lightweight method (diversity-aware aggregation) + a published artifact (leakage-controlled FL benchmark). **Not** a new-architecture paper. This is a legitimate and reviewable contribution class; the value is in the question, the rigor, and the reusable benchmark — not in inventing a novel network.

---

## PART 2 — THE CENTRAL QUESTION AND WHY IT'S A REAL GAP

**Central research question:**
> Under family-disjoint and source-heterogeneous client distributions, can reliability- and diversity-aware aggregation improve worst-client detection and transfer to locally unseen web-attack families, compared with FedAvg, FedProx, and discrepancy-aware aggregation (FedDisco)?

**The gap, in one sentence (defensible, hand-verified from 92 papers):**
> Federated payload detection exists only for single-family XSS (3/22 payload-text papers use FL, all XSS-binary), while the substantial diversity-/reliability-aware federated-aggregation literature (15 methods) is developed on generic image/sensor/flow data — none on multi-family web payloads under family-disjoint clients with leakage-controlled evaluation and locally-unseen-family transfer.

**What is NOT novel (state these plainly so reviewers can't ambush you):**
- FL for XSS — done (single-family).
- FedAvg/FedProx comparison — done.
- Using class-distribution discrepancy in aggregation — done (FedDisco).
- Diversity-aware client *selection* — done (DivFL, Fed-CBS, DPP).
- Prototype sharing in federated IDS — done (PROTEAN, FedProto).

**What is potentially novel (the defensible claim):**
- A domain-specific aggregation combining **reliability + attack-family rarity + complementarity** for **family-disjoint multi-family payloads**, evaluated with **leakage-controlled splits, worst-client F1, and locally-unseen-family recall**.

---

## PART 3 — SCOPE (UPDATED 2026-08-12)

**⚠️ Updated 2026-08-12 — 100% Raw Data Ingestion & Gold-Standard Processing.**
All raw source subfolders are consolidated under `data/raw/` (`data/raw/professor_dataset/`, `data/raw/httpparams/`, `data/raw/csic2010/`, `data/raw/modsecurity_production_2025/`, `data/raw/xss_fmereani/`, `data/raw/seclists_lfi/`, `data/raw/cicids2017_kaggle_mirror/`, `data/raw/cse_cic_ids2018/`). Full source manifest: `data/PROVENANCE.md`.

### In scope for SCIN (100% Data Ingestion Guarantee)
- **Data Ingestion:** Ingest **100% of raw data** across all 8 sources (`SRC_00` through `SRC_07`), including all 10 Suricata hourly log files (`suricata_2024-10-27_23.csv` to `2024-10-28_09.csv` — over 398MB raw HTTP captures), ModSecurity production logs (`SRC_03`), HttpParams (`SRC_01`), fmereani XSS (`SRC_04`), SecLists & PayloadsAllTheThings LFI (`SRC_05`), and network-flow scenarios (`SRC_06`/`SRC_07`). CSIC 2010 (`SRC_02`) as external test set only.
- **Gold-Standard Labeling:** OWASP ModSecurity CRS v4 rulesets (`REQUEST-941` XSS, `REQUEST-942` SQLi, `REQUEST-930` PathTrav) + D19 mislabel scrubbing (clean false malicious labels on benign strings like `"5739-5839"`) + dynamic sandbox verification (`sandbox_verify.py`).
- **Paper-Backed Local Data Augmentation (B5 Zhu 2021, A16 WAMM 2025):** Apply semantic obfuscation mutations strictly inside local client training sets to expand minority classes (PathTrav, SQLi) 5x–10x locally without touching validation or test sets.
- **Dedup & Leakage Barrier:** Exact + MinHash near-duplicate (adaptive Jaccard thresholds: 0.85 PathTrav, 0.60 XSS/SQLi) generating `dedup_cluster_id`. Splitting enforced strictly by `dedup_cluster_id` (Template-Disjoint). Zero cluster overlap between train and test sets.
- **Splits:** IID control + family-disjoint (primary, 6 clients) + source-disjoint + template-disjoint + global holdout.
- **Clients:** 6 simulated cross-silo clients (2 XSS, 2 SQLi, 2 PathTrav), grounded in real source heterogeneity (honeypot vs lab vs scraped vs synthetic sandbox-verified).
- **Models:** char TF-IDF+LogReg (classical), charCNN (primary FL backbone), DistilBERT (secondary reference).
- **FL:** Local-only, Centralized, FedAvg, FedProx, FedDisco, proposed diversity/rarity-aware method ($s_k = \alpha \cdot \log(1+n_k) + \beta \cdot D_k + \gamma \cdot C_k + \delta \cdot \log(\varepsilon+R_k)$).
- **Metrics:** global macro-F1, **worst-client macro-F1**, locally-unseen-family recall, cross-source drop, client variance, communication cost.
- **Statistics:** ≥3 seeds; template-cluster bootstrap CIs.

### Deferred to journal (do NOT touch before SCIN)
Open-set rejection, dual-view raw/canonical, FedLoRA, obfuscation/adversarial robustness, differential-privacy audit, **running/expanding a NEW honeypot to collect more data** (using the professor's ALREADY-COLLECTED honeypot logs as `SRC_00` is in scope and done — this deferred item means don't stand up additional honeypot infrastructure for more data before SCIN), multi-label (SR-BH).

### The proposed aggregation (definition to implement and defend)
`s_k = α·log(1+n_k) + β·D_k + γ·C_k + δ·log(ε+R_k)` ; `w_k = softmax(s_k/τ)`, `w_k` clipped.
- `n_k` local sample count; `D_k` complementarity (JS-distance of class dist. vs federation); `C_k` rare-family coverage this round; `R_k` reliability = EMA of **local-validation** macro-F1 (**never test set**); `τ` temperature.
- Threat-model note to state in paper: whether the server receives sanitized class-count metadata. This is a conference assumption, not a full privacy guarantee.

---

## PART 4 — THE CORRECTNESS HARNESS (build in week 1, run all project)

For a benchmark study the numbers ARE the product; a silent bug doesn't crash, it produces a clean wrong number that reviewers exist to find. Have AI write these as automated tests; a number without a green test does not enter a table.

| Test | Prevents |
|---|---|
| Leakage test (no exact/near-dup shared train↔test) | Inflated metrics from template leakage |
| Partition-integrity test (each client only its family+benign; held-out family truly absent) | Meaningless unseen-family results |
| Label-space test (one fixed global label index across clients) | Garbage multi-class aggregation |
| Aggregation sanity test (reproduce a published FedAvg/FedProx/FedDisco result within tolerance) | Wrong aggregation biasing every FL number |
| Reliability-source test (assert R_k never reads the test set) | Test leakage into the method itself |
| Determinism test (same config+seed → identical output) | Non-reproducible results = auto-reject |
| Metric test (hand-computed macro-F1 on toy set matches pipeline) | A subtly wrong metric poisoning all tables |

---

## PART 5 — FULL TIMELINE (anchored to real deadlines)

**Today 20 Jul · Abstract 3 Aug · Conference 3–5 Sep · Camera-ready 15 Nov**

> **⚠️ Superseded 2026-08-02 — read `project/plan/BUILD-PLAN-TO-CONFERENCE.md` for the live schedule.** The day-numbering below is anchored to a 20 Jul start and has drifted. The abstract was prepared and handled by Tri separately; the remaining work is now phased against the 3–5 Sep conference date. The research question, gap, scope lock, and decision gates in this file all still stand — only the calendar is stale. That file also documents a material change to the ≥6-client design (Part 3 / `build-execution-plan.md` §5.2), forced by measuring how much attack payload `SRC_00` actually contains per family: it yields ~10.9k unique path-traversal and ~767 unique SQLi payloads, but only 10 XSS — so XSS must come entirely from public sources.

### Stage 0 — Now → 3 Aug (14 days): ABSTRACT + PROOF THE PROBLEM EXISTS
Goal: submit abstract, and have a week-1 diagnostic that shows the failure mode is real.
- Days 1–3: repo + config/seed schema; data inventory & provenance; **write the correctness harness (leakage + partition tests) BEFORE processing data**; **write the pre-registered failure criteria into the README before looking at any result.**
- Days 4–7: ingest 2 sources → decode → sanitize → **dedup (exact+MinHash)**, output before/after table; generate IID + family-disjoint splits.
- Days 8–11: run diagnostic — Local / Centralized / FedAvg / FedProx on family-disjoint, 1 seed. Check against the pre-registered criteria.
- **Days 12–14: DECISION GATE.** If ≥1 failure criterion holds → the problem is real → submit abstract (add qualitative/quantitative result sentence). If none holds → tighten heterogeneity or revise question BEFORE committing the abstract; do not fabricate a failure.
- Submit abstract by 3 Aug (send professor the draft first — already prepared).

### Stage 1 — 4 Aug → 30 Aug (~4 weeks): METHOD + PRESENTABLE RESULTS
Goal: results good enough to present at the conference.
- Week 1: finish model ladder (charCNN primary; TF-IDF+LR; DistilBERT secondary). Full centralized + local-only under the partitions.
- Week 2: implement FedDisco baseline; **implement the proposed aggregation** (with reliability-source test green); pilot run.
- Week 3: main experiments — family-disjoint + source-disjoint, 3 seeds; core ablations (no-diversity / no-reliability / no-coverage).
- Week 4: cross-source eval; worst-client + unseen-family tables; communication cost; error analysis. Prepare slides.
- **Mid-point check (~end Aug):** does the proposed method beat baselines on worst-client and/or unseen-family with statistical significance? If yes → strong presentation. If marginal → present as honest benchmark finding (a well-designed negative result is still a finding) and diagnose for the camera-ready.

### Stage 2 — 3–5 Sep: CONFERENCE
Present. Collect reviewer/audience questions systematically — they define the camera-ready and journal to-do list.

### Stage 3 — 6 Sep → 15 Nov (~10 weeks): CAMERA-READY + JOURNAL LAUNCH
- Weeks 1–2: address conference feedback; upgrade to 5 seeds on the main table; template-cluster bootstrap CIs; finalize figures/tables.
- Weeks 3–4: write the camera-ready to venue standard; internal adversarial review by professor; **pre-submission gap re-scan** (re-run the primary gap-check; a paper you missed that a reviewer finds ≈ reject).
- Submit camera-ready by 15 Nov.
- Weeks 5+: begin the journal extension on the SAME benchmark (open-set, dual-view, FedLoRA, obfuscation, privacy audit). 80% of code/benchmark carries over — this is why the SCIN slice was scoped as a slice, not a detour.

---

## PART 6 — DIVISION OF LABOR (AI-heavy, correctness-owned)

| AI does freely | You + professor certify (never delegate) |
|---|---|
| Pipeline code, FL scaffold, plotting, tables, prose drafts, literature extraction | The 6 trust-boundary files: dedup/split, label-space, partitioner, aggregation, metrics, tokenizer |
| Debug, refactor, reproduce baselines | Every headline number (from config + seed + green test) |
| Suggest datasets/refactors, compute stats on request | Gap statement + differentiation (you write, you defend orally) |
| — | The decision-gate calls and the target-venue decision |

Rule: **AI produces, you verify; AI drafts, you decide; AI extracts, you understand.**

---

## PART 7 — VENUE & EXPECTATIONS (honest)

- **SCIN-2026:** first publication milestone. Springer LNNS proceedings possible for selected papers — **not** Q1, not a Transactions. Present + get selected = a real result for a 4th-year student.
- **Journal target after SCIN:** Computers & Security (Q1) or IEEE TNSM if the cross-organization/system angle is strong; TDSC/TIFS are stretch, not the plan.
- **Timeline honesty:** 4 months → *submission-ready*, not *accepted*. Journal accept runs into 2027 after review + revision. Tell the professor "submission-ready + one conference publication" — never promise acceptance, which no one controls.
- **Rough odds (execution-dependent):** SCIN presentation likely; SCIN→Springer selection plausible with a complete method + experiments; journal Q1 accept ~30–40% over the full cycle; Q2 the safe floor.

---

## PART 8 — TOP RISKS AND MITIGATIONS

1. **Silent pipeline bug** (highest risk for a benchmark paper) → the correctness harness (Part 4); no number without a green test.
2. **Scope creep** → the locked scope (Part 3); everything ambitious is explicitly deferred to journal.
3. **Matrix/report number mismatch** → normalize the broken dropdown values in synthesis_matrix_v3 so Dashboard counts == report counts before showing the professor.
4. **Novelty overclaim** → the "what is NOT novel" list (Part 2); cite and differentiate FedDisco, PROTEAN, DivFL, Fed-CBS, and the federated-XSS paper explicitly.
5. **A newer paper closing the gap mid-project** → weekly Scholar/arXiv alerts + a pre-submission gap re-scan (the C10 paper appeared during this very project).
6. **Failure mode doesn't appear in the diagnostic** → don't fabricate; tighten heterogeneity or revise the question at the week-2 gate, while there's still time.

---

## PART 9 — IMMEDIATE NEXT ACTIONS (this week)

**Status as of 2026-08-02** — items 4 (repo + harness tests, though still only against toy data, not real data) and the raw-data half of item 6 (all sources acquired, checksummed, documented — see `PROVENANCE.md`/`DATA_ACQUISITION.md`) are done. Items 1-3 and 5 not yet confirmed done in this repo. The rest of item 6 (ingest → decode → sanitize → dedup, i.e. actually running the pipeline on real data) has NOT started — this is the next work to do.

1. Send the professor the abstract draft (already prepared) with the three scope questions.
2. Normalize the dropdown values in `synthesis_matrix_v3.xlsx` so counts are consistent.
3. Verify F1 (FedDisco), F9 (PROTEAN), and A18 (federated-XSS) against their PDFs — they define your differentiation.
4. ✅ Create the repo; write the leakage + partition-integrity tests before touching data. (Done — tests pass against toy data; not yet run against real ingested data.)
5. Write the pre-registered failure criteria into the README before running anything.
6. Start the data pipeline: ✅ raw-data acquisition done (all 8 sources, `SRC_00`-`SRC_07`, checksummed). ⬜ ingest → decode → sanitize → dedup → before/after table — NOT started, this is the next step.

Then run the week-1 diagnostic and bring the results back to the decision gate.
