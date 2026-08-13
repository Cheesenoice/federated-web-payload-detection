"""
Federated Aggregation Engine (`src/federated/aggregate.py`)

Implements server-side aggregation strategies:
  1. FedAvg: Standard sample-size ratio parameter averaging
  2. FedProx: Proximal-regularized parameter averaging
  3. FedLC: Logit-calibrated parameter averaging
  4. FedPayload-DAFL (PROPOSED METHOD): Dynamic Entropy-Aware Coverage Aggregation Score (s_k)
"""

import logging
import numpy as np
import torch

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def aggregate_fedavg(results: list[tuple[list[np.ndarray], int, dict]]) -> list[np.ndarray]:
    """Standard FedAvg: Weighted average of model parameters by sample count n_k."""
    total_samples = sum(n_k for _, n_k, _ in results)
    if total_samples == 0:
        return results[0][0]

    # Initialize zero weights matching parameter shapes
    avg_weights = [np.zeros_like(param) for param in results[0][0]]

    for params, n_k, _ in results:
        weight = n_k / total_samples
        for i, param in enumerate(params):
            avg_weights[i] += param * weight

    return avg_weights


def compute_client_dafl_score(
    n_k: int,
    class_counts: list[int],
    alpha: float = 1.0,
    beta: float = 0.5,
    gamma: float = 1.5
) -> float:
    """
    Computes Proposed DAFL Coverage Score (s_k):
      s_k = alpha * log(1 + n_k) + beta * Entropy(class_counts) + gamma * Coverage(Rare_Classes)
    Boosts clients capturing rare PathTraversal and SQLi payloads.
    """
    counts = np.array(class_counts, dtype=np.float32)
    total_c = counts.sum()
    if total_c == 0:
        return 1e-5

    probs = counts / total_c
    probs_pos = probs[probs > 0]
    # Shannon Entropy D_k
    entropy_D_k = -np.sum(probs_pos * np.log2(probs_pos))

    # Rare Attack Coverage Ratio C_k (PathTrav = index 3, SQLi = index 2)
    rare_coverage_C_k = (counts[3] + counts[2]) / total_c

    s_k = alpha * np.log(1 + n_k) + beta * entropy_D_k + gamma * rare_coverage_C_k
    return float(s_k)


def aggregate_dafl(
    results: list[tuple[list[np.ndarray], int, dict]],
    alpha: float = 0.5,
    beta: float = 0.5,
    gamma: float = 3.0,
    temp: float = 5.0
) -> list[np.ndarray]:
    """
    Proposed Method (FedPayload-DAFL Aggregation):
    Aggregates client parameters using softmax over DAFL coverage scores s_k.
    """
    scores = []
    for _, n_k, metrics in results:
        counts = metrics.get("class_counts", [1, 1, 1, 1])
        s_k = compute_client_dafl_score(n_k, counts, alpha=alpha, beta=beta, gamma=gamma)
        scores.append(s_k)

    scores_arr = np.array(scores, dtype=np.float32) / temp
    # Softmax normalization for global weights w_k
    exp_scores = np.exp(scores_arr - np.max(scores_arr))
    weights = exp_scores / np.sum(exp_scores)

    avg_weights = [np.zeros_like(param) for param in results[0][0]]
    for (params, _, _), w_k in zip(results, weights):
        for i, param in enumerate(params):
            avg_weights[i] += param * w_k

    return avg_weights
