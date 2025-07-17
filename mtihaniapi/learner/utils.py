import string
import random
from rest_framework.pagination import PageNumberPagination

# ================================================== CONSTANTS
# ============================================================

class GlobalPagination(PageNumberPagination):
    page_size = 25
    page_size_query_param = 'page_size'
    max_page_size = 100


WEEKDAYS = [
    ("Monday", "Monday"),
    ("Tuesday", "Tuesday"),
    ("Wednesday", "Wednesday"),
    ("Thursday", "Thursday"),
    ("Friday", "Friday"),
]

EXPECTATION_LEVELS = [
    ("Below", "Below"),
    ("Approaching", "Approaching"),
    ("Meeting", "Meeting"),
    ("Exceeding", "Exceeding"),
]

STUDENT_STATUSES = [
    ("Active", "Active"),
    ("Inactive", "Inactive"),
    ("Archived", "Archived"),
]


# ================================================== FUNCTIONS
# ============================================================

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

def generate_unique_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
