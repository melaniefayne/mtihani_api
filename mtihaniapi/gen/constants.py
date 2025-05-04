import os
import dotenv
dotenv.load_dotenv()

APP_QUESTION_COUNT = 25
APP_BLOOM_SKILL_COUNT = 3
BLOOM_SKILLS = [
    "Knowledge", "Comprehension", "Application", "Analysis", "Synthesis", "Evaluation"
]

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
FLOWISE_API_URL = "https://cloud.flowiseai.com/api/v1/prediction/68022f7f-b4f3-431b-a64e-0c4d61734800"
FLOWISE_API_KEY = os.getenv("FLOWISE_MTIHANI_API_KEY")
FLOWISE_HEADERS = {"Authorization": f"Bearer {FLOWISE_API_KEY}"}

CURRICULUM_FILE = "gen/data/cbc_data.json"
QUESTION_LIST_OUTPUT_FILE = "output/question_list.json"
QUESTION_BRD_OUTPUT_FILE = "output/question_breakdown.json"

JSS_SCIENCE_STRANDS = [
    {
        "id": 1,
        "grade": 7,
        "strand": "Scientific Investigation"
    },
    {
        "id": 2,
        "grade": 7,
        "strand": "Mixtures, Elements and Compounds"
    },
    {
        "id": 3,
        "grade": 7,
        "strand": "Living Things and Their Environment"
    },
    {
        "id": 4,
        "grade": 7,
        "strand": "Force and Energy"
    },
    {
        "id": 5,
        "grade": 8,
        "strand": "Mixtures, Elements and Compounds"
    },
    {
        "id": 6,
        "grade": 8,
        "strand": "Living Things and the Environment"
    },
    {
        "id": 7,
        "grade": 8,
        "strand": "Force and Energy"
    },
    {
        "id": 8,
        "grade": 9,
        "strand": "Mixtures, Elements and Compounds"
    },
    {
        "id": 9,
        "grade": 9,
        "strand": "Living Things and Their Environment"
    },
    {
        "id": 10,
        "grade": 9,
        "strand": "Force and Energy"
    }
]
