from collections import defaultdict
import json
from statistics import mean

def format_scores(score_dict):
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
