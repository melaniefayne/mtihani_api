import json
from typing import List, Dict, Any, Union
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
import os
import dotenv
import re
import tiktoken
dotenv.load_dotenv()


QUESTION_LIST_OUTPUT_FILE = "output/question_list.json"

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
FLOWISE_API_URL = "https://cloud.flowiseai.com/api/v1/prediction/68022f7f-b4f3-431b-a64e-0c4d61734800"
FLOWISE_API_KEY = os.getenv("FLOWISE_MTIHANI_API_KEY")
FLOWISE_HEADERS = {"Authorization": f"Bearer {FLOWISE_API_KEY}"}

CREATE_EXAM_PROMPT_TEXT = """You are an expert Integrated Science teacher preparing a comprehensive exam for Junior Secondary School in Kenya.

You will receive a list of breakdown items. For each item:
- Generate EXACTLY three question.
- The questions MUST align strictly with the `strand`, `sub_strand`, `learning_outcomes`, and `skills_to_assess`.
- Each index i in the "questions" array must match the answer at expected_answers[i] and the skill at bloom_skills[i] (same order).
- Use scenario-based questions involving named characters. Vary the names to make the exam more engaging and realistic where appropriate. Especially for application and comprehension skills.
- For knowledge-based items, use direct questions when suitable (e.g. definitions, naming, listing).

Rules:
- Do NOT mix content between strands.
- Do NOT skip any item.
- Do NOT reorder or mix skills.
- Keep questions academically appropriate and realistic for junior secondary learners.

Use this structure per item:
{{
  "questions": "[your generated questions here]",
  "expected_answers": "[concise but accurate answers here]"
}}

Here are the breakdown items:
{question_breakdown}

Return ONLY a valid JSON array (no explanation, no markdown). Each object must have exactly two fields: "questions" and "expected_answers".
"""

CREATE_EXAM_LLM_PROMPT = PromptTemplate(
    input_variables=["question_breakdown"],
    template=CREATE_EXAM_PROMPT_TEXT
)

OPENAI_LLM_4O = ChatOpenAI(
    model_name="gpt-4o",
    temperature=0.1,
    max_tokens=10240,
    openai_api_key=OPENAI_API_KEY,
)


def generate_llm_question_list(
        input_data: Dict[str, Any],
        llm_model: str = "gpt-4o",
        is_debug: bool = False, 
        llm: Any = OPENAI_LLM_4O)-> Union[List[Dict[str, Any]], Dict[str, Any]]:
    try:
        # LCEL-style prompt-to-LLM pipe
        runnable = CREATE_EXAM_LLM_PROMPT | llm

        # Format and count input
        formatted_prompt = CREATE_EXAM_LLM_PROMPT.format(
            question_breakdown=json.dumps(input_data))

        if (is_debug):
            input_tokens = get_token_count_from_str(
                formatted_prompt, llm_model)
            print(f"📝 Input token count ({llm_model}): {input_tokens}")

        # Invoke model
        response = runnable.invoke(
            {"question_breakdown": json.dumps(input_data)})
        if (is_debug):
            print("📦 Raw LLM output:\n", response)

        # Clean and count output tokens
        cleaned = clean_llm_response(response.content)

        if (is_debug):
            output_tokens = get_token_count_from_str(cleaned, llm_model)
            print(f"📤 Output token count ({llm_model}): {output_tokens}")
            print(f"🔢 Total token usage: {input_tokens + output_tokens}")

        try:
            parsed = json.loads(cleaned)
            return parsed
        except json.JSONDecodeError as e:
            return {"error": f"Failed to parse LLM response: {e}", "raw": cleaned}

    except Exception as e:
        return {"error": f"Error: {e}", "raw": cleaned}


def get_token_count_from_str(text: str, llm_model: str) -> int:
    encoding = tiktoken.encoding_for_model(llm_model)
    return len(encoding.encode(text))


def clean_llm_response(raw_response: str) -> str:
    # Remove markdown-style code blocks
    cleaned = re.sub(r"^```(?:json)?\n?", "", raw_response.strip())
    cleaned = re.sub(r"\n?```$", "", cleaned)
    return cleaned.strip()


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
