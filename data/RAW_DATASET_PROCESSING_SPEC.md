# Raw Dataset Directory Tree & Processing Specification (`fedwebpayload`)

**Canonical Data Pipeline Specification for All 12 Raw Source Directories (`SRC_00` through `SRC_11`)**

This document specifies the exact directory tree, file contents, format columns, processing status, and extraction rules for every raw dataset subfolder under [`C:/Users/huynh/Desktop/fedwebpayload/data/raw`](file:///C:/Users/huynh/Desktop/fedwebpayload/data/raw).

---

## 1. Global Processing Status Dashboard

| Source ID | Directory Name | Data Modality & Format | Total Files | Processing Status | Output Target |
|---|---|---|---|---|---|
| **`SRC_00`** | [`SRC_00_professor_dataset`](file:///C:/Users/huynh/Desktop/fedwebpayload/data/raw/SRC_00_professor_dataset) | CSV (Event logs + 10 hourly Suricata captures) | 17 files | **Active Ingestion** | `unified.parquet` |
| **`SRC_01`** | [`SRC_01_httpparams`](file:///C:/Users/huynh/Desktop/fedwebpayload/data/raw/SRC_01_httpparams) | CSV (Parameter payloads) | 1 file | **Completed** | `unified.parquet` |
| **`SRC_02`** | [`SRC_02_csic2010`](file:///C:/Users/huynh/Desktop/fedwebpayload/data/raw/SRC_02_csic2010) | Raw HTTP Dumps (.txt) | 2 files | **Completed (OOD Test)** | `external_csic2010.parquet` |
| **`SRC_03`** | [`SRC_03_modsecurity_waf`](file:///C:/Users/huynh/Desktop/fedwebpayload/data/raw/SRC_03_modsecurity_waf) | ModSec Audit Logs (.log) + JSON | 30 daily logs + JSON | **Active Ingestion** | `unified.parquet` |
| **`SRC_04`** | [`SRC_04_xss_collections`](file:///C:/Users/huynh/Desktop/fedwebpayload/data/raw/SRC_04_xss_collections) | CSV (XSS Payloads + Scraped Benign) | 4 CSV files | **Active Ingestion** | `unified.parquet` |
| **`SRC_05`** | [`SRC_05_pathtrav_collections`](file:///C:/Users/huynh/Desktop/fedwebpayload/data/raw/SRC_05_pathtrav_collections) | TXT (PathTraversal & LFI lists) | 14 TXT files | **Active Ingestion (Sandbox Verified)** | `unified.parquet` |
| **`SRC_06`** | [`SRC_06_sqli_collections`](file:///C:/Users/huynh/Desktop/fedwebpayload/data/raw/SRC_06_sqli_collections) | CSV, JSONL, TXT (SQLi Payloads) | 20 files | **Active Ingestion (D16/D19 Scrubbed)** | `unified.parquet` |
| **`SRC_07`** | [`SRC_07_cse_cic_ids2018`](file:///C:/Users/huynh/Desktop/fedwebpayload/data/raw/SRC_07_cse_cic_ids2018) | CSV (Network Flow scenarios) | 10 CSV files | Pending (Flow Benchmark) | `flow_ids2018.parquet` |
| **`SRC_08`** | [`SRC_08_cicids2017`](file:///C:/Users/huynh/Desktop/fedwebpayload/data/raw/SRC_08_cicids2017) | CSV (Network Flow scenarios) | 8 CSV files | Pending (Flow Benchmark) | `flow_ids2017.parquet` |
| **`SRC_09`** | [`SRC_09_ecml_pkdd_2007`](file:///C:/Users/huynh/Desktop/fedwebpayload/data/raw/SRC_09_ecml_pkdd_2007) | XML & Raw Request Dumps | 3 dataset files | Pending (Analytical Pool) | `interim_ecml.parquet` |
| **`SRC_10`** | [`SRC_10_sr_bh_2020`](file:///C:/Users/huynh/Desktop/fedwebpayload/data/raw/SRC_10_sr_bh_2020) | CSV / ARFF Payload Benchmark | 2 files | **Locked (Holdout Test Set)** | `holdout_srbh2020.parquet` |
| **`SRC_11`** | [`SRC_11_webspotter_fpad_ood`](file:///C:/Users/huynh/Desktop/fedwebpayload/data/raw/SRC_11_webspotter_fpad_ood) | JSON / CSV Payload Corpus | 2 files | **Locked (OOD Test Set)** | `ood_webspotter.parquet` |

---

## 2. Directory Trees & Column Specifications (Folder by Folder)

---

### 📂 `SRC_00_professor_dataset`
- **Location:** [`data/raw/SRC_00_professor_dataset/`](file:///C:/Users/huynh/Desktop/fedwebpayload/data/raw/SRC_00_professor_dataset)
- **Status:** **Active Ingestion**

```
SRC_00_professor_dataset/
├── Cross-site_scripting_XSS.csv       (276 KB, 167 campaign log rows)
├── SQL_injection.csv                  (73.0 MB, 11,740 campaign log rows)
├── Path_traversal.csv                 (165.5 MB, 42,340 campaign log rows)
├── SQL_injection_predictions.csv      (5.0 MB, 2,250 rows)
├── SQL_injection_predictions_decode.csv (2.2 MB, 2,250 rows)
├── Path_traversal_predictions.csv     (2.5 MB, 5,102 rows)
├── Path_traversal_predictions_decode.csv (1.1 MB, 5,102 rows)
└── Suricata Hourly Log Captures (10 files, >398 MB):
    ├── suricata_2024-10-27_23.csv
    ├── suricata_2024-10-28_00.csv
    ├── suricata_2024-10-28_01.csv
    ├── suricata_2024-10-28_02.csv
    ├── suricata_2024-10-28_03.csv
    ├── suricata_2024-10-28_04.csv
    ├── suricata_2024-10-28_05.csv
    ├── suricata_2024-10-28_06.csv
    ├── suricata_2024-10-28_07.csv
    ├── suricata_2024-10-28_08.csv
    └── suricata_2024-10-28_09.csv
```

#### Column Mapping & Extraction Specification
- **Event Log CSVs (`Path_traversal.csv`, `SQL_injection.csv`, `Cross-site_scripting_XSS.csv`):**
  - **Key Columns:** `@timestamp`, `app_proto`, `dest_ip`, `src_ip`, `http` (nested dictionary / JSON string containing `url`, `method`, `user_agent`), `payload_printable` (Base64 or printable raw HTTP POST body).
  - **Payload Extraction Rules:**
    1. If `app_proto` == `http` and `http.url` exists: Extract parameter string from `http.url`.
    2. If POST body exists in `payload_printable`: Decode Base64 and extract raw request body text.
    3. Labeling: Run OWASP CRS v4 regex signature matching (`label_signatures.py`) on payload text. Do NOT assign label by campaign filename alone.
- **Suricata Hourly Logs (`suricata_2024-10-28_*.csv`):**
  - **Key Columns:** `@timestamp`, `payload`, `payload_printable`, `src_ip`, `alert.signature`, `alert.category`.
  - **Extraction Rules:** Extract `payload_printable` string. Cross-check `alert.signature` with OWASP CRS v4 regex matching.

---

### 📂 `SRC_01_httpparams`
- **Location:** [`data/raw/SRC_01_httpparams/`](file:///C:/Users/huynh/Desktop/fedwebpayload/data/raw/SRC_01_httpparams)
- **Status:** **Completed**

```
SRC_01_httpparams/
└── httpparams_payload_full.csv        (2.0 MB, 31,067 rows)
```

#### Column Mapping & Extraction Specification
- **Columns:** `payload` (string), `length` (int), `attack_type` (string: `norm`, `sqli`, `xss`, `path-traversal`, `cmdi`), `label` (int: 0 binary benign, 1 malicious).
- **Processing Rule:** Direct column mapping (`raw_payload = payload`, `label_multiclass = attack_type`). Apply D19 (Zhang et al. 2026) mislabel scrubbing to revert false positive labels on benign strings (e.g. `"5739-5839"` and `"1wwis"`).

---

### 📂 `SRC_02_csic2010`
- **Location:** [`data/raw/SRC_02_csic2010/`](file:///C:/Users/huynh/Desktop/fedwebpayload/data/raw/SRC_02_csic2010)
- **Status:** **Completed (Out-of-Domain External Test Set)**

```
SRC_02_csic2010/
├── normalTrafficTraining.txt          (20.6 MB, 492,000 lines raw HTTP)
└── anomalousTrafficTest.txt           (16.1 MB, 355,776 lines raw HTTP)
```

#### Column Mapping & Extraction Specification
- **Format:** Raw multi-line HTTP request dumps separated by blank lines.
- **Processing Rule:** Parse HTTP GET URL parameters and POST request body strings. Assign `split_role = external_test` (never touched during local client training or tuning).

---

### 📂 `SRC_03_modsecurity_waf`
- **Location:** [`data/raw/SRC_03_modsecurity_waf/`](file:///C:/Users/huynh/Desktop/fedwebpayload/data/raw/SRC_03_modsecurity_waf)
- **Status:** **Active Ingestion**

```
SRC_03_modsecurity_waf/
├── 30 Daily Log Subdirectories (27-Jul-2025 to 25-Aug-2025):
│   └── modsec_audit.anon.log          (397 MB uncompressed total, 147,205 requests)
└── modsec_learn_dataset/
    ├── legitimate/openappsec/legitimate_1..6.json (225 MB JSON)
    └── malicious/sqli_kaggle, sqlmap, openappsec/ (10.5 MB JSON)
```

#### Column Mapping & Extraction Specification
- **Audit Logs (`modsec_audit.anon.log`):** Section A (Header), Section B (Request Headers + URI), Section C (POST body), Section H (Audit Trailer / Rule ID tags).
- **Extraction Rules:** Extract URI parameter text from Section B and POST request body from Section C. Parse Section H ModSecurity Rule IDs (e.g. Rule 941, 942, 930) for ground-truth labeling.

---

### 📂 `SRC_04_xss_collections`
- **Location:** [`data/raw/SRC_04_xss_collections/`](file:///C:/Users/huynh/Desktop/fedwebpayload/data/raw/SRC_04_xss_collections)
- **Status:** **Active Ingestion**

```
SRC_04_xss_collections/
├── xss_fmereani_payloads_full.csv     (19.1 MB, 43,217 rows)
├── 1/xss_dataset.csv                  (185.6 MB, Query + Label columns)
└── 4/XSS_dataset1_engineered.csv      (64.2 MB, engineered features)
```

#### Column Mapping & Extraction Specification
- **`xss_fmereani_payloads_full.csv`:** `Payloads` (string), `Class` (int: 0 benign, 1 XSS).
- **`1/xss_dataset.csv`:** `Query` (string payload), `Label` (int: 0 benign, 1 XSS).
- **Extraction Rules:** Extract `Payloads` and `Query` strings. Apply OWASP CRS v4 Rule 941 regex verification.

---

### 📂 `SRC_05_pathtrav_collections`
- **Location:** [`data/raw/SRC_05_pathtrav_collections/`](file:///C:/Users/huynh/Desktop/fedwebpayload/data/raw/SRC_05_pathtrav_collections)
- **Status:** **Active Ingestion (Sandbox Verified)**

```
SRC_05_pathtrav_collections/ (14 Payload Text Lists, >4.8 MB total):
├── anthonymcqueen_directory_traversal_10k.txt (565 KB)
├── deepakghengat_directory_traversal_1.6k.txt (57 KB)
├── deep_traversal.txt                         (70 KB)
├── directory_traversal.txt                    (9 KB)
├── dotdotpwn.txt                              (1.87 MB)
├── ifconfig_me_directory_traversal_17k.txt    (1.05 MB)
├── LFI-Jhaddix.txt                            (33 KB)
├── LFI-LFISuite-pathtotest-huge.txt           (503 KB)
├── LFI-LFISuite-pathtotest.txt                (22 KB)
├── LFI-linux-and-windows_CrowdShield.txt      (32 KB)
├── seclists_lfi_huge.txt                      (503 KB)
├── seclists_lfi_jhaddix.txt                   (33 KB)
├── seclists_lfi_linux_windows.txt             (32 KB)
└── traversals_8_deep_exotic_encoding.txt      (70 KB)
```

#### Column Mapping & Extraction Specification
- **Format:** One raw traversal payload string per line (`.txt`).
- **Processing & Sandbox Verification Rule:**
  1. Read line-by-line.
  2. Pass candidate string to `sandbox_verify.py` against a mock filesystem root.
  3. If `os.path.abspath()` demonstrably escapes root, assign `label_multiclass = PathTrav`.
  4. Apply MinHash deduplication with adaptive threshold `J_t = 0.88`.

---

### 📂 `SRC_06_sqli_collections`
- **Location:** [`data/raw/SRC_06_sqli_collections/`](file:///C:/Users/huynh/Desktop/fedwebpayload/data/raw/SRC_06_sqli_collections)
- **Status:** **Active Ingestion (D16/D19 Scrubbed)**

```
SRC_06_sqli_collections/ (20 Files & Subdirectories, >165 MB total):
├── chhaya_g_sqli_merge_5MB.csv        (5.2 MB, Input + label)
├── royzsec_sqli_723KB.csv             (723 KB, UTF-8/Latin-1 encoded CSV)
├── sunnythakur_web_payloads_4.2k.jsonl(164 KB, JSONL payloads)
├── sqli-extended.csv                  (50.6 MB, Sentence + Label)
├── SQLInjection_XSS_MixDataset.csv   (57.8 MB, Sentence + SQLInjection + XSS + Normal)
├── SQLInjection_XSS_CommandInjection_MixDataset.csv (98.0 MB)
├── SQLiV3.csv                         (2.3 MB, Sentence + Label)
├── BWAFSQLi-214d976a04d241c6.../       (BWAFSQLi paper dataset - Zhang 2026)
├── FuzzDB SQLi Collections:
│   ├── Generic_UnionSelect.txt        (37 KB)
│   ├── Generic-BlindSQLi.fuzzdb.txt   (1 KB)
│   ├── Generic_ErrorBased.txt         (3 KB)
│   ├── Generic_TimeBased.txt          (2.5 KB)
│   ├── Auth_Bypass.txt                (1.2 KB)
│   ├── MSSQL.fuzzdb.txt, MySQL.fuzzdb.txt, oracle-payloads.txt, postgresql-payloads.txt
```

#### Column Mapping & Extraction Specification
- **CSVs (`chhaya_g_sqli_merge_5MB.csv`, `sqli-extended.csv`, `SQLiV3.csv`):** Extract `Input` or `Sentence` text column and binary/multiclass label column.
- **Mix Datasets (`SQLInjection_XSS_MixDataset.csv`):** Parse binary flags (`SQLInjection==1`, `XSS==1`, `Normal==1`).
- **Processing Rule:** Apply D16/D19 boilerplate scrubbing to strip outer SQL wrappers. Apply MinHash deduplication with adaptive threshold `J_t = 0.75`.

---

### 📂 `SRC_07_cse_cic_ids2018` & `SRC_08_cicids2017`
- **Locations:** [`data/raw/SRC_07_cse_cic_ids2018/`](file:///C:/Users/huynh/Desktop/fedwebpayload/data/raw/SRC_07_cse_cic_ids2018) & [`data/raw/SRC_08_cicids2017/`](file:///C:/Users/huynh/Desktop/fedwebpayload/data/raw/SRC_08_cicids2017)
- **Status:** **Pending (Secondary Network-Flow Benchmark)**

```
SRC_07_cse_cic_ids2018/ (10 CSV files, 6.41 GB total network flow features)
SRC_08_cicids2017/      (8 CSV files, 885 MB total network flow features)
```

#### Column Mapping Specification
- **Columns:** 78 CICFlowMeter numerical features (`FlowDuration`, `TotalFwd_Packets`, `DestinationPort`, etc.) + `Label` column (`Web Attack - SQL Injection`, `Web Attack - XSS`, `Benign`).
- **Processing Rule:** Maintained as a separate network-flow feature benchmark. Kept isolated from `unified.parquet` payload text table.

---

### 📂 `SRC_09_ecml_pkdd_2007`
- **Location:** [`data/raw/SRC_09_ecml_pkdd_2007/`](file:///C:/Users/huynh/Desktop/fedwebpayload/data/raw/SRC_09_ecml_pkdd_2007)
- **Status:** **Pending (Analytical Pool)**

```
SRC_09_ecml_pkdd_2007/
└── dataset_ecml_pkdd_train_test XML & raw request dumps
```

#### Column Mapping Specification
- **Format:** XML formatted HTTP web request logs. Extract HTTP URI parameters and POST body text.

---

### 📂 `SRC_10_sr_bh_2020` & `SRC_11_webspotter_fpad_ood`
- **Locations:** [`data/raw/SRC_10_sr_bh_2020/`](file:///C:/Users/huynh/Desktop/fedwebpayload/data/raw/SRC_10_sr_bh_2020) & [`data/raw/SRC_11_webspotter_fpad_ood/`](file:///C:/Users/huynh/Desktop/fedwebpayload/data/raw/SRC_11_webspotter_fpad_ood)
- **Status:** **Locked (Independent Holdout & OOD Test Sets)**

```
SRC_10_sr_bh_2020/             (SR-BH multi-label web payload benchmark CSV/ARFF)
SRC_11_webspotter_fpad_ood/    (WebSpotter FPAD out-of-domain benchmark JSON/CSV)
```

#### Processing Rule
- Kept strictly as locked test sets. Zero overlap with training sets (`test_leakage` green).

---

## 3. Sequential Execution Workflow

```powershell
# Step 1: Multi-source ingestion & extraction across active folders
& "C:\Users\huynh\Desktop\fedwebpayload\.venv\Scripts\python.exe" src/data/ingest.py

# Step 2: Decoding, sanitization & OWASP CRS v4 scrubbing
& "C:\Users\huynh\Desktop\fedwebpayload\.venv\Scripts\python.exe" src/data/decode.py
& "C:\Users\huynh\Desktop\fedwebpayload\.venv\Scripts\python.exe" src/data/sanitize.py

# Step 3: Adaptive MinHash deduplication (0.88 PathTrav, 0.75 SQLi)
& "C:\Users\huynh\Desktop\fedwebpayload\.venv\Scripts\python.exe" src/data/dedup.py

# Step 4: Fast deterministic semantic augmentation
& "C:\Users\huynh\Desktop\fedwebpayload\.venv\Scripts\python.exe" src/data/augment.py
```
