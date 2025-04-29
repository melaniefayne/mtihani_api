import os
import dotenv

dotenv.load_dotenv()

CURRICULUM_FILE = "mtihanigen/cbc_data.json"
OUTPUT_FILE = "mtihanigen/output/question_breakdown.json"
BLOOM_SKILLS = [
    "Knowledge", "Comprehension", "Application", "Analysis", "Synthesis", "Evaluation"
]

FLOWISE_API_URL = "https://cloud.flowiseai.com/api/v1/prediction/68022f7f-b4f3-431b-a64e-0c4d61734800"
FLOWISE_API_KEY = os.getenv("FLOWISE_MTIHANI_API_KEY")
FLOWISE_HEADERS = {"Authorization": f"Bearer {FLOWISE_API_KEY}"}