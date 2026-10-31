"""Offline, selective TF-IDF / Logistic Regression inference from numeric JSON.

The artifact contains data only: no pickle loading or training dependencies at runtime.
Ambiguous source labels, unseen text and uncertain predictions abstain.
"""
import json
import logging
import math
import re
from collections import Counter
from functools import lru_cache
from pathlib import Path

import numpy as np

from app.config import settings
from app.models.category import CATEGORIES

ARTIFACT = Path(__file__).resolve().parents[3] / "ml" / "wallet_text_model.json"
logger = logging.getLogger(__name__)
TOKEN = re.compile(r"(?u)\b\w\w+\b")


@lru_cache(maxsize=1)
def load_model():
    try:
        model = json.loads(ARTIFACT.read_text(encoding="utf-8"))
        if model["format_version"] != 1:
            raise ValueError("Unsupported model format")
        model["coef"] = np.asarray(model["coef"], dtype=float)
        model["intercept"] = np.asarray(model["intercept"], dtype=float)
        if model["coef"].shape != (len(model["classes"]), len(model["vocabulary"])):
            raise ValueError("Invalid coefficient dimensions")
        if not np.isfinite(model["coef"]).all() or not np.isfinite(model["intercept"]).all():
            raise ValueError("Non-finite model weights")
        return model
    except Exception:
        logger.exception("Local classifier unavailable; using existing fallbacks")
        return None


def predict_probabilities(text: str, model: dict) -> np.ndarray | None:
    """Match sklearn's default word unigram/bigram TF-IDF and softmax."""
    tokens = TOKEN.findall(text.lower())
    terms = tokens + [a + " " + b for a, b in zip(tokens, tokens[1:])]
    counts = Counter(terms)
    features = {
        model["vocabulary"][term]: count * model["idf"][model["vocabulary"][term]]
        for term, count in counts.items() if term in model["vocabulary"]
    }
    norm = math.sqrt(sum(value * value for value in features.values()))
    if not norm:
        return None
    scores = model["intercept"].copy()
    for index, value in features.items():
        scores += model["coef"][:, index] * (value / norm)
    probabilities = np.exp(scores - scores.max())
    return probabilities / probabilities.sum()


def categorize_with_model(description: str) -> str | None:
    if not settings.ML_CATEGORIZATION_ENABLED or not description.strip():
        return None
    model = load_model()
    if model is None:
        return None
    try:
        probabilities = predict_probabilities(description, model)
        if probabilities is None:
            return None
        index = int(probabilities.argmax())
        category = model["category_mapping"].get(model["classes"][index])
        if category not in CATEGORIES or probabilities[index] < model["threshold"]:
            return None
        return category
    except Exception:
        logger.exception("Local classifier prediction failed; using existing fallbacks")
        return None
