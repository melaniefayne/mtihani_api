import json
from typing import List, Dict, Any, Union
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
import re
import tiktoken
import os
import dotenv
dotenv.load_dotenv()

APP_BLOOM_SKILL_COUNT = 3
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

CREATE_EXAM_PROMPT_TEXT = """
You are an expert Integrated Science teacher preparing a high-quality exam for Junior Secondary School learners in Kenya (Grades 7–9, ages 11–14). Your goal is to create exam questions that are clear, relatable, and promote both understanding and deeper thinking.

You will receive a list of breakdown items. For each item:

- Generate **EXACTLY {bloom_skill_count} question-answer pairs** based on the provided `bloom_skills` list. Each index `i` in the `questions` and `expected_answers` list must match `bloom_skills[i]` — maintain the order.
- Each question must align with the given `strand`, `sub_strand`, `learning_outcomes`, and `skills_to_assess`.

**Question Style Guidelines:**
- Use **simple, clear language** suitable for learners aged 11–14. Avoid advanced vocabulary or long, complex sentences.
- For **Knowledge-level** skills, keep questions short and direct: e.g., “What is…”, “Name…”, “List…”.
**For higher-order skills (Comprehension, Application, Analysis, Synthesis, Evaluation):**
- Use **short real-life scenarios** to introduce the question. These can include familiar settings (home, school, farm, market).
- Ask questions that require learners to:
  - Explain or justify something
  - Compare ideas or outcomes
  - Make decisions or evaluate a situation
  - Plan or describe simple investigations
- Use realistic settings (school, home, farm, market, etc.) and **Kenyan names** like Amina, Brian, Zawadi, Musa, etc. Vary the names to avoid repetition.

**Answer Guidelines:**
- All answers must be **correct, concise**, and clearly match the question and skill level.
- For higher-order skills, answers should include **examples, reasons, or explanations** where appropriate.

**Rules:**
- Do NOT mix content between strands or sub-strands.
- Do NOT skip any item.
- Vary how you phrase each question. Avoid repeating sentence patterns like “Tom is asked to…”.
- Use only accurate, CBC-aligned science facts and processes.

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
    input_variables=["question_breakdown", "bloom_skill_count"],
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
        llm: Any = OPENAI_LLM_4O,
        bloom_skill_count: int = APP_BLOOM_SKILL_COUNT) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
    try:
        # LCEL-style prompt-to-LLM pipe
        runnable = CREATE_EXAM_LLM_PROMPT | llm

        # Format and count input
        formatted_prompt = CREATE_EXAM_LLM_PROMPT.format(
            question_breakdown=json.dumps(input_data), bloom_skill_count=bloom_skill_count)

        if (is_debug):
            input_tokens = get_token_count_from_str(
                formatted_prompt, llm_model)
            print(f"📝 Input token count ({llm_model}): {input_tokens}")

        # Invoke model
        response = runnable.invoke(
            {
                "question_breakdown": json.dumps(input_data),
                "bloom_skill_count": bloom_skill_count})
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
        return {"error": f"Error: {e}"}


def get_token_count_from_str(text: str, llm_model: str) -> int:
    encoding = tiktoken.encoding_for_model(llm_model)
    return len(encoding.encode(text))


def clean_llm_response(raw_response: str) -> str:
    # Remove markdown-style code blocks
    cleaned = re.sub(r"^```(?:json)?\n?", "", raw_response.strip())
    cleaned = re.sub(r"\n?```$", "", cleaned)
    return cleaned.strip()
