import re
from typing import List
from pathlib import Path
import logging

import pandas as pd
import numpy as np
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import MaxAbsScaler
from scipy.sparse import csr_matrix, hstack
import nltk
from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer
from nltk.corpus import stopwords

# Ensure NLTK data is downloaded
def init_nltk():
    try:
        # Silently check for resources, only download if missing
        for resource in ['tokenizers/punkt', 'corpora/stopwords', 'corpora/wordnet', 'corpora/omw-1.4', 'tokenizers/punkt_tab']:
            try:
                nltk.data.find(resource)
            except LookupError:
                logger.info(f"[NLTK] Resource {resource} missing, attempting download...")
                nltk.download(resource.split('/')[-1], quiet=True)
    except Exception as e:
        logger.warning(f"[NLTK] Initialization failed ({e}). App will proceed.")

logger = logging.getLogger("ml.feature_pipeline")

init_nltk()

_PUNCT_TABLE = str.maketrans('', '', '!"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~')
_STOP_WORDS = None

def get_stop_words():
    global _STOP_WORDS
    if _STOP_WORDS is None:
        try:
            _STOP_WORDS = set(stopwords.words("english"))
        except LookupError:
            logger.warning("[NLTK] Stopwords not found. Using empty set.")
            _STOP_WORDS = set()
    return _STOP_WORDS

_LEMMATIZER = None

def get_lemmatizer():
    global _LEMMATIZER
    if _LEMMATIZER is None:
        _LEMMATIZER = WordNetLemmatizer()
    return _LEMMATIZER

# Text cleaning functions 
def clean_text(text: str) -> str:
    """Lower-case → remove punctuation → strip extra whitespace."""
    text = str(text).lower()
    text = text.translate(_PUNCT_TABLE)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def tokenize_and_lemmatize(text: str) -> List[str]:
    """Tokenise → remove stopwords → lemmatise."""
    tokens = word_tokenize(text)
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

#  Numeric feature extractor 
def extract_numeric_features(texts: pd.Series) -> np.ndarray:
    """Return (n, 3) array: [msg_length, special_char_count, digit_count]."""
    lengths  = texts.str.len().fillna(0).values
    specials = texts.apply(
        lambda t: sum(1 for c in str(t) if not c.isalnum() and not c.isspace())
    ).values
    digits = texts.apply(lambda t: sum(c.isdigit() for c in str(t))).values
    return np.column_stack([lengths, specials, digits]).astype(np.float64)

#  Sklearn-compatible transformers 
class TextCleaner(BaseEstimator, TransformerMixin):
    def fit(self, X, y=None): return self
    def transform(self, X):
        return pd.Series(X).apply(preprocess_text).tolist()

class NumericFeatureExtractor(BaseEstimator, TransformerMixin):
    def fit(self, X, y=None): return self
    def transform(self, X):
        return extract_numeric_features(pd.Series(X))

#  TF-IDF vectorizer For Words --> captures the meaning 
def build_tfidf_word(max_features: int = 30_000) -> TfidfVectorizer:
    """Word-level TF-IDF (unigrams + bigrams)."""
    return TfidfVectorizer(
        analyzer="word", ngram_range=(1, 2),
        max_features=max_features, sublinear_tf=True,
        min_df=2, token_pattern=r"(?u)\b[a-zA-Z]\w+\b",
    )

# TF-IDF vectorizer For Char --> Handles the spelling trick
def build_tfidf_char(max_features: int = 20_000) -> TfidfVectorizer:
    """Character n-gram TF-IDF (3–5 grams)."""
    return TfidfVectorizer(
        analyzer="char_wb", ngram_range=(3, 5),
        max_features=max_features, sublinear_tf=True, min_df=2,
    )

# ── SMSFeaturePipeline 
class SMSFeaturePipeline:
   # Intialization 
   # for the words char and normalizes numeric features 
    def __init__(self, word_max_features=30_000, char_max_features=20_000):
        self.word_tfidf = build_tfidf_word(word_max_features)
        self.char_tfidf = build_tfidf_char(char_max_features)
        self.scaler     = MaxAbsScaler()
        self._fitted    = False

    # Cleaning helper 
    def _clean_series(self, texts) -> List[str]:
        return [preprocess_text(t) for t in texts]

    # Training Phase 
    def fit_transform(self, texts, y=None):
        raw  = pd.Series(texts)                                             # Pandas series
        clean = self._clean_series(raw)
        word_feats = self.word_tfidf.fit_transform(clean)                   # word TF-IDF
        char_feats = self.char_tfidf.fit_transform(clean)                   # char TF-IDF
        num_feats  = extract_numeric_features(raw)                          # numeric scaling 
        num_sparse = csr_matrix(self.scaler.fit_transform(num_feats))       # CSR format for sparse matrix
        combined = hstack([word_feats, char_feats, num_sparse], format="csr")
        self._fitted = True
        logger.info("Feature matrix shape: %s", combined.shape)
        return combined

    # Testing Phase 
    def transform(self, texts):
        if not self._fitted:
            raise RuntimeError("Pipeline not fitted. Call fit_transform() first.")
        raw   = pd.Series(texts)
        clean = self._clean_series(raw)
        word_feats = self.word_tfidf.transform(clean)
        char_feats = self.char_tfidf.transform(clean)
        num_feats  = extract_numeric_features(raw)
        num_sparse = csr_matrix(self.scaler.transform(num_feats))
        return hstack([word_feats, char_feats, num_sparse], format="csr")

    def save(self, path=None):
        pass # Not needed for loading
