"""
ml/feature_pipeline.py
----------------------
Extended SMS Feature Pipeline — v6

Improvements over v4:
  1. Adversarial normalisation  — decodes leet-speak, homoglyphs, zero-width
     chars, and unicode look-alikes BEFORE TF-IDF so obfuscated tokens
     ("fr33", "cl1ck", "v3rify") are recognised.
  2. Rich feature engineering  — 29 hand-crafted numeric signals covering link
     count, caps ratio, urgency score, phishing keywords, emoji density,
     repeated-char ratio, special-char ratio, OTP detection, delivery-phrase
     detection, brand-impersonation scoring, and aggressive-caps detection.
  3. Larger TF-IDF vocabulary  — bumped to 30 k word / 20 k char by default
     (same as original SMSFeaturePipeline) so the pipeline benefits from
     broader coverage.
  4. Backward-compatible API   — SMSFeaturePipeline and RobustSMSFeaturePipeline
     both still exist and follow the same fit_transform / transform contract.
     No service.py changes required for loading.
  5. New tricky-ham signals    — OTP regex, delivery phrase set, and brand-
     spoofing score let the classifier correctly handle legitimate notifications
     that superficially look like phishing.
"""

import re
import unicodedata
from typing import List

import pandas as pd
import numpy as np
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import MaxAbsScaler
from scipy.sparse import csr_matrix, hstack
import logging

import nltk
from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer
from nltk.corpus import stopwords

logger = logging.getLogger("ml.feature_pipeline")

# ── NLTK bootstrap ────────────────────────────────────────────────────────────

def init_nltk():
    try:
        for resource in [
            "tokenizers/punkt",
            "corpora/stopwords",
            "corpora/wordnet",
            "corpora/omw-1.4",
            "tokenizers/punkt_tab",
        ]:
            try:
                nltk.data.find(resource)
            except LookupError:
                logger.info("[NLTK] Downloading missing resource: %s", resource)
                nltk.download(resource.split("/")[-1], quiet=True)
    except Exception as exc:
        logger.warning("[NLTK] Initialization warning (%s). Proceeding anyway.", exc)


init_nltk()

# ── Shared stopwords / lemmatizer (lazy singletons) ───────────────────────────

_STOP_WORDS = None
_LEMMATIZER = None
_PUNCT_TABLE = str.maketrans("", "", '!"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~')


def get_stop_words():
    global _STOP_WORDS
    if _STOP_WORDS is None:
        try:
            _STOP_WORDS = set(stopwords.words("english"))
        except LookupError:
            logger.warning("[NLTK] Stopwords unavailable. Using empty set.")
            _STOP_WORDS = set()
    return _STOP_WORDS


def get_lemmatizer():
    global _LEMMATIZER
    if _LEMMATIZER is None:
        _LEMMATIZER = WordNetLemmatizer()
    return _LEMMATIZER


# ── Adversarial normalisation ─────────────────────────────────────────────────
#
# Handles the most common obfuscation tricks attackers use to bypass TF-IDF:
#   • Leet-speak digit substitutions  (3→e, 1→i/l, 0→o, …)
#   • Homoglyphs (Cyrillic/Latin lookalikes, ℂ→C, ꓤ→N, …)
#   • Zero-width / invisible characters
#   • Dot / hyphen / underscore word-splitting  (f.r.e.e → free)
#   • Repeated character compression  (freeeee → free)

# Leet-speak substitution map (digit/symbol → canonical ASCII)
_LEET_MAP = str.maketrans(
    {
        "3": "e",
        "1": "i",
        "0": "o",
        "5": "s",
        "4": "a",
        "7": "t",
        "@": "a",
        "$": "s",
        "!": "i",
        "8": "b",
    }
)

# Invisible / zero-width Unicode characters (common in adversarial text)
_INVISIBLE_RE = re.compile(
    r"[\u200b\u200c\u200d\u200e\u200f\u00ad\ufeff\u2060\u180e\u00a0]"
)

# Dot/hyphen/underscore separators inserted between letters (c.l.i.c.k)
_DOTTED_LETTERS_RE = re.compile(r"\b([a-zA-Z])([.\-_])(?=[a-zA-Z])")

# Repeated characters compressed to max 2 (freeeeee → free)
_REPEAT_RE = re.compile(r"(.)\1{2,}")


def normalise_adversarial(text: str) -> str:
    """
    Normalise obfuscated text before feature extraction.

    Steps applied in order:
    1. NFKC unicode normalisation (converts homoglyphs to ASCII where possible)
    2. Strip zero-width / invisible characters
    3. Remove dot/hyphen separators inserted between individual letters
    4. Leet-speak substitution (3→e, 1→i, 0→o …)
    5. Repeated-character compression (freeee→free)
    """
    # 1. Unicode NFKC — maps ℂ→C, ｆｒｅｅ→free, Cyrillic А→A etc.
    text = unicodedata.normalize("NFKC", text)
    # 2. Remove invisible chars
    text = _INVISIBLE_RE.sub("", text)
    # 3. c.l.i.c.k → click (only between single letters)
    text = _DOTTED_LETTERS_RE.sub(r"\1", text)
    # 4. Leet-speak
    text = text.translate(_LEET_MAP)
    # 5. Compress runs
    text = _REPEAT_RE.sub(r"\1\1", text)
    return text


# ── Text cleaning ─────────────────────────────────────────────────────────────

_URL_RE = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)
_EMAIL_RE = re.compile(r"\S+@\S+\.\S+")
_NUMBER_RE = re.compile(r"\b\d[\d\s]*\b")
_EMOJI_RE = re.compile(
    "["
    "\U0001F600-\U0001F64F"
    "\U0001F300-\U0001F5FF"
    "\U0001F680-\U0001F6FF"
    "\U0001F1E0-\U0001F1FF"
    "\U00002702-\U000027B0"
    "\U000024C2-\U0001F251"
    "]+",
    flags=re.UNICODE,
)
_PUNCT_STRIP_RE = re.compile(r"[^\w\s]")
_WHITESPACE_RE = re.compile(r"\s+")


def clean_text(text: str) -> str:
    """Lower-case → remove punctuation → strip extra whitespace."""
    text = normalise_adversarial(str(text))
    text = text.lower()
    text = text.translate(_PUNCT_TABLE)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def tokenize_and_lemmatize(text: str) -> List[str]:
    """Tokenise → remove stopwords → lemmatise."""
    try:
        tokens = word_tokenize(text)
    except Exception:
        tokens = text.split()
    lemmatizer = get_lemmatizer()
    stop_words = get_stop_words()
    return [
        lemmatizer.lemmatize(tok)
        for tok in tokens
        if tok not in stop_words and tok.isalpha()
    ]


def preprocess_text(text: str) -> str:
    """Full pipeline → clean string ready for TF-IDF."""
    return " ".join(tokenize_and_lemmatize(clean_text(text)))


# ── Phishing / urgency signals ─────────────────────────────────────────────────
#
# These word sets are applied to the *raw* (not cleaned) text so that
# adversarial variants normalised above still match.

_URGENCY_WORDS = {
    "urgent", "immediately", "asap", "now", "today", "hurry",
    "limited", "expire", "expires", "expiring", "deadline",
    "last chance", "act now", "don't wait", "dont wait",
    "time sensitive", "final notice", "account suspended",
    "act fast", "verify now", "pending"
}

_PHISHING_WORDS = {
    "verify", "verification", "confirm", "password", "username",
    "login", "sign in", "bank", "account", "credit card",
    "social security", "ssn", "pin", "otp", "one time",
    "suspended", "locked", "blocked", "unusual activity",
    "security alert", "click here", "click link", "update now",
    "claim", "prize", "winner", "reward", "gift card",
    "invoice", "payment", "refund", "transaction",
    "free iphone", "pay shipping", "reward points"
}

_SUSPICIOUS_DOMAINS = {
    "bit.ly", "tinyurl", "goo.gl", "t.co", "ow.ly",
    "rb.gy", "buff.ly", "short.io", "cutt.ly",
    "is.gd", "tiny.cc", "bc.vc", "lnkd.in",
}

# ── OTP / verification-code patterns ─────────────────────────────────────────
# These strongly indicate a legitimate system-generated auth message (ham).
_OTP_RE = re.compile(
    r"\b(otp|one[\s-]time[\s-](?:password|code|pin)|verification[\s-]code"
    r"|your[\s\w]{0,15}code[\s\w]{0,5}is[:\s]+\d{4,8}"
    r"|use[\s]+\d{4,8}[\s]+to"
    r"|\d{4,8}[\s]+is[\s]+your)",
    re.IGNORECASE,
)

# ── Legitimate delivery / shipping phrases ────────────────────────────────────
_DELIVERY_PHRASES = {
    "your order", "order #", "order has shipped", "out for delivery",
    "expected delivery", "package has been", "parcel", "track your",
    "delivery attempt", "attempted delivery", "reschedule delivery",
    "shipped", "dispatched", "tracking number", "courier",
    "swiggy", "zomato", "amazon", "flipkart", "myntra",
    "blinkit", "zepto", "dunzo", "ubereats", "doordash",
    "fedex", "ups", "dhl", "usps", "royal mail",
}

# ── Brand-impersonation / sender-spoofing signals ─────────────────────────────
# Spammers often name-drop high-trust brands to appear legitimate.
# When combined with urgency words / suspicious links these are strong spam cues.
_SPOOFED_BRANDS = {
    "apple", "paypal", "amazon", "microsoft", "google", "netflix",
    "facebook", "instagram", "whatsapp", "twitter", "linkedin",
    "bank of america", "chase", "wells fargo", "citibank", "barclays",
    "hsbc", "sbi", "hdfc", "icici", "axis bank",
    "irs", "hmrc", "income tax", "government", "federal",
    "social security", "medicare", "visa", "mastercard",
}

# ── AI-generated spam signals ──────────────────────────────────────────────────
# AI spam tends to be: formally toned, long, polished, no slang,
# cold-outreach framing, and ends with a soft persuasive CTA.

_COLD_OUTREACH_PHRASES = {
    "i hope this finds you", "i hope i'm not overstepping",
    "forgive the cold outreach", "reaching out directly",
    "on behalf of", "i've been following your work",
    "i've spent", "as we enter", "many executives",
    "data-driven", "measurable outcomes", "high-growth",
    "consortium of investors", "i do value your time",
    "hope you'll forgive", "i don't want to take up too much",
    "would love to connect", "worth a quick chat",
    "if you're open to it", "positioning yourself",
    "professionals i speak with", "revisiting their",
    "rooted in measurable", "optimize", "optimise",
}

_FORMAL_BUSINESS_WORDS = {
    "leverage", "synergy", "scalable", "framework", "innovative",
    "solution", "strategy", "ecosystem", "stakeholder", "deliverable",
    "bandwidth", "pipeline", "roadmap", "roi", "kpi",
    "q1", "q2", "q3", "q4", "enterprise", "portfolio",
    "acquisition", "market share", "due diligence", "monetize",
}

_PERSUASIVE_CTA_PHRASES = {
    "would love to", "worth a quick", "happy to share",
    "let me know if", "feel free to", "open to a brief",
    "15-minute call", "schedule a call", "book a time",
    "at your convenience", "no obligation", "complimentary",
    "at no cost", "free consultation", "quick intro call",
    "can i send", "would you be open", "i'd be happy",
}

_SLANG_WORDS = {
    "lol", "omg", "wtf", "btw", "lmao", "brb", "imo", "tbh",
    "gonna", "wanna", "gotta", "ya", "nah", "yep", "nope",
    "sup", "dude", "bro", "sis", "bestie", "haha", "hehe",
    "smh", "fr", "ngl", "gg", "ty", "thx", "rn", "af",
}


def _count_matches(text_lower: str, word_set: set) -> int:
    return sum(1 for w in word_set if w in text_lower)


# ── Rich numeric feature extraction ──────────────────────────────────────────
#
# Returns a (n, 20) matrix of hand-crafted features that complement TF-IDF.

def extract_numeric_features(texts: pd.Series) -> np.ndarray:
    """
    Extract 29 hand-crafted numeric features per message:

     0  msg_length          — character count
     1  word_count          — token count
     2  url_count           — number of URLs
     3  suspicious_url      — 1 if any URL uses a URL-shortener
     4  exclamation_count   — number of '!' characters
     5  question_count      — number of '?' characters
     6  digit_ratio         — fraction of chars that are digits
     7  upper_ratio         — fraction of chars that are uppercase
     8  caps_word_count     — number of ALL-CAPS words (len >= 2)
     9  special_char_ratio  — fraction of non-alphanumeric non-space chars
    10  urgency_score       — count of urgency-keyword matches
    11  phishing_score      — count of phishing-keyword matches
    12  emoji_count         — number of emoji characters
    13  repeated_char_ratio — fraction of chars in runs of 3+
    14  avg_word_length     — mean character length per word
    15  email_count         — number of email addresses
    16  currency_count      — number of currency symbols ($, £, €, ₹)
    17  number_count        — count of standalone number tokens
    18  leet_ratio          — fraction of chars that are leet digits
    19  invisible_char_flag — 1 if zero-width / invisible chars present
    --- AI-generated spam features ---
    20  formal_biz_score    — count of formal business jargon words
    21  cold_outreach_score — count of cold-outreach opener phrases
    22  persuasive_cta      — count of persuasive CTA phrases
    23  no_slang_flag       — 1 if message has NO slang words (AI-style)
    24  long_paragraph_flag — 1 if msg > 200 chars and < 3 sentences (dense prose)
    --- Tricky-ham disambiguation features (v6) ---
    25  otp_flag            — 1 if message matches OTP/verification-code pattern
    26  delivery_flag       — 1 if message mentions legitimate delivery phrases
    27  sender_spoof_score  — count of brand names mentioned (spam impersonation cue)
    28  all_caps_flag       — 1 if upper_ratio > 0.30 (aggressive caps = spam signal)
    """
    raw = texts.astype(str)

    # Pre-compute frequently reused values
    lengths     = raw.str.len().fillna(0).values.astype(float)
    words_lists = raw.apply(lambda t: t.split())

    def _safe_div(a, b):
        return np.where(b > 0, a / b, 0.0)

    # 0. msg_length
    f0 = lengths

    # 1. word_count
    f1 = words_lists.apply(len).values.astype(float)

    # 2. url_count
    f2 = raw.apply(lambda t: len(_URL_RE.findall(t))).values.astype(float)

    # 3. suspicious_url (shortener)
    def _has_suspicious_url(t):
        urls = _URL_RE.findall(t)
        return float(any(d in u.lower() for u in urls for d in _SUSPICIOUS_DOMAINS))
    f3 = raw.apply(_has_suspicious_url).values

    # 4-5. punctuation counts
    f4 = raw.str.count("!").fillna(0).values.astype(float)
    f5 = raw.str.count(r"\?").fillna(0).values.astype(float)

    # 6. digit_ratio
    f6 = raw.apply(lambda t: sum(c.isdigit() for c in t) / max(len(t), 1)).values

    # 7. upper_ratio
    f7 = raw.apply(lambda t: sum(c.isupper() for c in t) / max(len(t), 1)).values

    # 8. caps_word_count
    f8 = words_lists.apply(
        lambda ws: sum(1 for w in ws if w.isupper() and len(w) >= 2)
    ).values.astype(float)

    # 9. special_char_ratio
    f9 = raw.apply(
        lambda t: sum(1 for c in t if not c.isalnum() and not c.isspace()) / max(len(t), 1)
    ).values

    # 10. urgency_score
    f10 = raw.apply(lambda t: _count_matches(t.lower(), _URGENCY_WORDS)).values.astype(float)

    # 11. phishing_score
    f11 = raw.apply(lambda t: _count_matches(t.lower(), _PHISHING_WORDS)).values.astype(float)

    # 12. emoji_count
    f12 = raw.apply(lambda t: len(_EMOJI_RE.findall(t))).values.astype(float)

    # 13. repeated_char_ratio (chars in runs of 3+)
    def _repeated_ratio(t):
        if not t:
            return 0.0
        runs = sum(len(m.group()) for m in re.finditer(r"(.)\1{2,}", t))
        return runs / len(t)
    f13 = raw.apply(_repeated_ratio).values

    # 14. avg_word_length
    f14 = words_lists.apply(
        lambda ws: np.mean([len(w) for w in ws]) if ws else 0.0
    ).values.astype(float)

    # 15. email_count
    f15 = raw.apply(lambda t: len(_EMAIL_RE.findall(t))).values.astype(float)

    # 16. currency_count
    f16 = raw.apply(lambda t: sum(c in "$\u00a3\u20ac\u20b9\u00a5" for c in t)).values.astype(float)

    # 17. number_count (standalone tokens that are all digits)
    f17 = words_lists.apply(lambda ws: sum(1 for w in ws if w.isdigit())).values.astype(float)

    # 18. leet_ratio (digit chars / total, proxy for leet usage)
    _LEET_DIGITS = set("31054@7!8")
    f18 = raw.apply(
        lambda t: sum(c in _LEET_DIGITS for c in t) / max(len(t), 1)
    ).values

    # 19. invisible_char_flag
    f19 = raw.apply(lambda t: float(bool(_INVISIBLE_RE.search(t)))).values

    # ── AI-generated spam features (20-24) ────────────────────────────────────

    # 20. formal_biz_score — count of formal business jargon
    f20 = raw.apply(lambda t: _count_matches(t.lower(), _FORMAL_BUSINESS_WORDS)).values.astype(float)

    # 21. cold_outreach_score — cold-email opener phrases
    f21 = raw.apply(lambda t: _count_matches(t.lower(), _COLD_OUTREACH_PHRASES)).values.astype(float)

    # 22. persuasive_cta — soft CTA phrases used by AI spam
    f22 = raw.apply(lambda t: _count_matches(t.lower(), _PERSUASIVE_CTA_PHRASES)).values.astype(float)

    # 23. no_slang_flag — 1 if NO slang words present (AI msgs avoid slang)
    f23 = raw.apply(
        lambda t: 1.0 if not any(s in t.lower().split() for s in _SLANG_WORDS) else 0.0
    ).values

    # 24. long_paragraph_flag — dense prose: >200 chars, few sentence breaks
    def _long_para(t):
        if len(t) < 200:
            return 0.0
        sentence_count = len(re.findall(r"[.!?]+", t))
        return 1.0 if sentence_count <= 3 else 0.0
    f24 = raw.apply(_long_para).values

    # ── v6: Tricky-ham disambiguation features ────────────────────────────────

    # 25. otp_flag — message matches OTP/verification-code pattern (strong ham signal)
    f25 = raw.apply(lambda t: float(bool(_OTP_RE.search(t)))).values

    # 26. delivery_flag — message contains delivery/shipping phrases (ham signal)
    f26 = raw.apply(
        lambda t: float(_count_matches(t.lower(), _DELIVERY_PHRASES) >= 1)
    ).values

    # 27. sender_spoof_score — count of brand names mentioned
    #     In isolation these are neutral; high score + urgency = phishing
    f27 = raw.apply(
        lambda t: float(_count_matches(t.lower(), _SPOOFED_BRANDS))
    ).values

    # 28. all_caps_flag — more than 30% uppercase chars (aggressive spam tactic)
    f28 = (f7 > 0.30).astype(float)

    return np.column_stack([
        f0, f1, f2, f3, f4, f5, f6, f7, f8, f9,
        f10, f11, f12, f13, f14, f15, f16, f17, f18, f19,
        f20, f21, f22, f23, f24,
        f25, f26, f27, f28,
    ]).astype(np.float64)


# ── Sklearn-compatible transformers ───────────────────────────────────────────

class TextCleaner(BaseEstimator, TransformerMixin):
    def fit(self, X, y=None):
        return self

    def transform(self, X):
        return pd.Series(X).apply(preprocess_text).tolist()


class NumericFeatureExtractor(BaseEstimator, TransformerMixin):
    def fit(self, X, y=None):
        return self

    def transform(self, X):
        return extract_numeric_features(pd.Series(X))


# ── TF-IDF builders ───────────────────────────────────────────────────────────

def build_tfidf_word(max_features: int = 30_000) -> TfidfVectorizer:
    """Word-level TF-IDF (unigrams + bigrams)."""
    return TfidfVectorizer(
        analyzer="word",
        ngram_range=(1, 2),
        max_features=max_features,
        sublinear_tf=True,
        min_df=2,
        token_pattern=r"(?u)\b[a-zA-Z]\w+\b",
    )


def build_tfidf_char(max_features: int = 20_000) -> TfidfVectorizer:
    """Character n-gram TF-IDF (3–5 grams) — robust to spelling tricks."""
    return TfidfVectorizer(
        analyzer="char_wb",
        ngram_range=(3, 5),
        max_features=max_features,
        sublinear_tf=True,
        min_df=2,
    )


# ── SMSFeaturePipeline (preserved for backward compat with pickled v3) ────────

class SMSFeaturePipeline:
    """
    Original feature pipeline — preserved exactly for pickle compatibility.
    New training should use RobustSMSFeaturePipeline (below).
    """

    def __init__(self, word_max_features=30_000, char_max_features=20_000):
        self.word_tfidf = build_tfidf_word(word_max_features)
        self.char_tfidf = build_tfidf_char(char_max_features)
        self.scaler = MaxAbsScaler()
        self._fitted = False

    def _clean_series(self, texts) -> List[str]:
        return [preprocess_text(t) for t in texts]

    def fit_transform(self, texts, y=None):
        raw = pd.Series(texts)
        clean = self._clean_series(raw)
        word_feats = self.word_tfidf.fit_transform(clean)
        char_feats = self.char_tfidf.fit_transform(clean)
        num_feats = extract_numeric_features(raw)
        num_sparse = csr_matrix(self.scaler.fit_transform(num_feats))
        combined = hstack([word_feats, char_feats, num_sparse], format="csr")
        self._fitted = True
        logger.info("SMSFeaturePipeline feature matrix shape: %s", combined.shape)
        return combined

    def transform(self, texts):
        if not self._fitted:
            raise RuntimeError("Pipeline not fitted. Call fit_transform() first.")
        raw = pd.Series(texts)
        clean = self._clean_series(raw)
        word_feats = self.word_tfidf.transform(clean)
        char_feats = self.char_tfidf.transform(clean)
        num_feats = extract_numeric_features(raw)
        num_sparse = csr_matrix(self.scaler.transform(num_feats))
        return hstack([word_feats, char_feats, num_sparse], format="csr")

    def get_feature_names_out(self) -> List[str]:
        word_names = [f"word_{f}" for f in self.word_tfidf.get_feature_names_out()]
        char_names = [f"char_{f}" for f in self.char_tfidf.get_feature_names_out()]
        num_names = [
            "num_length", "num_word_count", "num_url_count", "num_suspicious_url",
            "num_exclaim", "num_question", "num_digit_ratio", "num_upper_ratio",
            "num_caps_word_count", "num_special_char_ratio",
            "num_urgency_score", "num_phishing_score", "num_emoji_count",
            "num_repeated_char_ratio", "num_avg_word_length", "num_email_count",
            "num_currency_count", "num_number_count", "num_leet_ratio",
            "num_invisible_char_flag",
            # AI-generated spam features
            "num_formal_biz_score", "num_cold_outreach_score", "num_persuasive_cta",
            "num_no_slang_flag", "num_long_paragraph_flag",
            # v6: tricky-ham disambiguation features
            "num_otp_flag", "num_delivery_flag", "num_sender_spoof_score",
            "num_all_caps_flag",
        ]
        return word_names + char_names + num_names

    def save(self, path=None):
        pass  # Not needed for loading


# ── RobustSMSFeaturePipeline (used by train_robust.py) ───────────────────────

class RobustSMSFeaturePipeline:
    """
    Two-branch TF-IDF pipeline (word + char) + 20 numeric features.

    Differences from v3:
    - Adversarial normalisation applied before text cleaning.
    - 20 rich numeric features instead of 6.
    - Larger vocabulary caps for better generalisation.
    """

    def __init__(
        self,
        word_max_features: int = 8_000,
        char_max_features: int = 5_000,
    ):
        self.word_tfidf = TfidfVectorizer(
            analyzer="word",
            ngram_range=(1, 2),
            max_features=word_max_features,
            sublinear_tf=True,
            min_df=2,
            max_df=0.95,
            token_pattern=r"(?u)\b[a-zA-Z]\w+\b",
        )
        self.char_tfidf = TfidfVectorizer(
            analyzer="char_wb",
            ngram_range=(3, 5),
            max_features=char_max_features,
            sublinear_tf=True,
            min_df=2,
            max_df=0.95,
        )
        # Unsupervised LSA (Latent Semantic Analysis) for deep semantics
        from sklearn.decomposition import TruncatedSVD
        self.lsa = TruncatedSVD(n_components=50, random_state=42)
        
        self.scaler = MaxAbsScaler()
        self._fitted = False

    def _clean(self, texts) -> List[str]:
        """Apply adversarial normalisation + full text cleaning."""
        return [preprocess_text(t) for t in texts]

    def fit_transform(self, texts, y=None):
        raw = pd.Series(texts)
        clean = self._clean(raw)
        w = self.word_tfidf.fit_transform(clean)
        c = self.char_tfidf.fit_transform(clean)
        
        # Unsupervised semantic extraction
        lsa_feats = csr_matrix(self.lsa.fit_transform(w))
        
        n = csr_matrix(self.scaler.fit_transform(extract_numeric_features(raw)))
        self._fitted = True
        combined = hstack([w, c, lsa_feats, n], format="csr")
        logger.info(
            "RobustSMSFeaturePipeline shape: %s (word=%d, char=%d, lsa=%d, numeric=29)",
            combined.shape, w.shape[1], c.shape[1], lsa_feats.shape[1]
        )
        return combined

    def transform(self, texts):
        if not self._fitted:
            raise RuntimeError("Pipeline not fitted. Call fit_transform() first.")
        raw = pd.Series(texts)
        clean = self._clean(raw)
        w = self.word_tfidf.transform(clean)
        c = self.char_tfidf.transform(clean)
        lsa_feats = csr_matrix(self.lsa.transform(w))
        n = csr_matrix(self.scaler.transform(extract_numeric_features(raw)))
        return hstack([w, c, lsa_feats, n], format="csr")

    def get_feature_names_out(self) -> List[str]:
        word_names = [f"word_{f}" for f in self.word_tfidf.get_feature_names_out()]
        char_names = [f"char_{f}" for f in self.char_tfidf.get_feature_names_out()]
        lsa_names = [f"lsa_{i}" for i in range(self.lsa.n_components)]
        num_names = [
            "num_length", "num_word_count", "num_url_count", "num_suspicious_url",
            "num_exclaim", "num_question", "num_digit_ratio", "num_upper_ratio",
            "num_caps_word_count", "num_special_char_ratio",
            "num_urgency_score", "num_phishing_score", "num_emoji_count",
            "num_repeated_char_ratio", "num_avg_word_length", "num_email_count",
            "num_currency_count", "num_number_count", "num_leet_ratio",
            "num_invisible_char_flag",
            # AI-generated spam features
            "num_formal_biz_score", "num_cold_outreach_score", "num_persuasive_cta",
            "num_no_slang_flag", "num_long_paragraph_flag",
            # v6: tricky-ham disambiguation features
            "num_otp_flag", "num_delivery_flag", "num_sender_spoof_score",
            "num_all_caps_flag",
        ]
        return word_names + char_names + lsa_names + num_names


# ══════════════════════════════════════════════════════════════════════════════
# V7: Extended keyword sets (superset of base sets — only used by V7 pipeline)
# ══════════════════════════════════════════════════════════════════════════════

_URGENCY_WORDS_V7 = _URGENCY_WORDS | {
    "right now", "don't delay", "closing soon", "last hour", "final warning",
    "critical", "terminated", "restricted", "deactivated", "compromised",
    "breached", "unauthorized", "abnormal", "risk", "alert", "must act",
    "immediate action", "within 24 hours", "within 48 hours", "do not ignore",
}

_PHISHING_WORDS_V7 = _PHISHING_WORDS | {
    "credentials", "authenticate", "reactivate", "restore access",
    "billing information", "payment method", "update details",
    "validate", "submit your", "enter your", "provide your",
    "identity", "two-factor", "2fa", "authentication code",
    "wire transfer", "bitcoin", "crypto", "wallet", "zelle", "venmo",
    "gift cards", "itunes", "google play", "amazon gift",
    "inheritance", "next of kin", "beneficiary", "unclaimed funds",
    "lottery", "sweepstakes", "jackpot", "you have won",
    "approved loan", "pre-approved", "low interest rate",
    "debt relief", "tax refund", "irs refund", "customs duty",
    "redelivery fee", "pay to release", "your parcel is held",
}

_SUSPICIOUS_DOMAINS_V7 = _SUSPICIOUS_DOMAINS | {
    "rebrand.ly", "smarturl.it", "shorturl.at", "go2l.ink",
    "x.co", "gg.gg", "v.gd", "vurl.biz", "qr.io",
    "mcaf.ee", "su.pr", "ff.im", "tiny.pl", "clck.ru",
}


# ══════════════════════════════════════════════════════════════════════════════
# V7: Extended numeric feature extractor (31 features = base 29 + 2 new)
# ══════════════════════════════════════════════════════════════════════════════

def extract_numeric_features_extended(texts: pd.Series) -> np.ndarray:
    """
    Extract 31 hand-crafted numeric features per message.

    Extends the base 29 features with:
      29  grammar_anomaly_score — irregular sentence structure (run-ons,
          missing spaces after punctuation); AI text often has unnaturally
          uniform sentence length.
      30  char_entropy          — Shannon entropy of the character
          distribution; human spam is noisier than AI spam; legitimate
          messages have characteristic entropy profiles.

    Also uses V7 expanded keyword sets for features 10 (urgency) and 11
    (phishing) to improve coverage of novel phishing phrasing.
    """
    import math

    raw = texts.astype(str)

    # ── Recompute base features with V7 keyword expansions ─────────────────
    # We rebuild urgency/phishing scores with extended sets; all other
    # features are identical to extract_numeric_features() so we call it
    # and then overwrite columns 10 and 11.
    base = extract_numeric_features(texts)  # shape (n, 29)

    # Override col 10: urgency_score with V7 expanded set
    f10_v7 = raw.apply(
        lambda t: float(_count_matches(t.lower(), _URGENCY_WORDS_V7))
    ).values
    # Override col 11: phishing_score with V7 expanded set
    f11_v7 = raw.apply(
        lambda t: float(_count_matches(t.lower(), _PHISHING_WORDS_V7))
    ).values
    # Override col 3: suspicious_url with V7 extended shortener list
    def _has_suspicious_url_v7(t):
        urls = _URL_RE.findall(t)
        return float(any(d in u.lower() for u in urls for d in _SUSPICIOUS_DOMAINS_V7))
    f3_v7 = raw.apply(_has_suspicious_url_v7).values

    base[:, 3]  = f3_v7
    base[:, 10] = f10_v7
    base[:, 11] = f11_v7

    # ── f29: grammar_anomaly_score ─────────────────────────────────────────
    def _grammar_anomaly(t: str) -> float:
        sentences = re.split(r"[.!?]+", t.strip())
        sentences = [s.strip() for s in sentences if s.strip()]
        if not sentences:
            return 0.0
        lens = [len(s.split()) for s in sentences]
        avg_len = float(np.mean(lens))
        score = 0.0
        # Very long average sentence → likely run-on (AI spam or verbose phish)
        if avg_len > 25:
            score += 1.0
        # Single undivided block of >120 chars — dense prose spam
        if len(sentences) == 1 and len(t) > 120:
            score += 1.0
        # Missing space after punctuation (common in low-quality spam)
        missing_space = len(re.findall(r"[,;:][a-zA-Z]", t))
        score += min(missing_space * 0.3, 1.5)
        return score

    f29 = raw.apply(_grammar_anomaly).values.astype(np.float64)

    # ── f30: char_entropy (Shannon entropy over character distribution) ─────
    def _char_entropy(t: str) -> float:
        if not t:
            return 0.0
        t_lc = t.lower()
        n = len(t_lc)
        counts: dict = {}
        for ch in t_lc:
            counts[ch] = counts.get(ch, 0) + 1
        return -sum((cnt / n) * math.log2(cnt / n) for cnt in counts.values())

    f30 = raw.apply(_char_entropy).values.astype(np.float64)

    return np.column_stack([base, f29, f30]).astype(np.float64)


# ══════════════════════════════════════════════════════════════════════════════
# RobustSMSFeaturePipelineV7 — used by train_ensemble_v7.py
# ══════════════════════════════════════════════════════════════════════════════

class RobustSMSFeaturePipelineV7:
    """
    V7 production feature pipeline.

    Feature space: Word TF-IDF (1-3gram) + Char TF-IDF (2-5gram) + 31 numeric.
    No LSA — eliminated the dimensionality overhead for faster inference.

    Improvements over V6 RobustSMSFeaturePipeline:
      • Word trigrams capture longer phishing phrases ("click here to verify",
        "update your payment method") that bigrams miss.
      • Char 2-gram lower bound catches short obfuscated tokens.
      • 31 numeric features (adds grammar anomaly + char entropy).
      • V7 expanded urgency/phishing/domain sets for feature cols 3/10/11.
      • Larger vocabulary caps → better generalisation to unseen data.
    """

    def __init__(
        self,
        word_max_features: int = 12_000,
        char_max_features: int = 8_000,
    ):
        self.word_tfidf = TfidfVectorizer(
            analyzer="word",
            ngram_range=(1, 3),
            max_features=word_max_features,
            sublinear_tf=True,
            min_df=2,
            max_df=0.95,
            token_pattern=r"(?u)\b[a-zA-Z]\w+\b",
        )
        self.char_tfidf = TfidfVectorizer(
            analyzer="char_wb",
            ngram_range=(2, 5),
            max_features=char_max_features,
            sublinear_tf=True,
            min_df=2,
            max_df=0.95,
        )
        self.scaler = MaxAbsScaler()
        self._fitted = False

    def _clean(self, texts) -> List[str]:
        """Adversarial normalisation + full text cleaning."""
        return [preprocess_text(t) for t in texts]

    def fit_transform(self, texts, y=None):
        raw = pd.Series(texts)
        clean = self._clean(raw)
        w = self.word_tfidf.fit_transform(clean)
        c = self.char_tfidf.fit_transform(clean)
        n = csr_matrix(
            self.scaler.fit_transform(extract_numeric_features_extended(raw))
        )
        self._fitted = True
        combined = hstack([w, c, n], format="csr")
        logger.info(
            "RobustSMSFeaturePipelineV7 shape: %s (word=%d, char=%d, numeric=31)",
            combined.shape, w.shape[1], c.shape[1],
        )
        return combined

    def transform(self, texts):
        if not self._fitted:
            raise RuntimeError("Pipeline not fitted. Call fit_transform() first.")
        raw = pd.Series(texts)
        clean = self._clean(raw)
        w = self.word_tfidf.transform(clean)
        c = self.char_tfidf.transform(clean)
        n = csr_matrix(
            self.scaler.transform(extract_numeric_features_extended(raw))
        )
        return hstack([w, c, n], format="csr")

    def get_feature_names_out(self) -> List[str]:
        word_names = [f"word_{f}" for f in self.word_tfidf.get_feature_names_out()]
        char_names = [f"char_{f}" for f in self.char_tfidf.get_feature_names_out()]
        num_names = [
            "num_length", "num_word_count", "num_url_count", "num_suspicious_url",
            "num_exclaim", "num_question", "num_digit_ratio", "num_upper_ratio",
            "num_caps_word_count", "num_special_char_ratio",
            "num_urgency_score", "num_phishing_score", "num_emoji_count",
            "num_repeated_char_ratio", "num_avg_word_length", "num_email_count",
            "num_currency_count", "num_number_count", "num_leet_ratio",
            "num_invisible_char_flag",
            "num_formal_biz_score", "num_cold_outreach_score", "num_persuasive_cta",
            "num_no_slang_flag", "num_long_paragraph_flag",
            "num_otp_flag", "num_delivery_flag", "num_sender_spoof_score",
            "num_all_caps_flag",
            # V7 additions
            "num_grammar_anomaly", "num_char_entropy",
        ]
        return word_names + char_names + num_names
