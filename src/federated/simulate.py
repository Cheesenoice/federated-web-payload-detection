"""
Federated Simulation & FL Benchmark Orchestrator (`src/federated/simulate.py`)

Executes multi-round federated learning simulations across all 6 Non-IID client datasets
and evaluates global model performance on Global In-Domain & Out-of-Domain Test Sets.

Evaluated Algorithms:
  1. FedAvg (McMahan et al. 2017)
  2. FedProx (Li et al. 2020)
  3. FedLC (Zhang et al. ICML 2022)
  4. FedPayload-DAFL (PROPOSED METHOD)

Outputs:
  - `data/reporting/federated_benchmark_matrix.json`
"""

import os
import sys
import json
import logging
import torch
import numpy as np
import pandas as pd
from torch.utils.data import TensorDataset, DataLoader

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.models.charcnn import CharCNN
from src.features.tokenizer import CharTokenizer
from src.training.trainer import evaluate_model_pytorch, LABEL_MAP
from src.federated.client import PayloadFlowerClient, set_model_parameters, get_model_parameters
from src.federated.aggregate import aggregate_fedavg, aggregate_dafl

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data"))
SPLITS_DIR = os.path.join(DATA_DIR, "splits")
FEATURES_DIR = os.path.join(DATA_DIR, "features")
REPORTING_DIR = os.path.join(DATA_DIR, "reporting")

os.makedirs(REPORTING_DIR, exist_ok=True)


def run_federated_simulation_experiment(rounds: int = 10, local_epochs: int = 2):
    logger.info("=== STARTING PHASE 5: FEDERATED LEARNING BENCHMARK SIMULATION ===")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info(f"Hardware Accelerator: {device}")

    # 1. Load Global In-Domain Test Set & Features
    df_test = pd.read_parquet(os.path.join(SPLITS_DIR, "test_indomain.parquet"))
    y_test = np.array([LABEL_MAP.get(lbl, 0) for lbl in df_test["label_multiclass"]])
    test_tokens = np.load(os.path.join(FEATURES_DIR, "test_indomain_tokens.npy"))
    test_dataset = TensorDataset(torch.from_numpy(test_tokens).long(), torch.from_numpy(y_test).long())
    test_loader = DataLoader(test_dataset, batch_size=128, shuffle=False)

    # Load Client Token Datasets & Class Distributions
    client_datasets = []
    client_class_counts = []
    for c_id in range(1, 7):
        df_c = pd.read_parquet(os.path.join(SPLITS_DIR, f"client_{c_id}.parquet"))
        y_c = np.array([LABEL_MAP.get(lbl, 0) for lbl in df_c["label_multiclass"]])
        c_tokens = np.load(os.path.join(FEATURES_DIR, f"client_{c_id}_tokens.npy"))

        ds = TensorDataset(torch.from_numpy(c_tokens).long(), torch.from_numpy(y_c).long())
        client_datasets.append(ds)

        # Count occurrences for classes 0, 1, 2, 3
        counts = [int((y_c == i).sum()) for i in range(4)]
        client_class_counts.append(torch.tensor(counts, dtype=torch.float32))

    algorithms = ["FedAvg", "FedProx", "FedLC", "FedPayload-DAFL"]
    benchmark_results = {}

    for algo in algorithms:
        logger.info(f"\n==================================================")
        logger.info(f"🚀 Running FL Simulation Algorithm: {algo}")
        logger.info(f"==================================================")

        # Initialize global model from W_general pre-trained weights
        global_model = CharCNN(vocab_size=128, num_classes=4).to(device)
        w_gen_path = os.path.join(DATA_DIR, "models", "w_general_charcnn.pt")
        if os.path.exists(w_gen_path):
            logger.info(f"Initializing global model with W_general base weights: {w_gen_path}")
            global_model.load_state_dict(torch.load(w_gen_path, map_location=device))
        global_params = get_model_parameters(global_model)

        round_history = []

        for r in range(1, rounds + 1):
            client_results = []

            for c_idx in range(6):
                # Instantiate client model
                client_model = CharCNN(vocab_size=128, num_classes=4)
                c_loader = DataLoader(client_datasets[c_idx], batch_size=64, shuffle=True)

                fl_client = PayloadFlowerClient(
                    client_id=c_idx + 1,
                    model=client_model,
                    train_loader=c_loader,
                    val_loader=test_loader,
                    class_counts=client_class_counts[c_idx],
                    device=device,
                    strategy_name=algo,
                    epochs=local_epochs
                )

                # Fit local client
                updated_params, n_k, metrics = fl_client.fit(global_params, config={})
                client_results.append((updated_params, n_k, metrics))

            # Aggregate parameters
            if algo == "FedPayload-DAFL":
                global_params = aggregate_dafl(client_results, alpha=1.0, beta=0.5, gamma=1.5)
            else:
                global_params = aggregate_fedavg(client_results)

            # Evaluate Global Model on In-Domain Test Set
            set_model_parameters(global_model, global_params)
            eval_metrics = evaluate_model_pytorch(global_model, test_loader, device)

            logger.info(
                f"[{algo}] Round {r:02d}/{rounds:02d} -> "
                f"Macro-F1: {eval_metrics['macro_f1']:.4f} | "
                f"Recall SQLi: {eval_metrics['recall_sqli']:.4f} | "
                f"Recall PathTrav: {eval_metrics['recall_pathtrav']:.4f} | "
                f"Recall XSS: {eval_metrics['recall_xss']:.4f}"
            )
            round_history.append(eval_metrics)

        # Final Round Metrics
        final_metrics = round_history[-1]
        benchmark_results[algo] = {
            "final_metrics": final_metrics,
            "round_history": round_history
        }

    # Save Benchmark Matrix Report JSON
    out_path = os.path.join(REPORTING_DIR, "federated_benchmark_matrix.json")
    with open(out_path, "w") as f:
        json.dump(benchmark_results, f, indent=2)
    logger.info(f"Saved federated benchmark results to {out_path}")

    # Print Final Summary Comparison Table
    print("\n" + "="*85)
    print("FINAL FEDERATED LEARNING BENCHMARK MATRIX REPORT (SCIN-2026 BENCHMARK)")
    print("="*85)
    print(f"{'FL Algorithm':<18} | {'Macro-F1':<10} | {'Recall-SQLi':<12} | {'Recall-Path':<12} | {'Recall-XSS':<10} | {'Status':<10}")
    print("-" * 85)
    for algo in algorithms:
        m = benchmark_results[algo]["final_metrics"]
        status = "PROPOSED" if algo == "FedPayload-DAFL" else "Baseline"
        print(f"{algo:<18} | {m['macro_f1']:<10.4f} | {m['recall_sqli']:<12.4f} | {m['recall_pathtrav']:<12.4f} | {m['recall_xss']:<10.4f} | {status:<10}")
    print("="*85 + "\n")


if __name__ == "__main__":
    run_federated_simulation_experiment(rounds=10, local_epochs=2)
