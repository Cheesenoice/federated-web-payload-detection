"""
Loss Functions & Imbalance Objectives (`src/training/losses.py`)

Implements specialized loss objectives for federated learning under Non-IID label skew:
  - FedLC Calibrated Cross-Entropy (Zhang et al. ICML 2022) with Laplace Smoothing
  - Class-Weighted Focal Loss (gamma = 2.0)
"""

import torch
import torch.nn as nn
import torch.nn.functional as F


class FedLCCalibratedLoss(nn.Module):
    """
    FedLC (Zhang et al. ICML 2022) Logit-Calibrated Cross-Entropy Loss:
    Applies smooth client-local shift offset: z_j - tau * n_j^(-1/4)
    Uses Laplace/prior smoothing (min_count=10.0) to prevent gradient explosion on missing classes.
    """
    def __init__(self, class_counts: torch.Tensor, tau: float = 0.5, weight: torch.Tensor = None, min_count: float = 10.0):
        super().__init__()
        counts = torch.as_tensor(class_counts, dtype=torch.float32)
        # Apply smoothing for zero-count missing classes
        smoothed_counts = torch.clamp(counts, min=min_count)
        self.tau = float(tau)
        self.register_buffer("class_counts", counts)
        self.register_buffer("smoothed_counts", smoothed_counts)
        self.register_buffer("class_weight", weight)

    def forward(self, logits: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
        # Compute smooth logit offset margin
        offsets = self.tau * self.smoothed_counts.pow(-0.25)
        calibrated_logits = logits - offsets.to(logits.device)
        return F.cross_entropy(calibrated_logits, target, weight=self.class_weight)


class FocalLoss(nn.Module):
    """Class-Weighted Focal Loss for severe class imbalance."""
    def __init__(self, gamma: float = 2.0, weight: torch.Tensor = None):
        super().__init__()
        self.gamma = gamma
        self.register_buffer("weight", weight)

    def forward(self, logits: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
        ce_loss = F.cross_entropy(logits, target, weight=self.weight, reduction="none")
        pt = torch.exp(-ce_loss)
        focal_loss = ((1 - pt) ** self.gamma) * ce_loss
        return focal_loss.mean()
