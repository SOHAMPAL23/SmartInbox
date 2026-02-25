"""
evaluate.py
-----------
Model evaluation utilities for the SmartInbox spam detection system.

Provides:
  • evaluate_model()        – compute all required metrics from y_true / y_prob
  • print_evaluation_report() – formatted console output
  • plot_roc_curve()        – saves ROC curve PNG to artifacts/
  • plot_pr_curve()         – saves PR  curve PNG to artifacts/
  • plot_confusion_matrix() – saves confusion matrix heatmap to artifacts/
"""

from typing import Dict, Optional, Tuple

import matplotlib
matplotlib.use("Agg")   # non-interactive backend (safe on servers)
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns

from threshold import (
    compute_roc_curve,
    compute_pr_curve,
    compute_auc_trapezoidal,
    precision_recall_at_threshold,
    find_optimal_threshold,
)
from utils import get_logger, ARTIFACTS_DIR

logger = get_logger("evaluate")


# ──────────────────────────────────────────────────────────────────────────────
# Core evaluation
# ──────────────────────────────────────────────────────────────────────────────

def evaluate_model(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    threshold: float = 0.5,
    run_threshold_opt: bool = True,
) -> Dict:
    """
    Compute all required evaluation metrics.

    Parameters
    ----------
    y_true            : ground-truth binary labels
    y_prob            : predicted probabilities for the *positive* class
    threshold         : fixed decision threshold (usually 0.5)
    run_threshold_opt : if True, additionally find the F1-optimal threshold

    Returns
    -------
    dict containing:
        roc_auc, pr_auc, f1, accuracy, precision, recall,
        confusion_matrix, optimal_threshold (if run_threshold_opt),
        roc_curve {fpr, tpr, thresholds}, pr_curve {precision, recall, thresholds}
    """
    y_true = np.asarray(y_true, dtype=int)
    y_prob = np.asarray(y_prob, dtype=float)

    # ── ROC curve & AUC ──────────────────────────────────────────────────────
    fpr, tpr, roc_thresholds = compute_roc_curve(y_true, y_prob)
    roc_auc = compute_auc_trapezoidal(fpr, tpr)

    # ── PR curve & AUC ───────────────────────────────────────────────────────
    prec_curve, rec_curve, pr_thresholds = compute_pr_curve(y_true, y_prob)
    # Use recall on x-axis (must be non-decreasing for trapz → reverse)
    pr_auc = compute_auc_trapezoidal(rec_curve, prec_curve)

    # ── Fixed-threshold metrics ───────────────────────────────────────────────
    stats = precision_recall_at_threshold(y_true, y_prob, threshold)

    # ── Confusion matrix ─────────────────────────────────────────────────────
    tp, fp, tn, fn = stats["tp"], stats["fp"], stats["tn"], stats["fn"]
    confusion = np.array([[tn, fp], [fn, tp]])

    result = {
        "roc_auc":  round(roc_auc, 6),
        "pr_auc":   round(pr_auc,  6),
        "f1":       stats["f1"],
        "accuracy": stats["accuracy"],
        "precision":stats["precision"],
        "recall":   stats["recall"],
        "threshold_used": threshold,
        "confusion_matrix": confusion.tolist(),
        "roc_curve": {
            "fpr":        fpr.tolist(),
            "tpr":        tpr.tolist(),
            "thresholds": roc_thresholds.tolist(),
        },
        "pr_curve": {
            "precision":  prec_curve.tolist(),
            "recall":     rec_curve.tolist(),
            "thresholds": pr_thresholds.tolist(),
        },
    }

    # ── Threshold optimisation ────────────────────────────────────────────────
    if run_threshold_opt:
        opt = find_optimal_threshold(y_true, y_prob, metric="f1")
        result["optimal_threshold"] = opt["best_threshold"]
        result["optimal_f1"]        = opt["best_metric_value"]

    logger.info(
        "Evaluation complete │ ROC-AUC=%.4f │ PR-AUC=%.4f │ F1=%.4f │ Acc=%.4f",
        result["roc_auc"], result["pr_auc"], result["f1"], result["accuracy"],
    )
    return result


# ──────────────────────────────────────────────────────────────────────────────
# Cross-validation aggregation
# ──────────────────────────────────────────────────────────────────────────────

def aggregate_cv_metrics(fold_metrics: list) -> Dict:
    """
    Given a list of per-fold metric dicts, return mean ± std for scalar metrics.
    Array metrics (roc_curve, pr_curve, confusion_matrix) are excluded.
    """
    scalar_keys = ["roc_auc", "pr_auc", "f1", "accuracy", "precision", "recall"]
    agg = {}
    for key in scalar_keys:
        values = [m[key] for m in fold_metrics if key in m]
        if values:
            agg[f"{key}_mean"] = round(float(np.mean(values)), 6)
            agg[f"{key}_std"]  = round(float(np.std(values)),  6)
    return agg


# ──────────────────────────────────────────────────────────────────────────────
# Console report
# ──────────────────────────────────────────────────────────────────────────────

def print_evaluation_report(metrics: Dict, title: str = "Evaluation Report") -> None:
    """Pretty-print a metrics dictionary to the console."""
    width = 60
    sep   = "─" * width

    print(f"\n{'═' * width}")
    print(f"  {title}")
    print(f"{'═' * width}")

    scalar_items = {
        k: v for k, v in metrics.items()
        if not isinstance(v, (list, dict, np.ndarray))
    }
    for key, val in scalar_items.items():
        label = key.replace("_", " ").title()
        if isinstance(val, float):
            print(f"  {label:<30} {val:.6f}")
        else:
            print(f"  {label:<30} {val}")

    # Confusion matrix
    if "confusion_matrix" in metrics:
        cm = np.array(metrics["confusion_matrix"])
        print(f"\n  {'Confusion Matrix':}")
        print(f"  {sep}")
        print(f"  {'':20}  Pred HAM   Pred SPAM")
        print(f"  {'Actual HAM':<20}  {cm[0,0]:>8}   {cm[0,1]:>9}")
        print(f"  {'Actual SPAM':<20}  {cm[1,0]:>8}   {cm[1,1]:>9}")

    print(f"{'═' * width}\n")


# ──────────────────────────────────────────────────────────────────────────────
# Plots
# ──────────────────────────────────────────────────────────────────────────────

def _save_fig(fig: plt.Figure, filename: str) -> None:
    path = ARTIFACTS_DIR / filename
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("Plot saved → %s", path)


def plot_roc_curve(metrics: Dict, model_version: str = "v1") -> None:
    """Save ROC curve to artifacts/roc_curve_<version>.png."""
    roc = metrics.get("roc_curve", {})
    if not roc:
        logger.warning("No ROC curve data found in metrics dict.")
        return

    fpr = np.array(roc["fpr"])
    tpr = np.array(roc["tpr"])

    fig, ax = plt.subplots(figsize=(7, 6))
    ax.plot(fpr, tpr, lw=2, color="#E63946",
            label=f"ROC (AUC = {metrics.get('roc_auc', 0):.4f})")
    ax.plot([0, 1], [0, 1], lw=1, ls="--", color="grey", label="Random (AUC = 0.5)")
    ax.set_xlabel("False Positive Rate", fontsize=13)
    ax.set_ylabel("True Positive Rate", fontsize=13)
    ax.set_title("ROC Curve – SMS Spam Detector", fontsize=15, fontweight="bold")
    ax.legend(fontsize=11)
    ax.set_xlim([0, 1]); ax.set_ylim([0, 1.02])
    ax.grid(alpha=0.3)
    fig.tight_layout()
    _save_fig(fig, f"roc_curve_{model_version}.png")


def plot_pr_curve(metrics: Dict, model_version: str = "v1") -> None:
    """Save Precision-Recall curve to artifacts/pr_curve_<version>.png."""
    pr = metrics.get("pr_curve", {})
    if not pr:
        logger.warning("No PR curve data found in metrics dict.")
        return

    prec = np.array(pr["precision"])
    rec  = np.array(pr["recall"])

    fig, ax = plt.subplots(figsize=(7, 6))
    ax.plot(rec, prec, lw=2, color="#2A9D8F",
            label=f"PR (AUC = {metrics.get('pr_auc', 0):.4f})")
    ax.set_xlabel("Recall", fontsize=13)
    ax.set_ylabel("Precision", fontsize=13)
    ax.set_title("Precision-Recall Curve – SMS Spam Detector", fontsize=15, fontweight="bold")
    ax.legend(fontsize=11)
    ax.set_xlim([0, 1]); ax.set_ylim([0, 1.02])
    ax.grid(alpha=0.3)
    fig.tight_layout()
    _save_fig(fig, f"pr_curve_{model_version}.png")


def plot_confusion_matrix(metrics: Dict, model_version: str = "v1") -> None:
    """Save confusion matrix heatmap to artifacts/confusion_matrix_<version>.png."""
    cm = metrics.get("confusion_matrix")
    if cm is None:
        logger.warning("No confusion matrix found in metrics dict.")
        return

    cm = np.array(cm)
    labels = ["HAM (0)", "SPAM (1)"]

    fig, ax = plt.subplots(figsize=(6, 5))
    sns.heatmap(
        cm, annot=True, fmt="d",
        xticklabels=labels, yticklabels=labels,
        cmap="Blues", linewidths=0.5, ax=ax,
        annot_kws={"size": 14},
    )
    ax.set_xlabel("Predicted Label", fontsize=12)
    ax.set_ylabel("True Label", fontsize=12)
    ax.set_title("Confusion Matrix", fontsize=15, fontweight="bold")
    fig.tight_layout()
    _save_fig(fig, f"confusion_matrix_{model_version}.png")


def plot_threshold_curve(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    model_version: str = "v1",
) -> None:
    """
    Plot F1, Precision, and Recall against threshold and save to artifacts/.
    """
    thresholds = np.linspace(0.01, 0.99, 200)
    f1s, precs, recs = [], [], []

    for t in thresholds:
        stats = precision_recall_at_threshold(y_true, y_prob, t)
        f1s.append(stats["f1"])
        precs.append(stats["precision"])
        recs.append(stats["recall"])

    best_idx = int(np.argmax(f1s))

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(thresholds, f1s,   label="F1",        color="#E63946", lw=2)
    ax.plot(thresholds, precs, label="Precision",  color="#2A9D8F", lw=1.5, ls="--")
    ax.plot(thresholds, recs,  label="Recall",     color="#F4A261", lw=1.5, ls="--")
    ax.axvline(thresholds[best_idx], color="black", ls=":", lw=1.5,
               label=f"Best thr={thresholds[best_idx]:.2f} (F1={f1s[best_idx]:.3f})")
    ax.set_xlabel("Threshold", fontsize=12)
    ax.set_ylabel("Score", fontsize=12)
    ax.set_title("Metrics vs Decision Threshold", fontsize=14, fontweight="bold")
    ax.legend(fontsize=10)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    _save_fig(fig, f"threshold_curve_{model_version}.png")
    logger.info("Threshold curve saved.")
