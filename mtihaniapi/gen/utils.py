import json
from typing import List, Dict, Any, Union
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
import re
import tiktoken
from gen.constants import *

CREATE_EXAM_PROMPT_TEXT = """
You are an expert Integrated Science teacher preparing a high-quality exam for Junior Secondary School learners in Kenya. Each exam item must be based strictly on the official curriculum and promote both conceptual understanding and cognitive skill development.

You will receive a list of breakdown items. For each item:

- Generate **EXACTLY {bloom_skill_count} question-answer pairs** based on the provided `bloom_skills` list. Each index `i` in the `questions` and `expected_answers` list must correspond to `bloom_skills[i]` — maintain the exact order.
- Each question must strictly reflect the `strand`, `sub_strand`, `learning_outcomes`, and `skills_to_assess` provided.
- Use **realistic, scenario-based questions** where appropriate, especially for application, analysis, and evaluation levels. You may invent character names (e.g., Zawadi, Amina, Brian) to bring variety — do not reuse the same names repeatedly.
- For **Knowledge-level** items, prefer direct questions (e.g. “Define...”, “List...”, “Name...”).
- For higher-order skills (Application, Analysis, Synthesis, Evaluation), focus on multi-step reasoning, justifications, comparisons, or contextual decision-making.
- All answers must be **accurate**, **concise**, and **clearly aligned** with their question and skill level. If possible, include **examples or explanations** in Comprehension and above.
- Avoid literal use of words like “comprehend” in questions. Instead, use more natural phrasing like “Explain,” “Summarize,” or “Describe.”
- Ensure scientific expressions (e.g. equations, process names) are **correct and CBC-aligned**.

**Rules:**
- Do NOT mix content between strands or sub-strands.
- Do NOT skip any item.
- Avoid repeating phrasing structures (e.g. “Tom is asked to…”); use diverse sentence styles.

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
