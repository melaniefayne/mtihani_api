# curriculum.py

from collections import defaultdict
from operator import itemgetter
import random
import json
from typing import List, Dict, Any
import json
from itertools import cycle, groupby
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
    parsed_curriculum: dict,
    question_count: int,
    bloom_skill_count: int,
) -> list:
    """Plan questions across Bloom skills and strands fairly."""
    selected = parsed_curriculum.get("selected", [])
    current_number = 1
    question_plan = []

    # Group sub-strands by strand name
    strand_groups = defaultdict(list)
    for item in selected:
        grade = item["grade"]
        strand = item["strand_name"]
        for sub in item.get("sub_strands", []):
            skills_list = []
            for skill_item in sub.get("skills", []):
                if isinstance(skill_item, dict) and "skill" in skill_item:
                    skills_list.append(skill_item["skill"])
                elif isinstance(skill_item, str):
                    skills_list.append(skill_item)

            strand_groups[strand].append({
                "grade": grade,
                "strand": strand,
                "sub_strand": sub["name"],
                "learning_outcomes": sub.get("learning_outcomes", []),
                "skills_to_assess": skills_list,
            })

    if not strand_groups:
        return []

    # Create a round-robin cycle of strand keys
    strand_cycle = cycle(strand_groups.keys())

    while len(question_plan) < question_count:
        strand_key = next(strand_cycle)
        items = strand_groups[strand_key]
        if not items:
            continue

        target = random.choice(items)
        bloom_skills = random.sample(BLOOM_SKILLS, min(
            bloom_skill_count, len(BLOOM_SKILLS)))

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
        question_plan: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
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

    return structured_questions


def get_exam_curriculum(
    strand_ids: List[int],
    question_count: int = APP_QUESTION_COUNT,
    curriculum_file: str = CURRICULUM_FILE,
    bloom_skill_count: int = APP_BLOOM_SKILL_COUNT,
) -> List[Dict[str, Any]]:
    cbc_data = load_curriculum(curriculum_file)

    parsed = parse_curriculum(strand_ids, cbc_data)

    question_plan = generate_question_plan(
        parsed, question_count=question_count, bloom_skill_count=bloom_skill_count)

    question_brd = build_question_breakdown_json(question_plan)

    return question_brd


def get_cbc_grouped_questions(
    strand_ids: List[int],
    question_count: int = APP_QUESTION_COUNT,
    is_debug: bool = False,
    curriculum_file: str = CURRICULUM_FILE,
    bloom_skill_count: int = APP_BLOOM_SKILL_COUNT,
    output_file: str = QUESTION_BRD_OUTPUT_FILE,
) -> List[Dict[str, Any]]:
    question_brd = get_exam_curriculum(
        strand_ids=strand_ids,
        question_count=question_count,
        curriculum_file=curriculum_file,
        bloom_skill_count=bloom_skill_count,
    )

    sorted_data = sorted(question_brd, key=itemgetter("sub_strand"))

    grouped = defaultdict(list)
    for key, group_items in groupby(sorted_data, key=itemgetter("strand", "sub_strand")):
        strand, sub_strand = key
        grouped[key].extend(list(group_items))

    grouped_questions = []
    for (strand, sub_strand), items in grouped.items():
        if not items:
            continue

        # Use shared fields from the first item
        grade = items[0]["grade"]
        learning_outcomes = items[0]["learning_outcomes"]
        skills_to_assess = items[0]["skills_to_assess"]

        # Collect all skill breakdowns in this sub_strand group
        skills_group = [{"number": item["number"],
                        "skills_to_test": item["bloom_skills"]} for item in items]

        # Create the formatted dictionary
        grouped_questions.append({
            "grade": grade,
            "strand": strand,
            "sub_strand": sub_strand,
            "learning_outcomes": learning_outcomes,
            "skills_to_assess": skills_to_assess,
            "skills_to_test": skills_group
        })

    if (is_debug):
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(grouped_questions, f, ensure_ascii=False, indent=4)
        print(
            f"\n✅ Question breakdown written to {output_file}. Total: {len(grouped_questions)}")

    return grouped_questions


def get_rubrics_by_sub_strand(
        sub_strand_name: str,
        curriculum_file: str = CURRICULUM_FILE,
) -> List[Dict[str, str]]:
    cbc_data = load_curriculum(curriculum_file)

    for grade_data in cbc_data:
        for strand in grade_data.get("strands", []):
            for sub_strand in strand.get("sub_strands", []):
                if sub_strand.get("name") == sub_strand_name:
                    all_rubrics = []
                    for skill in sub_strand.get("skills", []):
                        all_rubrics.append({
                            "skill": skill.get("skill"),
                            "rubrics": skill.get("rubrics", [])
                        })
                    return all_rubrics
    return []


def get_uncovered_strands_up_to_grade(
    grade: int,
    tested_strands: list[str],
    curriculum_file: str = CURRICULUM_FILE,
) -> list[str]:
    """
    Returns a list of strand names from grade 7 up to the given grade,
    excluding any already present in tested_strands.
    """
    missing_strands = []
    cbc_data = load_curriculum(curriculum_file)

    for item in cbc_data:
        g = item.get("grade")
        if g is not None and 7 <= g <= grade:
            for strand in item.get("strands", []):
                strand_name = strand["name"]
                if strand_name not in tested_strands:
                    missing_strands.append(f"G{g}: {strand_name}")

    return sorted(missing_strands)


if __name__ == "__main__":
    selected_strands = [6, 9, 4]
    question_brd = get_cbc_grouped_questions(
        strand_ids=selected_strands, question_count=10)


def get_all_strand_names(
    curriculum_file: str = CURRICULUM_FILE,
) -> List[str]:
    cbc_data = load_curriculum(curriculum_file)

    strand_names = []
    for item in cbc_data:
        for strand in item.get("strands", []):
            strand_names.append(strand['name'])
            sub_strands = strand['sub_strands']
            for sub_strand in sub_strands:
                strand_names.append(sub_strand['name'])

    return strand_names
