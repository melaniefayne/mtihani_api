from collections import defaultdict
import json
import re
from statistics import mean
from typing import Dict, Any, List

import numpy as np
from sklearn.cluster import KMeans


def format_scores(score_dict) -> List[Dict[str, Any]]:
    return sorted(
        [
            {
                "name": str(k),
                "percentage": round((sum(v) / (len(v) * 4)) * 100, 2)
            }
            for k, v in score_dict.items()
        ],
        key=lambda item: item["percentage"],
        reverse=True
    )


def merge_and_average_score_lists(score_lists):
    combined = defaultdict(list)
    for score_json in score_lists:
        for item in json.loads(score_json):
            combined[item["name"]].append(item["percentage"])
    return [
        {"name": name, "percentage": round(mean(vals), 2)}
        for name, vals in combined.items()
    ]


def classify_scores(score_list, weak_thresh=50, strong_thresh=75):
    weak = [s for s in score_list if s["percentage"] <= weak_thresh]
    strong = [s for s in score_list if s["percentage"] >= strong_thresh]
    return weak, strong

def find_elbow(X, min_k=2, max_k=6):
    inertias = []
    possible_ks = range(min_k, max_k+1)
    for k in possible_ks:
        kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
        kmeans.fit(X)
        inertias.append(kmeans.inertia_)
    # Find the "elbow" point (simple version: biggest drop in inertia)
    drops = np.diff(inertias)
    elbow_k = possible_ks[np.argmin(drops) + 1] if len(drops) else min_k
    return elbow_k

def extract_grade_from_strand(strand_name: str) -> int:
    match = re.search(r'\(G(\d+)\)', strand_name or "")
    return int(match.group(1)) if match else None

def split_text(text, max_chars=100):
    """Helper to split long text into lines of max_chars."""
    import textwrap
    return textwrap.wrap(text, width=max_chars)