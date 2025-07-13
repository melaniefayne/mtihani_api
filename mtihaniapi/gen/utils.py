from collections import defaultdict
import json
from operator import itemgetter
from typing import List, Dict, Any, Union
from langchain.prompts import PromptTemplate
import re
import tiktoken
from gen.prompts import *
from gen.constants import *

# ================================================================== UTILS


def get_token_count_from_str(text: str, llm_model: str) -> int:
    encoding = tiktoken.encoding_for_model(llm_model)
    return len(encoding.encode(text))


def clean_llm_response(raw_response: str) -> str:
    cleaned = raw_response.strip()

    # Only remove code block markers if they exist
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\n?", "", cleaned)
        cleaned = re.sub(r"\n?```$", "", cleaned)

    return cleaned.strip()


def run_llm_function(
        invoke_param: Dict[str, Any],
        prompt_template: PromptTemplate,
        formatted_prompt: str,
        llm: Any = OPENAI_LLM_4O,
        is_debug: bool = False) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
    try:
        # LCEL-style prompt-to-LLM pipe
        runnable = prompt_template | llm
        llm_model = llm.model_name

        if (is_debug):
            input_tokens = get_token_count_from_str(
                formatted_prompt, llm_model)
            print(f"📝 Input token count ({llm_model}): {input_tokens}")

        # Invoke model
        response = runnable.invoke(invoke_param)
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


# ================================================================== CREATE EXAM


CREATE_EXAM_LLM_PROMPT = PromptTemplate(
    input_variables=["strand", "sub_strand", "learning_outcomes",
                     "skills_to_assess", "skills_to_test", "question_count",
                     "sample_questions"],
    template=CREATE_EXAM_PROMPT_TEXT
)


def generate_llm_sub_strand_questions(
        sub_strand_data: Dict[str, Any],
        is_debug: bool = False,
        llm: Any = OPENAI_LLM_4O,
) -> Union[List[Dict[str, Any]], Dict[str, Any]]:

    prompt_template = CREATE_EXAM_LLM_PROMPT
    formatted_prompt = prompt_template.format(
        strand=sub_strand_data["strand"],
        sub_strand=sub_strand_data["sub_strand"],
        learning_outcomes=sub_strand_data["learning_outcomes"],
        skills_to_assess=sub_strand_data["skills_to_assess"],
        skills_to_test=sub_strand_data["skills_to_test"],
        question_count=sub_strand_data["question_count"],
        sample_questions=sub_strand_data["sample_questions"],
    )

    invoke_param = {
        "strand": sub_strand_data["strand"],
        "sub_strand": sub_strand_data["sub_strand"],
        "learning_outcomes": sub_strand_data["learning_outcomes"],
        "skills_to_assess": sub_strand_data["skills_to_assess"],
        "skills_to_test": sub_strand_data["skills_to_test"],
        "question_count": sub_strand_data["question_count"],
        "sample_questions": sub_strand_data["sample_questions"],
    }

    res = run_llm_function(
        invoke_param=invoke_param,
        prompt_template=prompt_template,
        formatted_prompt=formatted_prompt,
        llm=llm,
        is_debug=is_debug
    )

    return res


def generate_llm_question_list(
    grouped_question_data: List[Dict[str, Any]],
    is_debug: bool = False,
    llm: Any = OPENAI_LLM_4O,
    output_file: str = QUESTION_LIST_OUTPUT_FILE,
) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
    all_question_list = []

    for group in grouped_question_data:
        strand = group["strand"]
        sub_strand = group["sub_strand"]
        learning_outcomes = "\n- " + "\n- ".join(group["learning_outcomes"])
        skills_to_assess = "\n- " + "\n- ".join(group["skills_to_assess"])
        sample_questions = group["sample_questions"]

        # Step 1: Flatten all skills with their associated breakdown number
        numbered_skills = []
        for entry in group["skills_to_test"]:
            number = entry["number"]
            for skill in entry["skills_to_test"]:
                numbered_skills.append({"number": number, "skill": skill})

        # Step 2: Build a flat list of just the skills (in order)
        skills_only = [entry["skill"] for entry in numbered_skills]

        # Step 3: Generate all questions in one LLM call
    
        sub_strand_data = {
            "question_count": len(skills_only),
            "strand": strand,
            "sub_strand": sub_strand,
            "learning_outcomes": learning_outcomes,
            "skills_to_assess": skills_to_assess,
            "skills_to_test": skills_only,
            "sample_questions": sample_questions,
        }

        if (is_debug):
            print(f"\n{sub_strand} =========")

        parsed_output = generate_llm_sub_strand_questions(
            llm=llm,
            sub_strand_data=sub_strand_data,
            is_debug=is_debug,
        )

        if not isinstance(parsed_output, list):
            return parsed_output

        # Step 4: Map each generated question back to the correct `number`
        tagged_responses = []
        for idx, qa in enumerate(parsed_output):
            question_item = {}
            question_item["number"] = numbered_skills[idx]["number"]
            question_item["grade"] = group["grade"]
            question_item["strand"] = group["strand"]
            question_item["sub_strand"] = group["sub_strand"]
            question_item["bloom_skill"] = numbered_skills[idx]["skill"]
            question_item["description"] = qa["question"]
            question_item["expected_answer"] = qa["expected_answer"]

            tagged_responses.append(question_item)

        all_question_list.extend(tagged_responses)

    all_question_list = sorted(all_question_list, key=itemgetter("number"))

    if (is_debug):
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(all_question_list, f, ensure_ascii=False, indent=4)
        print(
            f"\n✅ Question list written to {output_file}. Total: {len(all_question_list)}")

    return all_question_list


def get_db_question_objects(
    all_question_list: List[Dict[str, Any]],
    is_debug: bool = False,
    output_file: str = QUESTION_LIST_OUTPUT_FILE,
) -> List[Dict[str, Any]]:
    grouped = defaultdict(lambda: {
        "bloom_skills": [],
        "questions": [],
        "expected_answers": []
    })

    for item in all_question_list:
        # Create a key based on shared fields
        key = (
            item["number"],
            item["grade"],
            item["strand"],
            item["sub_strand"]
        )

        grouped_item = grouped[key]
        grouped_item["number"] = item["number"]
        grouped_item["grade"] = item["grade"]
        grouped_item["strand"] = item["strand"]
        grouped_item["sub_strand"] = item["sub_strand"]

        grouped_item["bloom_skills"].append(item["bloom_skill"])
        grouped_item["questions"].append(item["description"])
        grouped_item["expected_answers"].append(item["expected_answer"])

        grouped_item["bloom_skill"] = grouped_item["bloom_skills"][0]
        grouped_item["description"] = grouped_item["questions"][0]
        grouped_item["expected_answer"] = grouped_item["expected_answers"][0]

    exam_questions = list(grouped.values())
    exam_questions = sorted(exam_questions, key=lambda x: x["number"])

    if (is_debug):
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(exam_questions, f, ensure_ascii=False, indent=4)
        print(
            f"\n✅ Question list to {output_file}. Total: {len(exam_questions)}")

    return exam_questions


# ================================================================== MOCK EXAM ANSWERS


MOCK_EXAM_ANSWERS_LLM_PROMPT = PromptTemplate(
    input_variables=["exam", "student_list"],
    template=MOCK_EXAM_ANSWERS_PROMPT_TEXT
)


def generate_llm_exam_answers_list(
        exam_data: List[Dict[str, Any]],
        student_data: List[Dict[str, Any]],
        is_debug: bool = False,
        llm: Any = OPENAI_LLM_4O,
        output_file: str = ANSWERS_LIST_OUTPUT_FILE,
) -> Union[List[Dict[str, Any]], Dict[str, Any]]:

    prompt_template = MOCK_EXAM_ANSWERS_LLM_PROMPT
    exam_str = json.dumps(exam_data, indent=2)
    student_str = json.dumps(student_data, indent=2)
    formatted_prompt = prompt_template.format(
        exam=exam_str, student_list=student_str)
    invoke_param = {
        "exam": exam_data,
        "student_list": student_data
    }

    res = run_llm_function(
        invoke_param=invoke_param,
        prompt_template=prompt_template,
        formatted_prompt=formatted_prompt,
        llm=llm,
        is_debug=is_debug
    )

    if (is_debug):
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(res, f, ensure_ascii=False, indent=4)
        print(f"\n✅ Mocked Answers list written to {output_file}")

    return res


# ================================================================== GRADE ANSWERS


GRADE_ANSWERS_LLM_PROMPT = PromptTemplate(
    input_variables=["question", "expected_answer",
                     "rubrics", "student_answers"],
    template=GRADE_ANSWERS_PROMPT_TEXT
)


def generate_llm_qa_grades(
    answers_data: Dict[str, Any],
    is_debug: bool = False,
    llm: Any = OPENAI_LLM_4O,
) -> Union[List[List[Any]], Dict[str, Any]]:

    prompt_template = GRADE_ANSWERS_LLM_PROMPT
    formatted_prompt = prompt_template.format(
        question=answers_data["question"],
        expected_answer=answers_data["expected_answer"],
        rubrics=answers_data["rubrics"],
        student_answers=answers_data["student_answers"],
    )

    invoke_param = {
        "question": answers_data["question"],
        "expected_answer": answers_data["expected_answer"],
        "rubrics": answers_data["rubrics"],
        "student_answers": answers_data["student_answers"],
    }

    res = run_llm_function(
        invoke_param=invoke_param,
        prompt_template=prompt_template,
        formatted_prompt=formatted_prompt,
        llm=llm,
        is_debug=is_debug
    )

    return res


def generate_llm_answer_grades_list(
    grouped_answers_data: List[Dict[str, Any]],
    is_debug: bool = False,
    llm: Any = OPENAI_LLM_4O,
    output_file: str = GRADES_LIST_OUTPUT_FILE,
) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
    all_grades = []

    for answer_group in grouped_answers_data:
        if (is_debug):
            print(f"\n{answer_group['question']} =========")

        parsed_output = generate_llm_qa_grades(
            llm=llm,
            answers_data=answer_group,
            is_debug=is_debug,
        )

        if not isinstance(parsed_output, list):
            return parsed_output

        all_grades.extend(parsed_output)

    if (is_debug):
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(all_grades, f, ensure_ascii=False, indent=4)
        print(f"\n✅ Graded Answers list written to {output_file}")

    return all_grades


# ================================================================== GRADE ANSWERS

CLASSROOM_EXAM_INSIGHTS_LLM_PROMPT = PromptTemplate(
    input_variables=["class_performance_data"],
    template=CLASSROOM_EXAM_INSIGHTS_PROMPT
)


def generate_llm_class_perf_insights(
        class_performance_data: List[Dict[str, Any]],
        is_debug: bool = False,
        llm: Any = OPENAI_LLM_4O,
) -> Union[List[Dict[str, Any]], Dict[str, Any]]:

    prompt_template = CLASSROOM_EXAM_INSIGHTS_LLM_PROMPT
    formatted_prompt = prompt_template.format(
        class_performance_data=class_performance_data
    )
    invoke_param = {
        "class_performance_data": class_performance_data
    }

    res = run_llm_function(
        invoke_param=invoke_param,
        prompt_template=prompt_template,
        formatted_prompt=formatted_prompt,
        llm=llm,
        is_debug=is_debug
    )

    return res


STRAND_PERFORMANCE_INSIGHTS_LLM_PROMPT = PromptTemplate(
    input_variables=["strand_performance_data"],
    template=STRAND_PERFORMANCE_INSIGHTS_PROMPT
)


def generate_llm_strand_insights(
        strand_performance_data: List[Dict[str, Any]],
        is_debug: bool = False,
        llm: Any = OPENAI_LLM_4O,
) -> Union[List[Dict[str, Any]], Dict[str, Any]]:

    prompt_template = STRAND_PERFORMANCE_INSIGHTS_LLM_PROMPT
    formatted_prompt = prompt_template.format(
        strand_performance_data=strand_performance_data
    )
    invoke_param = {
        "strand_performance_data": strand_performance_data
    }

    res = run_llm_function(
        invoke_param=invoke_param,
        prompt_template=prompt_template,
        formatted_prompt=formatted_prompt,
        llm=llm,
        is_debug=is_debug
    )

    return res


FLAGGED_SUB_STRAND_INSIGHTS_LLM_PROMPT = PromptTemplate(
    input_variables=["sub_strand_correlations"],
    template=FLAGGED_SUB_STRAND_INSIGHTS_PROMPT
)


def generate_llm_sub_strand_corr_insights(
        sub_strand_correlations: List[Dict[str, Any]],
        is_debug: bool = False,
        llm: Any = OPENAI_LLM_4O,
) -> Union[List[Dict[str, Any]], Dict[str, Any]]:

    prompt_template = FLAGGED_SUB_STRAND_INSIGHTS_LLM_PROMPT
    formatted_prompt = prompt_template.format(
        sub_strand_correlations=sub_strand_correlations
    )
    invoke_param = {
        "sub_strand_correlations": sub_strand_correlations
    }

    res = run_llm_function(
        invoke_param=invoke_param,
        prompt_template=prompt_template,
        formatted_prompt=formatted_prompt,
        llm=llm,
        is_debug=is_debug
    )

    return res


CREATE_CLUSTER_FOLLOW_UP_QUIZ_LLM_PROMPT = PromptTemplate(
    input_variables=["exam_questions",
                     "cluster_performance", "question_count"],
    template=CREATE_CLUSTER_FOLLOW_UP_QUIZ_PROMPT
)


def generate_llm_follow_up_quiz(
        exam_questions: List[Dict[str, Any]],
        cluster_performance: Dict[str, Any],
        question_count: int = 15,
        is_debug: bool = False,
        llm: Any = OPENAI_LLM_4O,
) -> Union[List[Dict[str, Any]], Dict[str, Any]]:

    prompt_template = CREATE_CLUSTER_FOLLOW_UP_QUIZ_LLM_PROMPT
    formatted_prompt = prompt_template.format(
        exam_questions=exam_questions,
        cluster_performance=cluster_performance,
        question_count=question_count,
    )
    invoke_param = {
        "exam_questions": exam_questions,
        "cluster_performance": cluster_performance,
        "question_count": question_count,
    }

    res = run_llm_function(
        invoke_param=invoke_param,
        prompt_template=prompt_template,
        formatted_prompt=formatted_prompt,
        llm=llm,
        is_debug=is_debug
    )

    return res


# ================================================================== EXTRACT EXAM CONTEXT


EXTRACT_SUB_STRAND_CONTEXT_LLM_PROMPT = PromptTemplate(
    input_variables=["sub_strand", "strand", "description", "reference_text"],
    template=EXTRACT_SUB_STRAND_CONTEXT_PROMPT
)


def generate_llm_sub_strand_q_samples(
    sub_strand: str,
    strand: str,
    description: str,
    reference_text: str,
    is_debug: bool = False,
    llm: Any = OPENAI_LLM_4O,
) -> Union[List[List[Any]], Dict[str, Any]]:
    prompt_template = EXTRACT_SUB_STRAND_CONTEXT_LLM_PROMPT
    formatted_prompt = prompt_template.format(
        sub_strand=sub_strand,
        strand=strand,
        description=description,
        reference_text=reference_text,
    )

    invoke_param = {
        "sub_strand": sub_strand,
        "strand": strand,
        "description": description,
        "reference_text": reference_text,
    }

    res = run_llm_function(
        invoke_param=invoke_param,
        prompt_template=prompt_template,
        formatted_prompt=formatted_prompt,
        llm=llm,
        is_debug=is_debug
    )

    return res


def generate_llm_strand_context_list(
    cbc_data: List[List[str]],
    reference_text: str,
    is_debug: bool = False,
    llm: Any = OPENAI_LLM_4O,
    output_file: str = DOC_EXTRACT_OUTPUT_FILE,
) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
    all_sub_strand_content = []

    for strand, sub_strand, description in cbc_data:
        if (is_debug):
            print(f"\n{sub_strand} =========")

        parsed_output = generate_llm_sub_strand_q_samples(
            llm=llm,
            sub_strand=sub_strand,
            strand=strand,
            description=description,
            reference_text=reference_text,
            is_debug=is_debug,
        )

        if not isinstance(parsed_output, list):
            return parsed_output

        all_sub_strand_content.append({
            "sub_strand": sub_strand,
            "strand": strand,
            "samples": parsed_output,
        })

    if (is_debug):
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(all_sub_strand_content, f, ensure_ascii=False, indent=4)
        print(
            f"\n✅ Doc Extract written to {output_file}. Total: {len(all_sub_strand_content)}")

    return all_sub_strand_content
