from langchain_openai import ChatOpenAI
import os
import dotenv
dotenv.load_dotenv()

APP_QUESTION_COUNT = 25
APP_BLOOM_SKILL_COUNT = 3
BLOOM_SKILLS = [
    "Remembering", "Understanding", "Applying", "Analysing", "Evaluating", "Creating"
]

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_LLM_4O = ChatOpenAI(
    model_name="gpt-4o",
    temperature=0.1,
    max_tokens=10240,
    openai_api_key=OPENAI_API_KEY,
)

FLOWISE_API_URL = "https://cloud.flowiseai.com/api/v1/prediction/68022f7f-b4f3-431b-a64e-0c4d61734800"
FLOWISE_API_KEY = os.getenv("FLOWISE_MTIHANI_API_KEY")
FLOWISE_HEADERS = {"Authorization": f"Bearer {FLOWISE_API_KEY}"}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CURRICULUM_FILE = os.path.join(BASE_DIR, "data", "cbc_data.json")
QUESTION_LIST_OUTPUT_FILE = os.path.join(
    BASE_DIR, "output", "question_list.json")
QUESTION_BRD_OUTPUT_FILE = os.path.join(
    BASE_DIR, "output", "question_breakdown.json")
ANSWERS_LIST_OUTPUT_FILE = os.path.join(
    BASE_DIR, "output", "answers_list.json")
GRADES_LIST_OUTPUT_FILE = os.path.join(BASE_DIR, "output", "grades_list.json")

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
