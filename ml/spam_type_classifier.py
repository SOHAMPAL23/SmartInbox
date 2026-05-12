"""
ml/spam_type_classifier.py
---------------------------
Multi-class spam type classifier — v8 (Hybrid-aware)

Key fixes over v7:
  1. REMOVED the ham_score override that was incorrectly turning spam → ham.
     The old logic: "if ham_score > 5.0 → force HAM" was the root bug.
  2. Threshold for AI spam detection lowered from 6.0 → 3.5.
  3. Added prompt injection and social engineering categories.
  4. New method classify_spam_type_v8() accepts optional GroqResult.
  5. When Groq is available, its prediction is used to break ties.
  6. Confidence calculation now reflects the hybrid score, not just heuristics.
"""

import re
import numpy as np
from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger("ml.spam_type_classifier")

# ══════════════════════════════════════════════════════════════════════════════
# PATTERN LIBRARIES
# ══════════════════════════════════════════════════════════════════════════════

_AI_SPAM_PATTERNS = {
    "cold_outreach": [
        r"i hope (?:i'm not|you'll forgive|this finds you)",
        r"forgive the cold (?:outreach|email|message|contact)",
        r"reaching out (?:directly|on behalf|today)",
        r"i(?:'ve| have) been following your (?:work|career|profile|company)",
        r"i do value your time",
        r"i don't want to take up too much",
        r"just (?:checking|wanted to see) if you (?:saw|received|had a chance)",
        r"pending (?:verification|review|approval|decision)",
        r"when you get a (?:minute|chance|moment)",
        r"hope (?:you'll|this).*forgive",
        r"i've spent (?:years?|time|considerable)",
        r"as we (?:enter|approach|navigate)",
        r"many (?:executives|professionals|leaders) i (?:speak|work|talk) with",
    ],
    "business_jargon": [
        r"\b(?:leverage|synergy|scalable|framework|innovative|disruptive)\b",
        r"\b(?:ecosystem|stakeholder|deliverable|bandwidth|throughput)\b",
        r"\b(?:pipeline|roadmap|roi|kpi|monetize|monetise)\b",
        r"data[- ]driven",
        r"measurable outcomes?",
        r"high[- ]growth",
        r"\b(?:market[\s-]leading|best[\s-]in[\s-]class|industry[\s-]leading)\b",
        r"\b(?:value proposition|use case|go[\s-]to[\s-]market|thought leadership)\b",
    ],
    "persuasive_cta": [
        r"would (?:love to|you be (?:open|willing|interested))",
        r"worth (?:a|your) (?:quick|brief|15[\s-]minute)",
        r"happy to (?:share|schedule|arrange|walk you through)",
        r"feel free to (?:reach|contact|reply|connect)",
        r"15[- ]minute (?:call|chat|intro|conversation)",
        r"at your (?:earliest )?convenience",
        r"no (?:obligation|strings attached|commitment|cost)",
        r"complimentary (?:consultation|session|demo|review|assessment)",
        r"you can (?:review|check|see) it (?:here|at|below)",
        r"(?:click|tap|visit) (?:here|this link|below)",
        r"can i (?:send|share|schedule|book)",
        r"would you be open to",
    ],
    "opportunity_lang": [
        r"consortium of investors",
        r"exclusive (?:opportunity|offer|access|invitation)",
        r"select (?:group|number) of (?:clients|professionals|partners)",
        r"unconventional proposition",
        r"mutually beneficial",
        r"positioning (?:yourself|your (?:company|business))",
        r"passive income",
        r"financial freedom",
        r"guaranteed (?:returns?|profits?|income|approval)",
        r"pre[\s-]approved|pre[\s-]qualified",
    ],
    "job_scam": [
        r"work from home",
        r"remote (?:position|opportunity|work|job)",
        r"flexible (?:hours|schedule|working)",
        r"be your own boss",
        r"earn \$\d+.{0,20}(?:day|week|hour|month)",
        r"no (?:experience|skills?|degree) (?:needed|required|necessary)",
    ],
}

_TRADITIONAL_SPAM_PATTERNS = {
    "leet_speak": [
        r"[a-z]*[0-9]+[a-z]*[0-9]+",  # fr33, cl1ck, v3r1fy
        r"[A-Z]{4,}",                  # Multiple ALL-CAPS words
        r"[!]{2,}",                    # Multiple exclamation marks
    ],
    "classic_spam": [
        r"\b(?:free|win|winner|prize|reward|claim)\b",
        r"\b(?:click here|act now|limited time|hurry|don't miss)\b",
        r"\b(?:congratulations?|you(?:'ve| have) won)\b",
        r"(?:iphone|gift card|bitcoin|crypto|lottery|jackpot)",
        r"\$\d+[,\d]*(?:\.\d{2})?",   # Money amounts
        r"\b(?:risk[\s-]free|money[\s-]back|100%?[\s-](?:free|guaranteed))\b",
    ],
    "urgency": [
        r"\b(?:urgent|immediately|asap|right now|today only)\b",
        r"\b(?:suspended|locked|blocked|terminated|deactivated|frozen)\b",
        r"\b(?:expire[sd]?|deadline|last chance|final notice|closing soon)\b",
        r"(?:verify|confirm|update|restore) (?:now|immediately|urgently)",
        r"\b(?:within 24|within 48|within 72) hours?\b",
        r"\b(?:final warning|last opportunity|account at risk)\b",
    ],
    "phishing": [
        r"(?:account|password|login) (?:suspended|locked|compromised|at risk)",
        r"(?:click|tap) (?:here|link|below) to (?:verify|confirm|restore)",
        r"(?:verify|confirm) your (?:account|identity|information|details)",
        r"unusual (?:activity|login|sign[\s-]in|access) detected",
        r"(?:kyc|know your customer).{0,30}(?:complet|verif|updat)",
        r"(?:redelivery|customs|parcel held|pay to release)",
        r"(?:inheritance|next of kin|beneficiary|unclaimed funds)",
        r"(?:irs|income tax|hmrc|customs).{0,30}(?:refund|owe|payment|penalt)",
    ],
}

_PROMPT_INJECTION_PATTERNS = [
    r"ignore (previous|all|prior|above|below) instructions",
    r"(pretend|act|behave) (as if|like) (you are|you're)",
    r"(new )?system prompt",
    r"(jailbreak|bypass|override|circumvent).{0,30}(filter|detection|classifier|guard)",
    r"(you must|you should|you will) (now|always|never).{0,30}(answer|respond|output)",
    r"(forget|disregard|discard).{0,20}(training|guidelines|rules|restrictions)",
    r"(translate|repeat|echo|output|print).{0,20}(the following|this message|all text)",
]

_HAM_PATTERNS = {
    "otp": [
        r"\b(?:otp|one[- ]time (?:password|code|pin))\b",
        r"verification code",
        r"(?:your|use) code (?:is|:)\s*\d{4,8}",
        r"\d{4,8}\s+is your",
        r"(?:authentication|security|login) code",
        r"do not share (?:this|your) (?:otp|code|pin)",
    ],
    "delivery": [
        r"(?:order|package|parcel|shipment) (?:has|is|was|will)",
        r"out for delivery",
        r"(?:track|tracking) (?:number|your|at|id)",
        r"(?:swiggy|zomato|amazon|flipkart|fedex|ups|dhl|usps|myntra|blinkit)",
        r"expected (?:delivery|arrival)",
        r"(?:delivered|attempted delivery|delivery attempt)",
    ],
    "personal": [
        r"\b(?:thanks?|thank you|please|sorry|apologies?)\b",
        r"\b(?:meeting|lunch|dinner|coffee|drinks?)\b.{0,30}\b(today|tomorrow|tonight|this)\b",
        r"(?:see you|talk soon|catch up|let's meet)",
        r"(?:how are you|hope you'?re|hope you are)",
        r"(?:miss you|thinking of you|hope all is well)",
    ],
    "banking_legit": [
        r"(?:you have (successfully|been)) (?:transfer|paid|received|credited|debited)",
        r"(?:account balance|available balance|transaction (?:alert|update|notification))",
        r"(?:statement|passbook) (?:available|ready|generated)",
    ],
}

_COMPILED_INJECT = [re.compile(p, re.IGNORECASE) for p in _PROMPT_INJECTION_PATTERNS]


class SpamTypeClassifier:
    """
    Multi-class spam type classifier — v8.

    Determines the *type* of message:
      - ham
      - traditional_spam
      - ai_spam
      - phishing
      - prompt_injection
      - social_engineering
      - suspicious

    IMPORTANT: This classifier no longer overrides ML predictions.
    It provides supplementary classification signals to the HybridDetector.
    """

    def __init__(self):
        self._ai_patterns   = self._compile_patterns(_AI_SPAM_PATTERNS)
        self._trad_patterns = self._compile_patterns(_TRADITIONAL_SPAM_PATTERNS)
        self._ham_patterns  = self._compile_patterns(_HAM_PATTERNS)

    def _compile_patterns(self, pattern_dict: Dict) -> Dict:
        compiled = {}
        for category, patterns in pattern_dict.items():
            compiled[category] = [re.compile(p, re.IGNORECASE) for p in patterns]
        return compiled

    def _count_pattern_matches(self, text: str, pattern_dict: Dict) -> Dict[str, int]:
        counts = {}
        text_lower = text.lower()
        for category, patterns in pattern_dict.items():
            count = sum(1 for p in patterns if p.search(text_lower))
            counts[category] = count
        return counts

    def _calculate_ai_spam_score(self, text: str) -> float:
        matches = self._count_pattern_matches(text, self._ai_patterns)
        score = 0.0
        score += matches.get("cold_outreach", 0) * 2.5
        score += matches.get("business_jargon", 0) * 1.2
        score += matches.get("persuasive_cta", 0) * 1.8
        score += matches.get("opportunity_lang", 0) * 2.0
        score += matches.get("job_scam", 0) * 2.0

        word_count = len(text.split())
        if word_count > 50:
            score += 0.8
        if word_count > 100:
            score += 1.2

        sentences = re.split(r"[.!?]+", text)
        sentences = [s.strip() for s in sentences if s.strip()]
        if sentences:
            avg_len = np.mean([len(s.split()) for s in sentences])
            if avg_len > 18:
                score += 1.2
            elif avg_len > 12:
                score += 0.5

        slang_words = {"lol", "omg", "wtf", "btw", "lmao", "gonna", "wanna", "ya", "nah", "haha", "bruh"}
        has_slang = any(w in text.lower().split() for w in slang_words)
        if not has_slang and word_count > 25:
            score += 0.8

        exclamation_count = text.count("!")
        if exclamation_count == 0 and word_count > 25:
            score += 0.4

        return min(score, 10.0)

    def _calculate_traditional_spam_score(self, text: str) -> float:
        matches = self._count_pattern_matches(text, self._trad_patterns)
        score = 0.0
        score += matches.get("leet_speak", 0) * 2.0
        score += matches.get("classic_spam", 0) * 2.5
        score += matches.get("urgency", 0) * 2.0
        score += matches.get("phishing", 0) * 2.5

        if len(text) > 0:
            caps_ratio = sum(1 for c in text if c.isupper()) / len(text)
            if caps_ratio > 0.3:
                score += 2.0
            elif caps_ratio > 0.15:
                score += 0.8

        punct_count = text.count("!") + text.count("?")
        if punct_count >= 3:
            score += 1.5
        elif punct_count >= 2:
            score += 0.5

        suspicious_domains = ["bit.ly", "tinyurl", "goo.gl", "t.co", "ow.ly", "rb.gy", "shorturl"]
        if any(d in text.lower() for d in suspicious_domains):
            score += 2.0

        return min(score, 10.0)

    def _calculate_ham_score(self, text: str) -> float:
        """
        Calculate ham signal strength.

        NOTE: This score is now ADVISORY ONLY — it no longer overrides ML predictions.
        A high ham_score means the message *looks like* ham, but the final decision
        is made by the hybrid ensemble, not this function alone.
        """
        matches = self._count_pattern_matches(text, self._ham_patterns)
        score = 0.0
        score += matches.get("otp", 0) * 3.5
        score += matches.get("delivery", 0) * 2.5
        score += matches.get("personal", 0) * 1.5
        score += matches.get("banking_legit", 0) * 2.0

        word_count = len(text.split())
        if 5 <= word_count <= 25:
            score += 1.0

        return min(score, 10.0)

    def _detect_prompt_injection(self, text: str) -> bool:
        return any(p.search(text) for p in _COMPILED_INJECT)

    def classify_spam_type(
        self,
        text: str,
        spam_probability: float,
    ) -> Dict[str, Any]:
        """
        Classify the type of message based on ML probability + heuristics.

        CRITICAL CHANGE from v7:
        - Ham score NO LONGER overrides ML predictions.
        - Prediction follows spam_probability with heuristic boosting only.
        """
        ai_score   = self._calculate_ai_spam_score(text)
        trad_score = self._calculate_traditional_spam_score(text)
        ham_score  = self._calculate_ham_score(text)

        # Check for prompt injection first (highest priority)
        if self._detect_prompt_injection(text):
            return {
                "spam_type": "prompt_injection",
                "confidence": 0.97,
                "ai_spam_score": ai_score,
                "traditional_spam_score": trad_score,
                "ham_score": ham_score,
                "explanation": "Prompt injection attempt detected — adversarial instructions embedded in message.",
                "scores_breakdown": {
                    "ai_probability": 1.0,
                    "traditional_probability": 0.0,
                    "ham_probability": 0.0,
                },
            }

        total = ai_score + trad_score + ham_score + 0.01
        ai_prob   = ai_score   / total
        trad_prob = trad_score / total
        ham_prob  = ham_score  / total

        # ── Strong heuristic overrides (spam direction only) ──────────────────
        if ai_score > 3.5 and ai_score > trad_score:
            spam_type = "ai_spam"
            confidence = min(0.75 + (ai_score / 40), 0.97)
            explanation = "AI-generated spam detected: formal tone, cold outreach, persuasive CTA."

        elif trad_score > 4.0:
            spam_type = "traditional_spam"
            confidence = min(0.75 + (trad_score / 40), 0.97)
            explanation = "Traditional spam patterns: urgency, prizes, phishing indicators."

        # ── ML probability drives the decision (no ham override!) ─────────────
        elif spam_probability >= 0.65:
            if ai_score > trad_score:
                spam_type = "ai_spam"
                confidence = spam_probability
                explanation = "ML ensemble detected spam with AI-style characteristics."
            else:
                spam_type = "traditional_spam"
                confidence = spam_probability
                explanation = "ML ensemble detected traditional spam patterns."

        elif spam_probability >= 0.38:
            # Suspicious zone — use heuristics to disambiguate
            if ai_score > 2.0 and ai_score > trad_score:
                spam_type = "ai_spam"
                confidence = min(spam_probability + 0.15, 0.90)
                explanation = "Borderline confidence with AI spam signals — flagged as suspicious."
            elif trad_score > 2.0:
                spam_type = "traditional_spam"
                confidence = min(spam_probability + 0.10, 0.88)
                explanation = "Borderline confidence with traditional spam signals."
            else:
                spam_type = "suspicious"
                confidence = spam_probability
                explanation = "Low-confidence prediction — manual review recommended."

        else:
            # Low ML probability → ham (but only if no strong spam heuristics)
            # FIX: Don't blindly say ham if heuristics found something
            if ai_score > 4.5 or trad_score > 4.5:
                spam_type = "ai_spam" if ai_score > trad_score else "traditional_spam"
                confidence = 0.70
                explanation = "Strong spam signals override low ML probability."
            else:
                spam_type = "ham"
                confidence = 1.0 - spam_probability
                explanation = "Message shows legitimate communication patterns."

        return {
            "spam_type": spam_type,
            "confidence": round(float(confidence), 4),
            "ai_spam_score": round(float(ai_score), 2),
            "traditional_spam_score": round(float(trad_score), 2),
            "ham_score": round(float(ham_score), 2),
            "explanation": explanation,
            "scores_breakdown": {
                "ai_probability": round(float(ai_prob), 4),
                "traditional_probability": round(float(trad_prob), 4),
                "ham_probability": round(float(ham_prob), 4),
            },
        }

    def classify_spam_type_v8(
        self,
        text: str,
        spam_probability: float,
        groq_result=None,
    ) -> Dict[str, Any]:
        """
        V8 variant: Groq-aware classification.

        When Groq result is available, its prediction is used to break ties
        in the suspicious zone (0.38–0.65).
        """
        base = self.classify_spam_type(text, spam_probability)

        if groq_result is None or not groq_result.available:
            return base

        # Use Groq to resolve borderline cases
        if base["spam_type"] == "suspicious":
            if groq_result.spam_prediction == "spam" and groq_result.spam_confidence > 0.6:
                # Groq confirms spam
                ai_score = base["ai_spam_score"]
                trad_score = base["traditional_spam_score"]
                if groq_result.ai_generated_probability > 0.5 or ai_score > trad_score:
                    base["spam_type"] = "ai_spam"
                    base["explanation"] = "Groq LLM confirmed AI-generated spam in suspicious zone."
                else:
                    base["spam_type"] = "traditional_spam"
                    base["explanation"] = "Groq LLM confirmed traditional spam in suspicious zone."
                base["confidence"] = min(base["confidence"] + 0.15, 0.95)

            elif groq_result.spam_prediction == "ham" and groq_result.spam_confidence > 0.7:
                base["spam_type"] = "ham"
                base["explanation"] = "Groq LLM classified as legitimate in borderline zone."
                base["confidence"] = groq_result.spam_confidence

        # Boost AI probability if Groq detected it
        if groq_result.ai_generated_probability > 0.7 and base["spam_type"] == "ham":
            # Even ham can be AI-generated (e.g. legitimate auto-emails)
            base["ai_generated"] = True

        return base


# ── Singleton ─────────────────────────────────────────────────────────────────

_classifier_instance: Optional[SpamTypeClassifier] = None


def get_spam_type_classifier() -> SpamTypeClassifier:
    global _classifier_instance
    if _classifier_instance is None:
        _classifier_instance = SpamTypeClassifier()
    return _classifier_instance
