"""
score_reviews.py
================
Run RoBERTa once locally, store results in the database.
Run this script once — never needs to run again unless reviews change.
"""

import numpy as np
from scipy.special import softmax
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os
import torch

load_dotenv()
engine = create_engine(os.getenv("DATABASE_URL"))

MODEL_NAME = "cardiffnlp/twitter-roberta-base-sentiment"
LABELS     = ["negative", "neutral", "positive"]

print("Loading RoBERTa model...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model     = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME)
model.eval()
print("Model loaded.")

def score(input_text: str) -> tuple[str, float]:
    encoded = tokenizer(
        input_text,
        return_tensors="pt",
        truncation=True,
        max_length=512,
    )
    with torch.no_grad():
        output = model(**encoded)
    scores    = softmax(output.logits[0].numpy())
    label     = LABELS[int(np.argmax(scores))]
    compound  = round(float(scores[2]) - float(scores[0]), 4)
    return label, compound

# Load all reviews
with engine.connect() as conn:
    rows = conn.execute(text(
        "SELECT review_id, review_text FROM reviews ORDER BY review_id"
    )).fetchall()

print(f"Scoring {len(rows)} reviews...")

results = []
for i, (review_id, review_text) in enumerate(rows):
    label, compound = score(review_text)
    results.append({
        "review_id": review_id,
        "label":     label,
        "score":     compound,
    })
    if (i + 1) % 100 == 0:
        print(f"  {i+1}/{len(rows)} scored...")

# Write all results back to the database
with engine.connect() as conn:
    for r in results:
        conn.execute(text("""
            UPDATE reviews
            SET roberta_sentiment = :label,
                roberta_score     = :score
            WHERE review_id = :review_id
        """), r)
    conn.commit()

print(f"Done. {len(results)} reviews scored and stored.")