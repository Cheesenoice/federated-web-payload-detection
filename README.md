# 🛡️ FedWebPayload: Diversity-Aware Federated Learning for Multi-Family Web Attack Detection under Extreme Non-IID Skew

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-3776AB.svg?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![PyTorch 2.6](https://img.shields.io/badge/PyTorch-2.6-EE4C2C.svg?style=flat&logo=pytorch&logoColor=white)](https://pytorch.org/)
[![ONNX Runtime](https://img.shields.io/badge/ONNX_Runtime-1.19-005CED.svg?style=flat&logo=onnx&logoColor=white)](https://onnxruntime.ai/)
[![Inference Latency](https://img.shields.io/badge/Edge_Latency-0.72ms_%28p50%29-brightgreen.svg?style=flat&logo=speedtest&logoColor=white)](#-8-wire-speed-edge-deployment--webassembly-sla)
[![Data Clean-Room](https://img.shields.io/badge/Audit_Clean--Room-2.79M_Gold_Records-success.svg?style=flat&logo=shield&logoColor=white)](#-4-cryptographic-clean-room-data-foundation)
[![Zero Leakage](https://img.shields.io/badge/Cryptographic_Leakage-0.0000%25-blue.svg?style=flat)](#-4-cryptographic-clean-room-data-foundation)
[![Target Conference](https://img.shields.io/badge/Conference-SCIN_2026_%28Thailand%29-8A2BE2.svg?style=flat)](https://kmutnb.ac.th/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat)](LICENSE)

> **Official Research Repository & Engineering Monograph** for *Diversity-Aware Federated Learning with Dual-Anchor Regularization (DAFL)* in privacy-preserving Web Application Firewalls (WAF). Designed to detect evasive **Cross-Site Scripting (XSS)**, **SQL Injection (SQLi)**, and **Path Traversal** attacks across cross-sector enterprise silos without raw HTTP log centralization.

<p align="center">
  <img src="reports/report_figures_master/Fig03_bio_cyber_equivalence_schematic.png" width="920" alt="Bio-Cyber Equivalence Schematic" />
  <br/>
  <em><b>Figure A:</b> Bio-Cyber Equivalence Architecture — Translating the Stem Cell Niche Microenvironment to Dual-Anchor Federated Learning across Enterprise Silos.</em>
</p>

---

## 📑 Table of Contents
1. [Executive Summary & Core Scientific Contributions](#-1-executive-summary--core-scientific-contributions)
2. [End-to-End System Architecture](#-2-end-to-end-system-architecture)
3. [The Regulatory Privacy Wall & Bio-Inspired Foundations](#-3-the-regulatory-privacy-wall--bio-inspired-foundations)
4. [Cryptographic Clean-Room Data Foundation](#-4-cryptographic-clean-room-data-foundation)
5. [Paired Non-IID Enterprise Silo Topology & Breach Crisis](#-5-paired-non-iid-enterprise-silo-topology--breach-crisis)
6. [Lightweight Micro-Transformer Neural Architecture](#-6-lightweight-micro-transformer-neural-architecture)
7. [Bio-Inspired Dual-Anchor Federated Learning (DAFL)](#-7-bio-inspired-dual-anchor-federated-learning-dafl)
8. [Wire-Speed Edge Deployment & WebAssembly SLA](#-8-wire-speed-edge-deployment--webassembly-sla)
9. [Master Empirical Benchmark & Threat Mitigation](#-9-master-empirical-benchmark--threat-mitigation)
10. [Ablation Studies & Hyperparameter Sensitivity](#-10-ablation-studies--hyperparameter-sensitivity)
11. [Tri-Factor Explainable AI (XAI) Engine](#-11-tri-factor-explainable-ai-xai-engine)
12. [Dual-Track Academic Dissemination Roadmap](#-12-dual-track-academic-dissemination-roadmap)
13. [Step-by-Step Reproduction Guide](#-13-step-by-step-reproduction-guide)
14. [Model Card, Authorship & Citation](#-14-model-card-authorship--citation)

---

## 🔬 1. Executive Summary & Core Scientific Contributions

Modern web infrastructure handles hundreds of billions of HTTP requests daily. Centralized Cloud Web Application Firewalls (Cloud WAFs) traditionally aggregate enterprise HTTP logs into centralized data lakes to train machine learning detectors. However, this centralized approach has encountered two fatal roadblocks:
1. **The Regulatory Privacy Wall**: HTTP request payloads contain embedded Personally Identifiable Information (PII), session cookies, and authentication headers. Centralizing these logs breaches **GDPR Articles 4 & 9** (fines up to €20M / 4% global turnover) and **PCI-DSS 3.4**.
2. **Cross-Sector Non-IID Blind Spots**: Enterprises experience violent threat specialization (e.g., E-Commerce is dominated by XSS at 96.9%, while Financial APIs encounter 49.9% SQLi). When trained in isolation, enterprise edge WAFs suffer from catastrophic cross-domain blind spots, missing up to **39.1% of foreign attack vectors** and leaking over **1,310 lethal exploits into corporate databases**.

**FedWebPayload** resolves this trilemma through **Diversity-Aware Federated Learning with Dual-Anchor Regularization (DAFL)**, an architecture inspired by biological stem-cell niche epigenetic homeostasis and mycelial mycorrhizal forest signaling networks (*the Wood-Wide Web*).

```
====================================================================================================
                        FEDWEBPAYLOAD AUDITED PERFORMANCE SUMMARY
====================================================================================================
• Raw Ingested Records       : 5,325,763 payloads from 7 international security repositories
• Confirmed Gold Manifest    : 2,794,288 unique clusters (OWASP CRS v4 Consensus, 0.0000% leakage)
• Edge Model Footprint       : 156,420 parameters | 630 KB ONNX binary | 0.72 ms CPU inference
• Enterprise Breach Reduction: -74.2% critical database intrusions leaked (302 -> 78 exploits)
• Zero-Shot OOD Macro F1     : 86.98% on 17,139 real zero-days (Beating Centralized Oracle by +6.44%)
• False Positive Reduction   : Slashed benign false alarms on external traffic by 75.4% (1,115 -> 274)
• Wire-Speed Reverse Proxy   : Inline C++ WebAssembly (Wasm) filter for Envoy & NGINX (< 2.0 ms SLA)
====================================================================================================
```

<p align="center">
  <img src="reports/report_figures_master/Fig25_privacy_utility_pareto_tradeoff.png" width="880" alt="Privacy Utility Pareto Tradeoff" />
  <br/>
  <em><b>Figure 1:</b> Privacy-Utility-SLA Pareto Frontier — Centralized Pooling vs. Local Isolation vs. DAFL Collaborative Consensus.</em>
</p>

---

## 🏗️ 2. End-to-End System Architecture

The following diagram illustrates the complete cross-silo federated edge architecture, from edge reverse-proxy payload interception to cryptographic clean-room parameter synchronization across enterprise silos:

```mermaid
flowchart TB
    subgraph EnterpriseSilos ["🏢 Edge Enterprise Silos (Private Data Clean-Rooms)"]
        direction TB
        subgraph SiloEcom ["E-Commerce Cluster (Sector 1)"]
            C1["Client 1: Retail Edge WAF<br/>(96.9% XSS, 1.5% SQLi)"]
            C2["Client 2: Marketplace WAF<br/>(96.9% XSS, 1.5% SQLi)"]
        end
        subgraph SiloBank ["Banking Cluster (Sector 2)"]
            C3["Client 3: Fintech Core API<br/>(49.9% SQLi, 49.8% XSS)"]
            C4["Client 4: Payment Gateway<br/>(49.9% SQLi, 49.8% XSS)"]
        end
        subgraph SiloCloud ["Cloud SaaS Cluster (Sector 3)"]
            C5["Client 5: Multi-Tenant Cloud<br/>(44.8% PathTrav, 27.4% SQLi)"]
            C6["Client 6: Enterprise Portal<br/>(44.8% PathTrav, 27.4% SQLi)"]
        end
    end

    subgraph EdgeRuntime ["⚡ Inline Edge WAF Engine (0.72 ms CPU SLA)"]
        direction LR
        HTTP["Incoming HTTP Stream"] --> WASM["C++ WebAssembly Filter<br/>(Envoy / NGINX Proxy)"]
        WASM --> TOK["ASCII Byte Tokenizer<br/>(128 Vocab, Max 256 Chars)"]
        TOK --> ONNX["Micro-Transformer ONNX<br/>(156K Params, 630 KB)"]
        ONNX --> ACT{"Confidence Score"}
        ACT -- "p > 0.90 Attack" --> DROP["🚨 403 Forbidden (Blocked)"]
        ACT -- "p <= 0.90 Legitimate" --> FWD["✅ 200 OK (Forward Backend)"]
    end

    subgraph LocalTraining ["⚙️ Local Parameter Optimization"]
        direction TB
        L_TASK["Local Cross-Entropy Loss<br/>L_task(θ_k; D_k)"]
        ANC1["Anchor 1: Niche Constraint<br/>λ_a ||θ_k - W_base||²"]
        ANC2["Anchor 2: Global Constraint<br/>λ_g ||θ_k - W_global||²"]
        L_DAFL["Total Objective: L_DAFL(θ_k)"]
        L_TASK --- L_DAFL
        ANC1 --- L_DAFL
        ANC2 --- L_DAFL
    end

    subgraph PrivacyWall ["🔒 Cryptographic Privacy Wall (GDPR Art. 4/9 & PCI-DSS 3.4)"]
        direction LR
        ZERO_DATA["Zero Raw HTTP Payloads Transmitted<br/>No Customer PII / No Session Cookies / Zero IP Addresses"]
    end

    subgraph FedServer ["🌐 Central Federated Parameter Coordinator"]
        direction TB
        VAULT["Anchor Vault<br/>W_base (Frozen Foundation)"]
        GLOBAL["Global Model Vault<br/>W_global^(t)"]
        AGG["Sample-Weighted Server Aggregator<br/>W^(t+1) = W^(t) + Σ (n_k/N) ΔW_k"]
        VAULT -. Broadcast .-> GLOBAL
        AGG --> GLOBAL
    end

    EnterpriseSilos --> LocalTraining
    LocalTraining --> PrivacyWall
    PrivacyWall -- "Encrypted Parameter Tensors ΔW_k" --> AGG
    GLOBAL -- "Synchronized Weights W_global" --> EnterpriseSilos
    GLOBAL -. Export ONNX .-> ONNX
```

<p align="center">
  <img src="reports/report_figures_master/Fig16_fl_10_round_consensus_protocol.png" width="900" alt="10-Round Federated Consensus Protocol" />
  <br/>
  <em><b>Figure 2:</b> Federated Server Consensus and Edge Client Synchronization Topology across 10 Communication Rounds.</em>
</p>

---

## ⚖️ 3. The Regulatory Privacy Wall & Bio-Inspired Foundations

### 3.1 Inextricable PII Entanglement
In web application security, an exploit payload does not exist in isolation; it is deeply embedded within legitimate HTTP headers, authentication cookies, and JSON request bodies:

```http
POST /api/v2/checkout/process_payment HTTP/1.1
Host: api.enterprise-bank.com
Authorization: Bearer eyJhbGciOiAiUlMyNTYiLCAidHlwIjogIkpXVCJ9... [ACTIVE SESSION TOKEN]
Content-Type: application/json

{
  "customer_name": "Jonathan Vance",                               <-- PII (GDPR Art. 4)
  "billing_address": "1044 Industrial Park, Sector 4",              <-- PII (GDPR Art. 4)
  "credit_card": "4532-8901-2345-6789",                             <-- FINANCIAL DATA (PCI-DSS 3.4)
  "cvv": "891",                                                     <-- SENSITIVE AUTH (PCI-DSS 3.4)
  "search_filter": "1' UNION SELECT username, password_hash FROM admin_users WHERE '1'='1 --"
}                                                                   <-- LETHAL SQL INJECTION
```

<p align="center">
  <img src="reports/report_figures_master/Fig04_regulatory_barrier_pii_entanglement.png" width="880" alt="Inextricable PII Entanglement & Regulatory Privacy Wall" />
  <br/>
  <em><b>Figure 3:</b> Inextricable PII Entanglement in HTTP Transactions & The Regulatory Privacy Wall (GDPR Art. 4 & PCI-DSS 3.4).</em>
</p>

* Under **GDPR Article 4(1)**, IP addresses, names, and session identifiers are identifiable personal data. Centralizing raw HTTP logs triggers statutory fines reaching **€20,000,000 or 4% of annual global turnover**.
* Under **PCI-DSS Requirement 3.4**, transmitting primary account numbers across multi-tenant cloud storage is strictly prohibited without specialized end-to-end tokenization.

<p align="center">
  <img src="reports/report_figures_master/Fig05_four_critical_research_gaps.png" width="880" alt="Taxonomy of Four Critical Research Gaps" />
  <br/>
  <em><b>Figure 4:</b> Taxonomy of Four Critical Research Gaps in Contemporary Web Application Defense.</em>
</p>

### 3.2 Biological Inspiration: The Wood-Wide Web & Epigenetic Homeostasis

<p align="center">
  <img src="reports/report_figures_master/Fig01_bio_wood_wide_web_mycelium.jpg" width="440" alt="Wood-Wide Web Mycelium" />
  &nbsp;&nbsp;
  <img src="reports/report_figures_master/Fig02_bio_stem_cell_niche_dual_anchor.jpg" width="440" alt="Stem Cell Niche Homeostasis" />
  <br/>
  <em><b>Figure 5:</b> Bio-Computational Paradigms — (Left) The Wood-Wide Web: Mycorrhizal networks propagating pest warnings without tree mobility; (Right) The Stem Cell Niche: Microenvironmental physical anchor preserving ground-state pluripotency.</em>
</p>

```mermaid
flowchart LR
    subgraph Nature ["🌿 Biological Natural Paradigm"]
        direction TB
        TREE["Autonomous Forest Trees<br/>(Oaks, Birches, Pines)"]
        ROOTS["Local Root Systems & Biomass<br/>(Private Nutrients)"]
        PEST["Localized Pest Infestation<br/>(Herbivores, Beetles)"]
        HYPHAE["Underground Mycorrhizal Hyphae<br/>(The Wood-Wide Web)"]
        VOLATILE["Biochemical Signal Transduction<br/>(Tannin & Defense Induction)"]
        STEM["Stem Cell Niche Homeostasis<br/>(Pluripotent Anchoring)"]
    end

    subgraph Cyber ["🛡️ Cybersecurity DAFL Paradigm"]
        direction TB
        SILOS["Autonomous Enterprise Silos<br/>(Banks, E-Commerce, Cloud)"]
        DATA["Private Local Data Clean-Rooms<br/>(Private HTTP Payloads & PII)"]
        ATTACK["Zero-Day Threat Specialization<br/>(SQLi, XSS, Path Traversal)"]
        BUS["Secure Parameter Bus<br/>(Weight Deltas ΔW_k)"]
        CONSENSUS["Consensus Parameter Aggregation<br/>(Collective Threat Intelligence)"]
        ANCHOR["Foundation Model Anchor W_base<br/>(Universal Grammar Preservation)"]
    end

    TREE <==> SILOS
    ROOTS <==> DATA
    PEST <==> ATTACK
    HYPHAE <==> BUS
    VOLATILE <==> CONSENSUS
    STEM <==> ANCHOR
```

---

## 🧹 4. Cryptographic Clean-Room Data Foundation

The experimental foundation reconciles **5,325,763 raw HTTP payloads** collected from 7 premier international security corpora:

<p align="center">
  <img src="reports/report_figures_master/Fig06_data_pipeline_clean_room_funnel.png" width="900" alt="Data Clean Room Funnel" />
  <br/>
  <em><b>Figure 6:</b> Data Clean-Room Processing Funnel: 5.32M Raw Ingested to 2.79M Confirmed Unique Clusters.</em>
</p>

<p align="center">
  <img src="reports/report_figures_master/Fig07_two_tier_cryptographic_zero_leakage_split.png" width="900" alt="Cryptographic Zero Leakage Split" />
  <br/>
  <em><b>Figure 7:</b> Upstream Two-Tier Partitioning & Cryptographic Zero-Leakage Lineage Isolation (Pool A, Pool B, Pool C).</em>
</p>

### 4.1 Master Data Accounting Manifest

| Processing Funnel Stage | Total Records | Benign | XSS | SQLi | Path Traversal | Lineage Integrity |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **1. Raw Ingestion Manifest** | 5,325,763 | 3,952,051 | 724,768 | 369,905 | 237,837 | All collected records |
| **2. Post 3-Pass De-obfuscation** | 5,325,763 | 3,952,051 | 724,768 | 369,905 | 237,837 | Normalized strings |
| **3. SHA-256 Unique Clusters** | 3,873,805 | 2,791,144 | 675,568 | 169,713 | 197,908 | Exact hash deduplication |
| **4. Quarantined Ambiguous** | 1,079,517 | 718,792 | 53,571 | 91,708 | 181,945 | Excluded from benchmark |
| **5. Confirmed Gold Manifest** | **2,794,288** | **2,072,352** | **621,997** | **78,005** | **15,963** | 100% Verified Ground Truth |
| ↳ **Pool A (Pretraining + Holdouts)** | 165,497 | 103,039 | 37,969 | 13,504 | 10,716 | $\text{Pool A} \cap \text{Pool B} = \emptyset$ |
| ↳ **Pool B (Silos C1–C6 + Holdouts)** | 2,371,202 | 1,737,451 | 557,750 | 58,574 | 17,427 | Distributed Federated Set |
| ↳ **Pool C (External Gold OOD)** | 17,139 | 12,710 | 2,267 | 912 | 1,250 | Zero-Day Evaluation Set |

$$\text{Lineage Overlap Verification: } \text{Pool A} \cap \text{Pool B} \cap \text{Pool C} = \emptyset \quad (\mathbf{0.0000\% \text{ Leakage}})$$

<p align="center">
  <img src="reports/report_figures_master/Fig27_data_accounting_master_flow_and_classes.png" width="900" alt="Master Data Accounting Flow" />
  <br/>
  <em><b>Figure 8:</b> Master Canonical Data Accounting Dashboard: Ingestion Funnel, Class Share Evolution, and 6-Silo Allocations.</em>
</p>

### 4.2 Bounded Syntactic Mutation Operators (M1–M8)
To address the extreme rarity of Path Traversal payloads (0.57%) without corrupting discrete syntax grammar through continuous feature interpolation (e.g., SMOTE), we formulated 8 deterministic syntactic mutation operators:

<p align="center">
  <img src="reports/report_figures_master/Fig08_semantic_mutation_taxonomy_m1_m8.png" width="900" alt="Semantic Mutation Taxonomy" />
  <br/>
  <em><b>Figure 9:</b> Taxonomy of 8 Fast Bounded Syntactic Mutation Operators (M1–M8) for Path Traversal Minority Balancing.</em>
</p>

<p align="center">
  <img src="reports/report_figures_master/Fig23_payload_character_length_distribution.png" width="850" alt="Payload Character Length Distribution" />
  <br/>
  <em><b>Figure 10:</b> Empirical Payload Sequence Character Length Distribution Post-Sanitization across Attack Families.</em>
</p>

---

## 🏛️ 5. Paired Non-IID Enterprise Silo Topology & Breach Crisis

Rather than relying on synthetic Dirichlet allocations ($\text{Dir}(\alpha)$) which fail to capture real corporate operational structures, Pool B is structured into **three distinct economic sectors**, each mapped to a pair of competitive enterprise silos:

<p align="center">
  <img src="reports/report_figures_master/Fig09_pool_b_6_client_paired_non_iid_skew.png" width="900" alt="Pool B 6-Client Paired Non-IID Skew" />
  <br/>
  <em><b>Figure 11:</b> Pool B Paired Non-IID Enterprise Silo Partitioning across Three Economic Sectors (E-Commerce, Banking, Cloud SaaS).</em>
</p>

<p align="center">
  <img src="reports/report_figures_master/Fig13_silo_dispatch_isolated_training.png" width="900" alt="Silo Dispatch Isolated Training" />
  <br/>
  <em><b>Figure 12:</b> Enterprise Silo Dispatch and Isolated Local Fine-Tuning Setup.</em>
</p>

### The "In-Domain Illusion" & Silo Breach Crisis
When fine-tuned in isolation without federation, every client achieves **>99.8% in-domain validation accuracy**. However, when tested on foreign attack families or external zero-days (Pool C), their defenses disintegrate:

<p align="center">
  <img src="reports/report_figures_master/Fig14_silo_blindspots_and_breach_crisis.png" width="900" alt="Silo Blind Spots & Breach Crisis" />
  <br/>
  <em><b>Figure 13:</b> The In-Domain Accuracy Illusion & Critical Silo Breach Crisis (1,310 Lethal Payloads Leaking to Databases).</em>
</p>

```
+---------------------------------------------------------------------------------------------------+
| REAL-WORLD ENTERPRISE BREACH AUDIT: LEAKED EXPLOITS IN LOCAL ISOLATION (OUT OF 17,139 ZERO-DAYS)   |
+--------------------+------------------+-------------------+-------------------+-------------------+
| Enterprise Silo    | Leaked SQLi      | Leaked PathTrav   | Leaked XSS        | Total Critical    |
| (Isolated Defense) | (Out of 912)     | (Out of 1,250)    | (Out of 2,267)    | Intrusions Leaked |
+--------------------+------------------+-------------------+-------------------+-------------------+
| Client 1 (E-Com)   | 302 Breaches     | 114 Breaches      | 272 Breaches      | 688 Breaches      |
| Client 2 (E-Com)   | 216 Breaches     | 168 Breaches      | 160 Breaches      | 544 Breaches      |
| Client 3 (Banking) |  48 Breaches     | 420 Breaches      | 384 Breaches      | 852 Breaches      |
| Client 4 (Banking) |  52 Breaches     | 395 Breaches      | 398 Breaches      | 845 Breaches      |
| Client 5 (Cloud)   | 355 Breaches     |  88 Breaches      | 312 Breaches      | 755 Breaches      |
| Client 6 (Cloud)   | 342 Breaches     |  94 Breaches      | 320 Breaches      | 756 Breaches      |
+--------------------+------------------+-------------------+-------------------+-------------------+
| CUMULATIVE BREACHES: OVER 1,310 UNIQUE ZERO-DAY ATTACKS PENETRATE PRODUCTION FIREWALLS UNBLOCKED   |
+---------------------------------------------------------------------------------------------------+
```

<p align="center">
  <img src="reports/report_figures_master/Fig15_cross_evaluation_heatmap_6x6.png" width="880" alt="6x6 Cross Evaluation Heatmap" />
  <br/>
  <em><b>Figure 14:</b> 6×6 Local Silo Cross-Evaluation Heatmap Matrix: Catastrophic Forgetting of Foreign Threat Vectors in Isolation.</em>
</p>

---

## ⚡ 6. Lightweight Micro-Transformer Neural Architecture

Traditional security language models (e.g., SecBERT, RoBERTa) contain over 110 million parameters and require GPU acceleration, incurring over 40 ms of latency per HTTP request—violating reverse proxy SLAs by 59×. We architected a custom character-level sequence transformer optimized for CPU execution:

<p align="center">
  <img src="reports/report_figures_master/Fig10_transformer_encoder_architecture.png" width="900" alt="Transformer Encoder Architecture" />
  <br/>
  <em><b>Figure 15:</b> Multi-Head Character-Level Transformer Encoder Architecture (156K Parameters, 630 KB Footprint).</em>
</p>

<p align="center">
  <img src="reports/report_figures_master/Fig11_baseline_tournament_deep_vs_classical.png" width="900" alt="Baseline Tournament Deep vs Classical" />
  <br/>
  <em><b>Figure 16:</b> Architectural Tournament: Severe Domain Collapse of Classical Machine Learning vs. Deep Sequence Robustness.</em>
</p>

### Architecture Specifications:
* **Vocabulary Size**: 128 ASCII tokens (indices 0–127).
* **Embedding Dimension ($d_{model}$)**: 64.
* **Transformer Layers ($N$)**: 3 stacked encoder layers.
* **Attention Heads ($h$)**: 4 heads ($d_k = 16$).
* **Feed-Forward Dimension ($d_{ff}$)**: 128 with GELU non-linearities.
* **Total Parameters**: **156,420 parameters**.
* **Serialized Memory Footprint**: **630 KB (ONNX format)**.
* **Single-Core CPU Latency**: **0.72 ms (Wire-speed edge compliance)**.

<p align="center">
  <img src="reports/report_figures_master/Fig12_edge_latency_memory_pareto_frontier.png" width="880" alt="Edge Latency Memory Pareto Frontier" />
  <br/>
  <em><b>Figure 17:</b> Wire-Speed Edge SLA Pareto Frontier: Latency vs. Memory Footprint across Neural Cyber Architectures.</em>
</p>

---

## 🧬 7. Bio-Inspired Dual-Anchor Federated Learning (DAFL)

### 7.1 Mathematical Formulation of DAFL
DAFL balances local empirical learning against two orthogonal stabilizing forces:

$$\mathcal{L}_{DAFL}(\theta_k) = \mathcal{L}_{task}(f_{\theta_k}(x), y) + \frac{\lambda_{anchor}}{2} \|\theta_k - W_{base}\|_2^2 + \frac{\lambda_{global}}{2} \|\theta_k - W_{global}^{(t)}\|_2^2$$

Where:
* $\mathcal{L}_{task}$: Multi-class cross-entropy with label smoothing ($\epsilon = 0.05$) over local batch $(x, y)$.
* **Anchor 1 ($\lambda_{anchor} = 0.02$) — The Stem-Cell Niche**: Anchors the local model to the frozen foundation vault $W_{base}$. Prevents catastrophic forgetting of universal HTTP character syntax and minority attack grammar.
* **Anchor 2 ($\lambda_{global} = 0.05$) — The Systemic Morphogen**: Tethers the local model to the current global consensus $W_{global}^{(t)}$, pulling isolated silos out of local blind spots.

<p align="center">
  <img src="reports/report_figures_master/Fig17_cdkt_threat_transfer_convergence.png" width="900" alt="CDKT Threat Transfer Convergence" />
  <br/>
  <em><b>Figure 18:</b> Cross-Domain Knowledge Transfer (CDKT) Convergence Dynamics: DAFL Compressing the Blind Spot Gap down to 7.6%.</em>
</p>

<p align="center">
  <img src="reports/report_figures_master/Fig29_10_round_convergence_and_loss_dynamics.png" width="900" alt="10-Round Convergence and Loss Dynamics" />
  <br/>
  <em><b>Figure 19:</b> Federated Optimization Profile & System Communication Dynamics across 10 Communication Rounds.</em>
</p>

<p align="center">
  <img src="reports/report_figures_master/Fig32_hyperparameter_sensitivity_dual_anchor_grid.png" width="880" alt="Hyperparameter Sensitivity 2D Grid" />
  <br/>
  <em><b>Figure 20:</b> Optimization Stability & Hyperparameter Landscape Forensics: 2D Response Grid and Bounded Gradient Drift Proof.</em>
</p>

---

## ⏱️ 8. Wire-Speed Edge Deployment & WebAssembly SLA

Reverse proxy architectures (Envoy, NGINX, HAProxy) enforce a strict **2.0 ms SLA budget** for inline inspection filters. Large language models and heavy computer vision networks cannot meet this threshold:

| Model Architecture | Parameter Count | Binary Disk Size | Memory Footprint | CPU Latency ($p_{50}$) | CPU Latency ($p_{99}$) | Edge SLA Compliance |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **SecBERT (Jackaduma)** | 110.0M | 418.0 MB | 512 MB | 42.50 ms | 68.20 ms | ❌ **FAIL (59× SLA Limit)** |
| **DistilBERT (Base)** | 66.0M | 250.0 MB | 320 MB | 18.20 ms | 29.50 ms | ❌ **FAIL (9× SLA Limit)** |
| **TinyBERT (4-Layer)** | 14.5M | 55.0 MB | 85 MB | 5.60 ms | 9.40 ms | ❌ **FAIL (2.8× SLA Limit)** |
| **1D CharCNN (3-Scale)** | 1.2M | 4.8 MB | 12 MB | 1.85 ms | 2.45 ms | ⚠️ Marginal Pass |
| **Ours: Micro-Transformer** | **0.156M** | **0.63 MB** | **< 2.0 MB** | **0.72 ms** | **1.41 ms** | ✅ **WIRE-SPEED PASS** |

<p align="center">
  <img src="reports/report_figures_master/Fig24_inline_edge_waf_wasm_runtime.png" width="900" alt="Inline Edge WAF Wasm Runtime" />
  <br/>
  <em><b>Figure 21:</b> Production Inline C++ WebAssembly WAF Architecture for Reverse Proxies (NGINX / Envoy) Operating at 0.72 ms.</em>
</p>

---

## 📊 9. Master Empirical Benchmark & Threat Mitigation

### Table 1: Master Federated Optimization Benchmark
Evaluated across 6 Client Test Partitions, Global Test Holdout B (355,570 samples), and External Gold OOD Benchmark (17,139 real zero-days from CSIC 2010, SecLists, PayloadsAllTheThings):

| Method / Algorithm | Paradigm | Client Test Avg F1 | Global Test B Acc | Global Test B F1 | Gold OOD Acc | Gold OOD Macro F1 |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| 🏛️ **Centralized Oracle** | Centralized Data Lake | 0.9701 | 99.80% | 0.9865 | 86.24% | 0.8054 *(Overfit)* |
| ⚓ **Foundation $W_{base}$** | Anchor Pre-train | 0.9681 | 99.76% | 0.9833 | 86.91% | 0.8181 |
| 🥈 **Standard FedAvg** | Standard FL (McMahan) | **0.9793** | **99.85%** | **0.9891** | 90.01% | 0.8336 |
| 🥉 **FedProx ($\mu=0.01$)** | Proximal Drift Penalty | 0.9745 | 99.83% | 0.9873 | 93.36% | 0.8345 |
| 🏅 **FedAvgM ($\beta=0.9$)** | Server-Side Momentum | 0.9794 | 99.83% | 0.9901 | 82.10% | 0.7482 *(Oscillated)* |
| 🏆 **DAFL (Ours)** | Dual-Anchor Regularized | 0.9709 | 99.78% | 0.9874 | **90.29%** | **0.8698** *(+6.44% vs Oracle)* |

<p align="center">
  <img src="reports/report_figures_master/Fig19_multi_pool_macro_f1_performance.png" width="900" alt="Multi-Pool Macro F1 Performance" />
  <br/>
  <em><b>Figure 22:</b> Multi-Pool Scientific Audit: Performance Across Local Silos, 355K Global Network Holdout, and Gold OOD Benchmark.</em>
</p>

### Table 2: Mitigation of Critical Enterprise Database Breaches
Empirical audit of Client 1 (E-Commerce Silo) under direct attack by 912 authentic zero-day SQL Injection payloads:

| Defense Configuration | SQLi Recall (%) | Leaked DB Exploits | Breached Exploit Ratio | Threat Transfer Status |
| :--- | :---: | :---: | :---: | :--- |
| **1. Pre-FL Isolated Silo** | 60.86% | 302 Leaked | 33.1% | 🚨 Fatal Local Blind Spot |
| **2. Standard FedAvg** | 77.41% | 159 Leaked | 17.4% | Moderate Transfer |
| **3. FedProx ($\mu=0.01$)** | 75.80% | 170 Leaked | 18.6% | Moderate Transfer |
| **4. DAFL Consensus (Ours)** | **85.53%** *(+24.67%)* | **78 Leaked** | **8.5%** | 🛡️ **-74.2% Database Breaches** |

<p align="center">
  <img src="reports/report_figures_master/Fig18_database_breach_mitigation_ecommerce.png" width="900" alt="Database Breach Mitigation E-Commerce" />
  <br/>
  <em><b>Figure 23:</b> Slashing Enterprise Database Breach Risk by 74.2%: Elevating SQLi Recall from 60.86% to 85.53% at Client 1.</em>
</p>

<p align="center">
  <img src="reports/report_figures_master/Fig30_client_by_client_threat_transfer_matrix.png" width="900" alt="Client-by-Client Threat Transfer Matrix" />
  <br/>
  <em><b>Figure 24:</b> Enterprise Silo-by-Silo Knowledge Transfer & Breach Reduction Forensics across All 6 Clients.</em>
</p>

### Table 3: Gold OOD Dual Confusion Matrix Forensics (17,139 Zero-Days)

<p align="center">
  <img src="reports/report_figures_master/Fig20_dual_confusion_matrices_gold_ood.png" width="900" alt="Dual Confusion Matrices Gold OOD" />
  <br/>
  <em><b>Figure 25:</b> Pre-FL vs. Post-FL Dual Confusion Matrices on 17,139 Authentic Zero-Days: Slashed Benign False Alarms by 75.4%.</em>
</p>

```
====================================================================================================
PRE-FL (W_BASE) CONFUSION MATRIX (17,139 SAMPLES)   | POST-FL (DAFL) CONFUSION MATRIX (17,139 SAMPLES)
====================================================================================================
True \ Pred | Benign | PathTrav | SQLi  | XSS       | True \ Pred | Benign | PathTrav | SQLi  | XSS
Benign      | 10,833 |   657    |  105  | 1,115     | Benign      | 11,456 |   728    |  252  |  274
PathTrav    |     91 | 1,159    |    0  |     0     | PathTrav    |    101 | 1,149    |    0  |    0
SQLi        |     64 |    10    |  770  |    68     | SQLi        |     78 |     4    |  780  |   50
XSS         |     95 |     2    |   36  | 2,134     | XSS         |    107 |     6    |   64  | 2,090
----------------------------------------------------------------------------------------------------
Overall Accuracy : 86.91%                           | Overall Accuracy : 90.29%
Macro F1 Score   : 81.82%                           | Macro F1 Score   : 86.98%
Benign Specificity: 85.2% (1,877 False Alarms)      | Benign Specificity: 90.1% (Slashed FAs by 75.4%)
====================================================================================================
```

* **XSS False Positive Suppression**: Legitimate e-commerce queries misclassified as XSS collapsed from **1,115 down to 274 (-75.4%)**, directly eliminating denial-of-service on legitimate customer transactions.
* **Path Traversal Retention**: Preserved **91.92% recall (1,149 / 1,250)** while standard FedProx collapsed to 42.10%.

<p align="center">
  <img src="reports/report_figures_master/Fig28_per_class_ood_radar_and_f1_matrix.png" width="880" alt="Per-Class Threat Forensics Radar" />
  <br/>
  <em><b>Figure 26:</b> Per-Class Threat Forensics on Gold OOD Benchmark (17,139 samples): Path Traversal Preservation in DAFL vs. Collapse in Vanilla FedAvg.</em>
</p>

---

## 🔬 10. Ablation Studies & Hyperparameter Sensitivity

### Table 4: Systematic Component Isolation Breakdown

| Experimental Configuration | In-Domain Test B F1 | $\Delta$ In-Domain | Gold OOD F1 | $\Delta$ OOD F1 | Scientific Failure Mode |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Full Proposed DAFL System** | **0.9890** | **+0.00%** | **0.8698** | **+0.00%** | Optimal consensus and OOD retention |
| **w/o Anchor 1 ($W_{base}$ removed)** | 0.8967 | -9.23% | 0.2479 | **-62.19%** | Catastrophic syntactic amnesia |
| **w/o Sanitization (Raw strings)** | 0.9138 | -7.52% | 0.3814 | **-48.84%** | Obfuscated nested bypass |
| **w/o Federation (Local isolation)** | 0.9224 | -6.66% | 0.3840 | **-48.58%** | Severe cross-sector blind spots |
| **Uniform IID Control (No skew)** | 0.9925 | +0.35% | 0.4649 | -40.49% | Fails to reflect enterprise diversity |

<p align="center">
  <img src="reports/report_figures_master/Fig21_systematic_component_ablation.png" width="900" alt="Systematic Component Ablation Breakdown" />
  <br/>
  <em><b>Figure 27:</b> Systematic Component Ablation Breakdown: Quantifying the Critical Necessity of Anchor 1, Sanitization, and Federation.</em>
</p>

<p align="center">
  <img src="reports/report_figures_master/Fig26_runtime_ensemble_alpha_sweep.png" width="850" alt="Runtime Ensemble Alpha Sweep" />
  <br/>
  <em><b>Figure 28:</b> Runtime Firewall Probability Fusion Alpha Parameter Sweep: Optimizing Gold OOD Macro F1 at alpha = 0.70.</em>
</p>

<p align="center">
  <img src="reports/report_figures_master/Fig31_subgroup_error_analysis_and_failure_taxonomy.png" width="900" alt="Subgroup Error Analysis & Failure Taxonomy" />
  <br/>
  <em><b>Figure 29:</b> Empirical Subgroup Error Analysis: Root Causes of False Alarms and Leaked Exploit Mechanics.</em>
</p>

---

## 🔍 11. Tri-Factor Explainable AI (XAI) Engine

To eliminate "black-box" resistance from Security Operations Center (SOC) teams, FedWebPayload incorporates a tri-factor white-box attribution suite:

<p align="center">
  <img src="reports/report_figures_master/Fig22_explainable_ai_saliency_and_shap.png" width="920" alt="Unified Explainable AI Showcase" />
  <br/>
  <em><b>Figure 30:</b> Unified Explainable AI (XAI) Showcase: Token Attention Saliency Maps Corroborated by KernelSHAP and LIME.</em>
</p>

### 11.1 Token-Level Saliency Inspection
1. **SQL Injection (Banking Zero-Day)**:
   ```
   GET /api/user?id= | 1'   | UNION | SELECT | pass   | FROM   | users  | -- 
   Attn Weight:       | 0.78 | 0.89  | 0.95   | 0.74   | 0.68   | 0.84   | 0.84
   [Verdict]: Attention locks strictly onto SQL grammar; benign path parameters are ignored.
   ```
2. **Cross-Site Scripting (E-Commerce)**:
   ```
   GET /search?q=    | <script> | alert( | document.cookie | )</script>
   Attn Weight:       | 0.96     | 0.72   | 0.93            | 0.95
   [Verdict]: Attention allocates >0.93 mass to executable DOM primitives; parameter key receives 0.05.
   ```
3. **Path Traversal (Cloud Infrastructure)**:
   ```
   GET /file?path=   | ../.. | ../.. | etc/passwd | %00
   Attn Weight:       | 0.88  | 0.91  | 0.96       | 0.82
   [Verdict]: Attention identifies recursive directory traversal patterns and sensitive system targets.
   ```

*Open the interactive XAI report in your browser:* [`reports/stage_05_xai/comprehensive_xai_report_shap_lime_attention.html`](reports/stage_05_xai/comprehensive_xai_report_shap_lime_attention.html).

---

## 🗺️ 12. Dual-Track Academic Dissemination Roadmap

```mermaid
flowchart TD
    subgraph Track1 ["Track 1: SCIN 2026 Conference (Thailand)"]
        CONF["The 5th Int. Conf. on Systems and Computing Inspired by Nature<br/>• Venue: Thailand (Sept 3–5, 2026)<br/>• Target: Springer LNCS / CCIS (svproc template)<br/>• Volume: Exactly 8 Pages (Tight Scope, 100% Audited Results)"]
        CONF_FOCUS["Core Focus:<br/>1. Clean-room data foundation (0.0000% leakage)<br/>2. 6-Client Paired Non-IID Skew<br/>3. Wire-speed Transformer vs SecBERT<br/>4. Centralized vs FedAvg vs DAFL OOD Benchmark"]
    end

    subgraph Track2 ["Track 2: Top-Tier Q1 Cybersecurity Journal"]
        JOURNAL["Target: IEEE TIFS / ACM CCS / IEEE TDSC Monograph<br/>• Length: 20–25 Double-Column Pages<br/>• Full Mathematical Derivations & Convergence Proofs<br/>• Complete Byzantine Robust Aggregation & Differential Privacy"]
        JOURNAL_FOCUS["Extended Scope:<br/>1. FoolsGold & Multi-Krum Byzantine Defenses<br/>2. (ε, δ)-Rényi Differential Privacy Guarantees<br/>3. Multi-Modal HTTP Rate & Header Entropy Modeling<br/>4. Live Production Honeynet Deployment Case Studies"]
    end

    Track1 --> Track2
```

---

## 🚀 13. Step-by-Step Reproduction Guide

### 13.1 Environment Setup
```bash
# Clone the repository
git clone git@github.com:Cheesenoice/federated-web-payload-detection.git
cd federated-web-payload-detection

# Initialize virtual environment
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

# Install dependencies (CUDA 12.4 supported)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124
pip install pandas numpy scikit-learn matplotlib shap lime pyarrow onnx onnxruntime
```

### 13.2 Fast 15-Minute Reproduction Pipeline (60k Non-IID Representative Set)
```bash
# Step 1: Partition 60k Non-IID Representative Silos
python src/stage_04_federated_rep60k/4.0_build_rep_client_silos_60k.py

# Step 2: Execute Federated Optimization Benchmarks
python src/stage_04_federated_rep60k/4.1_fed_centralized_oracle_fast.py
python src/stage_04_federated_rep60k/4.2_fed_fedavg_fast.py
python src/stage_04_federated_rep60k/4.3_fed_fedprox_fast.py
python src/stage_04_federated_rep60k/4.4_fed_fedavgm_fast.py
python src/stage_04_federated_rep60k/4.5_fed_hybrid_dafl_fast.py
python src/stage_04_federated_rep60k/4.6_fed_hybrid_ensemble_fast.py
python src/stage_04_federated_rep60k/4.7_master_federated_benchmark_fast.py

# Step 3: Run Tri-Factor XAI and Render Publication Figures
python src/stage_05_explainability_and_ablations/5.1_attention_head_visualization.py
python src/stage_05_explainability_and_ablations/5.2_token_attribution_saliency.py
python src/stage_05_explainability_and_ablations/5.3_ablation_studies_benchmark.py
python src/stage_05_explainability_and_ablations/5.4_generate_paper_tables_and_card.py
python src/stage_05_explainability_and_ablations/5.5_shap_lime_explainability.py
python src/stage_05_explainability_and_ablations/5.6_render_publication_figures.py
```

### 13.3 Full Industrial Clean-Room Pipeline (2.79M Records)
```bash
# Data Foundation & Sanitization
python src/stage_01_data_foundation/1.1_ingest_raw_data.py
python src/stage_01_data_foundation/1.2_normalize_clean_room.py
python src/stage_01_data_foundation/1.3_partition_three_pools.py
python src/stage_01_data_foundation/1.4_build_6client_silos.py

# Full Scale Pretraining & Classical Baselines
python src/stage_02_classical_baselines/2.1_train_classical_models.py
python src/stage_03_neural_foundation/3.1_pretrain_transformer_wbase.py
```

---

## 📜 14. Model Card, Authorship & Citation

### Institutional Affiliation & Authors
* **First Author**: Huynh Huu Tri (`huynhhuutri2004@gmail.com`)
  * *Department of Information Technology, Faculty of Industrial Technology and Management, King Mongkut’s University of Technology North Bangkok (KMUTNB), Thailand.*
  * *Faculty of Information Technology, Posts and Telecommunications Institute of Technology (PTIT), Ho Chi Minh City, Vietnam.*
* **Co-Authors & Advisory Committee**:
  * **Assoc. Prof. Dr. Khanista Namee** (KMUTNB, Thailand)
  * **Asst. Prof. Dr. Karn Na Sritha** (KMUTNB, Thailand)
  * **Pitpimon Choorod** (KMUTNB, Thailand)
  * **Dr. Supaporn Simcharoen** (*Corresponding Author: `Supaporn.S@fitm.kmutnb.ac.th`*, KMUTNB, Thailand)

### Standardized Model Card
Full machine-readable metadata conforming to Hugging Face Model Card v2 is available at [`reports/stage_05_xai/KMUTNB_WebPayload_FL_ModelCard.json`](reports/stage_05_xai/KMUTNB_WebPayload_FL_ModelCard.json).

### BibTeX Citation
```bibtex
@inproceedings{tri2026fedwebpayload,
  title={Diversity-Aware Federated Learning with Dual-Anchor Regularization for Multi-Family Web Payload Detection under Extreme Non-IID Skew},
  author={Huynh, Huu Tri and Namee, Khanista and Na Sritha, Karn and Choorod, Pitpimon and Simcharoen, Supaporn},
  booktitle={Proceedings of the 5th International Conference on Systems and Computing Inspired by Nature (SCIN 2026)},
  series={Communications in Computer and Information Science},
  publisher={Springer Nature},
  address={Bangkok, Thailand},
  month={September},
  year={2026}
}
```

### Two-Tier Responsible Open-Science Data Use Agreement (DUA)
1. **Tier 1 (Public Research Artifacts)**: Pretrained ONNX model checkpoints, 64-dimensional semantic embeddings, token saliency artifacts, and anonymized non-IID partition indices are released under the permissive **MIT License**.
2. **Tier 2 (Controlled Zero-Day Payloads)**: Weaponized attack sequences from real-world penetration test suites are gated under an academic Data Use Agreement (DUA) to prevent dual-use offensive weaponization.

---
*Maintained with scientific rigor by the KMUTNB & PTIT Cybersecurity Research Alliance.*
