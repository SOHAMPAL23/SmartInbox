"""
ml/groq_analyzer.py
-------------------
Layer 2 — Groq LLM Semantic Analysis Engine

Calls the Groq API to perform deep semantic analysis on SMS messages.
Detects: spam intent, AI-generation likelihood, phishing, social engineering,
psychological manipulation, urgency tactics, and financial scam patterns.

Features:
- Async/sync hybrid (works from both FastAPI async context and sync ML service)
- LRU cache with TTL (avoids duplicate Groq calls for same text)
- Retry with exponential backoff (3 attempts)
- Hard timeout (8s) with graceful fallback
- Primary: llama3-70b-8192 / Fallback: llama3-8b-8192
"""

import os
import json
import time
import hashlib
import logging
import threading
from typing import Any, Dict, Optional
from functools import lru_cache

logger = logging.getLogger("ml.groq_analyzer")

# ── Result dataclass ──────────────────────────────────────────────────────────

class GroqResult:
    """Structured result from Groq LLM semantic analysis."""

    def __init__(self, raw: Dict[str, Any], latency_ms: float = 0.0, from_cache: bool = False, error: Optional[str] = None):
        self.spam_prediction: str = raw.get("spam_prediction", "ham")
        self.spam_confidence: float = float(raw.get("spam_confidence", 50)) / 100.0  # normalize 0-1
        self.ai_generated_probability: float = float(raw.get("ai_generated_probability", 0)) / 100.0
        self.phishing_probability: float = float(raw.get("phishing_probability", 0)) / 100.0
        self.threat_level: str = raw.get("threat_level", "low")
        self.detected_patterns: list = raw.get("detected_patterns", [])
        self.reasoning: str = raw.get("reasoning", "")
        self.recommended_action: str = raw.get("recommended_action", "")
        self.latency_ms: float = latency_ms
        self.from_cache: bool = from_cache
        self.error: Optional[str] = error
        self.available: bool = error is None

    @property
    def spam_score(self) -> float:
        """Normalized spam probability 0-1 for ensemble weighting."""
        if self.spam_prediction == "spam":
            return max(self.spam_confidence, 0.5)
        return min(self.spam_confidence, 0.5)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "spam_prediction": self.spam_prediction,
            "spam_confidence": round(self.spam_confidence, 4),
            "ai_generated_probability": round(self.ai_generated_probability, 4),
            "phishing_probability": round(self.phishing_probability, 4),
            "threat_level": self.threat_level,
            "detected_patterns": self.detected_patterns,
            "reasoning": self.reasoning,
            "recommended_action": self.recommended_action,
            "latency_ms": round(self.latency_ms, 2),
            "from_cache": self.from_cache,
            "available": self.available,
        }


# ── Fallback result (returned when API fails) ─────────────────────────────────

def _neutral_fallback(error: str = "Groq unavailable") -> GroqResult:
    """Return a neutral result that won't skew the hybrid ensemble."""
    return GroqResult(
        raw={
            "spam_prediction": "ham",
            "spam_confidence": 50,
            "ai_generated_probability": 0,
            "phishing_probability": 0,
            "threat_level": "low",
            "detected_patterns": [],
            "reasoning": f"Groq analysis unavailable: {error}",
            "recommended_action": "Review message manually if uncertain.",
        },
        error=error,
    )


# ── Groq prompt template ──────────────────────────────────────────────────────

_ANALYSIS_PROMPT = """You are an elite AI cybersecurity analyst specializing in SMS spam detection. Your task is to deeply analyze the following SMS message.

Analyze for:
1. Whether this message is spam or legitimate (ham)
2. Whether it appears to be AI-generated (polished prose, cold outreach, no typos, persuasive framing)
3. Phishing indicators (impersonation, credential harvesting, malicious links)
4. Social engineering (urgency, authority, scarcity, reciprocity, fear tactics)
5. Psychological manipulation (FOMO, greed, fear, trust exploitation)
6. Financial scam patterns (prizes, investments, KYC, gift cards, wire transfers)
7. AI-generated ham (legitimate but written by AI, like automated order confirmations)

Spam categories to detect:
- traditional_spam: prize/lottery, urgency, click-here, leet-speak
- ai_spam: cold outreach, BEC, spear-phishing, professional-sounding scams
- prompt_injection: instructions embedded in text to confuse AI filters
- social_engineering: authority spoofing, fake urgency, emotional manipulation
- crypto_scam: investment opportunity, wallet connection, DeFi scams
- phishing: credential theft, account suspension, link-based attacks

Return ONLY a valid JSON object with EXACTLY this structure:
{
  "spam_prediction": "spam",
  "spam_confidence": 87,
  "ai_generated_probability": 72,
  "phishing_probability": 45,
  "threat_level": "high",
  "detected_patterns": ["cold_outreach", "persuasive_cta", "no_slang"],
  "reasoning": "This message exhibits hallmarks of AI-generated cold-outreach spam: formal tone, specific value propositions, a soft persuasive CTA, and no natural language markers. The sender attempts to establish false familiarity.",
  "recommended_action": "Block sender. Do not click any links."
}

Rules:
- spam_confidence and all probabilities are integers 0-100
- threat_level must be one of: low, medium, high, critical
- detected_patterns is a list of strings describing what was found
- reasoning must be a concise explanation (max 200 chars)
- recommended_action must be actionable (max 100 chars)
- Return ONLY the JSON. No preamble. No markdown. No explanation outside JSON.

Message to analyze:
"{sms_text}"
"""


# ── TTL Cache ─────────────────────────────────────────────────────────────────

class _TTLCache:
    """Thread-safe LRU cache with TTL expiry."""

    def __init__(self, maxsize: int = 500, ttl: int = 300):
        self._cache: Dict[str, tuple] = {}  # key → (result, expire_ts)
        self._maxsize = maxsize
        self._ttl = ttl
        self._lock = threading.Lock()

    def _make_key(self, text: str) -> str:
        return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()[:16]

    def get(self, text: str) -> Optional[GroqResult]:
        key = self._make_key(text)
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return None
            result, expire_ts = entry
            if time.time() > expire_ts:
                del self._cache[key]
                return None
            return result

    def set(self, text: str, result: GroqResult) -> None:
        key = self._make_key(text)
        with self._lock:
            # Evict oldest entries if at capacity
            if len(self._cache) >= self._maxsize:
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]
            self._cache[key] = (result, time.time() + self._ttl)

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()


# ── Main Analyzer Class ───────────────────────────────────────────────────────

class GroqSpamAnalyzer:
    """
    Groq-powered semantic spam analyzer.

    Thread-safe. Designed to be used as a singleton.
    Supports both sync (blocking) and async usage patterns.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "llama3-70b-8192",
        fallback_model: str = "llama3-8b-8192",
        timeout: int = 8,
        max_retries: int = 3,
        cache_ttl: int = 300,
        cache_maxsize: int = 500,
    ):
        self._api_key = api_key or os.environ.get("GROQ_API_KEY", "")
        logger.info("[Groq] API Key loaded: %s...", self._api_key[:5] if self._api_key else "NONE")
        self._model = model
        self._fallback_model = fallback_model
        self._timeout = timeout
        self._max_retries = max_retries
        self._cache = _TTLCache(maxsize=cache_maxsize, ttl=cache_ttl)
        self._client = None  # lazy init

    def _get_client(self):
        """Lazy-initialize Groq client (avoids import errors if groq not installed)."""
        if self._client is not None:
            return self._client
        try:
            from groq import Groq
            self._client = Groq(api_key=self._api_key)
            return self._client
        except ImportError:
            raise RuntimeError("groq package not installed. Run: pip install groq>=0.5.0")

    def _call_api(self, text: str, model: str) -> Dict[str, Any]:
        """Make a single blocking Groq API call and return parsed JSON."""
        client = self._get_client()
        prompt = _ANALYSIS_PROMPT.format(sms_text=text[:800])

        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=512,
            timeout=self._timeout,
        )

        raw_text = response.choices[0].message.content.strip()
        
        # Robust JSON extraction
        import re
        json_match = re.search(r"(\{.*\})", raw_text, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
            try:
                data = json.loads(json_str)
                # Handle double-encoded JSON strings
                if isinstance(data, str):
                    try:
                        data = json.loads(data)
                    except:
                        pass
                if not isinstance(data, dict):
                    raise ValueError(f"Decoded JSON is not a dictionary: {type(data)}")
                return data
            except Exception as e:
                logger.error("[Groq] Parsing failed: %s | Match: %s", e, json_str[:100])
                raise e
        else:
            logger.error("[Groq] No JSON found in response: %s", raw_text)
            raise ValueError(f"No JSON found in response: {raw_text[:100]}")

    def analyze(self, text: str) -> GroqResult:
        """
        Analyze a message synchronously with retry and fallback logic.

        Returns a GroqResult (never raises — returns fallback on failure).
        """
        if not text or not text.strip():
            return _neutral_fallback("Empty input")

        if not self._api_key:
            return _neutral_fallback("No GROQ_API_KEY configured")

        # Check cache first
        cached = self._cache.get(text)
        if cached is not None:
            cached.from_cache = True
            return cached

        start_t = time.perf_counter()
        last_error = ""

        # Try primary model, then fallback model
        models_to_try = [self._model, self._fallback_model]

        for model_name in models_to_try:
            for attempt in range(self._max_retries):
                try:
                    raw = self._call_api(text, model_name)
                    latency_ms = (time.perf_counter() - start_t) * 1000
                    result = GroqResult(raw=raw, latency_ms=latency_ms)
                    self._cache.set(text, result)
                    logger.info(
                        "[Groq] Analysis complete | model=%s | threat=%s | latency=%.0fms | cached=False",
                        model_name, result.threat_level, latency_ms
                    )
                    return result

                except json.JSONDecodeError as e:
                    last_error = f"JSON parse error: {e}"
                    logger.warning("[Groq] JSON parse failed (attempt %d/%d, model=%s): %s", attempt + 1, self._max_retries, model_name, e)

                except Exception as e:
                    last_error = str(e)
                    wait_s = 2 ** attempt  # 1s, 2s, 4s
                    logger.warning("[Groq] API call failed (attempt %d/%d, model=%s): %s | retrying in %ds", attempt + 1, self._max_retries, model_name, e, wait_s)
                    if attempt < self._max_retries - 1:
                        time.sleep(wait_s)

        logger.error("[Groq] All retries exhausted. Last error: %s", last_error)
        return _neutral_fallback(last_error)

    def clear_cache(self) -> None:
        """Clear the result cache."""
        self._cache.clear()


# ── Singleton factory ─────────────────────────────────────────────────────────

_analyzer_instance: Optional[GroqSpamAnalyzer] = None
_analyzer_lock = threading.Lock()


def get_groq_analyzer() -> GroqSpamAnalyzer:
    """Get or create the global GroqSpamAnalyzer singleton."""
    global _analyzer_instance
    if _analyzer_instance is None:
        with _analyzer_lock:
            if _analyzer_instance is None:
                api_key = os.environ.get("GROQ_API_KEY", "")
                model = os.environ.get("GROQ_MODEL", "llama3-70b-8192")
                fallback = os.environ.get("GROQ_FALLBACK_MODEL", "llama3-8b-8192")
                timeout = int(os.environ.get("GROQ_TIMEOUT_SECONDS", "8"))
                retries = int(os.environ.get("GROQ_MAX_RETRIES", "3"))

                _analyzer_instance = GroqSpamAnalyzer(
                    api_key=api_key,
                    model=model,
                    fallback_model=fallback,
                    timeout=timeout,
                    max_retries=retries,
                )
                logger.info(
                    "[Groq] Analyzer initialized | model=%s | timeout=%ds | key_set=%s",
                    model, timeout, bool(api_key)
                )
    return _analyzer_instance
