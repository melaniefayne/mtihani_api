import string
import random
from rest_framework.pagination import PageNumberPagination


class GlobalPagination(PageNumberPagination):
    page_size = 25
    page_size_query_param = 'page_size'
    max_page_size = 100


def generate_unique_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))


AVG_EXPECTATION_LEVELS = {
    "Exceeding": {"label": "Exceeding", "min_score": 80},
    "Meeting": {"label": "Meeting", "min_score": 60},
    "Approaching": {"label": "Approaching", "min_score": 40},
    "Below": {"label": "Below", "min_score": 0},
}

SORTED_AVG_EXPECTATION_LEVELS = sorted(
    AVG_EXPECTATION_LEVELS.values(),
    key=lambda item: item["min_score"],
    reverse=True
)


def get_avg_expectation_level(score):
    if score is None:
        return None

    for level in SORTED_AVG_EXPECTATION_LEVELS:
        if score >= level["min_score"]:
            return level["label"]

    return None


ANSWER_EXPECTATION_LEVELS = {
    0: "Below",
    1: "Below",
    2: "Approaching",
    3: "Meeting",
    4: "Exceeding",
}


def get_answer_expectation_level(score):
    if score is None:
        return None

    try:
        score = int(float(score))
    except (TypeError, ValueError):
        return None

    return ANSWER_EXPECTATION_LEVELS.get(score, None)


# ================================================== CONSTANTS
# ============================================================
WEEKDAYS = [
    ("Monday", "Monday"),
    ("Tuesday", "Tuesday"),
    ("Wednesday", "Wednesday"),
    ("Thursday", "Thursday"),
    ("Friday", "Friday"),
]

STUDENT_STATUSES = [
    ("Active", "Active"),
    ("Inactive", "Inactive"),
    ("Archived", "Archived"),
]

EXPECTATION_LEVELS = [
    ("Below", "Below"),
    ("Approaching", "Approaching"),
    ("Meeting", "Meeting"),
    ("Exceeding", "Exceeding"),
]

EXAM_STATUSES = [
    ("Generating", "Generating"),
    ("Failed", "Failed"),
    ("Upcoming", "Upcoming"),
    ("Ongoing", "Ongoing"),
    ("Grading", "Grading"),
    ("Complete", "Complete"),
    ("Analysing", "Analysing"),
    ("Archive", "Archive"),
]

EXAM_TYPES = [
    ("Standard", "Standard"),
    ("FollowUp", "FollowUp"),
]

DOC_CHUNK_STATUSES = [
    ("Unapproved", "Unapproved"),
    ("Chunking", "Chunking"),
    ("Success", "Success"),
    ("Failed", "Failed"),
]