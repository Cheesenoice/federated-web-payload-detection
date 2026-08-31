# 🛡️ Federated Web Payload Detection: Robust Sequence Transformers under Extreme Non-IID Skew

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![PyTorch 2.6](https://img.shields.io/badge/PyTorch-2.6-EE4C2C.svg)](https://pytorch.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Research: KMUTNB](https://img.shields.io/badge/Research-KMUTNB%20Cybersecurity-purple.svg)](https://kmutnb.ac.th/)

> **Official Research Artifact & Codebase** for privacy-preserving federated web application firewall (WAF) payload classification, benchmarked against classical baselines, deep sequence models, and out-of-domain (OOD) evasion attacks.

---

## 📌 1. Overview & Key Contributions

Cross-organization collaborative defense against web application attacks (such as **Cross-Site Scripting [XSS]**, **SQL Injection [SQLi]**, and **Path Traversal**) is severely hampered by enterprise privacy constraints and statistical data heterogeneity (Non-IID skew).

This repository presents **FedWebPayload**, an end-to-end framework featuring:
1. **Clean-Room Two-Tier Data Foundation:** Curated from 5.3 million raw payloads into **2.79 million verified gold clusters** using OWASP CRS v4 regex consensus, with complete cryptographic zero-leakage separation across Pretrain (Pool A), Federated Silos (Pool B), and External OOD holdout (CSIC 2010).
2. **Deep Sequence Modeling & Foundation Anchor ($W_{base}$):** Multi-Scale 1D CharCNN, Bi-LSTM + Attention, and Character-level Transformer Encoders. The Transformer Champion achieves **93.8% Zero-Shot OOD Accuracy** and is frozen as the universal anchor.
3. **Federated Optimization Suite:** Rigorous empirical comparison of 5 federated algorithms (**Centralized Oracle**, **Standard FedAvg**, **FedProx**, **FedAvgM**, **Dual-Anchor FL [DAFL - Ours]**, and **Hybrid Ensemble**).
4. **Out-of-Domain (OOD) Discovery:** Proves that **Federated Learning outperforms Centralized Learning on zero-shot OOD robustness** (Centralized collapses to 21.09% Acc due to in-domain overfitting, while FedProx reaches 84.46% and Hybrid Ensemble reaches 95.64%).
5. **Tri-Factor Explainable AI (XAI):** Character-level Multi-Head Self-Attention Heatmaps, Gradient Saliency, **SHAP (KernelSHAP)** Shapley value waterfalls, and **LIME** local surrogate linear models.

---

## 📂 2. Repository Structure

```
.
├── src/
│   ├── stage_01_data_foundation/             # Clean-room pipeline: regex verification, pooling, 6-client non-IID splits
│   ├── stage_02_classical_baselines/          # TF-IDF + Lexical feature pipeline (LR, SVM, RF, XGBoost GPU)
│   ├── stage_03_neural_foundation/            # CharCNN, Bi-LSTM, Transformer pretraining & 6x6 Silo benchmarks
│   ├── stage_04_federated_learning/           # Full-scale industrial federated learning suite (1.32M samples)
│   ├── stage_04_federated_rep60k/             # Fast representative benchmark suite (60k Non-IID samples, 15-min run)
│   └── stage_05_explainability_and_ablations/ # Attention heatmaps, Saliency, SHAP, LIME & Ablation studies
├── reports/
│   ├── publication_figures/                   # 300 DPI IEEE/ACM-ready figures
│   │   ├── fig1_federated_convergence_curves.png
│   │   ├── fig2_generalization_gap_indomain_vs_ood.png
│   │   ├── fig3_cross_evaluation_heatmap.png
│   │   ├── fig4_ablation_studies_breakdown.png
│   │   └── fig5_unified_xai_showcase.png
│   ├── stage_05_xai/
│   │   ├── comprehensive_xai_report_shap_lime_attention.html # Interactive HTML XAI report
│   │   ├── paper_tables_latex.tex             # Ready-to-paste LaTeX tables (Tables 1 to 5)
│   │   └── KMUTNB_WebPayload_FL_ModelCard.json # Standardized Model Card
│   └── stage_04_federated_rep60k/             # Benchmark CSVs and convergence logs
└── README.md
```

---

## 📊 3. Master Empirical Benchmark (Publication Tables)

### Table 4: Federated Learning Algorithms Master Comparison
*Evaluated across 6 Client Tests, Global Test B (354,808 samples), and External OOD CSIC 2010 (122,130 samples).*

| Method / Algorithm | Paradigm | Avg Local Test F1 | Global Test B Acc | Global Test B F1 | OOD CSIC Acc | OOD CSIC Macro F1 |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| 🏛️ **Centralized Oracle** | Centralized Upper Bound | 0.9703 | 99.80% | 0.9866 | 21.09% | 0.3506 |
| ⚓ **Foundation $W_{base}$** | Anchor Pre-train | 0.9689 | 99.76% | 0.9833 | 93.80% | 0.4567 |
| 🥇 **FedAvgM ($\beta=0.9$)** | FL + Server Momentum | **0.9794** | **99.83%** | **0.9901** | **96.48%** | 0.4432 |
| 🥈 **Standard FedAvg** | Standard FL (McMahan) | 0.9793 | **99.85%** | 0.9890 | 95.49% | 0.4859 |
| 🥉 **Hybrid Ensemble** | Dual Intelligence (Ours) | 0.9777 | 99.84% | 0.9888 | 95.64% | **0.5029** |
| 🏅 **FedProx ($\mu=0.01$)** | FL + Proximal Penalty | 0.9745 | 99.83% | 0.9873 | 84.46% | **0.5151** |
| 🏅 **DAFL ($\lambda=0.02$)** | Dual-Anchor FL (Ours) | 0.9714 | 99.78% | 0.9844 | 94.59% | 0.4777 |

---

### Table 5: Scientific Ablation Studies Analysis

| Ablation Study | Configuration | Global Test B F1 | $\Delta$ Global F1 | OOD CSIC F1 | $\Delta$ OOD F1 | Key Scientific Insight |
| :--- | :--- | :---: | :---: | :---: | :---: | :--- |
| **Full Proposed System** | Default ($W_{base}$ + 3-Pass + FL) | **0.9890** | **+0.00%** | **0.4859** | **+0.00%** | Optimal balance of consensus and zero-shot OOD generalization. |
| **Ablation 1: No Anchor** | Random Initialization (No $W_{base}$) | 0.8967 | **-9.23%** | 0.2479 | **-23.80%** | Proves $W_{base}$ stabilizes non-IID client gradient divergence. |
| **Ablation 2: No Sanitization** | Raw Encoded Strings (No URL decode) | 0.9138 | **-7.52%** | 0.3814 | **-10.45%** | Obfuscated evasions easily bypass detection without decoding. |
| **Ablation 3: No Federated Sharing** | Isolated Local Client Silos | 0.9224 | **-6.66%** | 0.3840 | **-10.19%** | Isolated clients suffer severe catastrophic forgetting. |
| **Ablation 4: Uniform IID Partitions** | Synthetic Uniform Data Partitions | 0.9925 | +0.35% | 0.4649 | -2.10% | IID simplifies optimization but reduces cross-domain diversity. |

---

## 🎨 4. Explainable AI (XAI) Showcase

The framework generates character-level interpretability artifacts demonstrating why the Transformer classifies attack vectors:

*   **Self-Attention Maps:** Highlights attention heads focusing on `<script>`, `UNION SELECT`, and `../../`.
*   **SHAP Waterfall Values:** Evaluates marginal Shapley attributions ($\phi_i$) for individual tokens.
*   **LIME Surrogates:** Measures prediction shifts across 200 local perturbations.
*   **Interactive HTML Report:** Open `reports/stage_05_xai/comprehensive_xai_report_shap_lime_attention.html` in any browser.

---

## 🚀 5. Quickstart & Reproducibility

### Installation
```bash
git clone git@github.com:Cheesenoice/federated-web-payload-detection.git
cd federated-web-payload-detection

python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124
pip install pandas numpy scikit-learn matplotlib shap lime pyarrow
```

### Reproducing Stage 4 & 5 (Fast 15-Minute Pipeline)
```bash
# 1. Generate 60k Non-IID Representative Silos
python src/stage_04_federated_rep60k/4.0_build_rep_client_silos_60k.py

# 2. Run Federated Benchmark
python src/stage_04_federated_rep60k/4.1_fed_centralized_oracle_fast.py
python src/stage_04_federated_rep60k/4.2_fed_fedavg_fast.py
python src/stage_04_federated_rep60k/4.3_fed_fedprox_fast.py
python src/stage_04_federated_rep60k/4.4_fed_fedavgm_fast.py
python src/stage_04_federated_rep60k/4.5_fed_hybrid_dafl_fast.py
python src/stage_04_federated_rep60k/4.6_fed_hybrid_ensemble_fast.py
python src/stage_04_federated_rep60k/4.7_master_federated_benchmark_fast.py

# 3. Run Explainable AI & Ablations
python src/stage_05_explainability_and_ablations/5.1_attention_head_visualization.py
python src/stage_05_explainability_and_ablations/5.2_token_attribution_saliency.py
python src/stage_05_explainability_and_ablations/5.3_ablation_studies_benchmark.py
python src/stage_05_explainability_and_ablations/5.4_generate_paper_tables_and_card.py
python src/stage_05_explainability_and_ablations/5.5_shap_lime_explainability.py
python src/stage_05_explainability_and_ablations/5.6_render_publication_figures.py
```

---

## 📜 6. Model Card & Citation

Model card metadata is available at [`reports/stage_05_xai/KMUTNB_WebPayload_FL_ModelCard.json`](reports/stage_05_xai/KMUTNB_WebPayload_FL_ModelCard.json).

```bibtex
@article{kmutnb_fedwebpayload_2026,
  title={Towards OOD-Resilient Web Attack Detection via Dual-Anchor Federated Sequence Modeling},
  author={KMUTNB Cybersecurity Research Team},
  journal={IEEE Transactions on Information Forensics and Security / ACM Conference on Computer and Communications Security},
  year={2026}
}
```

---

## 📄 License
This research codebase is released under the **MIT License**.
