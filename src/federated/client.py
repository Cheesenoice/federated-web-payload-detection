"""
Federated Learning Client Wrapper (`src/federated/client.py`)

Implements PyTorch Flower NumPyClient for local client training under Non-IID distributions.
Supports local objectives:
  - Standard Cross-Entropy (FedAvg)
  - Proximal Loss Penalty (FedProx)
  - Logit-Calibrated Focal Loss (FedLC / Proposed DAFL)
"""

import logging
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
import flwr as fl

from src.training.losses import FedLCCalibratedLoss, FocalLoss

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def get_model_parameters(model: nn.Module) -> list[np.ndarray]:
    """Extracts model weights as a list of NumPy arrays for Flower serialization."""
    return [val.cpu().numpy() for _, val in model.state_dict().items()]


def set_model_parameters(model: nn.Module, parameters: list[np.ndarray]) -> None:
    """Sets model weights from a list of NumPy arrays."""
    params_dict = zip(model.state_dict().keys(), parameters)
    state_dict = {k: torch.tensor(v) for k, v in params_dict}
    model.load_state_dict(state_dict, strict=True)


class PayloadFlowerClient(fl.client.NumPyClient):
    """Flower NumPyClient for federated payload classification training."""
    def __init__(
        self,
        client_id: int,
        model: nn.Module,
        train_loader: DataLoader,
        val_loader: DataLoader,
        class_counts: torch.Tensor,
        device: torch.device,
        strategy_name: str = "FedAvg",
        epochs: int = 2,
        lr: float = 1e-3,
        proximal_mu: float = 0.01,
        tau: float = 0.5
    ):
        self.client_id = client_id
        self.model = model.to(device)
        self.train_loader = train_loader
        self.val_loader = val_loader
        self.class_counts = class_counts.to(device)
        self.device = device
        self.strategy_name = strategy_name
        self.epochs = epochs
        self.lr = lr
        self.proximal_mu = proximal_mu
        self.tau = tau

    def get_parameters(self, config) -> list[np.ndarray]:
        return get_model_parameters(self.model)

    def fit(self, parameters: list[np.ndarray], config) -> tuple[list[np.ndarray], int, dict]:
        set_model_parameters(self.model, parameters)
        global_params = [p.clone().detach().to(self.device) for p in self.model.parameters()]
        
        optimizer = torch.optim.AdamW(self.model.parameters(), lr=self.lr, weight_decay=1e-4)

        # Select Loss Objective
        if self.strategy_name in ["FedLC", "FedPayload-DAFL"]:
            loss_fn = FedLCCalibratedLoss(self.class_counts, tau=self.tau)
        else:
            loss_fn = nn.CrossEntropyLoss()

        self.model.train()
        for epoch in range(self.epochs):
            for x_batch, y_batch in self.train_loader:
                x_batch, y_batch = x_batch.to(self.device), y_batch.to(self.device)
                optimizer.zero_grad()
                logits = self.model(x_batch)
                loss = loss_fn(logits, y_batch)

                # Add FedProx proximal term: (mu / 2) * || w - w_t ||^2
                if self.strategy_name == "FedProx":
                    prox_term = 0.0
                    for w, w_t in zip(self.model.parameters(), global_params):
                        prox_term += (w - w_t).norm(2) ** 2
                    loss += (self.proximal_mu / 2.0) * prox_term

                loss.backward()
                optimizer.step()

        # Compute local metrics
        num_samples = len(self.train_loader.dataset)
        updated_params = get_model_parameters(self.model)
        metrics = {
            "client_id": self.client_id,
            "sample_count": num_samples,
            "class_counts": self.class_counts.cpu().numpy().tolist()
        }

        return updated_params, num_samples, metrics

    def evaluate(self, parameters: list[np.ndarray], config) -> tuple[float, int, dict]:
        set_model_parameters(self.model, parameters)
        self.model.eval()
        loss_fn = nn.CrossEntropyLoss()

        total_loss = 0.0
        correct = 0
        total = 0

        with torch.no_grad():
            for x_batch, y_batch in self.val_loader:
                x_batch, y_batch = x_batch.to(self.device), y_batch.to(self.device)
                logits = self.model(x_batch)
                loss = loss_fn(logits, y_batch)
                total_loss += loss.item() * len(y_batch)
                preds = torch.argmax(logits, dim=1)
                correct += (preds == y_batch).sum().item()
                total += len(y_batch)

        avg_loss = total_loss / max(1, total)
        acc = correct / max(1, total)
        return avg_loss, total, {"accuracy": acc}
