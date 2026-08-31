# 🚀 Stage 1 Execution & Run Guide

This guide provides step-by-step instructions to run the Stage 1 Data Foundation pipeline from raw data to the final 6-client partitioned datasets.

---

## 📋 Prerequisites
Ensure the virtual environment is activated and dependencies are installed:
```powershell
& "C:\Users\huynh\Desktop\fedwebpayload\.venv\Scripts\python.exe" -m pip install pandas numpy pyarrow fastparquet joblib scikit-learn
```

---

## ⚡ Sequential Execution Instructions

### Step 1: Ingestion, Decoding & Sanitization
Scans 8 raw data sources (`SRC_00` to `SRC_07`), applies 3-pass URL decoding, masks PII/Tokens/UUIDs, and computes SHA-256 hashes.
```powershell
& "C:\Users\huynh\Desktop\fedwebpayload\.venv\Scripts\python.exe" C:\Users\huynh\Desktop\fedwebpayload\src\stage_01_data_foundation\1.1_data_ingest_and_hash.py
```
*Output:* `data/interim/manifest_stage1.parquet` (5,325,763 rows).

---

### Step 2: Global Exact Deduplication
Clusters identical `sanitized_hash` payloads to identify primary unique representatives and eliminate duplicates.
```powershell
& "C:\Users\huynh\Desktop\fedwebpayload\.venv\Scripts\python.exe" C:\Users\huynh\Desktop\fedwebpayload\src\stage_01_data_foundation\1.2_global_dedup_and_cluster.py
```
*Output:* `data/interim/manifest_stage2.parquet` (3,873,805 unique clusters).

---

### Step 3: OWASP CRS v4 Consensus Audit
Evaluates unique clusters against WAF regex signatures (`1.3.1_label_signatures.py`) to confirm labels and flag ambiguous records.
```powershell
& "C:\Users\huynh\Desktop\fedwebpayload\.venv\Scripts\python.exe" C:\Users\huynh\Desktop\fedwebpayload\src\stage_01_data_foundation\1.3_label_consensus_audit.py
```
*Output:* `data/processed/sample_manifest.parquet` (2,794,288 confirmed clusters).

---

### Step 4: Per-Source Data Balance Accounting
Generates comprehensive ingestion matrices and label distribution tables.
```powershell
& "C:\Users\huynh\Desktop\fedwebpayload\.venv\Scripts\python.exe" C:\Users\huynh\Desktop\fedwebpayload\src\stage_01_data_foundation\1.4_generate_accounting_report.py
```
*Outputs:* `data/processed/data_accounting.csv`, `data/processed/source_label_accounting.csv`.

---

### Step 5: Two-Tier Stratified Pool Split (15% Pool A / 85% Pool B / OOD)
Partitions confirmed unique clusters into Pool A (Base pretraining), Pool B (Federated silos), and isolates OOD CSIC 2010.
```powershell
& "C:\Users\huynh\Desktop\fedwebpayload\.venv\Scripts\python.exe" C:\Users\huynh\Desktop\fedwebpayload\src\stage_01_data_foundation\1.5_pool_split.py
```
*Output:* Updated `sample_manifest.parquet` with `pool_id`.

---

### Step 6: Build Pool A Balanced Pre-Training Corpus (M1–M8 Mutations)
Applies 8 semantic mutation rules to expand minority seeds in Pool A Train, producing a 1:1:1:1 balanced pretraining corpus of 40,000 samples.
```powershell
& "C:\Users\huynh\Desktop\fedwebpayload\.venv\Scripts\python.exe" C:\Users\huynh\Desktop\fedwebpayload\src\stage_01_data_foundation\1.6_build_pool_a_balanced.py
```
*Outputs:* `pool_a_train_balanced_40k.parquet`, `pool_a_val.parquet`, `pool_a_test.parquet`.

---

### Step 7: Partition Pool B into Global Holdouts & 6 Non-IID Client Silos
Extracts Global Test (15%) and Global Val (15%) holdouts. Partitions Train B into 6 specialized client silos with paired attack skew.
```powershell
& "C:\Users\huynh\Desktop\fedwebpayload\.venv\Scripts\python.exe" C:\Users\huynh\Desktop\fedwebpayload\src\stage_01_data_foundation\1.7_partition_pool_b_clients.py
```
*Outputs:* `pool_b_global_test.parquet`, `pool_b_global_val.parquet`, `clients/client_{1..6}_{train,val,test}.parquet`.

---

### Step 8: Master Zero-Leakage Verification & Accounting
Runs mathematical set-disjointness assertions and exports final publication tables.
```powershell
& "C:\Users\huynh\Desktop\fedwebpayload\.venv\Scripts\python.exe" C:\Users\huynh\Desktop\fedwebpayload\src\stage_01_data_foundation\1.8_master_accounting_report.py
```
*Outputs:* `data_accounting_master.csv`, `client_silo_distribution_matrix.csv`.

---

## 🔄 One-Liner Full Pipeline Run
To execute all steps sequentially in a single command:
```powershell
& "C:\Users\huynh\Desktop\fedwebpayload\.venv\Scripts\python.exe" C:\Users\huynh\Desktop\fedwebpayload\src\stage_01_data_foundation\1.1_data_ingest_and_hash.py; & "C:\Users\huynh\Desktop\fedwebpayload\.venv\Scripts\python.exe" C:\Users\huynh\Desktop\fedwebpayload\src\stage_01_data_foundation\1.2_global_dedup_and_cluster.py; & "C:\Users\huynh\Desktop\fedwebpayload\.venv\Scripts\python.exe" C:\Users\huynh\Desktop\fedwebpayload\src\stage_01_data_foundation\1.3_label_consensus_audit.py; & "C:\Users\huynh\Desktop\fedwebpayload\.venv\Scripts\python.exe" C:\Users\huynh\Desktop\fedwebpayload\src\stage_01_data_foundation\1.4_generate_accounting_report.py; & "C:\Users\huynh\Desktop\fedwebpayload\.venv\Scripts\python.exe" C:\Users\huynh\Desktop\fedwebpayload\src\stage_01_data_foundation\1.5_pool_split.py; & "C:\Users\huynh\Desktop\fedwebpayload\.venv\Scripts\python.exe" C:\Users\huynh\Desktop\fedwebpayload\src\stage_01_data_foundation\1.6_build_pool_a_balanced.py; & "C:\Users\huynh\Desktop\fedwebpayload\.venv\Scripts\python.exe" C:\Users\huynh\Desktop\fedwebpayload\src\stage_01_data_foundation\1.7_partition_pool_b_clients.py; & "C:\Users\huynh\Desktop\fedwebpayload\.venv\Scripts\python.exe" C:\Users\huynh\Desktop\fedwebpayload\src\stage_01_data_foundation\1.8_master_accounting_report.py
```
