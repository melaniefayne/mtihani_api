import string, random
from rest_framework.pagination import PageNumberPagination


class GlobalPagination(PageNumberPagination):
    page_size = 25
    page_size_query_param = 'page_size'
    max_page_size = 100


def generate_unique_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))


EXPECTATION_LEVELS = {
    "EXCEEDING": {
        "label": "Exceeding",
        "min_score": 80,
    },
    "MEETING": {
        "label": "Meeting",
        "min_score": 60,
    },
    "APPROACHING": {
        "label": "Approaching",
        "min_score": 40,
    },
    "BELOW": {
        "label": "Below",
        "min_score": 0,
    }
}

LEVEL_ORDER = [
    ("EXCEEDING", 80),
    ("MEETING", 60),
    ("APPROACHING", 40),
    ("BELOW", 0),
]

def get_expectation_level(score):
    if score is None:
        return None

    for key, min_score in LEVEL_ORDER:
        if score >= min_score:
            return EXPECTATION_LEVELS[key]["label"]
    return None
