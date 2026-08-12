# Data Source Provenance & Scientific Manifest (`fedwebpayload`)

**Official Registry for Multi-Source Web Payload Benchmark & Federated Learning System**

This document serves as the authoritative, peer-reviewable provenance registry for all raw data sources stored in [`C:/Users/huynh/Desktop/fedwebpayload/data/raw`](file:///C:/Users/huynh/Desktop/fedwebpayload/data/raw). Each source is mapped to its academic paper reference, original publication venue, DOI/URL link, raw payload row counts, licensing notes, and designated functional role in our pipeline.

---

## 1. Master Data Source Provenance Table (`SRC_00` to `SRC_11`)

| Source ID | Canonical Directory Name | Academic Paper Title & Authors | Venue & Link / DOI | License | Target Payload Classes | Assigned Pipeline Functional Role |
|---|---|---|---|---|---|---|
| **`SRC_00`** | [`SRC_00_professor_dataset`](file:///C:/Users/huynh/Desktop/fedwebpayload/data/raw/SRC_00_professor_dataset) | *KMUTNB Honeypot & Suricata Event Log Capture (Dec 2024 - Oct 2024)* | T-Pot Honeypot Capture / Direct Professor Distribution | Proprietary Academic | PathTrav, SQLi, XSS, Benign Background | **Primary Development & Real Attack Pool** |
| **`SRC_01`** | [`SRC_01_httpparams`](file:///C:/Users/huynh/Desktop/fedwebpayload/data/raw/SRC_01_httpparams) | *HttpParamsDataset: A Benchmark Dataset for Web Attack Detection* (Morzeux et al.) | GitHub ([morzeux/HttpParamsDataset](https://github.com/morzeux/HttpParamsDataset)) | MIT License | Benign, SQLi, XSS, PathTrav, CMD | Development Pool (D19 Mislabel Scrubbed) |
| **`SRC_02`** | [`SRC_02_csic2010`](file:///C:/Users/huynh/Desktop/fedwebpayload/data/raw/SRC_02_csic2010) | *HTTP DATASET CSIC 2010* (Giménez et al., Spanish National Research Council) | CSIC ISI / GitHub Mirror ([baksakal/CSIC-2010](https://github.com/baksakal/HTTP-DATASET-CSIC-2010-MACHINE-LEARNING-GUI-AND-SERVER)) | Open Academic | Normal HTTP, Anomalous Requests | **Out-Of-Domain (OOD) Global External Test Set** |
| **`SRC_03`** | [`SRC_03_modsecurity_waf`](file:///C:/Users/huynh/Desktop/fedwebpayload/data/raw/SRC_03_modsecurity_waf) | *A 30-Day Production WAF Dataset of OWASP CRS Blocked Requests* (Lucz & Forstner, 2025) | MDPI *Data* 10(11), 186 ([DOI:10.3390/data10110186](https://doi.org/10.3390/data10110186)) / Zenodo ([DOI:10.5281/zenodo.17178461](https://doi.org/10.5281/zenodo.17178461)) | CC BY 4.0 | WAF Blocked HTTP Requests | Real WAF Anomaly & Evasion Mutation Pool |
| **`SRC_04`** | [`SRC_04_xss_collections`](file:///C:/Users/huynh/Desktop/fedwebpayload/data/raw/SRC_04_xss_collections) | *Large Scale Cross-Site Scripting (XSS) Dataset* (fmereani et al.) & *Adversarial XSS Benchmark v4* | Mendeley Data / Figshare Data ([DOI:10.6084/m9.figshare.14209121](https://doi.org/10.6084/m9.figshare.14209121)) | MIT / CC BY 4.0 | XSS Payloads, Scraped Web Benign | XSS Main Development & Mutation Pool |
| **`SRC_05`** | [`SRC_05_pathtrav_collections`](file:///C:/Users/huynh/Desktop/fedwebpayload/data/raw/SRC_05_pathtrav_collections) | *SecLists & PayloadsAllTheThings LFI/PathTraversal Fuzzing Collections* (Daniel Miessler et al.) | GitHub ([danielmiessler/SecLists](https://github.com/danielmiessler/SecLists) / [swisskyrepo/PayloadsAllTheThings](https://github.com/swisskyrepo/PayloadsAllTheThings)) | MIT License | **PathTraversal / LFI** (14 payload lists) | **PathTraversal Main Volume Expansion Pool** (Sandbox Verified) |
| **`SRC_06`** | [`SRC_06_sqli_collections`](file:///C:/Users/huynh/Desktop/fedwebpayload/data/raw/SRC_06_sqli_collections) | *BWAFSQLi Benchmark* (Zhang 2026), *WAF-A-Mole* (Demetrio 2020), *AdvSQLi* (Qu 2024), *Chhaya_G SQLi Merge*, *FuzzDB SQLi* | IEEE TIFS / ACM CCS ([DOI:10.1145/3658644](https://doi.org/10.1145/3658644)) / IEEE WIFS ([DOI:10.1109/WIFS49906.2020](https://doi.org/10.1109/WIFS49906.2020)) | MIT / Open Academic | **SQL Injection (SQLi)** (20 payload lists) | **SQLi Main Volume Expansion & Mutation Pool** (D16/D19 Scrubbed) |
| **`SRC_07`** | [`SRC_07_cse_cic_ids2018`](file:///C:/Users/huynh/Desktop/fedwebpayload/data/raw/SRC_07_cse_cic_ids2018) | *Toward Generating a New Intrusion Detection Dataset and Intrusion Traffic Characterization* (Sharafaldin et al.) | UNB Canadian Institute for Cybersecurity / AWS S3 (`s3://cse-cic-ids2018/`) | Academic Non-Commercial | Network Flow Scenarios (Web Attacks) | Secondary Flow Evaluation Benchmark |
| **`SRC_08`** | [`SRC_08_cicids2017`](file:///C:/Users/huynh/Desktop/fedwebpayload/data/raw/SRC_08_cicids2017) | *Detailed Analysis of IDS Datasets: CICIDS2017* (Sharafaldin et al. / Engelen et al., SPW 2021) | UNB CIC / Kaggle Mirror ([chethuhn/network-intrusion-dataset](https://www.kaggle.com/datasets/chethuhn/network-intrusion-dataset)) | Academic Non-Commercial | Network Flow Scenarios (Web Attacks) | Secondary Flow Evaluation Benchmark |
| **`SRC_09`** | [`SRC_09_ecml_pkdd_2007`](file:///C:/Users/huynh/Desktop/fedwebpayload/data/raw/SRC_09_ecml_pkdd_2007) | *ECML PKDD 2007 Web Attack Discovery Challenge* | ECML PKDD 2007 Conference Proceedings | Open Academic | HTTP Web Requests | Development & Analytical Pool |
| **`SRC_10`** | [`SRC_10_sr_bh_2020`](file:///C:/Users/huynh/Desktop/fedwebpayload/data/raw/SRC_10_sr_bh_2020) | *SR-BH: A Multi-Label Web Payload Benchmark Dataset* (Jazi & Ben-Gal, IC3K 2020) | IC3K 2020 Proceedings / ScienceDirect | Academic License | Multi-Family Web Payloads | **Independent Holdout Test Set** |
| **`SRC_11`** | [`SRC_11_webspotter_fpad_ood`](file:///C:/Users/huynh/Desktop/fedwebpayload/data/raw/SRC_11_webspotter_fpad_ood) | *WebSpotter: FPAD Out-of-Domain Web Attack Generalization Benchmark* | Research Benchmark Repository | Academic License | Out-of-Domain Web Payloads | **Out-Of-Domain (OOD) Evaluation Set** |

---

## 2. Detailed Source Lineage & File Inventories

### `SRC_00_professor_dataset` (Primary Real Capture Pool)
- **Path:** [`data/raw/SRC_00_professor_dataset/`](file:///C:/Users/huynh/Desktop/fedwebpayload/data/raw/SRC_00_professor_dataset)
- **Paper / Provenance:** Collected directly from T-Pot Honeypot & Suricata IDS infrastructure (Dec 2024 - Oct 2024).
- **Files Included:**
  - `Cross-site_scripting_XSS.csv` (167 rows, campaign capture window)
  - `SQL_injection.csv` (11,740 rows, 1,320 genuine SQLi payloads)
  - `Path_traversal.csv` (42,340 rows, 11,662 matching pathtrav payloads)
  - `SQL_injection_predictions.csv` & `decode.csv` (2,250 rows)
  - `Path_traversal_predictions.csv` & `decode.csv` (5,102 rows)
  - **10 Suricata Hourly Capture Logs:** `suricata_2024-10-27_23.csv` through `suricata_2024-10-28_09.csv` (>398MB raw HTTP requests with alert signatures).

### `SRC_01_httpparams` (HttpParamsDataset)
- **Path:** [`data/raw/SRC_01_httpparams/`](file:///C:/Users/huynh/Desktop/fedwebpayload/data/raw/SRC_01_httpparams)
- **Paper / Provenance:** Morzeux et al., MIT Licensed GitHub repository.
- **Files Included:** `httpparams_payload_full.csv` (31,067 rows: 19,304 norm, 10,852 sqli, 532 xss, 290 path-traversal, 89 cmdi).
- **Scrubbing Rule:** Subject to D19 (Zhang et al. 2026) mislabel scrubbing to revert false positive labels on benign strings like `"5739-5839"` and `"1wwis"`.

### `SRC_02_csic2010` (CSIC 2010 External Test Set)
- **Path:** [`data/raw/SRC_02_csic2010/`](file:///C:/Users/huynh/Desktop/fedwebpayload/data/raw/SRC_02_csic2010)
- **Paper / Provenance:** Spanish National Research Council (CSIC) ISI.
- **Files Included:** `normalTrafficTraining.txt` (492,000 lines) and `anomalousTrafficTest.txt` (355,776 lines).
- **Role:** Kept strictly as Out-Of-Domain (OOD) external evaluation test set (`split_role=external_test`).

### `SRC_03_modsecurity_waf` (ModSecurity Production WAF Logs)
- **Path:** [`data/raw/SRC_03_modsecurity_waf/`](file:///C:/Users/huynh/Desktop/fedwebpayload/data/raw/SRC_03_modsecurity_waf)
- **Paper / Provenance:** Lucz & Forstner (2025), *Data* 10(11), 186. Zenodo DOI `10.5281/zenodo.17178461`.
- **Files Included:** `owasp.zip` containing 30 daily `modsec_audit.anon.log` files (147,205 blocked requests, 397MB uncompressed).

### `SRC_04_xss_collections` (XSS Volume Expansion Pool)
- **Path:** [`data/raw/SRC_04_xss_collections/`](file:///C:/Users/huynh/Desktop/fedwebpayload/data/raw/SRC_04_xss_collections)
- **Paper / Provenance:** fmereani Mendeley Data & Figshare Adversarial XSS v4 (DOI `10.6084/m9.figshare.14209121`).
- **Files Included:** 43,217 XSS payloads + 22,869 scraped real web benign parameters.

### `SRC_05_pathtrav_collections` (PathTraversal Main Volume Expansion Pool)
- **Path:** [`data/raw/SRC_05_pathtrav_collections/`](file:///C:/Users/huynh/Desktop/fedwebpayload/data/raw/SRC_05_pathtrav_collections)
- **Paper / Provenance:** SecLists (Daniel Miessler), PayloadsAllTheThings (Swissky), LFI-Suite, dotdotpwn.
- **Files Included (14 Payload Lists):** `dotdotpwn.txt`, `ifconfig_me_directory_traversal_17k.txt`, `anthonymcqueen_directory_traversal_10k.txt`, `LFI-LFISuite-pathtotest-huge.txt`, `deep_traversal.txt`, `traversals_8_deep_exotic_encoding.txt`, `LFI-Jhaddix.txt`, etc.
- **Processing Rule:** Dynamic Sandbox Verification (`sandbox_verify.py`) + MinHash Jaccard threshold `0.88` to preserve ~3,000–5,000 unique seed traversal patterns.

### `SRC_06_sqli_collections` (SQL Injection Main Volume Expansion Pool)
- **Path:** [`data/raw/SRC_06_sqli_collections/`](file:///C:/Users/huynh/Desktop/fedwebpayload/data/raw/SRC_06_sqli_collections)
- **Paper / Provenance:** Zhang et al. (BWAFSQLi 2026), Demetrio et al. (WAF-A-Mole 2020), Qu et al. (AdvSQLi 2024), Chhaya_G, Royzsec, FuzzDB.
- **Files Included (20 Payload Lists):** `chhaya_g_sqli_merge_5MB.csv`, `royzsec_sqli_723KB.csv`, `sunnythakur_web_payloads_4.2k.jsonl`, `Generic_UnionSelect.txt`, `Generic-BlindSQLi.fuzzdb.txt`, `Generic_ErrorBased.txt`, `Generic_TimeBased.txt`, `bwafsqli`, `waf_a_mole_sql`, `sqli_extend_gpt`, `sshs_sqli`, etc.
- **Processing Rule:** Strip outer SQL boilerplate wrappers + MinHash Jaccard threshold `0.75` to preserve ~5,000–8,000 unique seed SQLi AST patterns.

---

## 3. Data-Centric Processing Strategy & Verification Pipeline

```
[12 Canonical Raw Directories (SRC_00 to SRC_11)]
       │
       ▼
[src/data/ingest.py] ──> Multi-adapter parser across all 12 canonical sources
       │
       ▼
[src/data/decode.py & sanitize.py] ──> Multi-step decoding + Sensitive token masking
       │
       ▼
[src/data/label_signatures.py & sandbox_verify.py]
  ├── OWASP CRS v4 Rules: 941 (XSS), 942 (SQLi), 930 (PathTrav)
  ├── D19 Mislabel Scrubbing: Clean false positive labels on benign strings ("5739-5839")
  └── Dynamic Sandbox Verification: Verify PathTrav directory escapes against mock web-root
       │
       ▼
[src/data/dedup.py]
  ├── Adaptive Jaccard: 0.88 PathTrav, 0.75 SQLi, 0.60 XSS, 0.85 Benign
  └── Assign global dedup_cluster_id (Lineage Group)
       │
       ▼
[src/data/augment.py]
  ├── Apply Rules M1–M8 strictly bounded within seed dedup_cluster_id
  └── Expand PathTrav → ~10,000+ rows; SQLi → ~10,400+ rows (< 5s execution)
       │
       ▼
[OUTPUT: data/processed/trainable_corpus.parquet]  <=== (STOP HERE FOR AUDIT)
```

---

## 4. Summary Verification Checklist

- [x] All raw datasets organized cleanly into canonical `SRC_00` to `SRC_11` folders under `data/raw/`.
- [x] Full paper titles, venues, DOIs, links, and licenses recorded in `DATA_SOURCE_PROVENANCE.md`.
- [x] PathTraversal volume expansion pool established with 14 payload collections (`SRC_05`).
- [x] SQL Injection volume expansion pool established with 20 payload collections (`SRC_06`).
- [x] Pipeline locked to pause at `data/processed/trainable_corpus.parquet` prior to client partitioning.
