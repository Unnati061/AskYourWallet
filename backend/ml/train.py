"""Reproduce the shipped text-only model: python backend/ml/train.py --csv PATH.

The original full-feature pickle is intentionally not used by the application.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import sklearn
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, f1_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
from app.services.categorization.ml import predict_probabilities

# Only labels with an unambiguous equivalent in the app can be accepted.
# Food mixes groceries/dining; Household mixes housing/utilities/shopping.
MAPPING = {
    "Apparel": "Shopping", "Beauty": "Personal Care", "Education": "Education",
    "Gift": "Gifts & Donations", "Health": "Healthcare",
    "Money transfer": "Transfer", "Transportation": "Transport",
    "subscription": "Subscriptions",
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", required=True, type=Path)
    args = parser.parse_args()
    raw = pd.read_csv(args.csv)
    df = raw.drop_duplicates().copy()
    df["Category"] = df.Category.str.strip()
    df = df[df["Income/Expense"] == "Expense"].copy()
    counts = df.Category.value_counts()
    df = df[df.Category.isin(counts[counts >= 15].index)].copy()
    df["text"] = df.Note.fillna("").str.lower().str.strip()
    trainval, test = train_test_split(df.index, test_size=.2, random_state=42, stratify=df.Category)
    train, validation = train_test_split(trainval, test_size=.25, random_state=42, stratify=df.loc[trainval, "Category"])
    model = Pipeline([
        ("text", TfidfVectorizer(ngram_range=(1, 2))),
        ("clf", LogisticRegression(max_iter=2000, class_weight="balanced")),
    ]).fit(df.loc[train, "text"], df.loc[train, "Category"])
    vec, clf = model.named_steps["text"], model.named_steps["clf"]
    artifact = {
        "format_version": 1, "classes": clf.classes_.tolist(),
        "vocabulary": {k: int(v) for k, v in vec.vocabulary_.items()},
        "idf": vec.idf_.tolist(), "coef": clf.coef_.tolist(),
        "intercept": clf.intercept_.tolist(), "category_mapping": MAPPING,
    }
    runtime = dict(artifact, coef=clf.coef_, intercept=clf.intercept_)
    # Verify the exported inference implementation against sklearn, including OOV/Unicode.
    probes = df.loc[test, "text"].tolist() + ["milk milk", "CAFÉ payment", "", "zzzzunseen123"]
    expected = model.predict_proba(probes)
    max_error = 0.
    for text, probabilities in zip(probes, expected):
        actual = predict_probabilities(text, runtime)
        if actual is not None:
            max_error = max(max_error, float(np.max(np.abs(actual - probabilities))))
    assert max_error < 1e-10, max_error

    def selective(indices, threshold):
        probabilities = model.predict_proba(df.loc[indices, "text"])
        pred = clf.classes_[probabilities.argmax(axis=1)]
        known = np.asarray(vec.transform(df.loc[indices, "text"]).getnnz(axis=1) > 0)
        accept = known & np.asarray([p in MAPPING for p in pred]) & (probabilities.max(axis=1) >= threshold)
        truth = df.loc[indices, "Category"].to_numpy()
        return {"accepted": int(accept.sum()), "coverage": float(accept.mean()),
                "accepted_accuracy": float(np.mean(pred[accept] == truth[accept])) if accept.any() else None}

    # Select using validation only. Test labels never influence the threshold.
    candidates = [(float(t), selective(validation, float(t))) for t in np.arange(.50, .96, .05)]
    eligible = [(t, stats) for t, stats in candidates if stats["accepted"] >= 10 and stats["accepted_accuracy"] >= .90]
    threshold = max(eligible, key=lambda pair: pair[1]["coverage"])[0] if eligible else 1.01
    artifact["threshold"] = round(threshold, 2)
    predictions = model.predict(df.loc[test, "text"])
    report = {
        "dataset_url": "https://www.kaggle.com/datasets/prasad22/daily-transactions-dataset",
        "dataset_sha256": hashlib.sha256(args.csv.read_bytes()).hexdigest(),
        "raw_rows": len(raw), "retained_rows": len(df),
        "split": {"train": len(train), "validation": len(validation), "test": len(test), "random_state": 42},
        "features": ["Note text only"], "sklearn_version": sklearn.__version__,
        "test_accuracy": accuracy_score(df.loc[test, "Category"], predictions),
        "test_macro_f1": f1_score(df.loc[test, "Category"], predictions, average="macro"),
        "threshold": artifact["threshold"], "validation_candidates": candidates,
        "validation_selective": selective(validation, artifact["threshold"]),
        "test_selective": selective(test, artifact["threshold"]),
        "classification_report": classification_report(df.loc[test, "Category"], predictions, output_dict=True, zero_division=0),
        "export_max_probability_error": max_error,
        "limitations": ["Single household; random row split can share merchant patterns across splits.",
                        "No independent bank-statement evaluation; probabilities are not calibrated guarantees.",
                        "Ambiguous categories abstain; only expense predictions are supported.",
                        "Coverage is measured before existing app rules; incremental app coverage may be lower."],
    }
    output = Path(__file__).resolve().parent
    (output / "wallet_text_model.json").write_text(json.dumps(artifact, separators=(",", ":")), encoding="utf-8")
    (output / "evaluation.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k not in ("classification_report", "validation_candidates")}, indent=2))


if __name__ == "__main__":
    main()
