"""
ml/service.py
-------------
Framework-agnostic spam detection service — v8.

4-layer hybrid detection pipeline:
  Layer 1  → Traditional ML ensemble (soft-vote)
  Layer 2  → Groq LLM semantic analysis
  Layer 3  → Heuristic + threat intelligence (inside hybrid_detector)
  Layer 4  → Weighted ensemble decision (hybrid_detector)

Verdict output includes:
  final_prediction, final_confidence, threat_level,
  ai_generated_probability, phishing_probability,
  ml_model_score, groq_semantic_score, heuristic_score,
  detected_categories, reasoning, feature_importance,
  recommended_action, safe_for_user
"""

import json
import os
import time
import pickle
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
import sys

_ML_ROOT = Path(__file__).resolve().parent
if str(_ML_ROOT) not in sys.path:
    sys.path.insert(0, str(_ML_ROOT))

from feature_pipeline import SMSFeaturePipeline
from spam_type_classifier import get_spam_type_classifier

logger = logging.getLogger("ml.service")

_MODELS_DIR    = _ML_ROOT / "models"
_ARTIFACTS_DIR = _ML_ROOT / "artifacts"
_DATA_DIR      = _ML_ROOT / "data"

_GROQ_ENABLED = os.environ.get("GROQ_ENABLED", "true").lower() == "true"


# ── Custom exceptions ─────────────────────────────────────────────────────────

class ServiceError(Exception):
    pass

class InvalidInputError(ServiceError):
    pass

class ModelNotLoadedError(ServiceError):
    pass


# ── Service ───────────────────────────────────────────────────────────────────

class SpamDetectorService:
    """
    Stateful ML service with full 4-layer hybrid detection.

    Parameters
    ----------
    model_version : str  e.g. "v8"
    auto_load     : bool load model at construction time
    groq_enabled  : bool whether to invoke Groq (Layer 2)
    """

    def __init__(
        self,
        model_version: str = "v8",
        auto_load: bool = True,
        groq_enabled: Optional[bool] = None,
    ):
        self._model_version   = model_version
        self._model: Any      = None
        self._ensemble: Any   = None
        self._pipeline: Any   = None
        self._is_ensemble     = False
        self._threshold       = 0.5
        self._spam_threshold  = 0.70
        self._suspicious_threshold = 0.50
        self._ham_threshold   = 0.35
        self._metadata: Dict  = {}
        self._feature_names: Optional[List[str]] = None
        self._loaded          = False
        self._loaded_at: Optional[str] = None
        self._groq_enabled    = groq_enabled if groq_enabled is not None else _GROQ_ENABLED

        if auto_load:
            self._load()

    # ── Loading ────────────────────────────────────────────────────────────

    def _load(self) -> None:
        tag = self._model_version

        ensemble_path  = _ARTIFACTS_DIR / f"ensemble_{tag}.pkl"
        model_path     = _ARTIFACTS_DIR / f"model_{tag}.pkl"
        pipeline_path  = _ARTIFACTS_DIR / "feature_pipeline.pkl"
        metadata_path  = _ARTIFACTS_DIR / f"metadata_{tag}.json"
        threshold_path = _ARTIFACTS_DIR / f"threshold_optimiser_{tag}.pkl"

        import os as _os
        logger.info("[ML] Models dir: %s | exists=%s", _MODELS_DIR, _MODELS_DIR.exists())
        if _MODELS_DIR.exists():
            logger.info("[ML] Models: %s", _os.listdir(_MODELS_DIR))
        if _ARTIFACTS_DIR.exists():
            logger.info("[ML] Artifacts: %s", _os.listdir(_ARTIFACTS_DIR))

        # Register pipeline classes before unpickling
        try:
            from feature_pipeline import RobustSMSFeaturePipeline
            sys.modules["__main__"].RobustSMSFeaturePipeline = RobustSMSFeaturePipeline
        except ImportError:
            pass
        try:
            from feature_pipeline import RobustSMSFeaturePipelineV7
            sys.modules["__main__"].RobustSMSFeaturePipelineV7 = RobustSMSFeaturePipelineV7
        except ImportError:
            pass
        sys.modules["__main__"].SMSFeaturePipeline = SMSFeaturePipeline
        if "logger" not in sys.modules["__main__"].__dict__:
            sys.modules["__main__"].logger = logger

        if ensemble_path.exists():
            logger.info("[ML] Loading ensemble %s", ensemble_path)
            with open(ensemble_path, "rb") as f:
                self._ensemble = pickle.load(f)
            self._is_ensemble = True
            self._pipeline    = self._ensemble["pipeline"]
            logger.info("[ML] Ensemble models: %s", list(self._ensemble.get("models", {}).keys()))
        elif model_path.exists():
            logger.info("[ML] Loading single model %s", model_path)
            with open(model_path, "rb") as f:
                self._model = pickle.load(f)
            self._is_ensemble = False
        else:
            raise ModelNotLoadedError(f"No model file found for version: {tag}")

        if not self._is_ensemble:
            # Try versioned pipeline first, then generic
            vp = _ARTIFACTS_DIR / f"feature_pipeline_{tag}.pkl"
            pp = vp if vp.exists() else pipeline_path
            if not pp.exists():
                raise ModelNotLoadedError(f"Pipeline file not found: {pp}")
            with open(pp, "rb") as f:
                self._pipeline = pickle.load(f)

        if metadata_path.exists():
            with open(metadata_path) as f:
                self._metadata = json.load(f)
            opt = self._metadata.get("optimal_threshold", 0.5)
            self._threshold = float(opt) if isinstance(opt, (int, float)) else float(opt.get("value", 0.5))

        if threshold_path.exists():
            try:
                with open(threshold_path, "rb") as f:
                    td = pickle.load(f)
                if isinstance(td, dict):
                    self._threshold              = td.get("threshold",            self._threshold)
                    self._spam_threshold         = td.get("spam_threshold",       self._spam_threshold)
                    self._suspicious_threshold   = td.get("suspicious_threshold", self._suspicious_threshold)
                    self._ham_threshold          = td.get("ham_threshold",        self._ham_threshold)
            except Exception:
                pass

        try:
            if hasattr(self._pipeline, "get_feature_names_out"):
                self._feature_names = list(self._pipeline.get_feature_names_out())
        except Exception:
            pass

        self._loaded    = True
        self._loaded_at = datetime.now(timezone.utc).isoformat()
        logger.info("[ML] Loaded v%s | threshold=%.4f | groq=%s", tag, self._threshold, self._groq_enabled)

    def _ensure_loaded(self) -> None:
        ok = (self._is_ensemble and self._ensemble) or self._model
        if not self._loaded or not ok:
            raise ModelNotLoadedError("Model not loaded. Call init_spam_detector() first.")

    # ── Ensemble inference ─────────────────────────────────────────────────

    def _predict_proba_single(self, features) -> float:
        if self._is_ensemble and self._ensemble:
            ens = self._ensemble
            models_cfg = ens.get("models", {})
            meta_learner = ens.get("meta_learner")
            ensemble_type = ens.get("ensemble_type", "soft_vote")

            base_probs: Dict[str, float] = {}
            total_w = weighted_p = 0.0
            for key, cfg in models_cfg.items():
                m, w = cfg.get("model"), cfg.get("weight", 0.0)
                if m is None or w == 0.0:
                    continue
                try:
                    p = float(m.predict_proba(features)[0][1])
                    base_probs[key] = p
                    weighted_p += w * p
                    total_w    += w
                except Exception as e:
                    logger.warning("[ML] Sub-model %s failed: %s", key, e)

            if ensemble_type == "stacking" and meta_learner and base_probs:
                try:
                    row = list(base_probs.values())
                    return float(meta_learner.predict_proba(np.array([row]))[0][1])
                except Exception:
                    pass
            return weighted_p / total_w if total_w > 0 else 0.5
        else:
            return float(self._model.predict_proba(features)[0][1])

    def _predict_proba_batch(self, features) -> np.ndarray:
        if self._is_ensemble and self._ensemble:
            ens = self._ensemble
            models_cfg = ens.get("models", {})
            total_w = 0.0
            weighted_p = None
            for key, cfg in models_cfg.items():
                m, w = cfg.get("model"), cfg.get("weight", 0.0)
                if m is None or w == 0.0:
                    continue
                try:
                    p = m.predict_proba(features)[:, 1]
                    weighted_p = (weighted_p + w * p) if weighted_p is not None else w * p
                    total_w += w
                except Exception as e:
                    logger.warning("[ML] Batch sub-model %s: %s", key, e)
            return weighted_p / total_w if total_w > 0 else np.full(features.shape[0], 0.5)
        else:
            return self._model.predict_proba(features)[:, 1]

    # ── Verdict tier ───────────────────────────────────────────────────────

    def _get_verdict(self, spam_prob: float) -> tuple:
        if spam_prob >= self._spam_threshold:
            return 1, "spam", "high"
        elif spam_prob >= self._suspicious_threshold:
            return 1, "suspicious", "medium"
        return 0, "ham", "high" if spam_prob < self._ham_threshold else "medium"

    # ── Feature importance ─────────────────────────────────────────────────

    def _get_feature_importance_for_text(self, text: str, top_n: int = 8) -> List[Dict]:
        """Extract top predictive tokens for a specific message."""
        try:
            feat = self._pipeline.transform([text])
            names = self._feature_names or []

            importances = None
            if self._is_ensemble and self._ensemble:
                for key in ("rf", "lgbm", "xgb"):
                    cfg = self._ensemble.get("models", {}).get(key, {})
                    m = cfg.get("model")
                    if m and hasattr(m, "feature_importances_"):
                        importances = m.feature_importances_
                        break
                if importances is None:
                    for key in ("lr",):
                        cfg = self._ensemble.get("models", {}).get(key, {})
                        m = cfg.get("model")
                        if m and hasattr(m, "coef_"):
                            importances = np.abs(m.coef_[0])
                            break
            elif self._model and hasattr(self._model, "feature_importances_"):
                importances = self._model.feature_importances_

            if importances is None or not names:
                return []

            # Only look at non-zero feature positions in the text
            import scipy.sparse as sp
            feat_arr = feat.toarray()[0] if sp.issparse(feat) else np.asarray(feat)[0]
            nonzero = np.where(feat_arr > 0)[0]
            if len(nonzero) == 0:
                return []

            scores = [(names[i], float(importances[i])) for i in nonzero if i < len(importances)]
            scores.sort(key=lambda x: x[1], reverse=True)
            return [{"feature": f, "importance": round(imp, 6)} for f, imp in scores[:top_n]]
        except Exception:
            return []

    # ── Core predict (full hybrid pipeline) ───────────────────────────────

    def predict(self, text: str) -> Dict[str, Any]:
        """
        Full 4-layer hybrid prediction.

        Returns
        -------
        dict with all intelligence fields including:
          final_prediction, final_confidence, threat_level,
          ai_generated_probability, phishing_probability,
          ml_model_score, groq_semantic_score, heuristic_score,
          detected_categories, reasoning, feature_importance,
          recommended_action, safe_for_user, probability,
          verdict, spam_type, spam_type_confidence, spam_scores
        """
        self._ensure_loaded()
        if not text or not text.strip():
            raise InvalidInputError("Text must be a non-empty string.")
        text = text.strip()

        # ── Layer 1: ML inference ─────────────────────────────────────────
        features  = self._pipeline.transform([text])
        ml_prob   = self._predict_proba_single(features)
        _, verdict, confidence_tier = self._get_verdict(ml_prob)

        # ── Layer 2: Heuristic Analysis (Fast local check) ────────────────
        from hybrid_detector import _heuristic_score
        h_score, h_cats = _heuristic_score(text)

        # ── Layer 3: Conditional Groq Semantic Analysis ───────────────────
        # Only call Groq if the message is suspicious, borderline, or has conflicting signals
        needs_groq = False
        if 0.05 < ml_prob < 0.85:
            needs_groq = True  # Borderline ML
        elif h_score > 0.10 and ml_prob < 0.50:
            needs_groq = True  # Heuristic alert but ML missed it
        elif "ai_spam" in h_cats or "phishing" in h_cats:
            needs_groq = True  # High-risk patterns detected locally

        groq_result = None
        if self._groq_enabled and needs_groq:
            try:
                from groq_analyzer import get_groq_analyzer
                groq_result = get_groq_analyzer().analyze(text)
                logger.info("[ML] Groq Fallback: threat=%s latency=%.0fms",
                            groq_result.threat_level, groq_result.latency_ms)
            except Exception as e:
                logger.warning("[ML] Groq fallback failed: %s", e)
        else:
            logger.info("[ML] Skipping Groq analysis (ML Confidence: %.1f%%)", ml_prob * 100)

        # ── Layer 3+4: Heuristic + Ensemble decision ───────────────────────
        from hybrid_detector import hybrid_detect
        hybrid = hybrid_detect(
            text=text,
            ml_probability=ml_prob,
            groq_result=groq_result,
            groq_enabled=self._groq_enabled,
            h_score=h_score,
            h_cats=h_cats
        )

        # ── Spam type classification (multi-class) ────────────────────────
        spam_classifier = get_spam_type_classifier()
        spam_type_result = spam_classifier.classify_spam_type(text, hybrid.final_score)

        # Override ML verdict with hybrid
        final_pred = hybrid.final_prediction
        final_verdict = (
            "spam" if final_pred == 1 and hybrid.final_confidence >= self._spam_threshold
            else "suspicious" if final_pred == 1
            else "ham"
        )

        # ── Feature importance for this message ───────────────────────────
        feature_imp = self._get_feature_importance_for_text(text)

        return {
            # Core
            "prediction":          final_pred,
            "probability":         round(hybrid.final_score, 6),
            "threshold_used":      round(self._threshold, 6),
            "verdict":             final_verdict,
            "confidence_tier":     confidence_tier,
            "confidence_score":    round(hybrid.final_confidence, 4),
            # Hybrid intelligence
            "final_prediction":    "spam" if final_pred == 1 else "ham",
            "final_confidence":    round(hybrid.final_confidence * 100, 2),
            "threat_level":        hybrid.threat_level,
            "ml_model_score":      round(ml_prob * 100, 2),
            "groq_semantic_score": round((hybrid.groq_score or 0.0) * 100, 2),
            "heuristic_score":     round(hybrid.heuristic_score * 100, 2),
            "ai_generated_probability": round(hybrid.ai_generated_probability * 100, 2),
            "phishing_probability":     round(hybrid.phishing_probability * 100, 2),
            "detected_categories": hybrid.detected_categories,
            "reasoning":           hybrid.reasoning,
            "recommended_action":  hybrid.recommended_action,
            "safe_for_user":       final_pred == 0,
            "groq_available":      hybrid.groq_available,
            # Spam type (Prioritize Hybrid detection over secondary classifier)
            "spam_type":                 hybrid.spam_type if hybrid.spam_type not in ("ham", "suspicious") else spam_type_result["spam_type"],
            "spam_type_confidence":      spam_type_result["confidence"],
            "spam_type_explanation":     spam_type_result["explanation"] if hybrid.spam_type == "ham" else hybrid.reasoning,
            "spam_scores": {
                "ai_spam":           max(spam_type_result["ai_spam_score"], 85.0 if hybrid.spam_type == "ai_spam" else 0.0),
                "traditional_spam":  max(spam_type_result["traditional_spam_score"], 85.0 if hybrid.spam_type == "traditional_spam" else 0.0),
                "ham":               min(spam_type_result["ham_score"], 15.0 if final_pred == 1 else 100.0),
            },
            # Feature importance
            "feature_importance": feature_imp,
        }

    def predict_proba(self, text: str) -> float:
        self._ensure_loaded()
        if not text or not text.strip():
            raise InvalidInputError("Text must be non-empty.")
        return self._predict_proba_single(self._pipeline.transform([text.strip()]))

    def batch_predict(self, texts: List[str]) -> List[Dict[str, Any]]:
        self._ensure_loaded()
        if not texts:
            raise InvalidInputError("texts list must not be empty.")
        if len(texts) > 1000:
            raise InvalidInputError("Maximum batch size is 1000.")

        stripped = [t.strip() for t in texts]
        start    = time.perf_counter()
        features = self._pipeline.transform(stripped)
        all_p    = self._predict_proba_batch(features)
        per_ms   = round((time.perf_counter() - start) * 1000 / len(stripped), 2)

        spam_classifier = get_spam_type_classifier()
        results = []
        for i, text in enumerate(stripped):
            ml_prob = float(all_p[i])
            pred, verdict, tier = self._get_verdict(ml_prob)

            # Heuristic only (no Groq on batch — too slow)
            from hybrid_detector import hybrid_detect
            hybrid = hybrid_detect(text=text, ml_probability=ml_prob, groq_result=None, groq_enabled=False)

            st_res = spam_classifier.classify_spam_type(text, ml_prob)

            # Override if heuristic catches spam ML missed
            if st_res["spam_type"] in ("ai_spam", "traditional_spam") and pred == 0:
                pred   = 1
                verdict = "spam"
                ml_prob = max(ml_prob, 0.85)

            results.append({
                "prediction":    pred,
                "probability":   round(hybrid.final_score, 6),
                "threshold_used": round(self._threshold, 6),
                "verdict":       verdict,
                "confidence_tier": tier,
                "confidence_score": round(hybrid.final_confidence, 4),
                "threat_level":  hybrid.threat_level,
                "ml_model_score": round(ml_prob * 100, 2),
                "groq_semantic_score": 0.0,
                "heuristic_score": round(hybrid.heuristic_score * 100, 2),
                "ai_generated_probability": round(hybrid.ai_generated_probability * 100, 2),
                "phishing_probability":     round(hybrid.phishing_probability * 100, 2),
                "detected_categories": hybrid.detected_categories,
                "reasoning":      hybrid.reasoning,
                "recommended_action": hybrid.recommended_action,
                "safe_for_user": pred == 0,
                "spam_type":      st_res["spam_type"],
                "spam_type_confidence":   st_res["confidence"],
                "spam_type_explanation":  st_res["explanation"],
                "spam_scores": {
                    "ai_spam":          st_res["ai_spam_score"],
                    "traditional_spam": st_res["traditional_spam_score"],
                    "ham":              st_res["ham_score"],
                },
                "_latency_ms": per_ms,
            })
        return results

    # ── Threshold management ───────────────────────────────────────────────

    def update_threshold(self, new_threshold: float) -> None:
        if not (0.0 < new_threshold < 1.0):
            raise InvalidInputError("Threshold must be between 0 and 1.")
        old = self._threshold
        self._threshold = new_threshold
        logger.info("[ML] Threshold updated: %.4f → %.4f", old, new_threshold)

    # ── Retrain ────────────────────────────────────────────────────────────

    def retrain(self, new_dataset: pd.DataFrame, n_estimators: int = 300,
                test_size: float = 0.20, seed: int = 42) -> Dict[str, Any]:
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.model_selection import train_test_split
        from sklearn.metrics import roc_auc_score, average_precision_score, f1_score, accuracy_score
        from sklearn.pipeline import Pipeline

        if "text" not in new_dataset.columns or "label" not in new_dataset.columns:
            raise InvalidInputError("Dataset must have 'text' and 'label' columns.")
        if len(new_dataset) < 100:
            raise InvalidInputError(f"Dataset too small ({len(new_dataset)} rows). Min 100.")

        texts  = new_dataset["text"].astype(str).tolist()
        labels = new_dataset["label"].astype(int).tolist()
        X_tr, X_te, y_tr, y_te = train_test_split(texts, labels, test_size=test_size,
                                                    random_state=seed, stratify=labels)
        pipeline = Pipeline([("tfidf", TfidfVectorizer(max_features=15000, ngram_range=(1,3),
                                                         analyzer="char_wb", sublinear_tf=True, min_df=2))])
        X_tr_f = pipeline.fit_transform(X_tr)
        X_te_f = pipeline.transform(X_te)

        clf = RandomForestClassifier(n_estimators=n_estimators, random_state=seed,
                                     n_jobs=-1, class_weight="balanced")
        clf.fit(X_tr_f, y_tr)
        y_p = clf.predict_proba(X_te_f)[:, 1]
        y_pred = (y_p >= 0.5).astype(int)
        metrics = {
            "roc_auc":  round(float(roc_auc_score(y_te, y_p)), 6),
            "f1":       round(float(f1_score(y_te, y_pred)), 6),
            "accuracy": round(float(accuracy_score(y_te, y_pred)), 6),
        }
        if metrics["roc_auc"] < 0.90:
            raise ServiceError(f"Quality gate failed: ROC-AUC={metrics['roc_auc']:.4f} < 0.90")

        existing = sorted(_MODELS_DIR.glob("model_v*.pkl"))
        last = max((int(p.stem.replace("model_v","")) for p in existing
                    if p.stem.replace("model_v","").isdigit()), default=8)
        new_tag  = f"v{last+1}"
        with open(_MODELS_DIR / f"model_{new_tag}.pkl", "wb") as f:
            pickle.dump(clf, f)
        with open(_ARTIFACTS_DIR / "feature_pipeline.pkl", "wb") as f:
            pickle.dump(pipeline, f)

        self._model = clf; self._pipeline = pipeline
        self._threshold = 0.5; self._model_version = new_tag
        logger.info("[ML] Retrain → %s | ROC-AUC=%.4f", new_tag, metrics["roc_auc"])
        return {"success": True, "new_version_tag": new_tag, "metrics": metrics}

    # ── Model info ─────────────────────────────────────────────────────────

    def get_model_info(self) -> Dict[str, Any]:
        self._ensure_loaded()
        tm = self._metadata.get("test_metrics", {})
        
        # Extract model params if single model
        n_est = 0
        if self._model and hasattr(self._model, "n_estimators"):
            n_est = self._model.n_estimators
        elif self._is_ensemble and self._ensemble:
            # Pick RF estimators as representative
            m = self._ensemble.get("models", {}).get("rf", {}).get("model")
            if m and hasattr(m, "n_estimators"):
                n_est = m.n_estimators

        return {
            "model_version":      self._model_version,
            "is_ensemble":        self._is_ensemble,
            "threshold":          round(self._threshold, 6),
            "trained_at":         self._metadata.get("trained_at", "unknown"),
            "roc_auc":            round(tm.get("roc_auc", 0.0), 4),
            "pr_auc":             round(tm.get("pr_auc", 0.0), 4),
            "f1":                 round(tm.get("f1", 0.0), 4),
            "accuracy":           round(tm.get("accuracy", 0.0), 4),
            "optimal_f1":         round(tm.get("optimal_f1", 0.0), 4),
            "optimal_threshold":  round(tm.get("optimal_threshold", 0.5), 4),
            "n_features":         len(self._feature_names) if self._feature_names else 0,
            "n_estimators":       n_est,
            "ensemble_composition": self._metadata.get("ensemble_composition", {}),
            "groq_enabled":       self._groq_enabled,
        }

    def get_feature_importance(self, top_n: int = 20) -> List[Dict[str, Any]]:
        self._ensure_loaded()
        importances = None
        if self._is_ensemble and self._ensemble:
            for key in ("rf", "lgbm", "xgb", "lr"):
                m = self._ensemble.get("models", {}).get(key, {}).get("model")
                if m and hasattr(m, "feature_importances_"):
                    importances = m.feature_importances_; break
                if m and hasattr(m, "coef_"):
                    importances = np.abs(m.coef_[0]); break
        elif self._model:
            if hasattr(self._model, "feature_importances_"):
                importances = self._model.feature_importances_

        if importances is None or not self._feature_names:
            return []
        idx = np.argsort(importances)[::-1][:top_n]
        return [{"feature": self._feature_names[i], "importance": round(float(importances[i]), 6)}
                for i in idx if i < len(self._feature_names)]

    def health(self) -> Dict[str, Any]:
        return {
            "status":        "healthy" if self._loaded else "not_loaded",
            "model_version": self._model_version,
            "is_ensemble":   self._is_ensemble,
            "loaded_at":     self._loaded_at,
            "groq_enabled":  self._groq_enabled,
            "threshold":     round(self._threshold, 6),
        }
