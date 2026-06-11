from __future__ import annotations

import os
import random

import numpy as np


def set_global_seed(seed: int) -> None:
    seed = abs(int(seed)) % (2**31 - 1)
    if seed == 0:
        seed = 1

    os.environ["PYTHONHASHSEED"] = str(seed)
    random.seed(seed)

    rng = np.random.RandomState(seed)
    np.random.set_state(rng.get_state())

    try:
        import torch

        torch.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False
    except Exception:
        pass
