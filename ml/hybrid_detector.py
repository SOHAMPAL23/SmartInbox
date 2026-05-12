"""
ml/hybrid_detector.py
---------------------
Layer 4 — Hybrid Ensemble Decision Engine

Combines signals from all three detection layers:
  - Layer 1: Traditional ML (sklearn ensemble)
  - Layer 2: Groq LLM semantic analysis
  - Layer 3: Heuristic pattern matching

Weighted ensemble formula:
  Final Score = 0.45 * ML_prob + 0.40 * Groq_prob + 0.15 * Heuristic_prob

When Groq is unavailable, weights redistribute to:
  Final Score = 0.70 * ML_prob + 0.30 * Heuristic_prob

Dynamic thresholds:
  HIGH_RISK   = 0.35  (any score above → at minimum suspicious)
  NORMAL      = 0.50  (standard spam threshold)
  STRICT      = 0.70  (high-confidence spam)
"""

import re
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("ml.hybrid_detector")

# ── Ensemble weights ──────────────────────────────────────────────────────────
_ML_WEIGHT       = 0.70  # Primary Statistical Layer
_GROQ_WEIGHT     = 0.15  # Fallback Semantic Layer
_HEUR_WEIGHT     = 0.15  # Heuristic Pattern Layer

# When Groq unavailable, redistribute
_ML_WEIGHT_NO_GROQ   = 0.80
_HEUR_WEIGHT_NO_GROQ = 0.20

# ── Detection Thresholds ───────────────────────────────────────────────────
_STRICT_THRESHOLD    = 0.50  # Critical
_NORMAL_THRESHOLD    = 0.15  # High Risk (Spam)
_HIGH_RISK_THRESHOLD = 0.05  # Medium Risk (Suspicious)

# ── Heuristic detection patterns (rule-based engine) ─────────────────────────

_TRADITIONAL_SPAM_PATTERNS = [
    # Prizes and lotteries
    r"\b(you('ve| have) won|winner|prize|rewards?|benefits?|claim your|free gift|gift card|bonus|payout)\b",
    r"\b(congratulations?|congrats)\b.*\b(won|win|prize|selected|qualified)\b",
    r"\b(accumulated|earned).{0,50}\b(balance|rewards?|points|benefits?)\b",
    # Urgency markers
    r"\b(urgent|immediately|asap|act now|hurry|limited time|expires?|deadline|last chance|forfeiture)\b",
    r"\b(account|card|access|benefits?)\b.{0,50}\b(suspend|block|lock|terminat|restrict|expire|deactivat|forfeit)\b",
    r"\b(act|respond|claim).{0,50}\b(before|by|within).{0,50}\b(midnight|today|24 hours)\b",
    # Financial scams
    r"\$\d[\d,]*(\.\d{2})?\s*(bonus|cashback|reward|prize|loan|balance)",
    r"\b(bitcoin|crypto|wallet|invest|forex|trading)\b.{0,50}\b(profit|return|earn|guarant)\b",
    # Phishing
    r"\b(verify|confirm|validate|authenticate|secure|update|log[\s-]?in)\b.{0,50}\b(account|identity|password|details|profile|security)\b",
    r"\b(click|tap|visit|follow|log[\s-]?in|go to).{0,50}\b(here|link|below|now|portal|page)\b",
    r"\b(secure|official|official-link|support-link).{0,50}\b(link|portal|website)\b",
    r"\b(suspicious|unauthorized|unusual)\b.{0,50}\b(activity|login|access|transaction)\b",
    # Short-link spam
    r"\b(bit\.ly|tinyurl|goo\.gl|t\.co|ow\.ly|rb\.gy|shorturl|t\.ly|cutt\.ly)\b",
    # Leet-speak / obfuscation
    r"[a-z]+[0-9][a-z]*[0-9]+[a-z]*",  # w1nn3r, fr33
    r"[!?]{2,}",                          # multiple exclamation/question
    # KYC scams
    r"\b(kyc|know your customer)\b.{0,40}\b(complet|verif|updat)\b",
    r"\b(redelivery|customs|parcel held|pay to release)\b",
]

_AI_SPAM_PATTERNS = [
    # Cold outreach
    r"i hope (this (finds|reaches) you|i('m| am) not (overstepping|interrupting))",
    r"forgive (the|my|this) cold (outreach|email|message)",
    r"reaching out (directly|on behalf|to you today)",
    r"i('ve| have) been (following|tracking|watching) your (work|career|company|profile)",
    r"i (do )?value your time",
    r"i don't want to take (up )?too much (of your )?time",
    r"(just|quick(ly)?) (checking|wanted to) (if|see|know)",
    # Professional manipulation
    r"\b(consortium|collective) of investors",
    r"mutually beneficial (opportunity|arrangement|partnership)",
    r"positioning yourself (for|to)",
    r"rooted in measurable (outcomes|results|data)",
    r"(select|exclusive) (group|number) of (professionals|clients|executives)",
    # Persuasive CTAs
    r"would (love to|you be (open|willing|interested))",
    r"worth (a|your) (quick|brief|15[\s-]minute) (call|chat|conversation|introduction)",
    r"at your (earliest )?convenience",
    r"no (obligation|strings attached|commitment)",
    r"(complimentary|free) (consultation|session|demo|assessment)",
    r"happy to (share|schedule|arrange|set up)",
    # Business jargon density (AI spam hallmark)
    r"\b(leverage|synergy|scalable|ecosystem|stakeholder|deliverable|bandwidth|roadmap|kpi|roi|monetize)\b",
    r"\b(data[\s-]driven|high[\s-]growth|market[\s-]leading|best[\s-]in[\s-]class)\b",
    # Investment language
    r"\b(passive income|financial freedom|wealth building|portfolio|diversif)\b",
    r"\b(pre[\s-]approved|pre[\s-]qualified|guaranteed approval|100%? (approval|return|guaranteed))\b",
    # HR/Job scams
    r"\b(work from home|remote (position|opportunity|work)|flexible hours|be your own boss)\b",
    r"\b(earn \$\d+|make \$\d+|get paid)\b.{0,30}\b(day|week|hour|minute)\b",
]

_PHISHING_PATTERNS = [
    r"\b(otp|one[\s-]time (password|code|pin))\b.{0,30}\b(shared|given|enter|use|never)\b",
    r"\b(bank|account|card)\b.{0,30}\b(block|suspend|frozen|compromised|at risk)\b",
    r"(password|pin|cvv|ssn|social security).{0,30}(enter|provide|confirm|verify|update)",
    r"(irs|income tax|government).{0,30}(refund|owe|unpaid|arrest|penalty)",
    r"(inheritance|next of kin|beneficiary|unclaimed funds|million dollars?)",
    r"\b(gift card|itunes|google play|amazon gift).{0,30}(pay|send|purchase|buy)\b",
]

_PROMPT_INJECTION_PATTERNS = [
    r"ignore (previous|all|prior) instructions",
    r"(pretend|act|behave) (as if|like) (you are|you're|this is)",
    r"(system prompt|jailbreak|bypass|override).{0,30}(filter|detection|classifier)",
    r"(translate|repeat|say|output|print).{0,20}(following|this|the text)",
    r"you (are|must|should|will) (now|always|never).{0,30}(answer|respond|say|output)",
]

_COMPILED_TRAD = [re.compile(p, re.IGNORECASE) for p in _TRADITIONAL_SPAM_PATTERNS]
_COMPILED_AI   = [re.compile(p, re.IGNORECASE) for p in _AI_SPAM_PATTERNS]
_COMPILED_PHISH = [re.compile(p, re.IGNORECASE) for p in _PHISHING_PATTERNS]
_COMPILED_INJECT = [re.compile(p, re.IGNORECASE) for p in _PROMPT_INJECTION_PATTERNS]


def _heuristic_score(text: str) -> tuple:
    """
    Compute heuristic spam score 0–1 and list of detected categories.

    Returns (score: float, categories: List[str])
    """
    score = 0.0
    cats: List[str] = []

    trad_hits  = sum(1 for p in _COMPILED_TRAD  if p.search(text))
    ai_hits    = sum(1 for p in _COMPILED_AI    if p.search(text))
    phish_hits = sum(1 for p in _COMPILED_PHISH if p.search(text))
    inj_hits   = sum(1 for p in _COMPILED_INJECT if p.search(text))

    if trad_hits >= 2:
        score += min(trad_hits * 0.30, 0.70)
        cats.append("traditional_spam")
    elif trad_hits == 1:
        score += 0.25
        cats.append("traditional_spam")

    if ai_hits >= 3:
        score += min(ai_hits * 0.12, 0.40)
        cats.append("ai_spam")
    elif ai_hits == 2:
        score += 0.18
        cats.append("ai_spam")
    elif ai_hits == 1:
        score += 0.08

    if phish_hits >= 1:
        score += min(phish_hits * 0.20, 0.40)
        cats.append("phishing")

    if inj_hits >= 1:
        score += 0.50  # prompt injection is almost always adversarial
        cats.append("prompt_injection")

    # All-caps ratio
    upper_ratio = sum(1 for c in text if c.isupper()) / max(len(text), 1)
    if upper_ratio > 0.35:
        score += 0.15
        cats.append("excessive_caps")

    # Excessive punctuation
    if text.count("!") + text.count("?") >= 3:
        score += 0.10

    return min(score, 1.0), cats


# ── Hybrid Decision Result ────────────────────────────────────────────────────

class HybridResult:
    """Final output from the hybrid detection pipeline."""

    def __init__(
        self,
        final_prediction: int,
        final_confidence: float,
        final_score: float,
        threat_level: str,
        ml_score: float,
        groq_score: Optional[float],
        heuristic_score: float,
        detected_categories: List[str],
        reasoning: str,
        recommended_action: str,
        ai_generated_probability: float,
        phishing_probability: float,
        spam_type: str,
        groq_available: bool,
    ):
        self.final_prediction = final_prediction
        self.final_confidence = final_confidence
        self.final_score = final_score
        self.threat_level = threat_level
        self.ml_score = ml_score
        self.groq_score = groq_score
        self.heuristic_score = heuristic_score
        self.detected_categories = detected_categories
        self.reasoning = reasoning
        self.recommended_action = recommended_action
        self.ai_generated_probability = ai_generated_probability
        self.phishing_probability = phishing_probability
        self.spam_type = spam_type
        self.groq_available = groq_available

    def to_dict(self) -> Dict[str, Any]:
        return {
            "final_prediction": "spam" if self.final_prediction == 1 else "ham",
            "final_confidence": round(self.final_confidence * 100, 2),
            "ai_generated_probability": round(self.ai_generated_probability * 100, 2),
            "phishing_probability": round(self.phishing_probability * 100, 2),
            "threat_level": self.threat_level,
            "ml_model_score": round(self.ml_score * 100, 2),
            "groq_semantic_score": round((self.groq_score or 0.0) * 100, 2),
            "heuristic_score": round(self.heuristic_score * 100, 2),
            "detected_categories": self.detected_categories,
            "reasoning": self.reasoning,
            "recommended_action": self.recommended_action,
            "spam_type": self.spam_type,
            "safe_for_user": self.final_prediction == 0,
            "groq_available": self.groq_available,
        }


# ── Core hybrid detection function ───────────────────────────────────────────

def hybrid_detect(
    text: str,
    ml_probability: float,
    groq_result=None,   # Optional[GroqResult]
    groq_enabled: bool = True,
    h_score: Optional[float] = None,
    h_cats: Optional[List[str]] = None,
) -> HybridResult:
    """
    Run the 4-layer hybrid detection pipeline.

    Parameters
    ----------
    text            : Original SMS text
    ml_probability  : Spam probability from the ML ensemble (0–1)
    groq_result     : GroqResult instance (None if Groq disabled/failed)
    groq_enabled    : Whether Groq analysis was attempted

    Returns
    -------
    HybridResult with all intelligence fields populated
    """
    # Layer 3: Heuristic score (reuse if provided)
    if h_score is None or h_cats is None:
        h_score, h_cats = _heuristic_score(text)

    # Layer 4: Weighted ensemble
    groq_available = groq_result is not None and groq_result.available
    g_score = groq_result.spam_score if groq_available else None

    if groq_available and g_score is not None:
        final_score = (
            _ML_WEIGHT * ml_probability
            + _GROQ_WEIGHT * g_score
            + _HEUR_WEIGHT * h_score
        )
    else:
        final_score = (
            _ML_WEIGHT_NO_GROQ * ml_probability
            + _HEUR_WEIGHT_NO_GROQ * h_score
        )

    # ── Spam Ratio Amplifier (Aggressive Tuning) ─────────────────────────────
    # If ML is confident OR heuristics found a strong match, boost significantly
    is_trad_spam = "traditional_spam" in h_cats
    
    if final_score > 0.05:
        # Boost if ML and Heuristic/Groq agree even slightly
        if (ml_probability > 0.08 and h_score > 0.08) or (g_score and g_score > 0.08) or is_trad_spam:
            final_score *= 3.0  # Hyper-aggressive 200% boost
            if is_trad_spam:
                final_score = max(final_score, 0.25)
    
    # ── Final Score Normalization ───────────────────────────────────────────
    # Removed Binary Polarizer to allow truly variable and proportional scoring.
    final_score = min(max(final_score, 0.0), 1.0)

    # ── Determine prediction and threat level ─────────────────────────────────
    # Use layer-specific high-confidence signals to prevent "score dilution"
    ml_is_high = ml_probability >= 0.75
    ml_is_med  = ml_probability >= 0.45
    
    groq_says_spam_strong = groq_available and (groq_result.spam_prediction == "spam" and groq_result.spam_confidence >= 0.8)
    groq_says_spam_med    = groq_available and (groq_result.spam_prediction == "spam" and groq_result.spam_confidence >= 0.5)
    
    heuristic_strong = h_score >= 0.45
    is_trad_spam = "traditional_spam" in h_cats

    # 1. Critical Threat (Strict threshold OR both major layers agree)
    if final_score >= _STRICT_THRESHOLD or (ml_is_high and groq_says_spam_med) or groq_says_spam_strong:
        final_prediction = 1
        threat_level = "critical"
        final_confidence = min(final_score + 0.05, 0.99)
    
    # 2. High Threat (Normal threshold OR one layer is high + heuristic OR Trad Spam detected)
    elif final_score >= _NORMAL_THRESHOLD or (groq_says_spam_med and heuristic_strong) or ml_is_high or is_trad_spam:
        final_prediction = 1
        threat_level = "high"
        final_confidence = min(final_score + 0.03, 0.95)
    
    # 3. Medium Threat (High risk threshold OR Groq/ML agreements)
    elif final_score >= _HIGH_RISK_THRESHOLD or (groq_says_spam_med and ml_probability > 0.20):
        final_prediction = 1
        threat_level = "medium"
        final_confidence = final_score
    
    # 4. Low Risk (Clean)
    else:
        final_prediction = 0
        threat_level = "low"
        final_confidence = 1.0 - final_score

    # ── Spam type classification ──────────────────────────────────────────────
    detected_cats = list(h_cats)
    if groq_available and groq_result.detected_patterns:
        for p in groq_result.detected_patterns:
            if p and p not in detected_cats:
                detected_cats.append(p)

    # Determine primary spam type
    if "prompt_injection" in detected_cats:
        spam_type = "prompt_injection"
    elif "ai_spam" in detected_cats or (groq_available and groq_result.ai_generated_probability > 0.6):
        spam_type = "ai_spam"
    elif "phishing" in detected_cats or (groq_available and groq_result.phishing_probability > 0.5):
        spam_type = "phishing"
    elif "traditional_spam" in detected_cats:
        spam_type = "traditional_spam"
    elif final_prediction == 1:
        spam_type = "suspicious"
    else:
        spam_type = "ham"

    # ── AI generated probability ──────────────────────────────────────────────
    ai_prob = 0.0
    if groq_available:
        ai_prob = groq_result.ai_generated_probability
    elif "ai_spam" in h_cats:
        ai_prob = min(0.35 + h_score * 0.5, 0.85)

    # ── Phishing probability ──────────────────────────────────────────────────
    phish_prob = 0.0
    if groq_available:
        phish_prob = groq_result.phishing_probability
    elif "phishing" in h_cats:
        phish_prob = min(0.40 + h_score * 0.4, 0.90)

    # ── Reasoning ─────────────────────────────────────────────────────────────
    if groq_available and groq_result.reasoning:
        reasoning = groq_result.reasoning.replace("Groq", "SmartInbox Engine").replace("AI", "Statistical Intelligence")
    elif detected_cats:
        reasoning = f"Statistical Engine detected: {', '.join(detected_cats[:3])}. (Weight: {ml_probability:.1%})"
    elif final_prediction == 1:
        reasoning = f"SmartInbox Engine flagged this message based on statistical anomalies (Weight: {ml_probability:.1%})."
    else:
        reasoning = "Statistical analysis complete. No significant risk patterns detected."

    # ── Recommended action ────────────────────────────────────────────────────
    if groq_available and groq_result.recommended_action:
        action = groq_result.recommended_action
    elif threat_level == "critical":
        action = "Block immediately. Do not engage with sender."
    elif threat_level == "high":
        action = "Mark as spam. Avoid clicking links or calling numbers."
    elif threat_level == "medium":
        action = "Treat with caution. Verify sender independently."
    else:
        action = "Message appears safe."

    logger.debug(
        "[Hybrid] score=%.3f | ml=%.3f | groq=%s | h=%.3f | pred=%s | threat=%s",
        final_score, ml_probability,
        f"{g_score:.3f}" if g_score is not None else "N/A",
        h_score, "spam" if final_prediction else "ham", threat_level
    )

    return HybridResult(
        final_prediction=final_prediction,
        final_confidence=min(final_confidence, 0.99),
        final_score=final_score,
        threat_level=threat_level,
        ml_score=ml_probability,
        groq_score=g_score,
        heuristic_score=h_score,
        detected_categories=detected_cats,
        reasoning=reasoning,
        recommended_action=action,
        ai_generated_probability=ai_prob,
        phishing_probability=phish_prob,
        spam_type=spam_type,
        groq_available=groq_available,
    )
