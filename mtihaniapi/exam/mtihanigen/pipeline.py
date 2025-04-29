# pipeline.py

import math
import json
from typing import List, Dict, Any
from constants import *
import json
import requests

def load_curriculum(file_path: str) -> List[Dict[str, Any]]:
    """Load the CBC curriculum JSON."""
    with open(file_path, "r") as f:
        return json.load(f)


def parse_curriculum(selected_strands: List[str], cbc_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Filter the curriculum based on selected strands."""
    selected_data = []
    for grade in cbc_data:
        for strand in grade.get("strands", []):
            if strand["name"] in selected_strands:
                selected_data.append({
                    "grade": grade["grade"],
                    "strand_name": strand["name"],
                    "sub_strands": strand.get("sub_strands", []),
                })
    return {"selected": selected_data}


def generate_question_plan(parsed_curriculum: Dict[str, Any], total_questions: int = 25) -> List[Dict[str, Any]]:
    """Plan questions across Bloom skills and strands evenly, dynamic based on total_questions."""
    selected = parsed_curriculum["selected"]
    question_plan = []

    if not selected:
        return question_plan

    strands_cycle = []
    for strand in selected:
        for sub_strand in strand["sub_strands"]:
            strands_cycle.append({
                "grade": strand["grade"],
                "strand_name": strand["strand_name"],
                "sub_strand": sub_strand["name"],
                "learning_outcomes": sub_strand.get("learning_outcomes", []),
                "skills": sub_strand.get("skills", []),
            })

    if not strands_cycle:
        return question_plan

    # Dynamic distribution: How many questions per skill
    questions_per_skill = math.ceil(total_questions / len(BLOOM_SKILLS))

    bloom_distribution = {skill: questions_per_skill for skill in BLOOM_SKILLS}

    # Adjust distribution if needed (remove extra questions)
    total_assigned = questions_per_skill * len(BLOOM_SKILLS)
    if total_assigned > total_questions:
        extra = total_assigned - total_questions
        for skill in BLOOM_SKILLS[-extra:]:
            bloom_distribution[skill] -= 1

    strands_index = 0

    for bloom_skill, count in bloom_distribution.items():
        for _ in range(count):
            selected_topic = strands_cycle[strands_index % len(strands_cycle)]
            strands_index += 1

            skills_list = []
            for skill_item in selected_topic.get("skills", []):
                if isinstance(skill_item, dict) and "skill" in skill_item:
                    skills_list.append(skill_item["skill"])
                elif isinstance(skill_item, str):
                    skills_list.append(skill_item)

            question_plan.append({
                "grade": selected_topic["grade"],
                "strand": selected_topic["strand_name"],
                "sub_strand": selected_topic["sub_strand"],
                "learning_outcomes": selected_topic["learning_outcomes"],
                "skills": skills_list,
                "target_bloom_skill": bloom_skill,
            })

    return question_plan


def build_question_breakdown_json(question_plan: List[Dict[str, Any]], output_file: str =OUTPUT_FILE) -> List[Dict[str, Any]]:
    """Build structured JSON from question plan and write to a file."""
    structured_questions = []

    for i, qp in enumerate(question_plan, start=1):
        structured_questions.append({
            "question_number": i,
            "grade": qp['grade'],
            "strand": qp['strand'],
            "sub_strand": qp['sub_strand'],
            "target_bloom_skill": qp['target_bloom_skill'],
            "learning_outcomes": qp['learning_outcomes'],  # keep as list
            "skills_to_assess": qp['skills'] if qp['skills'] else []
        })

    # Save to JSON file
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(structured_questions, f, ensure_ascii=False, indent=4)

    print(f"✅ Question breakdown written to {output_file}")
    return structured_questions


def generate_exam_questions(question_brd: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Call Flowise endpoint to LLM generate questions."""
    payload = {
        "question_breakdown": question_brd,
    }
    response = requests.post(FLOWISE_API_URL, headers=FLOWISE_HEADERS, json=payload)
    return response.json()


if __name__ == "__main__":
    # Load CBC data
    cbc_data = load_curriculum(CURRICULUM_FILE)

    # Select strands (later user input)
    selected_strands = ["Force and Energy", "Mixtures, Elements and Compounds"]

    # Parse Curriculum
    parsed = parse_curriculum(selected_strands, cbc_data)

    # Generate Question Breakdown
    question_plan = generate_question_plan(parsed, total_questions=10)
    question_brd = build_question_breakdown_json(question_plan)

    aiRes = generate_exam_questions(question_brd)
    print(aiRes)

