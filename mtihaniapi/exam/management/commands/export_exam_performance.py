import json
import csv
from collections import defaultdict
from django.core.management.base import BaseCommand
from exam.models import StudentExamSessionPerformance
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PERFORMANCE_OUTPUT_FILE = os.path.join(
    BASE_DIR, "output", "performance_list.csv")
SKILL_STRAND_OUTPUT_FILE = os.path.join(
    BASE_DIR, "output", "performance_strand_skills_list.csv")


class Command(BaseCommand):
    help = "Export detailed student performance for a given exam (clean, as requested)."

    def add_arguments(self, parser):
        parser.add_argument("exam_id", type=int)
        parser.add_argument("--output", type=str,
                            default=PERFORMANCE_OUTPUT_FILE)

    def handle(self, *args, **options):
        exam_id = options["exam_id"]
        output_file = options["output"]

        performances = StudentExamSessionPerformance.objects.filter(
            session__exam__id=exam_id)
        if not performances.exists():
            self.stdout.write(self.style.ERROR(
                "No student performances found for this exam."))
            return

        all_grades = set()
        all_skills = set()
        all_strands = set()
        all_sub_strands = set()

        # Pass 1: Collect all possible dynamic columns
        for perf in performances:
            try:
                strand_scores = json.loads(perf.strand_scores or "[]")
            except Exception:
                strand_scores = []
            for strand in strand_scores:
                grade = strand.get("grade")
                if grade is not None:
                    all_grades.add(f"Grade-{grade}")
                all_strands.add(f"Strand-{strand['name']}")
                for skill in strand.get("bloom_skills", []):
                    all_skills.add(f"Skill-{skill['name']}")
                for sub in strand.get("sub_strands", []):
                    all_sub_strands.add(f"SubStrand-{sub['name']}")

        grades = sorted(all_grades)
        skills = sorted(all_skills)
        strands = sorted(all_strands)
        sub_strands = sorted(all_sub_strands)

        fixed_fields = [
            "id", "student_id", "student_name",
            "avg_score", "completion_rate", "class_avg_difference",
            "avg_expectation_level", "best_5_answer_ids", "worst_5_answer_ids"
        ]

        fieldnames = grades + skills + strands + sub_strands + fixed_fields

        rows = []

        for perf in performances:
            row = {}

            # Zero fill all dynamic columns
            for k in grades + skills + strands + sub_strands:
                row[k] = 0.0

            # Fixed fields
            row.update({
                "id": perf.id,
                "student_id": perf.session.student.id,
                "student_name": perf.session.student.name,
                "avg_score": perf.avg_score,
                "completion_rate": perf.completion_rate,
                "class_avg_difference": perf.class_avg_difference,
                "avg_expectation_level": perf.avg_expectation_level,
                "best_5_answer_ids": perf.best_5_answer_ids,
                "worst_5_answer_ids": perf.worst_5_answer_ids,
            })

            # Parse strand_scores
            try:
                strand_scores = json.loads(perf.strand_scores or "[]")
            except Exception:
                strand_scores = []

            # For grades
            grade_totals = defaultdict(float)
            skill_totals = defaultdict(float)
            sub_strand_totals = defaultdict(float)

            for strand in strand_scores:
                # Grade columns
                grade = strand.get("grade")
                if grade is not None:
                    grade_key = f"Grade-{grade}"
                    grade_totals[grade_key] += strand.get("percentage", 0.0)
                    row[grade_key] = grade_totals[grade_key]
                # Strand columns
                strand_key = f"Strand-{strand['name']}"
                row[strand_key] = strand.get("percentage", 0.0)
                # Skill columns (sum across all strands)
                for skill in strand.get("bloom_skills", []):
                    skill_key = f"Skill-{skill['name']}"
                    skill_totals[skill_key] += skill.get("percentage", 0.0)
                # Sub-strand columns
                for sub in strand.get("sub_strands", []):
                    sub_key = f"SubStrand-{sub['name']}"
                    sub_strand_totals[sub_key] += sub.get("percentage", 0.0)

            # Assign overall skill and sub-strand totals
            for skill_key in skills:
                row[skill_key] = skill_totals[skill_key]
            for sub_key in sub_strands:
                row[sub_key] = sub_strand_totals[sub_key]

            rows.append(row)

        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

        self.stdout.write(self.style.SUCCESS(
            f"Exported {len(rows)} rows to {output_file}"))
