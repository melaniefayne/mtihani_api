# curriculum.py

import random
import json
from typing import List, Dict, Any
import json
from itertools import cycle
from gen.constants import *


def load_curriculum(file_path: str) -> List[Dict[str, Any]]:
    """Load the CBC curriculum JSON."""
    with open(file_path, "r") as f:
        cbc_data = json.load(f)
        return cbc_data


def get_strand_id_grade_pairs(cbc_data: List[Dict[str, Any]]) -> List[Dict[str, any]]:
    result = []
    for grade_obj in cbc_data:
        grade = grade_obj.get("grade")
        strands = grade_obj.get("strands", [])
        for strand in strands:
            result.append({
                "id": strand.get("id"),
                "grade": grade,
                "strand": strand.get("name")
            })
    return result


def parse_curriculum(selected_strands: List[int], cbc_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Filter the curriculum based on selected strands."""
    selected_data = []
    for grade in cbc_data:
        for strand in grade.get("strands", []):
            if strand["id"] in selected_strands:
                selected_data.append({
                    "grade": grade["grade"],
                    "strand_name": strand["name"],
                    "sub_strands": strand.get("sub_strands", []),
                })
    return {"selected": selected_data}


def generate_question_plan(
        parsed_curriculum: Dict[str, Any], 
        question_count: int = APP_QUESTION_COUNT, 
        bloom_skill_count: int = APP_BLOOM_SKILL_COUNT) -> List[Dict[str, Any]]:
    """Plan questions across Bloom skills and strands fairly."""
    question_plan = []
    selected = parsed_curriculum.get("selected", [])
    current_number = 1

    # Flatten all sub-strands with grade and strand info
    all_items = []
    for item in selected:
        grade = item["grade"]
        strand = item["strand_name"]
        sub_strands = item.get("sub_strands", [])

        for sub in sub_strands:
            skills_list = []
            for skill_item in sub.get("skills", []):
                if isinstance(skill_item, dict) and "skill" in skill_item:
                    skills_list.append(skill_item["skill"])
                elif isinstance(skill_item, str):
                    skills_list.append(skill_item)

            all_items.append({
                "grade": grade,
                "strand": strand,
                "sub_strand": sub["name"],
                "learning_outcomes": sub.get("learning_outcomes", []),
                "skills_to_assess": skills_list,
            })

    if not all_items:
        return []

    # Cycle through sub-strands to distribute fairly
    strand_cycle = cycle(all_items)

    for _ in range(question_count):
        target = next(strand_cycle)
        bloom_skills = random.sample(BLOOM_SKILLS, min(bloom_skill_count, len(BLOOM_SKILLS)))
    
        question_plan.append({
            "number": current_number,
            "grade": target["grade"],
            "strand": target["strand"],
            "sub_strand": target["sub_strand"],
            "learning_outcomes": target["learning_outcomes"],
            "skills_to_assess": target["skills_to_assess"],
            "bloom_skills": bloom_skills,
        })
        current_number += 1

    return question_plan


def build_question_breakdown_json(
        question_plan: List[Dict[str, Any]], 
        is_debug: bool, 
        output_file: str = QUESTION_BRD_OUTPUT_FILE) -> List[Dict[str, Any]]:
    """Build structured JSON from question plan and write to a file."""
    structured_questions = []

    for i, qp in enumerate(question_plan, start=1):
        structured_questions.append({
            "number": i,
            "grade": qp['grade'],
            "strand": qp['strand'],
            "sub_strand": qp['sub_strand'],
            "bloom_skills": qp["bloom_skills"],
            "learning_outcomes": qp['learning_outcomes'],  # keep as list
            "skills_to_assess": qp['skills_to_assess'] if qp['skills_to_assess'] else []
        })

    if (is_debug):
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(structured_questions, f, ensure_ascii=False, indent=4)
        print(f"✅ Question breakdown written to {output_file}")

    return structured_questions


def get_exam_curriculum(
        strand_ids: List[int],  
        question_count: int, 
        is_debug: bool = False, 
        curriculum_file: str = CURRICULUM_FILE,
        bloom_skill_count: int = APP_BLOOM_SKILL_COUNT,
    ) -> List[Dict[str, Any]]:
    cbc_data = load_curriculum(curriculum_file)

    parsed = parse_curriculum(strand_ids, cbc_data)

    question_plan = generate_question_plan(
        parsed, question_count=question_count, bloom_skill_count=bloom_skill_count)

    question_brd = build_question_breakdown_json(question_plan, is_debug)

    return question_brd


if __name__ == "__main__":
    selected_strands = [1, 4, 6]
    question_brd = get_exam_curriculum(
        strand_ids=selected_strands, question_count=10)
    print(question_brd)
