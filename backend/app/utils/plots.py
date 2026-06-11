from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable

from app.core.paths import get_mplconfig_dir

os.environ.setdefault("MPLCONFIGDIR", str(get_mplconfig_dir()))

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def save_simple_scatter(
    path: Path,
    x: Iterable[float],
    y: Iterable[float],
    title: str,
    xlabel: str,
    ylabel: str,
):
    plt.figure(figsize=(6, 4), dpi=160)
    plt.scatter(list(x), list(y), s=18, alpha=0.7)
    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.grid(True, alpha=0.25)
    plt.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(path, bbox_inches="tight")
    plt.close()


def save_line_plot(
    path: Path,
    series_list: list[tuple[str, Iterable[float]]],
    title: str,
    xlabel: str,
    ylabel: str,
):
    plt.figure(figsize=(8, 4.5), dpi=160)
    for label, series in series_list:
        values = list(series)
        plt.plot(range(1, len(values) + 1), values, label=label, linewidth=2)
    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.grid(True, alpha=0.25)
    if len(series_list) > 1:
        plt.legend(frameon=False)
    plt.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(path, bbox_inches="tight")
    plt.close()


def save_histogram(
    path: Path,
    values: Iterable[float],
    title: str,
    xlabel: str,
    ylabel: str = "Count",
    bins: int = 20,
    color: str = "#6aa7ff",
):
    values = [float(v) for v in values]
    plt.figure(figsize=(8, 4.5), dpi=160)
    plt.hist(values, bins=bins, color=color, alpha=0.88, edgecolor="white")
    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.grid(True, axis="y", alpha=0.2)
    plt.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(path, bbox_inches="tight")
    plt.close()


def save_horizontal_bar_chart(
    path: Path,
    labels: Iterable[str],
    values: Iterable[float],
    title: str,
    xlabel: str,
    ylabel: str,
    color: str = "#6aa7ff",
):
    labels = [str(v) for v in labels]
    values = [float(v) for v in values]
    order = np.argsort(values)
    labels = [labels[i] for i in order]
    values = [values[i] for i in order]

    height = max(4.0, 0.42 * len(labels) + 1.2)
    plt.figure(figsize=(9, height), dpi=160)
    bars = plt.barh(labels, values, color=color)
    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.grid(True, axis="x", alpha=0.25)
    for bar, value in zip(bars, values):
        plt.text(
            bar.get_width(),
            bar.get_y() + bar.get_height() / 2,
            f"  {value:.4f}",
            va="center",
            fontsize=8,
        )
    plt.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(path, bbox_inches="tight")
    plt.close()


def save_metric_panels(
    path: Path,
    df: pd.DataFrame,
    label_col: str,
    metric_cols: list[str],
    title: str,
    top_n: int = 12,
    sort_by: str | None = None,
):
    data = df.copy()
    if sort_by and sort_by in data.columns:
        ascending = sort_by.lower() in {"rmse", "mae", "mse", "loss"}
        data = data.sort_values(sort_by, ascending=ascending)
    data = data.head(max(1, int(top_n)))

    labels = data[label_col].astype(str).tolist()
    n_metrics = len(metric_cols)
    fig, axes = plt.subplots(n_metrics, 1, figsize=(11.5, max(3.6, 2.4 * n_metrics + 1.0)), sharex=False)
    if n_metrics == 1:
        axes = [axes]

    for ax, metric in zip(axes, metric_cols):
        if metric not in data.columns:
            ax.axis("off")
            continue

        raw_values = data[metric].replace([np.inf, -np.inf], np.nan).astype(float).fillna(0.0).tolist()
        order = np.argsort(raw_values)
        plot_labels = [labels[i] for i in order]
        plot_values = [raw_values[i] for i in order]

        finite = np.array([v for v in plot_values if np.isfinite(v)], dtype=float)
        if finite.size == 0:
            finite = np.array([0.0], dtype=float)

        sorted_vals = np.sort(finite)
        lower = float(sorted_vals[0])
        upper = float(sorted_vals[-1])
        if len(sorted_vals) >= 4:
            inner_low = float(sorted_vals[1])
            inner_high = float(sorted_vals[-2])
            inner_span = max(inner_high - inner_low, 1e-9)
            if abs(lower - inner_low) > inner_span * 3:
                lower = inner_low - inner_span * 0.15
            if abs(upper - inner_high) > inner_span * 3:
                upper = inner_high + inner_span * 0.15
        if lower >= upper:
            lower = float(np.min(finite))
            upper = float(np.max(finite))

        plot_lower = lower
        if np.min(finite) < lower and upper > 0:
            plot_lower = min(0.0, lower)

        clipped_values = np.clip(plot_values, plot_lower, upper)
        bars = ax.barh(plot_labels, clipped_values, color="#6aa7ff" if metric.lower() == "r2" else "#88d18a")
        ax.set_xlabel(metric)
        ax.grid(True, axis="x", alpha=0.2)
        ax.set_title(metric.upper())

        span = max(upper - plot_lower, 1e-9)
        margin = span * 0.06
        ax.set_xlim(plot_lower - margin, upper + margin)
        if plot_lower <= 0 <= upper:
            ax.axvline(0, color="#94a7c7", linewidth=1, alpha=0.6)

        clipped_any = any(abs(a - b) > 1e-12 for a, b in zip(plot_values, clipped_values))
        if clipped_any:
            ax.text(
                1.0,
                1.02,
                "outlier clipped for display",
                transform=ax.transAxes,
                ha="right",
                va="bottom",
                fontsize=8,
                color="#6f829f",
            )

        for bar, value, shown in zip(bars, plot_values, clipped_values):
            suffix = " *" if abs(value - shown) > 1e-12 else ""
            ax.text(
                shown,
                bar.get_y() + bar.get_height() / 2,
                f"  {value:.4f}{suffix}",
                va="center",
                fontsize=8,
            )

    fig.suptitle(title, fontsize=13)
    fig.subplots_adjust(left=0.22, right=0.96, top=0.90, bottom=0.12, hspace=0.32)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path)
    plt.close(fig)


def save_violin_compare(path: Path, a: pd.Series, b: pd.Series, labels=("Original", "Generated")):
    plt.figure(figsize=(6, 4), dpi=160)
    plt.violinplot([a.values, b.values], showmeans=True)
    plt.xticks([1, 2], list(labels))
    plt.title("Target Distribution (Original vs Generated)")
    plt.grid(True, axis="y", alpha=0.25)
    plt.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(path, bbox_inches="tight")
    plt.close()
