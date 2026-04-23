"""
ml/service.py
-------------
Framework-agnostic spam detection service.

Loads the trained RandomForest pipeline from disk and provides:
  - Single / batch prediction with probability + threshold application
  - Live threshold updates (no reload required)
  - Full model retraining with quality gate
  - Model-card metadata and feature importance queries
  - Health checks for orchestration (Docker, K8s)

All public methods return plain dicts  — FastAPI adapter in app/services/ml_service.py
handles HTTP concerns like error codes.
"""

import json
import time
import pickle
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
import sys

# Ensure ml directory is on path so we can import feature_pipeline
_ML_ROOT = Path(__file__).resolve().parent
if str(_ML_ROOT) not in sys.path:
    sys.path.insert(0, str(_ML_ROOT))

from feature_pipeline import SMSFeaturePipeline

logger = logging.getLogger("ml.service")

# ── Project paths ─────────────────────────────────────────────────────────────
_MODELS_DIR = _ML_ROOT / "models"
_ARTIFACTS_DIR = _ML_ROOT / "artifacts"
_DATA_DIR = _ML_ROOT / "data"


# ── Custom exceptions ─────────────────────────────────────────────────────────

class ServiceError(Exception):
    """Base exception for ML service errors."""
    pass


class InvalidInputError(ServiceError):
    """Raised when user-supplied data fails validation."""
    pass


class ModelNotLoadedError(ServiceError):
    """Raised when prediction is attempted before the model is loaded."""
    pass


# ── Service ───────────────────────────────────────────────────────────────────

class SpamDetectorService:
    """
    Stateful ML service wrapping a trained RandomForest + TF-IDF pipeline.

    Parameters
    ----------
    model_version : str
        Tag such as ``"v1"`` used to locate ``models/model_{tag}.pkl``.
    auto_load : bool
        If *True* (default), the model is loaded at construction time.
    """

    def __init__(
        self,
        model_version: str = "v1",
        auto_load: bool = True,
    ):
        self._model_version: str = model_version
        self._model: Any = None            # sklearn RandomForest classifier
        self._pipeline: Any = None         # TF-IDF feature pipeline
        self._threshold: float = 0.5       # decision threshold (can be updated)
        self._metadata: Dict[str, Any] = {}
        self._feature_names: Optional[List[str]] = None
        self._loaded: bool = False
        self._loaded_at: Optional[str] = None

        if auto_load:
            self._load()

    # ── Loading ────────────────────────────────────────────────────────────

    def _load(self) -> None:
        """Load model, pipeline, metadata, and threshold from disk."""
        tag = self._model_version

        model_path = _MODELS_DIR / f"model_{tag}.pkl"
        pipeline_path = _ARTIFACTS_DIR / "feature_pipeline.pkl"
        metadata_path = _ARTIFACTS_DIR / f"metadata_{tag}.json"
        threshold_path = _ARTIFACTS_DIR / f"threshold_optimiser_{tag}.pkl"

        import os
        logger.info(f"[ML-DEBUG] Current Working Directory: {os.getcwd()}")
        logger.info(f"[ML-DEBUG] Expected ML Dir: {_ML_ROOT}")
        logger.info(f"[ML-DEBUG] Expected Models Dir: {_MODELS_DIR}")
        logger.info(f"[ML-DEBUG] Expected Artifacts Dir: {_ARTIFACTS_DIR}")
        
        # Debug list directory contents
        if _MODELS_DIR.exists():
            logger.info(f"[ML-DEBUG] Models Dir contents: {os.listdir(_MODELS_DIR)}")
        else:
            logger.error(f"[ML-DEBUG] Models Dir does NOT exist!")
            
        if _ARTIFACTS_DIR.exists():
            logger.info(f"[ML-DEBUG] Artifacts Dir contents: {os.listdir(_ARTIFACTS_DIR)}")
        else:
            logger.error(f"[ML-DEBUG] Artifacts Dir does NOT exist!")

        if not model_path.exists():
            logger.error(f"[ML-DEBUG] Model file missing: {model_path}")
            raise ModelNotLoadedError(f"Model file not found: {model_path}")
        if not pipeline_path.exists():
            logger.error(f"[ML-DEBUG] Pipeline file missing: {pipeline_path}")
            raise ModelNotLoadedError(f"Pipeline file not found: {pipeline_path}")

        logger.info("Loading model %s from %s", tag, model_path)

        with open(model_path, "rb") as f:
            self._model = pickle.load(f)

        # Detect model type
        self._model_type = type(self._model).__name__

        # Alias SMSFeaturePipeline and RobustSMSFeaturePipeline in __main__ because they were pickled from a script/notebook
        # and pickle expects the class to exist in the __main__ module scope.
        if "SMSFeaturePipeline" not in sys.modules["__main__"].__dict__:
            sys.modules["__main__"].SMSFeaturePipeline = SMSFeaturePipeline

        try:
            from train_robust import RobustSMSFeaturePipeline
            if "RobustSMSFeaturePipeline" not in sys.modules["__main__"].__dict__:
                sys.modules["__main__"].RobustSMSFeaturePipeline = RobustSMSFeaturePipeline
        except ImportError:
            pass

        # Also alias logger in __main__ because some pickled objects might reference it
        if "logger" not in sys.modules["__main__"].__dict__:
            sys.modules["__main__"].logger = logger

        try:
            with open(pipeline_path, "rb") as f:
                self._pipeline = pickle.load(f)
        except Exception as pipe_exc:
            import traceback
            logger.error(f"[ML-DEBUG] Pipeline load failed: {pipe_exc}\n{traceback.format_exc()}")
            raise ModelNotLoadedError(f"Pipeline corrupted or incompatible: {pipe_exc}")

        # Metadata (optional but expected)
        if metadata_path.exists():
            with open(metadata_path, "r") as f:
                self._metadata = json.load(f)
            # Apply optimal threshold from metadata
            opt = self._metadata.get("optimal_threshold", {})
            if isinstance(opt, dict) and "value" in opt:
                self._threshold = opt["value"]
            elif isinstance(opt, (int, float)):
                self._threshold = float(opt)

        # Threshold optimiser artefact (optional)
        if threshold_path.exists():
            try:
                with open(threshold_path, "rb") as f:
                    threshold_data = pickle.load(f)
                if isinstance(threshold_data, dict) and "threshold" in threshold_data:
                    self._threshold = threshold_data["threshold"]
            except Exception:
                pass  # gracefully ignore corrupt threshold file

        # Extract feature names from pipeline if available
        try:
            if hasattr(self._pipeline, "get_feature_names_out"):
                self._feature_names = list(self._pipeline.get_feature_names_out())
            elif hasattr(self._pipeline, "named_steps"):
                # Try to get from the last transformer step
                for step_name in reversed(list(self._pipeline.named_steps.keys())):
                    step = self._pipeline.named_steps[step_name]
                    if hasattr(step, "get_feature_names_out"):
                        self._feature_names = list(step.get_feature_names_out())
                        break
        except Exception:
            self._feature_names = None

        self._loaded = True
        self._loaded_at = datetime.now(timezone.utc).isoformat()
        logger.info(
            "Model %s loaded | threshold=%.4f | features=%s",
            tag, self._threshold,
            len(self._feature_names) if self._feature_names else "unknown",
        )

    def _ensure_loaded(self) -> None:
        if not self._loaded or self._model is None:
            raise ModelNotLoadedError(
                "Model is not loaded. Call init_spam_detector() first."
            )

    # ── Prediction ─────────────────────────────────────────────────────────

    def predict(self, text: str) -> Dict[str, Any]:
        """
        Classify a single SMS message.

        Returns
        -------
        dict with keys: prediction, probability, threshold_used
        """
        self._ensure_loaded()

        if not text or not text.strip():
            raise InvalidInputError("Text must be a non-empty string.")

        text = text.strip()
        logger.debug(f"[ML] Predicting for text (len={len(text)}): {text[:50]}...")

        # Transform text through the pipeline
        features = self._pipeline.transform([text])

        # Get probability of spam (class 1)
        probas = self._model.predict_proba(features)
        spam_prob = float(probas[0][1])

        # Apply threshold
        prediction = 1 if spam_prob >= self._threshold else 0

        return {
            "prediction": prediction,
            "probability": round(spam_prob, 6),
            "threshold_used": round(self._threshold, 6),
        }

    def predict_proba(self, text: str) -> float:
        """
        Return the probability of the text being spam.
        """
        self._ensure_loaded()

        if not text or not text.strip():
            raise InvalidInputError("Text must be a non-empty string.")

        text = text.strip()

        # Transform text through the pipeline
        features = self._pipeline.transform([text])

        # Get probability of spam (class 1)
        probas = self._model.predict_proba(features)
        return float(probas[0][1])

    def batch_predict(self, texts: List[str]) -> List[Dict[str, Any]]:
        """
        Classify multiple SMS messages in a single vectorised pass.

        Results are returned in the **same order** as the input list,
        with a 1-to-1 correspondence guaranteed (Pydantic upstream
        ensures all texts are non-blank before this method is called).

        Parameters
        ----------
        texts : list[str]
            Between 1 and 100 non-blank messages.
        """
        self._ensure_loaded()

        if not texts:
            raise InvalidInputError("texts list must not be empty.")
        if len(texts) > 1000:
            raise InvalidInputError("Maximum batch size is 1000 messages.")

        # Strip each text but keep all positions so indexing stays aligned
        stripped = [t.strip() for t in texts]
        if not any(stripped):
            raise InvalidInputError("All texts are blank.")

        start = time.perf_counter()
        features = self._pipeline.transform(stripped)
        probas = self._model.predict_proba(features)
        elapsed = (time.perf_counter() - start) * 1000
        per_msg_ms = round(elapsed / len(stripped), 2)

        results = []
        for i, text in enumerate(stripped):
            spam_prob = float(probas[i][1])
            prediction = 1 if spam_prob >= self._threshold else 0
            results.append({
                "prediction": prediction,
                "probability": round(spam_prob, 6),
                "threshold_used": round(self._threshold, 6),
                "_latency_ms": per_msg_ms,   # internal hint; not part of public contract
            })
        return results

    # ── Threshold management ───────────────────────────────────────────────

    def update_threshold(self, new_threshold: float) -> None:
        """Update the decision threshold live (no model reload)."""
        if not (0.0 < new_threshold < 1.0):
            raise InvalidInputError(
                "Threshold must be strictly between 0 and 1."
            )
        old = self._threshold
        self._threshold = new_threshold
        logger.info("Threshold updated: %.4f → %.4f", old, new_threshold)

    # ── Retraining ─────────────────────────────────────────────────────────

    def retrain(
        self,
        new_dataset: pd.DataFrame,
        n_estimators: int = 300,
        test_size: float = 0.20,
        seed: int = 42,
    ) -> Dict[str, Any]:
        """
        Retrain the model from scratch on *new_dataset*.

        The new model must beat a quality gate (ROC-AUC ≥ 0.90) before
        it replaces the live model.

        Parameters
        ----------
        new_dataset : DataFrame
            Must have columns ``text`` and ``label`` (0/1).
        """
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.model_selection import train_test_split
        from sklearn.metrics import (
            roc_auc_score, average_precision_score,
            f1_score, accuracy_score,
        )
        from sklearn.pipeline import Pipeline
        from scipy.sparse import issparse

        # ── Validate dataset ──────────────────────────────────────────────
        if "text" not in new_dataset.columns or "label" not in new_dataset.columns:
            raise InvalidInputError("Dataset must have 'text' and 'label' columns.")
        if len(new_dataset) < 100:
            raise InvalidInputError(
                f"Dataset too small ({len(new_dataset)} rows). Minimum is 100."
            )
        if new_dataset["label"].nunique() < 2:
            raise InvalidInputError("Dataset must contain both spam and ham labels.")

        logger.info("Starting retrain | rows=%d | n_estimators=%d", len(new_dataset), n_estimators)
        train_start = datetime.now(timezone.utc)

        texts = new_dataset["text"].astype(str).tolist()
        labels = new_dataset["label"].astype(int).tolist()

        # ── Split ─────────────────────────────────────────────────────────
        X_train, X_test, y_train, y_test = train_test_split(
            texts, labels, test_size=test_size, random_state=seed, stratify=labels,
        )

        # ── Build pipeline ────────────────────────────────────────────────
        pipeline = Pipeline([
            ("tfidf", TfidfVectorizer(
                max_features=15000,
                ngram_range=(1, 3),
                analyzer="char_wb",
                sublinear_tf=True,
                min_df=2,
            )),
        ])

        X_train_feat = pipeline.fit_transform(X_train)
        X_test_feat = pipeline.transform(X_test)

        # ── Train classifier ──────────────────────────────────────────────
        clf = RandomForestClassifier(
            n_estimators=n_estimators,
            random_state=seed,
            n_jobs=-1,
            class_weight="balanced",
        )
        clf.fit(X_train_feat, y_train)

        # ── Evaluate ──────────────────────────────────────────────────────
        y_proba = clf.predict_proba(X_test_feat)[:, 1]
        y_pred = (y_proba >= 0.5).astype(int)

        metrics = {
            "roc_auc": round(float(roc_auc_score(y_test, y_proba)), 6),
            "pr_auc": round(float(average_precision_score(y_test, y_proba)), 6),
            "f1": round(float(f1_score(y_test, y_pred)), 6),
            "accuracy": round(float(accuracy_score(y_test, y_pred)), 6),
        }

        # Quality gate
        if metrics["roc_auc"] < 0.90:
            raise ServiceError(
                f"New model failed quality gate: ROC-AUC={metrics['roc_auc']:.4f} < 0.90. "
                "Model NOT deployed."
            )

        # ── Find optimal threshold ────────────────────────────────────────
        best_f1, best_threshold = 0.0, 0.5
        for t in np.arange(0.1, 0.9, 0.01):
            preds_t = (y_proba >= t).astype(int)
            f1_t = f1_score(y_test, preds_t)
            if f1_t > best_f1:
                best_f1 = f1_t
                best_threshold = float(t)

        # ── Determine new version tag ─────────────────────────────────────
        existing_versions = sorted(_MODELS_DIR.glob("model_v*.pkl"))
        if existing_versions:
            last_num = max(
                int(p.stem.replace("model_v", ""))
                for p in existing_versions
                if p.stem.replace("model_v", "").isdigit()
            )
            new_tag = f"v{last_num + 1}"
        else:
            new_tag = "v2"

        # ── Persist ───────────────────────────────────────────────────────
        model_path = _MODELS_DIR / f"model_{new_tag}.pkl"
        with open(model_path, "wb") as f:
            pickle.dump(clf, f)

        pipeline_path = _ARTIFACTS_DIR / "feature_pipeline.pkl"
        with open(pipeline_path, "wb") as f:
            pickle.dump(pipeline, f)

        train_end = datetime.now(timezone.utc)
        new_metadata = {
            "model_version": new_tag,
            "trained_at": train_start.isoformat(),
            "completed_at": train_end.isoformat(),
            "config": {
                "seed": seed,
                "test_size": test_size,
                "n_estimators": n_estimators,
            },
            "dataset": {
                "total_rows": len(new_dataset),
                "train_size": len(X_train),
                "test_size": len(X_test),
            },
            "test_metrics": {**metrics, "optimal_threshold": best_threshold, "optimal_f1": round(best_f1, 6)},
        }
        meta_path = _ARTIFACTS_DIR / f"metadata_{new_tag}.json"
        with open(meta_path, "w") as f:
            json.dump(new_metadata, f, indent=2)

        # ── Hot-swap the live model ───────────────────────────────────────
        self._model = clf
        self._pipeline = pipeline
        self._threshold = best_threshold
        self._model_version = new_tag
        self._metadata = new_metadata
        self._loaded_at = train_end.isoformat()

        try:
            self._feature_names = list(pipeline.get_feature_names_out())
        except Exception:
            self._feature_names = None

        logger.info(
            "Retrain complete | version=%s | ROC-AUC=%.4f | threshold=%.4f",
            new_tag, metrics["roc_auc"], best_threshold,
        )

        return {
            "success": True,
            "new_model_path": str(model_path),
            "new_version_tag": new_tag,
            "metrics": metrics,
            "threshold": best_threshold,
            "trained_at": train_start.isoformat(),
            "message": f"Model {new_tag} trained and deployed successfully.",
        }

    # ── Model information ──────────────────────────────────────────────────

    def get_model_info(self) -> Dict[str, Any]:
        """Return a comprehensive model card."""
        self._ensure_loaded()

        test_metrics = self._metadata.get("test_metrics", {})
        config = self._metadata.get("config", {})

        n_features = 0
        if self._feature_names:
            n_features = len(self._feature_names)
        elif hasattr(self._model, "n_features_in_"):
            n_features = self._model.n_features_in_

        return {
            "model_version": self._model_version,
            "threshold": round(self._threshold, 6),
            "trained_at": self._metadata.get("trained_at", "unknown"),
            "roc_auc": test_metrics.get("roc_auc", 0.0),
            "pr_auc": test_metrics.get("pr_auc", 0.0),
            "f1": test_metrics.get("f1", 0.0),
            "accuracy": test_metrics.get("accuracy", 0.0),
            "optimal_f1": test_metrics.get("optimal_f1", 0.0),
            "optimal_threshold": test_metrics.get("optimal_threshold", 0.5),
            "n_features": n_features,
            "n_estimators": config.get("n_estimators", 300),
        }

    def get_feature_importance(self, top_n: int = 20) -> List[Dict[str, Any]]:
        """Return the top-N features ranked by Gini importance."""
        self._ensure_loaded()

        if self._model_type == "RandomForestClassifier":
            importances = self._model.feature_importances_
        elif self._model_type == "LogisticRegression":
            # Use absolute coefficients as importance
            importances = np.abs(self._model.coef_[0])
        else:
            return [{"rank": 1, "feature": "Unknown Model Type", "importance": 0.0}]

        if self._feature_names and len(self._feature_names) == len(importances):
            names = self._feature_names
        else:
            names = [f"feat_{i}" for i in range(len(importances))]

        sorted_idx = np.argsort(importances)[::-1][:top_n]

        return [
            {
                "rank": rank + 1,
                "feature": names[idx],
                "importance": round(float(importances[idx]), 8),
            }
            for rank, idx in enumerate(sorted_idx)
        ]

    # ── Health check ───────────────────────────────────────────────────────

    def health(self) -> Dict[str, Any]:
        """Return health status for load balancers / orchestrators."""
        if not self._loaded:
            return {"status": "not_loaded"}
        return {
            "status": "healthy",
            "model_version": self._model_version,
            "threshold": self._threshold,
            "loaded_at": self._loaded_at,
        }
