# Master Implementation Plan — Raw Specification & Data Ingestion (`fedwebpayload`)

Rebuild the project fresh in [`C:/Users/huynh/Desktop/fedwebpayload`](file:///C:/Users/huynh/Desktop/fedwebpayload) implementing the **Raw Dataset Processing Specification**, fully registered in [`RAW_DATASET_PROCESSING_SPEC.md`](file:///C:/Users/huynh/Desktop/fedwebpayload/data/RAW_DATASET_PROCESSING_SPEC.md), [`DATA_SOURCE_PROVENANCE.md`](file:///C:/Users/huynh/Desktop/fedwebpayload/data/DATA_SOURCE_PROVENANCE.md), and [`implementation-plan-data-centric.md`](file:///C:/Users/huynh/Desktop/fedwebpayload/plan/implementation-plan-data-centric.md).

> [!IMPORTANT]
> **Scope Lock: Stopping at Trainable Data (No Client Splitting Yet):**
> Pipeline scope is locked to: **Raw Ingestion $\rightarrow$ Normalization $\rightarrow$ CRS Label Scrubbing $\rightarrow$ Entropy-Adaptive MinHash Dedup $\rightarrow$ Deterministic Semantic Augmentation $\rightarrow$ Trainable Corpus (`data/processed/trainable_corpus.parquet`)**. Client splitting is paused until this corpus is audited.

---

## 1. Raw Archive Cleanup & Directory Specification

All raw compressed archives (`.zip`, `.tar.gz`) across all 12 `SRC_NN` directories under [`data/raw/`](file:///C:/Users/huynh/Desktop/fedwebpayload/data/raw) have been **extracted in place and deleted/cleaned up**, leaving pristine raw payload files.

Full directory trees, column mappings, and file formats are documented in [`RAW_DATASET_PROCESSING_SPEC.md`](file:///C:/Users/huynh/Desktop/fedwebpayload/data/RAW_DATASET_PROCESSING_SPEC.md):

| Source ID | Canonical Directory Path | Processing Status | Primary Key Columns / File Format |
|---|---|---|---|
| **`SRC_00`** | [`SRC_00_professor_dataset`](file:///C:/Users/huynh/Desktop/fedwebpayload/data/raw/SRC_00_professor_dataset) | **Active Ingestion** | CSV: `@timestamp`, `payload_printable`, `http` dict, `alert.signature` (17 files) |
| **`SRC_01`** | [`SRC_01_httpparams`](file:///C:/Users/huynh/Desktop/fedwebpayload/data/raw/SRC_01_httpparams) | **Completed** | CSV: `payload`, `attack_type` (`norm`, `sqli`, `xss`, `path-traversal`) |
| **`SRC_02`** | [`SRC_02_csic2010`](file:///C:/Users/huynh/Desktop/fedwebpayload/data/raw/SRC_02_csic2010) | **Completed (OOD Test)** | Raw TXT: Multi-line HTTP request dumps |
| **`SRC_03`** | [`SRC_03_modsecurity_waf`](file:///C:/Users/huynh/Desktop/fedwebpayload/data/raw/SRC_03_modsecurity_waf) | **Active Ingestion** | ModSec Log: Sections A, B, C, H (30 daily logs + JSON) |
| **`SRC_04`** | [`SRC_04_xss_collections`](file:///C:/Users/huynh/Desktop/fedwebpayload/data/raw/SRC_04_xss_collections) | **Active Ingestion** | CSV: `Payloads`, `Class`, `Query`, `Label` (4 CSV files) |
| **`SRC_05`** | [`SRC_05_pathtrav_collections`](file:///C:/Users/huynh/Desktop/fedwebpayload/data/raw/SRC_05_pathtrav_collections) | **Active Ingestion (Sandbox Verified)** | Raw TXT: Line-by-line traversal payloads (14 TXT files) |
| **`SRC_06`** | [`SRC_06_sqli_collections`](file:///C:/Users/huynh/Desktop/fedwebpayload/data/raw/SRC_06_sqli_collections) | **Active Ingestion (D16/D19 Scrubbed)** | CSV/JSONL/TXT: `Input`, `Sentence`, `SQLInjection` (20 files) |
| **`SRC_07`** | [`SRC_07_cse_cic_ids2018`](file:///C:/Users/huynh/Desktop/fedwebpayload/data/raw/SRC_07_cse_cic_ids2018) | Pending (Flow Benchmark) | CSV: 78 CICFlowMeter numerical features + `Label` (10 CSVs) |
| **`SRC_08`** | [`SRC_08_cicids2017`](file:///C:/Users/huynh/Desktop/fedwebpayload/data/raw/SRC_08_cicids2017) | Pending (Flow Benchmark) | CSV: 78 CICFlowMeter numerical features + `Label` (8 CSVs) |
| **`SRC_09`** | [`SRC_09_ecml_pkdd_2007`](file:///C:/Users/huynh/Desktop/fedwebpayload/data/raw/SRC_09_ecml_pkdd_2007) | Pending (Analytical Pool) | XML & raw HTTP request dumps (3 dataset files) |
| **`SRC_10`** | [`SRC_10_sr_bh_2020`](file:///C:/Users/huynh/Desktop/fedwebpayload/data/raw/SRC_10_sr_bh_2020) | **Locked (Holdout Test)** | CSV/ARFF: Multi-label web payload benchmark |
| **`SRC_11`** | [`SRC_11_webspotter_fpad_ood`](file:///C:/Users/huynh/Desktop/fedwebpayload/data/raw/SRC_11_webspotter_fpad_ood) | **Locked (OOD Test)** | JSON/CSV: FPAD out-of-domain web attack corpus |

---

## 2. PathTraversal & SQL Injection Target Row Projections

| Attack Class | Raw Volume Input | Post-Dedup Unique Seeds | Post-Augmentation Count | Target Status |
|---|---|---|---|---|
| **PathTraversal** | ~53,000 | ~3,000 – 5,000 | **~10,000 – 12,000** | 🟢 Perfectly Balanced |
| **SQL Injection** | ~45,000 | ~5,000 – 8,000 | **~10,400 – 12,000** | 🟢 Perfectly Balanced |
| **XSS** | ~44,000 | ~10,400 | **~10,400 – 12,000** | 🟢 Perfectly Balanced |
| **Benign (Normal)** | ~45,000 | ~25,000 – 30,000 | **~25,000 – 30,000** | 🟢 1:1 Benign-to-Malicious Ratio |
| **TOTAL** | **~187,000** | **~43,400 – 53,400** | **~55,800 – 66,000** | 🎯 **Clean Leakage-Free Corpus** |

---

## Verification Plan

```powershell
# 1. Ingest all active raw dataset directories
& "C:\Users\huynh\Desktop\fedwebpayload\.venv\Scripts\python.exe" src/data/ingest.py

# 2. Decode, sanitize & scrub labels with OWASP CRS v4
& "C:\Users\huynh\Desktop\fedwebpayload\.venv\Scripts\python.exe" src/data/decode.py
& "C:\Users\huynh\Desktop\fedwebpayload\.venv\Scripts\python.exe" src/data/sanitize.py

# 3. MinHash dedup with adaptive thresholds (0.88 PathTrav)
& "C:\Users\huynh\Desktop\fedwebpayload\.venv\Scripts\python.exe" src/data/dedup.py

# 4. Fast deterministic augmentation
& "C:\Users\huynh\Desktop\fedwebpayload\.venv\Scripts\python.exe" src/data/augment.py
```
