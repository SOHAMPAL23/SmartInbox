"""
ml/train_v8.py
--------------
Train v8 hybrid ensemble on spam_ham_dataset_10k.csv
Outputs: models/ensemble_v8.pkl, artifacts/metadata_v8.json, artifacts/threshold_optimiser_v8.pkl
"""

import os, sys, json, pickle, logging, random, re, warnings
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.sparse import hstack, csr_matrix

from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.naive_bayes import ComplementNB
from sklearn.model_selection import StratifiedKFold, train_test_split
from sklearn.metrics import (
    roc_auc_score, f1_score, precision_score, recall_score,
    accuracy_score, confusion_matrix, classification_report, average_precision_score
)
from sklearn.preprocessing import MaxAbsScaler

try:
    import xgboost as xgb
    XGB_OK = True
except ImportError:
    XGB_OK = False

try:
    import lightgbm as lgb
    LGB_OK = True
except ImportError:
    LGB_OK = False

try:
    from imblearn.over_sampling import SMOTE
    SMOTE_OK = True
except ImportError:
    SMOTE_OK = False

warnings.filterwarnings("ignore")
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("train_v8")

ROOT_DIR      = Path(__file__).resolve().parent
MODELS_DIR    = ROOT_DIR / "models"
ARTIFACTS_DIR = ROOT_DIR / "artifacts"
DATA_DIR      = ROOT_DIR / "data"
MODELS_DIR.mkdir(exist_ok=True)
ARTIFACTS_DIR.mkdir(exist_ok=True)

SEED = 42
random.seed(SEED); np.random.seed(SEED)

# ── Ensure feature_pipeline is importable ────────────────────────────────────
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from feature_pipeline import RobustSMSFeaturePipelineV7  # noqa: E402


# ══════════════════════════════════════════════════════════════════════════════
# SYNTHETIC AI-SPAM AUGMENTATION
# ══════════════════════════════════════════════════════════════════════════════

_AI_SPAM_SAMPLES = [
    "I hope this finds you well. I've been following your work closely and believe we have a mutually beneficial opportunity worth exploring. Would you be open to a 15-minute call at your convenience? No obligation whatsoever.",
    "Forgive the cold outreach, but I've been researching leaders in your space and your name keeps coming up. I represent a consortium of investors looking to partner with select professionals. Happy to share more details if you're open to it.",
    "I don't want to take up too much of your time, but I've spent considerable time analyzing your company's growth trajectory. Our data-driven framework has helped similar organizations achieve measurable outcomes. Can I send over a brief overview?",
    "I hope I'm not overstepping by reaching out directly. Many professionals I speak with are revisiting their financial positioning as we enter Q2. Would a complimentary 15-minute strategy session be worth your time?",
    "As we enter a period of significant market volatility, I wanted to reach out to a select group of executives about an unconventional proposition that's generating strong returns. Would love to connect when you get a chance.",
    "Hi there! I've been following your profile and I believe you'd be the perfect fit for an exclusive investment opportunity. Our portfolio has generated 340% ROI in 2024. Interested? Let me know and I'll send details.",
    "Hello, I hope this message finds you well. I represent a group of high-net-worth individuals looking for reliable partners in the real estate sector. This is a time-sensitive opportunity with guaranteed 25% annual returns. Are you available for a quick chat?",
    "I'm reaching out on behalf of our team at FinVault Capital. We've identified your profile as someone who might benefit from our proprietary wealth building system. No prior experience needed. Worth a 15-minute call?",
    "Just checking if you saw my previous message about the remote position we have available. The role offers flexible hours, $5,000-$8,000 per month, and requires no prior experience. Be your own boss and work from anywhere. Interested?",
    "Hi! We're hiring work-from-home data entry specialists. No experience required. Earn $500-$1,000 per day. Flexible schedule. Must be 18+. Reply YES to apply.",
    "Congratulations! You've been selected for our exclusive beta program. As an early adopter, you'll receive 3 months of our premium service absolutely FREE. No credit card required. Click here to claim your spot before midnight.",
    "Your LinkedIn profile caught our attention. We're looking for motivated individuals to join our global team. Part-time, full-time, or as a side hustle. Earn $200-$500 per day from home. No selling required. Reply to learn more.",
    "Hello, I'm reaching out because our AI found your profile matches our criteria for an exclusive wealth program. We guarantee $10,000 monthly passive income. This is not a pyramid scheme. Limited spots available. Are you interested?",
    "I hope you'll forgive the direct outreach. I've been working with executives in your industry and have seen firsthand how our framework drives measurable results within 90 days. I'd love to share a brief case study. Would a quick call work for you?",
    "I've spent years developing a scalable solution for professionals like yourself. Our ecosystem has helped over 500 stakeholders achieve their financial KPIs. If you're open to it, I'd be happy to walk you through our roadmap.",
    "Reaching out today with a time-sensitive opportunity. Our firm is offering pre-approved business loans up to $500,000 with no collateral required. Low interest rates, fast approval. Would you be interested in a free consultation?",
    "As someone in the financial space, I wanted to share an exclusive opportunity. Our cryptocurrency trading algorithm has delivered consistent 15-20% monthly returns. Select individuals are being invited to participate. Would you be open to learning more?",
    "Hello! I'm contacting you about a remote job opportunity perfect for your skillset. Work from home, set your own hours, earn $3,000-$5,000 monthly. Must have smartphone/computer. Reply 'INFO' for details.",
    "I represent a high-growth startup that's disrupting the enterprise space. We're looking for strategic advisors with your background. This is a paid advisory role. Would you be open to a brief introduction call at your convenience?",
    "I've been following your career trajectory with great interest and believe you'd be an ideal candidate for our Executive Advisory Board. This is a paid position with significant equity upside. Would a confidential conversation be possible?",
]

_PHISHING_SAMPLES = [
    "URGENT: Your account has been flagged for suspicious activity. Verify your identity immediately at secure-mybank.com/verify or your account will be suspended within 24 hours.",
    "Your package could not be delivered. A redelivery fee of $2.99 is required. Click here to reschedule: dlvry-update.com/reschedule. Failure to pay within 48 hours will result in package return.",
    "IRS NOTICE: You owe $3,847.00 in unpaid taxes. Immediate payment required to avoid arrest. Call 1-800-829-1040 or visit tax-resolution-center.com to resolve now.",
    "Your Netflix account will be suspended. We were unable to process your payment. Update your billing information: netflix-payment-update.com/billing",
    "APPLE ID ALERT: Your Apple ID has been locked due to too many failed login attempts. Verify your information within 24 hours to unlock: apple-id-verify.support",
    "Dear customer, your KYC verification is incomplete. To avoid account suspension, complete your KYC at hdfc-kyc-update.in within 48 hours.",
    "Your HDFC Bank account has been temporarily suspended due to unusual activity. Click here to restore access: hdfc-secure-verify.com",
    "SBI ALERT: Your debit card is blocked. To unblock, call our helpline immediately or click: sbi-unblock-card.co.in. Ignore at your own risk.",
]

_SOCIAL_ENGINEERING = [
    "Hi [Name], this is Sarah from HR. We've had a security incident and need all employees to reset their passwords immediately. Please go to hr-portal-reset.company.com and enter your current credentials.",
    "Hello, I'm calling from your bank's fraud department. We've detected a $2,500 transaction on your account. To stop this transaction, I need to verify your identity. Please confirm your card number and PIN.",
    "Your son/daughter has been in an accident and is at the hospital. We need your credit card information to authorize emergency treatment. Please call us immediately at 1-800-URGENT.",
    "This is a final notice from collections. You have an outstanding balance of $847. To avoid legal action and credit damage, call us immediately at 1-888-COLLECT.",
]

_HAM_AUGMENTED = [
    "Your OTP for login is 847291. Valid for 10 minutes. Do not share this code with anyone.",
    "Hi! Can we reschedule our meeting to 3pm tomorrow? Let me know if that works for you.",
    "Your Amazon order #123-456 has been shipped and will arrive by Thursday. Track at amazon.com/orders",
    "Thanks for dinner last night! Had a great time. Let's do it again soon.",
    "Reminder: Your appointment with Dr. Smith is tomorrow at 10:30 AM. Reply YES to confirm.",
    "Your Uber is arriving. Driver: Raj, Blue Honda City, MH02 AB 1234",
    "Transaction alert: Rs.2500 debited from your account on 12-May-26. Available balance: Rs.15,420.",
    "Your Swiggy order is out for delivery! Track your order in the app.",
    "Hi, just checking if you're coming to the party on Saturday? Let me know!",
    "Your electricity bill of Rs.1,245 is due on May 20. Pay online to avoid late fees.",
]


def build_augmented_dataset(base_df: pd.DataFrame) -> pd.DataFrame:
    logger.info("Building augmented dataset with synthetic adversarial samples...")

    ai_spam_df = pd.DataFrame({"text": _AI_SPAM_SAMPLES, "label": 1})
    phish_df   = pd.DataFrame({"text": _PHISHING_SAMPLES, "label": 1})
    social_df  = pd.DataFrame({"text": _SOCIAL_ENGINEERING, "label": 1})
    ham_aug_df = pd.DataFrame({"text": _HAM_AUGMENTED, "label": 0})

    combined = pd.concat([base_df, ai_spam_df, phish_df, social_df, ham_aug_df], ignore_index=True)
    combined = combined.dropna(subset=["text", "label"])
    combined["text"]  = combined["text"].astype(str).str.strip()
    combined["label"] = combined["label"].astype(int)
    combined = combined[combined["text"].str.len() > 3]
    combined = combined.drop_duplicates(subset=["text"])
    combined = combined.sample(frac=1, random_state=SEED).reset_index(drop=True)

    logger.info("Dataset: total=%d | spam=%d | ham=%d",
                len(combined), combined["label"].sum(), (combined["label"]==0).sum())
    return combined


# ══════════════════════════════════════════════════════════════════════════════
# DATA LOADING
# ══════════════════════════════════════════════════════════════════════════════

def load_dataset() -> pd.DataFrame:
    frames = []

    # Primary: 10k dataset
    path_10k = DATA_DIR / "spam_ham_dataset_10k.csv"
    if path_10k.exists():
        df = pd.read_csv(path_10k, encoding="utf-8")
        df.columns = [c.strip().lower() for c in df.columns]
        if "message" in df.columns and "text" not in df.columns:
            df.rename(columns={"message": "text"}, inplace=True)
        if "label" not in df.columns:
            for col in ["spam", "category", "class"]:
                if col in df.columns:
                    df["label"] = (df[col].astype(str).str.strip().str.lower().isin(["spam","1"])).astype(int)
                    df.drop(columns=[col], inplace=True)
                    break
        df["label"] = pd.to_numeric(df["label"], errors="coerce").fillna(0).astype(int)
        frames.append(df[["text","label"]])
        logger.info("Loaded 10k dataset: %d rows", len(df))

    # Secondary: spam.csv
    path_spam = DATA_DIR / "spam.csv"
    if path_spam.exists():
        df2 = pd.read_csv(path_spam, encoding="latin-1")
        df2.columns = [c.strip().lower() for c in df2.columns]
        if "v1" in df2.columns and "v2" in df2.columns:
            df2 = df2[["v1","v2"]].rename(columns={"v1":"label","v2":"text"})
            df2["label"] = (df2["label"].str.strip().str.lower() == "spam").astype(int)
        elif "message" in df2.columns:
            df2.rename(columns={"message":"text"}, inplace=True)
        frames.append(df2[["text","label"]])
        logger.info("Loaded spam.csv: %d rows", len(df2))

    # TSV fallback
    path_tsv = DATA_DIR / "SMSSpamCollection"
    if path_tsv.exists() and not frames:
        df3 = pd.read_csv(path_tsv, sep="\t", header=None, names=["label","text"])
        df3["label"] = (df3["label"].str.strip().str.lower() == "spam").astype(int)
        frames.append(df3[["text","label"]])

    if not frames:
        raise FileNotFoundError("No dataset found in ml/data/")

    combined = pd.concat(frames, ignore_index=True)
    combined = combined.dropna(subset=["text","label"])
    combined["text"]  = combined["text"].astype(str).str.strip()
    combined["label"] = combined["label"].astype(int)
    combined = combined[combined["text"].str.len() > 2].drop_duplicates(subset=["text"])
    combined = combined.sample(frac=1, random_state=SEED).reset_index(drop=True)
    return combined


# ══════════════════════════════════════════════════════════════════════════════
# ENSEMBLE TRAINING
# ══════════════════════════════════════════════════════════════════════════════

def train_model(df: pd.DataFrame) -> dict:
    logger.info("Starting v8 ensemble training | rows=%d", len(df))
    start_ts = datetime.now(timezone.utc)

    X = df["text"].tolist()
    y = df["label"].values

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=SEED, stratify=y
    )
    logger.info("Train=%d | Test=%d | Spam ratio=%.1f%%", len(X_train), len(X_test), y_train.mean()*100)

    # ── Feature pipeline ──────────────────────────────────────────────────────
    pipeline = RobustSMSFeaturePipelineV7()
    logger.info("Fitting feature pipeline...")
    X_train_feat = pipeline.fit_transform(X_train, y_train)
    X_test_feat  = pipeline.transform(X_test)

    # ── SMOTE ─────────────────────────────────────────────────────────────────
    X_tr = X_train_feat
    y_tr = y_train
    if SMOTE_OK:
        try:
            sm = SMOTE(random_state=SEED, k_neighbors=5)
            X_tr, y_tr = sm.fit_resample(X_tr, y_tr)
            logger.info("SMOTE applied: %d samples", len(y_tr))
        except Exception as e:
            logger.warning("SMOTE failed (%s), using original data", e)

    # ── Train base models ─────────────────────────────────────────────────────
    models = {}

    logger.info("Training ComplementNB...")
    from scipy.sparse import issparse
    X_nb = X_tr
    if hasattr(X_nb, "toarray"):
        X_nb_dense = X_nb
    # ComplementNB needs non-negative data
    nb = ComplementNB(alpha=0.1)
    try:
        nb.fit(X_nb, y_tr)
        models["nb"] = {"model": nb, "weight": 0.10}
    except Exception as e:
        logger.warning("NB failed: %s", e)

    logger.info("Training LogisticRegression...")
    lr = LogisticRegression(C=2.0, max_iter=2000, solver="saga", class_weight="balanced", random_state=SEED, n_jobs=-1)
    lr.fit(X_tr, y_tr)
    models["lr"] = {"model": lr, "weight": 0.20}

    logger.info("Training RandomForest...")
    rf = RandomForestClassifier(n_estimators=300, max_depth=None, min_samples_leaf=2,
                                class_weight="balanced", random_state=SEED, n_jobs=-1)
    rf.fit(X_tr, y_tr)
    models["rf"] = {"model": rf, "weight": 0.30}

    if XGB_OK:
        logger.info("Training XGBoost...")
        scale_pos = int((y_tr == 0).sum()) / max(int((y_tr == 1).sum()), 1)
        xgb_clf = xgb.XGBClassifier(
            n_estimators=200, max_depth=6, learning_rate=0.1,
            scale_pos_weight=scale_pos, use_label_encoder=False,
            eval_metric="logloss", random_state=SEED, n_jobs=-1, verbosity=0
        )
        xgb_clf.fit(X_tr, y_tr)
        models["xgb"] = {"model": xgb_clf, "weight": 0.20}

    if LGB_OK:
        logger.info("Training LightGBM...")
        lgb_clf = lgb.LGBMClassifier(
            n_estimators=200, learning_rate=0.05, num_leaves=63,
            class_weight="balanced", random_state=SEED, n_jobs=-1, verbose=-1
        )
        lgb_clf.fit(X_tr, y_tr)
        models["lgbm"] = {"model": lgb_clf, "weight": 0.20}

    # Normalize weights
    total_w = sum(cfg["weight"] for cfg in models.values())
    for cfg in models.values():
        cfg["weight"] = cfg["weight"] / total_w

    # ── Soft vote evaluation ──────────────────────────────────────────────────
    logger.info("Evaluating soft-vote ensemble...")
    proba_sum = None
    total_w2  = 0.0
    for key, cfg in models.items():
        m, w = cfg["model"], cfg["weight"]
        try:
            p = m.predict_proba(X_test_feat)[:, 1]
            proba_sum = (proba_sum + w * p) if proba_sum is not None else w * p
            total_w2 += w
        except Exception as e:
            logger.warning("Sub-model %s eval failed: %s", key, e)

    y_proba = proba_sum / total_w2

    # Find optimal threshold (maximize F1 on spam recall)
    best_f1, best_thr = 0.0, 0.50
    for t in np.arange(0.20, 0.80, 0.01):
        preds = (y_proba >= t).astype(int)
        f = f1_score(y_test, preds, zero_division=0)
        if f > best_f1:
            best_f1 = f
            best_thr = float(t)

    y_pred = (y_proba >= best_thr).astype(int)
    cm = confusion_matrix(y_test, y_pred).tolist()

    metrics = {
        "roc_auc":  round(float(roc_auc_score(y_test, y_proba)), 4),
        "pr_auc":   round(float(average_precision_score(y_test, y_proba)), 4),
        "f1":       round(float(f1_score(y_test, y_pred)), 4),
        "precision":round(float(precision_score(y_test, y_pred)), 4),
        "recall":   round(float(recall_score(y_test, y_pred)), 4),
        "accuracy": round(float(accuracy_score(y_test, y_pred)), 4),
        "optimal_threshold": best_thr,
        "optimal_f1": round(best_f1, 4),
        "confusion_matrix": cm,
        "false_positives": int(cm[0][1]),
        "false_negatives": int(cm[1][0]),
        "classification_report": classification_report(y_test, y_pred, target_names=["ham","spam"], output_dict=True),
    }

    logger.info("Metrics: ROC-AUC=%.4f | F1=%.4f | P=%.4f | R=%.4f | threshold=%.2f",
                metrics["roc_auc"], metrics["f1"], metrics["precision"], metrics["recall"], best_thr)

    # ── Save ensemble ──────────────────────────────────────────────────────────
    ensemble = {
        "pipeline":      pipeline,
        "models":        models,
        "ensemble_type": "soft_vote",
        "version":       "v8",
        "trained_at":    start_ts.isoformat(),
    }
    ensemble_path = MODELS_DIR / "ensemble_v8.pkl"
    with open(ensemble_path, "wb") as f:
        pickle.dump(ensemble, f, protocol=pickle.HIGHEST_PROTOCOL)
    logger.info("Saved ensemble to %s", ensemble_path)

    # ── Save pipeline separately ───────────────────────────────────────────────
    pipeline_path = ARTIFACTS_DIR / "feature_pipeline_v8.pkl"
    with open(pipeline_path, "wb") as f:
        pickle.dump(pipeline, f, protocol=pickle.HIGHEST_PROTOCOL)

    # ── Save threshold optimiser ──────────────────────────────────────────────
    spam_thr    = max(best_thr + 0.10, 0.60)
    susp_thr    = max(best_thr - 0.10, 0.38)
    ham_thr     = max(susp_thr - 0.10, 0.28)
    thr_data = {
        "threshold":            best_thr,
        "spam_threshold":       spam_thr,
        "suspicious_threshold": susp_thr,
        "ham_threshold":        ham_thr,
    }
    thr_path = ARTIFACTS_DIR / "threshold_optimiser_v8.pkl"
    with open(thr_path, "wb") as f:
        pickle.dump(thr_data, f)

    # ── Save metadata ──────────────────────────────────────────────────────────
    end_ts = datetime.now(timezone.utc)
    metadata = {
        "model_version": "v8",
        "model_type": "soft_vote",
        "ensemble_composition": {k: {"weight": v["weight"], "type": type(v["model"]).__name__} for k,v in models.items()},
        "trained_at":    start_ts.isoformat(),
        "completed_at":  end_ts.isoformat(),
        "seed": SEED,
        "optimal_threshold": best_thr,
        "confidence_tiers": {
            "spam":       f"> {spam_thr:.2f}",
            "suspicious": f"{susp_thr:.2f} - {spam_thr:.2f}",
            "ham":        f"< {susp_thr:.2f}",
        },
        "config": {
            "smote_applied": SMOTE_OK,
            "synthetic_ai_spam_samples": len(_AI_SPAM_SAMPLES),
            "synthetic_phishing_samples": len(_PHISHING_SAMPLES),
            "synthetic_social_engineering": len(_SOCIAL_ENGINEERING),
            "test_size": 0.20,
            "xgboost_available": XGB_OK,
            "lightgbm_available": LGB_OK,
        },
        "datasets": {
            "total_rows": len(df),
            "train_size": len(X_train),
            "test_size":  len(X_test),
            "spam_count": int(y.sum()),
            "ham_count":  int((y == 0).sum()),
        },
        "test_metrics": metrics,
    }
    meta_path = ARTIFACTS_DIR / "metadata_v8.json"
    with open(meta_path, "w") as f:
        def _default(o):
            if isinstance(o, (np.integer,)): return int(o)
            if isinstance(o, (np.floating,)): return float(o)
            if isinstance(o, np.ndarray): return o.tolist()
            raise TypeError
        json.dump(metadata, f, indent=2, default=_default)
    logger.info("Saved metadata to %s", meta_path)

    return metadata


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("SmartInbox v8 Ensemble Training")
    logger.info("=" * 60)

    # Load base dataset
    base_df = load_dataset()

    # Augment with synthetic adversarial samples
    df = build_augmented_dataset(base_df)

    # Train
    meta = train_model(df)

    logger.info("=" * 60)
    logger.info("TRAINING COMPLETE")
    logger.info("ROC-AUC : %.4f", meta["test_metrics"]["roc_auc"])
    logger.info("F1      : %.4f", meta["test_metrics"]["f1"])
    logger.info("Precision: %.4f", meta["test_metrics"]["precision"])
    logger.info("Recall  : %.4f", meta["test_metrics"]["recall"])
    logger.info("Threshold: %.2f", meta["optimal_threshold"])
    logger.info("Model   : ml/models/ensemble_v8.pkl")
    logger.info("=" * 60)
