# 🛡️ Stage 1: Data Foundation (Clean Room & Provenance Architecture)

## 📌 Executive Summary
Stage 1 establishes the **Data Clean Room** for the Federated Web Payload project. Operating across 8 heterogeneous cybersecurity data repositories containing over **5.32 million raw records**, this stage transforms raw, noisy HTTP traffic into cryptographically disjoint, lineage-verified datasets.

The pipeline achieves:
1. **100% Provenance Tracking:** Complete audit trail from raw bytes to train/test partitions.
2. **Zero-Leakage Guarantee:** Cryptographic SHA-256 deduplication and strict disjointness assertions preventing train-test contamination.
3. **OWASP CRS v4 Consensus Gate:** Rule-based verification against Web Application Firewall (WAF) standards to eliminate noisy public annotations without circular AI dependencies.
4. **Two-Tier Architecture:** 
   - **Pool A (15%):** Pre-training foundation balanced to exact **1:1:1:1** (40,000 samples) via **M1–M8 Semantic Mutations**.
   - **Pool B (85%):** Natural distribution federated reservoir partitioned into **Global Holdouts (30%)** and **6 Extreme Non-IID Client Silos (70%)**.
5. **Independent Out-of-Domain Holdout:** **CSIC 2010 (122,130 records)** completely isolated for zero-shot generalized evaluation.

---

## 🏗️ End-to-End Pipeline Architecture (Mermaid Diagram)

```mermaid
flowchart TD
    subgraph S1["Stage 1.1: Multi-Source Ingestion & Sanitization"]
        SRC["8 Heterogeneous Raw Repositories<br/>(SRC_00 to SRC_07)"] --> ING["1.1 Vectorized Ingestion Engine<br/>(Pandas/NumPy C-Level Speed)"]
        ING --> RAW["Raw Ingestion: 5,325,763 Records"]
        RAW --> DEC["3-Pass Recursive URL & NFKC Decoding"]
        DEC --> SAN["Defensive PII & Token Sanitization<br/>(Masking IPs, Bearer Tokens, UUIDs)"]
        SAN --> HASH["Cryptographic Hashing Engine<br/>(SHA-256 raw_hash & sanitized_hash)"]
    end

    subgraph S2["Stage 1.2: Global Exact Deduplication"]
        HASH --> DEDUP["1.2 Exact Deduplication Engine"]
        DEDUP --> CLUST["3,873,805 Primary Unique Clusters<br/>(exact_cluster_id Assignment)"]
    end

    subgraph S3["Stage 1.3: OWASP CRS v4 Consensus Audit"]
        CLUST --> WAF["1.3 OWASP CRS v4 Signature Matcher<br/>(1.3.1_label_signatures.py)"]
        WAF --> AUDIT{"Label Consensus Gate"}
        AUDIT -->|"Disagreement / Multi-match"| AMB["Ambiguous / Rejected Set<br/>(1,079,517 Clusters)"]
        AUDIT -->|"Consensus Agreement"| CONF["2,794,288 Confirmed Gold Clusters<br/>(sample_manifest.parquet)"]
    end

    subgraph S4["Stage 1.5: Stratified Pool Bisection"]
        CONF --> SPLIT["1.5 Stratified Pool Split Engine"]
        SPLIT -->|"Leave-One-Out OOD"| OOD["External OOD CSIC 2010<br/>(13,463 Clusters / 122,130 Rows)"]
        SPLIT -->|"15% Stratified Allocation"| POOL_A["Pool A: Base Pre-training<br/>(~418,000 Clusters)"]
        SPLIT -->|"85% Stratified Allocation"| POOL_B["Pool B: Federated Reservoir<br/>(~2,369,000 Clusters)"]
    end

    subgraph S5["Stage 1.6: Pool A Balanced Pre-Training & M1-M8 Mutations"]
        POOL_A --> PA_SPLIT["Stratified 70/15/15 Bisection"]
        
        subgraph M1M8_ENGINE["1.5.1 M1–M8 Semantic Mutation Engine"]
            direction TB
            M_LIST["• M1: Case Toggling (sElEcT)<br/>• M2: Single URL Enc (%2e%2e%2f)<br/>• M3: Double URL Enc (%252e%252e%252f)<br/>• M4: Space-to-Comment (SELECT/**/FROM)<br/>• M5: Operator Swap (OR to ||)<br/>• M6: Null-Byte Injection (passwd%00)<br/>• M7: Path Depth Extension (../../../../)<br/>• M8: Separator Obfuscation (....//, ..\\/)"]
        end

        PA_SPLIT -->|"70% Train Seeds"| M1M8_ENGINE
        M1M8_ENGINE --> TRAIN_A["Pool A Train Balanced<br/>(40,000 Samples - 1:1:1:1 Exact)"]
        PA_SPLIT -->|"15% Natural Val"| VAL_A["Pool A Val (Natural: 62,747)"]
        PA_SPLIT -->|"15% Natural Test"| TEST_A["Pool A Test (Natural: 62,750)"]
    end

    subgraph S6["Stage 1.7: Pool B Client Silos & Global Holdouts"]
        POOL_B --> PB_SPLIT["Stratified 70/15/15 Bisection"]
        
        subgraph G_HOLDOUTS["Global Holdouts (Unified Benchmark)"]
            PB_SPLIT -->|"15% Test"| TEST_B["Global Test B: 355,570 Samples<br/>(Unaugmented Evaluation Ruler)"]
            PB_SPLIT -->|"15% Val"| VAL_B["Global Val B: 355,568 Samples"]
        end
        
        PB_SPLIT -->|"70% Train Reservoir"| NON_IID["Paired Extreme Non-IID Partitioning"]
        
        subgraph PAIR_XSS["Silo Pair 1: XSS Specialists (80% of Pool B XSS)"]
            NON_IID --> C1["Client 1 (XSS Heavy)<br/>147,922 XSS | 205k Benign | 356k Total"]
            C1 --- C2["Client 2 (XSS Heavy)<br/>147,922 XSS | 205k Benign | 356k Total"]
        end

        subgraph PAIR_SQLI["Silo Pair 2: SQLi Specialists (80% of Pool B SQLi)"]
            NON_IID --> C3["Client 3 (SQLi Heavy)<br/>18,531 SQLi | 205k Benign | 243k Total"]
            C3 --- C4["Client 4 (SQLi Heavy)<br/>18,531 SQLi | 205k Benign | 243k Total"]
        end

        subgraph PAIR_PATH["Silo Pair 3: PathTrav Specialists (80% of Pool B PathTrav)"]
            NON_IID --> C5["Client 5 (PathTrav Heavy)<br/>3,783 PathTrav | 205k Benign | 230k Total"]
            C5 --- C6["Client 6 (PathTrav Heavy)<br/>3,784 PathTrav | 205k Benign | 230k Total"]
        end
    end

    subgraph S7["Stage 1.8: Master Provenance & Zero-Leakage Proof"]
        TRAIN_A & TEST_A & TEST_B & PAIR_XSS & PAIR_SQLI & PAIR_PATH & OOD --> VERIFY["1.8 Zero-Leakage Assertion Engine<br/>(Mathematical Cryptographic Disjointness)"]
        VERIFY --> REP1["data_accounting_master.csv"]
        VERIFY --> REP2["client_silo_distribution_matrix.csv"]
    end
```

---

## 📂 Modular Script Breakdown

| Script File | Purpose | Key Inputs | Output Artifacts |
| :--- | :--- | :--- | :--- |
| **`1.1_data_ingest_and_hash.py`** | Vectorized multi-source ingestion, 3-pass decoding, defensive masking (IPs, tokens, UUIDs), and SHA-256 hashing. | `data/raw/SRC_00` to `SRC_07` | `data/interim/manifest_stage1.parquet` (5,325,763 rows) |
| **`1.2_global_dedup_and_cluster.py`** | Exact cluster deduplication based on `sanitized_hash`. Flags primary representatives (`is_primary_in_cluster`). | `data/interim/manifest_stage1.parquet` | `data/interim/manifest_stage2.parquet` (3,873,805 clusters) |
| **`1.3_label_consensus_audit.py`** | Audits primary clusters against OWASP CRS v4 regex engine. Establishes `confirmed`, `ambiguous`, and `rejected` labels. | `data/interim/manifest_stage2.parquet` | `data/processed/sample_manifest.parquet` (2,794,288 confirmed clusters) |
| **`1.3.1_label_signatures.py`** | The OWASP CRS v4 regex matching rules (Rules 941 XSS, 942 SQLi, 930 PathTrave) with D19 scrubbing. | Function calls | Signature verification module |
| **`1.4_generate_accounting_report.py`** | Computes per-source data balance matrix and ingestion funnel statistics. | `data/processed/sample_manifest.parquet` | `data/processed/data_accounting.csv`<br/>`data/processed/source_label_accounting.csv` |
| **`1.5_pool_split.py`** | Stratified bisection of confirmed data into **Pool A (15%)**, **Pool B (85%)**, and **OOD (CSIC 2010)**. | `data/processed/sample_manifest.parquet` | Updated `sample_manifest.parquet` (with `pool_id`) |
| **`1.5.1_m1_m8_augment.py`** | Deterministic semantic mutation engine implementing rules M1–M8 while strictly preserving parent cluster lineage. | Function calls | Mutation variant generator |
| **`1.6_build_pool_a_balanced.py`** | Generates the 1:1:1:1 balanced pretraining corpus (40,000 samples) for Pool A Train, while preserving natural Val/Test. | `sample_manifest.parquet` | `pool_a_train_balanced_40k.parquet`<br/>`pool_a_val.parquet`<br/>`pool_a_test.parquet` |
| **`1.7_partition_pool_b_clients.py`** | Carves out Global Test/Val holdouts (30%) and partitions Train B (70%) into 6 Extreme Non-IID Client Silos. | `sample_manifest.parquet` | `pool_b_global_test.parquet`<br/>`pool_b_global_val.parquet`<br/>`clients/client_{1..6}_{train,val,test}.parquet` |
| **`1.8_master_accounting_report.py`** | Executes mathematical Zero-Leakage assertions and generates master accounting matrices. | All processed parquet files | `data/processed/data_accounting_master.csv`<br/>`data/processed/client_silo_distribution_matrix.csv` |

---

## 📊 Summary Statistics & Provenance Ledger

### 1. 6-Client Non-IID Silo Distribution Matrix (`client_silo_distribution_matrix.csv`)

| Client ID | Specialization | Total Samples | Train (80%) | Val (10%) | Test (10%) | Benign | XSS | SQLi | PathTrav |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Client 1** | 🔴 **XSS Heavy** | 356,331 | 285,062 | 35,633 | 35,636 | 205,029 | **147,922** | 2,316 | 472 |
| **Client 2** | 🔴 **XSS Heavy** | 356,332 | 285,063 | 35,633 | 35,636 | 205,029 | **147,922** | 2,316 | 473 |
| **Client 3** | 🟠 **SQLi Heavy** | 243,115 | 194,490 | 24,311 | 24,314 | 205,029 | 18,490 | **18,531** | 473 |
| **Client 4** | 🟠 **SQLi Heavy** | 243,115 | 194,490 | 24,311 | 24,314 | 205,029 | 18,490 | **18,531** | 473 |
| **Client 5** | 🟣 **PathTrav Heavy** | 230,210 | 184,166 | 23,021 | 23,023 | 205,029 | 18,490 | 2,316 | **3,783** |
| **Client 6** | 🟣 **PathTrav Heavy** | 230,214 | 184,169 | 23,021 | 23,024 | 205,029 | 18,491 | 2,317 | **3,784** |

### 2. Master Dataset Provenance Table (`data_accounting_master.csv`)

| Category | Dataset Name | Total Records | Benign | XSS | SQLi | PathTrav | Other | Description |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **Data Clean Room** | Raw Manifest | **5,325,763** | 3,952,051 | 724,768 | 369,905 | 237,837 | 41,202 | Unified raw ingestion across 8 sources |
| **Data Clean Room** | Primary Unique Clusters | **3,873,805** | 2,791,144 | 675,568 | 169,713 | 197,908 | 39,472 | Post-Deduplication canonical clusters |
| **Data Clean Room** | OWASP Confirmed Clusters | **2,794,288** | 2,072,352 | 621,997 | 78,005 | 15,963 | 5,971 | **Gold Consensus Set (100% Pure)** |
| **Pool A (Pretrain)** | **Pool A Train Balanced** | **40,000** | **10,000** | **10,000** | **10,000** | **10,000** | 0 | **1:1:1:1 Pretraining Corpus (M1-M8)** |
| **Pool A (Pretrain)** | Pool A Natural Val | 62,747 | 46,519 | 13,984 | 1,752 | 358 | 134 | Base Validation (Unaugmented) |
| **Pool A (Pretrain)** | Pool A Natural Test | 62,750 | 46,520 | 13,985 | 1,752 | 358 | 135 | Base In-Domain Test (Unaugmented) |
| **Pool B (Holdout)** | **Pool B Global Test** | **355,570** | 263,609 | 79,244 | 9,928 | 2,027 | 762 | **Unified FL Evaluation Benchmark** |
| **Pool B (Holdout)** | Pool B Global Val | 355,568 | 263,609 | 79,244 | 9,927 | 2,027 | 761 | Global Validation Benchmark |
| **External Benchmark**| **OOD CSIC 2010 Test** | **122,130** | 120,048 | 1,504 | 384 | 194 | 0 | External Out-of-Domain Generalization |

---

## 🔬 Mathematical Zero-Leakage Proof
All generated datasets are verified via strict set-disjointness assertions in `1.8_master_accounting_report.py`:
$$\text{Pool A} \cap \text{Pool B} = \emptyset$$
$$\text{Train}_{\text{Client } i} \cap \text{Train}_{\text{Client } j} = \emptyset \quad \forall i \neq j$$
$$\text{Train}_{\text{Client } i} \cap \text{Test}_{\text{Global B}} = \emptyset \quad \forall i$$
$$\text{Train}_{\text{Pool A}} \cap \text{Test}_{\text{Pool A}} = \emptyset$$
$$\text{Pool A} \cap \text{OOD}_{\text{CSIC}} = \emptyset, \quad \text{Pool B} \cap \text{OOD}_{\text{CSIC}} = \emptyset$$
