from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from app.core.session_store import SessionStore
from app.utils.plots import save_line_plot, save_violin_compare
from app.utils.seed import set_global_seed


def gan_augment(
    session_id: str,
    store: SessionStore,
    df: pd.DataFrame,
    features: list[str],
    target: str,
    seed: int,
    epochs: int,
    latent_dim: int,
    batch_size: int,
    n_generate: int,
) -> dict[str, Any]:
    set_global_seed(seed)
    cols = list(dict.fromkeys(features + [target]))
    data = df[cols].dropna().copy()
    if len(data) < 8:
        raise ValueError("GAN needs at least 8 non-missing rows")

    try:
        import torch
        import torch.nn as nn
        from sklearn.preprocessing import MinMaxScaler
    except Exception as e:
        raise RuntimeError("GAN augmentation requires optional dependency 'torch'") from e

    scaler = MinMaxScaler(feature_range=(-1, 1))
    x = scaler.fit_transform(data.values).astype(np.float32)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    input_dim = x.shape[1]

    class Generator(nn.Module):
        def __init__(self):
            super().__init__()
            self.net = nn.Sequential(
                nn.Linear(latent_dim, 64),
                nn.LeakyReLU(0.2),
                nn.Dropout(0.1),
                nn.Linear(64, input_dim),
                nn.Tanh(),
            )

        def forward(self, z):
            return self.net(z)

    class Discriminator(nn.Module):
        def __init__(self):
            super().__init__()
            self.net = nn.Sequential(
                nn.Linear(input_dim, 64),
                nn.LeakyReLU(0.2),
                nn.Dropout(0.1),
                nn.Linear(64, 1),
                nn.Sigmoid(),
            )

        def forward(self, x_):
            return self.net(x_)

    G = Generator().to(device)
    D = Discriminator().to(device)

    opt_g = torch.optim.Adam(G.parameters(), lr=1e-4, betas=(0.5, 0.9))
    opt_d = torch.optim.Adam(D.parameters(), lr=1e-4, betas=(0.5, 0.9))
    bce = nn.BCELoss()

    x_t = torch.from_numpy(x).to(device)

    def sample_real(n: int):
        idx = torch.randint(0, x_t.shape[0], (n,), device=device)
        return x_t[idx]

    d_losses = []
    g_losses = []
    for ep in range(int(epochs)):
        # discriminator
        real = sample_real(batch_size)
        z = torch.randn(batch_size, latent_dim, device=device)
        fake = G(z).detach()
        d_real = D(real)
        d_fake = D(fake)
        real_label = 0.9
        fake_label = 0.1
        loss_d = 0.5 * (bce(d_real, torch.full_like(d_real, real_label, device=device)) +bce(d_fake, torch.full_like(d_fake, fake_label, device=device)))
        opt_d.zero_grad()
        loss_d.backward()
        opt_d.step()

        # generator
        for _ in range(2):
            z = torch.randn(batch_size, latent_dim, device=device)
            gen = G(z)
            d_gen = D(gen)
            loss_g = bce(d_gen, torch.ones_like(d_gen))
            opt_g.zero_grad()
            loss_g.backward()
            opt_g.step()

        if (ep + 1) % max(1, epochs // 20) == 0:
            store.append_log(session_id, f"[step6] epoch={ep+1}/{epochs} d={loss_d.item():.4f} g={loss_g.item():.4f}")
        d_losses.append(float(loss_d.item()))
        g_losses.append(float(loss_g.item()))

    loss_csv = store.artifact_path(session_id, "step6_gan_losses.csv")
    pd.DataFrame(
        {
            "epoch": np.arange(1, len(d_losses) + 1),
            "d_loss": d_losses,
            "g_loss": g_losses,
        }
    ).to_csv(loss_csv, index=False, encoding="utf-8-sig")

    loss_png = store.artifact_path(session_id, "step6_gan_losses.png")
    save_line_plot(
        loss_png,
        [("D loss", d_losses), ("G loss", g_losses)],
        title="GAN Training Loss",
        xlabel="Epoch",
        ylabel="Loss",
    )

    with torch.no_grad():
        z = torch.randn(int(n_generate), latent_dim, device=device)
        gen = G(z).cpu().numpy()

    gen_inv = scaler.inverse_transform(gen)
    gen_df = pd.DataFrame(gen_inv, columns=cols)

    store.write_df(session_id, "gan_raw", gen_df)

    violin_path = store.artifact_path(session_id, "step6_target_violin.png")
    save_violin_compare(violin_path, data[target], gen_df[target])

    out_csv = store.artifact_path(session_id, "gan_raw.csv")
    gen_df.to_csv(out_csv, index=False, encoding="utf-8-sig")

    return {
        "rows_generated": int(len(gen_df)),
        "generated_rows": int(len(gen_df)),
        "n_generate": int(n_generate),
        "cols": cols,
        "gan_csv_artifact": out_csv.name,
        "target_violin_png_artifact": violin_path.name,
        "loss_csv_artifact": loss_csv.name,
        "loss_png_artifact": loss_png.name,
        "loss_tail": {"d": d_losses[-10:], "g": g_losses[-10:]},
        "preview": gen_df.head(20).to_dict(orient="records"),
    }
