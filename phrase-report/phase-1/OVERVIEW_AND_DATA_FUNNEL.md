# TỔNG QUAN PHASE 1 VÀ PHỄU LỌC DỮ LIỆU TỔNG THỂ (OVERVIEW & DATA ATTRITION FUNNEL)

**Dự án:** `fedwebpayload` (Federated Web Attack Payload Detection)  
**Tài liệu:** Thống kê tổng hợp toàn bộ Giai đoạn 1  

---

## 1. HÀNH TRÌNH TỪ DỮ LIỆU THÔ ĐẾN TẬP HUẤN LUYỆN CHUẨN KHOA HỌC

Giai đoạn 1 là trái tim của dự án, áp dụng tư duy **Data-Centric AI** để biến 12 nguồn dữ liệu thô hỗn hợp thành tập dữ liệu huấn luyện vàng (`trainable_corpus.parquet`).

### Bảng Phễu Lọc Dữ Liệu Qua 5 Stage (Data Attrition Funnel Table)

| Stage ID | Tên Giai Đoạn | File Script Executed | Rows Before | Rows After | Retention % | Kỹ Thuật Chuyên Sâu Áp Dụng |
|---|---|---|---|---|---|---|
| **Stage 1** | Raw Ingestion | [`src/data/ingest.py`](file:///C:/Users/huynh/Desktop/fedwebpayload/src/data/ingest.py) | 12 Sources | **6,243,679** | 100.00% | Chunk-based streaming logs & multi-format parser |
| **Stage 2** | Decoding & Sanitization | [`src/data/decode.py`](file:///C:/Users/huynh/Desktop/fedwebpayload/src/data/decode.py) <br/> [`src/data/sanitize.py`](file:///C:/Users/huynh/Desktop/fedwebpayload/src/data/sanitize.py) | 6,243,679 | **6,242,588** | 99.98% | 3-Pass URL Decode, HTML Unescape, NFKC, PII Masking |
| **Stage 3** | OWASP Signature & Scrubbing | [`src/data/label_signatures.py`](file:///C:/Users/huynh/Desktop/fedwebpayload/src/data/label_signatures.py) | 6,242,588 | **126,450** | 2.03% | OWASP CRS v4 Rules, D19 Mislabel Reversion |
| **Stage 4** | Sandbox & MinHash Dedup | [`src/data/sandbox_verify.py`](file:///C:/Users/huynh/Desktop/fedwebpayload/src/data/sandbox_verify.py) <br/> [`src/data/dedup.py`](file:///C:/Users/huynh/Desktop/fedwebpayload/src/data/dedup.py) | 126,450 | **102,757** | 81.26% | `os.path.abspath` escape verify, Entropy MinHash LSH |
| **Stage 5** | Bounded Augmentation | [`src/data/augment.py`](file:///C:/Users/huynh/Desktop/fedwebpayload/src/data/augment.py) | 102,757 | **108,627** | 105.71% | Deterministic Mutations M1–M8, Lineage Cluster Lock |

---

## 2. BẢNG XÁC MINH NGUỒN GỐC HỌC THUẬT (PROVENANCE MANIFEST)

| Source ID | Tên Nguồn Dữ Liệu | Bài Báo & Tác Giả Tham Chiếu | Giấy Phép | Tác Vụ Quy Định |
|---|---|---|---|---|
| **`SRC_00`** | `SRC_00_professor_dataset` | KMUTNB Honeypot & Suricata Logs (Dec 2024 - Oct 2024) | Academic | Tấn công thực tế |
| **`SRC_01`** | `SRC_01_httpparams` | HttpParamsDataset (Morzeux et al.) | MIT | Dev Pool (Scrubbed) |
| **`SRC_02`** | `SRC_02_csic2010` | HTTP DATASET CSIC 2010 (Giménez et al.) | Open | OOD External Test |
| **`SRC_03`** | `SRC_03_modsecurity_waf` | Production WAF Dataset (Lucz 2025, Zenodo) | CC BY 4.0 | Real WAF Evasion Pool |
| **`SRC_04`** | `SRC_04_xss_collections` | XSS Benchmark (fmereani Mendeley / Figshare) | MIT | XSS Expansion Pool |
| **`SRC_05`** | `SRC_05_pathtrav_collections` | SecLists & PayloadsAllTheThings LFI/PathTrav | MIT | PathTrav Expansion Pool |
| **`SRC_06`** | `SRC_06_sqli_collections` | BWAFSQLi (Zhang 2026), WAF-A-Mole, AdvSQLi | MIT / IEEE | SQLi Expansion Pool |
| **`SRC_07`** | `SRC_07_cse_cic_ids2018` | CSE-CIC-IDS2018 Intrusion Dataset | Academic | Flow Benchmark |
| **`SRC_08`** | `SRC_08_cicids2017` | CICIDS2017 Intrusion Dataset | Academic | Flow Benchmark |
| **`SRC_09`** | `SRC_09_ecml_pkdd_2007` | ECML PKDD 2007 Web Attack Discovery | Academic | Dev Pool |
| **`SRC_10`** | `SRC_10_sr_bh_2020` | SR-BH Multi-Label Benchmark (Jazi 2020) | Academic | Independent Holdout |
| **`SRC_11`** | `SRC_11_webspotter_fpad_ood` | WebSpotter FPAD Generalization Benchmark | Academic | OOD Benchmark |
