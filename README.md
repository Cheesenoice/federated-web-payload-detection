# Federated Web Payload Benchmark (`fedwebpayload`)

**A Data-Centric, Leakage-Free Federated Learning System for Web Attack Payload Detection**

[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/release/python-3110/)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.1%2B-orange.svg)](https://pytorch.org/)
[![Flower](https://img.shields.io/badge/Flower-1.32%2B-green.svg)](https://flower.ai/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 📌 Project Overview

`fedwebpayload` is an academic benchmark and federated learning pipeline designed to detect HTTP web attack payloads (**SQL Injection, Cross-Site Scripting, and Path Traversal / LFI**) under Non-IID client distributions.

### Key Innovations & Data-Centric Breakthroughs:
1. **Canonical Multi-Source Data Acquisition (12 Raw Sources `SRC_00` to `SRC_11`):** Ingests real honeypot captures, production WAF audit logs (Lucz 2025), SecLists LFI collections, BWAFSQLi (Zhang 2026), and AdvSQLi (Qu 2024).
2. **OWASP CRS v4 & D19 Mislabel Scrubbing:** Re-evaluates raw labels against OWASP ModSecurity Core Rule Set (v4) and cleans false positive labels on benign numeric/alphanumeric strings.
3. **Dynamic Sandbox Resolution:** Empirically verifies path traversal escapes using Python `os.path.abspath` against a mock web-root directory structure.
4. **Entropy-Adaptive MinHash Deduplication (EDAMT):** Applies class-specific Jaccard thresholds (`0.88` PathTrav, `0.75` SQLi, `0.60` XSS) matching lexical entropy.
5. **Zero Train-Test Leakage Barrier (`dedup_cluster_id`):** Enforces indivisible lineage group IDs. Seed payloads and their mutated variants ALWAYS remain on the exact same side of train/test splits.

---

## 🛠️ Repository Directory Structure

```text
fedwebpayload/
├── data/
│   ├── raw/                 # Raw dataset source directories (SRC_00 to SRC_11)
│   ├── interim/             # Normalized & sanitized intermediate parquets
│   ├── processed/           # Gold-standard trainable corpus (trainable_corpus.parquet)
│   └── DATA_SOURCE_PROVENANCE.md
├── scripts/
│   └── download_data.py     # Automated raw dataset acquisition script
├── src/
│   └── data/
│       ├── ingest.py        # Stage 1: Multi-source raw ingestion
│       ├── decode.py        # Stage 2a: Multi-step URL/HTML/NFKC decode
│       ├── sanitize.py      # Stage 2b: Sensitive token masking
│       ├── label_signatures.py # Stage 3a: OWASP CRS v4 regex engine & D19 scrub
│       ├── sandbox_verify.py   # Stage 3b: Dynamic sandbox escape verification
│       ├── dedup.py         # Stage 4: Adaptive MinHash LSH deduplication
│       └── augment.py       # Stage 5: Deterministic semantic mutations (M1-M8)
├── plan/                    # Academic execution plans & specifications
├── README.md
└── .gitignore
```

---

## 🚀 Quickstart Guide

### 1. Environment Setup

```bash
# Clone repository
git clone https://github.com/your-username/fedwebpayload.git
cd fedwebpayload

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Download Raw Datasets

Run the automated data acquisition script to fetch raw dataset mirrors into `data/raw/`:

```bash
python scripts/download_data.py
```

### 3. Execute Data Processing Pipeline

Run the 5-stage data-centric processing pipeline to generate the clean, leakage-free `trainable_corpus.parquet`:

```bash
# Stage 1: Ingest multi-source raw payload logs
python src/data/ingest.py

# Stage 2: Decode & sanitize payloads
python src/data/decode.py
python src/data/sanitize.py

# Stage 3 & 4: CRS label scrubbing & Entropy-Adaptive MinHash deduplication
python src/data/dedup.py

# Stage 5: Fast deterministic semantic augmentation (Rules M1-M8)
python src/data/augment.py
```

### 4. Inspect Final Trainable Corpus

```bash
python -c "import pandas as pd; df=pd.read_parquet('data/processed/trainable_corpus.parquet'); print(df['label_multiclass'].value_counts())"
```

---

## 📊 Trainable Corpus Statistics

| Attack Class (`label_multiclass`) | Trainable Rows | Balance Status |
|---|---|---|
| **PathTraversal (`pathtrav`)** | **34,387** | 🟢 High-Volume Sandbox Verified |
| **Benign (Normal Traffic)** | **25,000** | 🟢 Balanced (1:3 Attack Ratio) |
| **SQL Injection (`sqli`)** | **25,000** | 🟢 OWASP CRS v4 & D16 Scrubbed |
| **Cross-Site Scripting (`xss`)** | **24,240** | 🟢 Lineage Group Deduplicated |
| **TOTAL TRAINABLE CORPUS** | **108,627** | 🎯 **100% LEAKAGE-FREE & BALANCED** |

---

## 📜 License & Provenance

All raw datasets belong to their respective academic authors as documented in [`data/DATA_SOURCE_PROVENANCE.md`](data/DATA_SOURCE_PROVENANCE.md). The codebase is licensed under the MIT License.
