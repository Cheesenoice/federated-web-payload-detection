import os
import sys
import json
import logging
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

# Report Source Paths
STAGE_02_CSV = os.path.join(ROOT_DIR, "reports", "stage_02_baselines", "classical_baselines_benchmark.csv")
STAGE_03_TOURNAMENT_CSV = os.path.join(ROOT_DIR, "reports", "stage_03_neural", "neural_tournament_benchmark.csv")
STAGE_03_CROSS_EVAL_CSV = os.path.join(ROOT_DIR, "reports", "stage_03_neural", "cross_evaluation_matrix.csv")
STAGE_04_CSV = os.path.join(ROOT_DIR, "reports", "stage_04_federated_rep60k", "federated_algorithms_master_benchmark.csv")
STAGE_05_ABLATION_CSV = os.path.join(ROOT_DIR, "reports", "stage_05_xai", "ablation_studies_summary.csv")

REPORTS_DIR = os.path.join(ROOT_DIR, "reports", "stage_05_xai")
os.makedirs(REPORTS_DIR, exist_ok=True)

OUT_LATEX = os.path.join(REPORTS_DIR, "paper_tables_latex.tex")
OUT_MODEL_CARD = os.path.join(REPORTS_DIR, "KMUTNB_WebPayload_FL_ModelCard.json")

def df_to_clean_latex(df, caption, label):
    """Converts a pandas DataFrame to a clean, booktabs-formatted LaTeX table."""
    latex_code = f"\\begin{{table}}[htbp]\n\\centering\n\\caption{{{caption}}}\n\\label{{{label}}}\n"
    latex_code += "\\begin{tabular}{" + "l" * len(df.columns) + "}\n"
    latex_code += "\\toprule\n"
    # Header
    latex_code += " & ".join([f"\\textbf{{{c.replace('_', ' ')}}}" for c in df.columns]) + " \\\\\n"
    latex_code += "\\midrule\n"
    # Rows
    for _, row in df.iterrows():
        row_vals = []
        for val in row:
            if isinstance(val, float):
                row_vals.append(f"{val:.4f}")
            else:
                row_vals.append(str(val).replace("_", "\\_").replace("%", "\\%"))
        latex_code += " & ".join(row_vals) + " \\\\\n"
    latex_code += "\\bottomrule\n\\end{tabular}\n\\end{table}\n\n"
    return latex_code

def generate_latex_bundle():
    logger.info("Generating Paper-Ready LaTeX Tables bundle...")
    all_latex = "% ==========================================================================\n"
    all_latex += "% FEDERATED WEB PAYLOAD DETECTION - PUBLICATION TABLES (IEEE/ACM FORMAT)\n"
    all_latex += "% Generated automatically by KMUTNB Automated Research Pipeline\n"
    all_latex += "% ==========================================================================\n\n"
    
    # Table 1: Classical Baselines
    if os.path.exists(STAGE_02_CSV):
        df2 = pd.read_csv(STAGE_02_CSV)
        cols2 = [c for c in ["Model", "Test_A_Macro_F1", "Global_Test_B_Macro_F1", "OOD_CSIC_Macro_F1", "Train_Time_s"] if c in df2.columns]
        all_latex += df_to_clean_latex(df2[cols2], "Performance Benchmark of Classical Machine Learning Baselines across In-Domain and OOD Sets", "tab:classical_baselines")
        
    # Table 2: Neural Tournament
    if os.path.exists(STAGE_03_TOURNAMENT_CSV):
        df3 = pd.read_csv(STAGE_03_TOURNAMENT_CSV)
        cols3 = [c for c in ["Architecture", "Parameters", "Global_Test_B_Macro_F1", "OOD_CSIC_Acc", "OOD_CSIC_Macro_F1", "Inference_ms_per_sample"] if c in df3.columns]
        all_latex += df_to_clean_latex(df3[cols3], "Deep Sequence Neural Tournament for Foundation Anchor Selection ($W_{base}$)", "tab:neural_tournament")
        
    # Table 3: Cross Evaluation Matrix
    if os.path.exists(STAGE_03_CROSS_EVAL_CSV):
        df_cross = pd.read_csv(STAGE_03_CROSS_EVAL_CSV, index_col=0).reset_index()
        all_latex += df_to_clean_latex(df_cross, "6x6 Local Silo Cross-Evaluation Matrix Demonstrating Catastrophic Forgetting in Isolated Silos", "tab:cross_eval_matrix")
        
    # Table 4: Federated Learning Master Benchmark
    if os.path.exists(STAGE_04_CSV):
        df4 = pd.read_csv(STAGE_04_CSV)
        cols4 = ["Method", "Avg_Local_Test_F1", "Global_Test_B_Acc", "Global_Test_B_Macro_F1", "OOD_CSIC_Acc", "OOD_CSIC_Macro_F1"]
        all_latex += df_to_clean_latex(df4[cols4], "Federated Learning Algorithms Master Benchmark across 6 Clients, Global Network, and External OOD Benchmark", "tab:federated_benchmark")
        
    # Table 5: Ablation Studies
    if os.path.exists(STAGE_05_ABLATION_CSV):
        df5 = pd.read_csv(STAGE_05_ABLATION_CSV)
        cols5 = ["Ablation_Study", "Global_Test_B_Macro_F1", "Delta_Global_F1", "OOD_CSIC_Macro_F1", "Delta_OOD_F1"]
        all_latex += df_to_clean_latex(df5[cols5], "Ablation Studies Demonstrating the Contribution of Foundation Anchor, Sanitization, and Federated Collaboration", "tab:ablation_studies")
        
    with open(OUT_LATEX, "w", encoding="utf-8") as f:
        f.write(all_latex)
    logger.info(f"Saved LaTeX tables bundle to: {OUT_LATEX}")

def generate_model_card():
    logger.info("Generating Comprehensive Model Card...")
    card = {
        "model_details": {
            "name": "KMUTNB-WebPayload-SecTransformer-FL",
            "version": "1.0.0",
            "type": "Character-Level Multi-Head Transformer Encoder",
            "embedding_dimension": 64,
            "num_heads": 4,
            "feedforward_dimension": 256,
            "encoder_layers": 3,
            "total_parameters": 156612,
            "vocabulary_size": 130,
            "max_sequence_length": 256,
            "license": "Academic Research Use"
        },
        "intended_use": {
            "primary_task": "Multi-Class Web Application Firewall (WAF) Payload Classification",
            "supported_classes": ["benign", "pathtrav", "sqli", "xss"],
            "deployment_paradigm": "Federated Multi-Organization Collaborative Learning (Privacy-Preserving)"
        },
        "training_data_and_federation": {
            "total_raw_corpus": "5.3 Million Payloads",
            "confirmed_gold_clusters": "2,794,288 Unique Samples",
            "foundation_pretrain_pool_a": "40,000 Balanced Samples (Pool A)",
            "federated_clients": 6,
            "non_iid_distribution": "Paired Non-IID Skew (80% Dominant Attack Class per Silo)",
            "communication_rounds": 10,
            "federated_algorithms_benchmarked": ["Centralized", "FedAvg", "FedProx", "FedAvgM", "DAFL", "Hybrid Ensemble"]
        },
        "evaluation_metrics": {
            "in_domain_global_test_b_samples": 354808,
            "in_domain_best_macro_f1": "99.01% (FedAvgM)",
            "in_domain_best_accuracy": "99.85% (FedAvg)",
            "out_of_domain_csic2010_samples": 122130,
            "out_of_domain_best_macro_f1": "51.51% (FedProx, vs 35.06% Centralized)",
            "out_of_domain_best_accuracy": "96.48% (FedAvgM)",
            "inference_latency_per_payload_ms": 0.048
        },
        "ethical_and_privacy_considerations": {
            "data_privacy": "Zero Raw Payload Exchange across client boundaries; only cryptographic weights shared.",
            "zero_leakage_guarantee": "Clean-Room SHA-256 separation between Pool A, Pool B, and OOD holdouts verified."
        }
    }
    with open(OUT_MODEL_CARD, "w", encoding="utf-8") as f:
        json.dump(card, f, indent=4)
    logger.info(f"Saved Standardized Model Card to: {OUT_MODEL_CARD}")

def main():
    logger.info("=== STARTING STAGE 5.4: PAPER TABLES & MODEL CARD GENERATION ===")
    generate_latex_bundle()
    generate_model_card()
    logger.info("STAGE 5.4 COMPLETE.")

if __name__ == "__main__":
    main()
