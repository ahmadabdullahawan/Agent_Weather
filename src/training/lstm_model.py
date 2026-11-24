"""Deep-learning family: LSTM (plan.md task 3). One model per metric,
same reasoning as the other two families.

Each training example is a 48-hour lookback window over the shared
tabular feature set (src/training/features.py), predicting that
metric's 24h-ahead target from the window's last ("now") hour. 48h
(two days) rather than 24h was chosen so the network sees a full prior
daily cycle to compare against, which matters for metrics with a
strong diurnal pattern (e.g. temperature -- see reports/eda.md).

Inputs are standardized and targets z-scored (both fit on train only)
purely for training stability with this small a network over few
epochs -- predictions are converted back to the metric's own units
before being returned.
"""

import numpy as np
import torch
from sklearn.preprocessing import StandardScaler
from torch import nn

LOOKBACK_HOURS = 48
HIDDEN_SIZE = 32
EPOCHS = 20
LEARNING_RATE = 1e-3
BATCH_SIZE = 64


class _Net(nn.Module):
    def __init__(self, n_features: int):
        super().__init__()
        self.lstm = nn.LSTM(n_features, HIDDEN_SIZE, batch_first=True)
        self.head = nn.Linear(HIDDEN_SIZE, 1)

    def forward(self, x):
        _, (h_n, _) = self.lstm(x)
        return self.head(h_n[-1]).squeeze(-1)


def _make_windows(X: np.ndarray, y: np.ndarray, lookback: int = LOOKBACK_HOURS):
    windows, targets = [], []
    for end in range(lookback - 1, len(X)):
        if np.isnan(y[end]):
            continue
        windows.append(X[end - lookback + 1 : end + 1])
        targets.append(y[end])
    if not windows:
        return np.empty((0, lookback, X.shape[1])), np.empty(0)
    return np.stack(windows), np.array(targets)


def fit(X_train: np.ndarray, y_train: np.ndarray):
    scaler = StandardScaler().fit(X_train)
    windows, targets = _make_windows(scaler.transform(X_train), y_train)
    if len(windows) < BATCH_SIZE:
        return None  # not enough real history for even one training batch

    target_mean, target_std = targets.mean(), targets.std() or 1.0
    targets_scaled = (targets - target_mean) / target_std

    net = _Net(X_train.shape[1])
    optimizer = torch.optim.Adam(net.parameters(), lr=LEARNING_RATE)
    loss_fn = nn.MSELoss()
    dataset = torch.utils.data.TensorDataset(
        torch.tensor(windows, dtype=torch.float32),
        torch.tensor(targets_scaled, dtype=torch.float32),
    )
    loader = torch.utils.data.DataLoader(dataset, batch_size=BATCH_SIZE, shuffle=True)

    net.train()
    for _ in range(EPOCHS):
        for xb, yb in loader:
            optimizer.zero_grad()
            loss = loss_fn(net(xb), yb)
            loss.backward()
            optimizer.step()

    return {"net": net, "scaler": scaler, "target_mean": target_mean, "target_std": target_std}


def predict(bundle, X: np.ndarray) -> np.ndarray:
    """Predicts for every row with a full 48h lookback available in X
    (rows before that -- including all of a cold-started split -- get
    NaN). Callers should pass the FULL chronological feature matrix
    (train+val+test), not a split alone, so validation/test rows near
    the split boundary still get real lookback context from train."""
    n = len(X)
    preds = np.full(n, np.nan)
    if bundle is None:
        return preds

    X_scaled = bundle["scaler"].transform(X)
    windows, valid_idx = [], []
    for end in range(LOOKBACK_HOURS - 1, n):
        windows.append(X_scaled[end - LOOKBACK_HOURS + 1 : end + 1])
        valid_idx.append(end)
    if not windows:
        return preds

    net = bundle["net"]
    net.eval()
    with torch.no_grad():
        out = net(torch.tensor(np.stack(windows), dtype=torch.float32)).numpy()
    preds[valid_idx] = out * bundle["target_std"] + bundle["target_mean"]
    return preds
