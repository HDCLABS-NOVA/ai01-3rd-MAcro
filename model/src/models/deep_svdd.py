from typing import Any, Dict, Tuple

import numpy as np

try:
    import torch
    from torch import nn
except Exception:
    torch = None
    nn = None


def torch_ready() -> bool:
    return torch is not None and nn is not None


class DeepSVDDNet(nn.Module):
    def __init__(self, input_dim: int, hidden_dim: int, latent_dim: int) -> None:
        super().__init__()
        mid_dim = max(8, hidden_dim // 2)
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, mid_dim),
            nn.ReLU(),
            nn.Linear(mid_dim, latent_dim),
        )

    def forward(self, x: Any) -> Any:
        return self.encoder(x)


def build_deep_svdd_net(input_dim: int, hidden_dim: int, latent_dim: int) -> Any:
    if not torch_ready():
        raise RuntimeError("PyTorch is required for Deep SVDD.")
    return DeepSVDDNet(input_dim=input_dim, hidden_dim=hidden_dim, latent_dim=latent_dim)


def bundle_from_trained_net(
    *,
    net: Any,
    center: np.ndarray,
    input_dim: int,
    hidden_dim: int,
    latent_dim: int,
) -> Dict[str, Any]:
    if not torch_ready():
        raise RuntimeError("PyTorch is required for Deep SVDD.")
    state_dict = {k: v.detach().cpu() for k, v in net.state_dict().items()}
    return {
        "kind": "deep_svdd_v1",
        "input_dim": int(input_dim),
        "hidden_dim": int(hidden_dim),
        "latent_dim": int(latent_dim),
        "state_dict": state_dict,
        "center": np.array(center, dtype=np.float32),
    }


def load_runtime_from_bundle(bundle: Dict[str, Any]) -> Tuple[Any, np.ndarray]:
    if not torch_ready():
        raise RuntimeError("PyTorch is required for Deep SVDD.")
    input_dim = int(bundle.get("input_dim", 0))
    hidden_dim = int(bundle.get("hidden_dim", 0))
    latent_dim = int(bundle.get("latent_dim", 0))
    state_dict = bundle.get("state_dict")
    center = np.array(bundle.get("center", []), dtype=np.float32)
    if input_dim <= 0 or hidden_dim <= 0 or latent_dim <= 0 or not isinstance(state_dict, dict):
        raise ValueError("Invalid Deep SVDD bundle")

    net = build_deep_svdd_net(input_dim=input_dim, hidden_dim=hidden_dim, latent_dim=latent_dim)
    net.load_state_dict(state_dict)
    net.eval()
    return net, center


def score_with_runtime(net: Any, center: np.ndarray, x_scaled: np.ndarray) -> np.ndarray:
    if not torch_ready():
        raise RuntimeError("PyTorch is required for Deep SVDD.")
    xs = np.array(x_scaled, dtype=np.float32)
    center_arr = np.array(center, dtype=np.float32)
    with torch.no_grad():
        x_tensor = torch.from_numpy(xs)
        z = net(x_tensor)
        center_tensor = torch.from_numpy(center_arr).to(z.device)
        raw = ((z - center_tensor) ** 2).sum(dim=1).cpu().numpy()
    return raw


def score_from_bundle(bundle: Dict[str, Any], x_scaled: np.ndarray) -> np.ndarray:
    net, center = load_runtime_from_bundle(bundle)
    return score_with_runtime(net, center, x_scaled)

