import json
import csv
from django.db.models import Avg
from django.core.management.base import BaseCommand
from exam.models import StudentExamSessionPerformance, StudentExamSessionAnswer
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PERFORMANCE_OUTPUT_FILE = os.path.join(BASE_DIR, "output", "performance_list.csv")
SKILL_STRAND_OUTPUT_FILE = os.path.join(BASE_DIR, "output", "performance_strand_skills_list.csv")

class Command(BaseCommand):
    help = "Export detailed student performance for a given exam."

    def add_arguments(self, parser):
        parser.add_argument("exam_id", type=int)
        parser.add_argument("--output", type=str, default=PERFORMANCE_OUTPUT_FILE)

    def handle(self, *args, **options):
        exam_id = options["exam_id"]
        output_file = options["output"]

        performances = StudentExamSessionPerformance.objects.filter(session__exam__id=exam_id)

        if not performances.exists():
            self.stdout.write(self.style.ERROR("No student performances found for this exam."))
            return

        # Gather all dynamic fields
        all_bloom_skills = set()
        all_grades = set()
        all_strands = set()
        all_sub_strands = set()

        for perf in performances:
            all_bloom_skills.update(entry["name"] for entry in json.loads(perf.bloom_skill_scores or "[]"))
            all_grades.update(entry["name"] for entry in json.loads(perf.grade_scores or "[]"))
            all_strands.update(entry["name"] for entry in json.loads(perf.strand_scores or "[]"))
            all_sub_strands.update(entry["name"] for entry in json.loads(perf.sub_strand_scores or "[]"))

        bloom_skills = sorted(f"Skill-{s}" for s in all_bloom_skills)
        grades = sorted(f"Grade-{g}" for g in all_grades)
        strands = sorted(f"Strand-{s}" for s in all_strands)
        sub_strands = sorted(f"SubStrand-{s}" for s in all_sub_strands)


        # Build CSV structure
        fieldnames = [
            "id", "student_id", "student_name",
            "avg_score", "completion_rate", "class_avg_difference",
            "avg_expectation_level"
        ] + bloom_skills + grades + strands + sub_strands + [
            "best_5_question_ids", "worst_5_question_ids"
        ]

        rows = []

        for perf in performances:
            row = {
                "id": perf.id,
                "student_id": perf.session.student.id,
                "student_name": perf.session.student.name,
                "avg_score": perf.avg_score,
                "completion_rate": perf.completion_rate,
                "class_avg_difference": perf.class_avg_difference,
                "avg_expectation_level": perf.avg_expectation_level,
                "best_5_question_ids": perf.best_5_question_ids,
                "worst_5_question_ids": perf.worst_5_question_ids,
            }

            # Bloom scores
            bloom_map = {f"Skill-{entry['name']}": entry["percentage"] for entry in json.loads(perf.bloom_skill_scores or "[]")}
            for skill in bloom_skills:
                row[skill] = bloom_map.get(skill, 0.0)

            # Grade scores
            grade_map = {f"Grade-{entry['name']}": entry["percentage"] for entry in json.loads(perf.grade_scores or "[]")}
            for g in grades:
                row[g] = grade_map.get(g, 0.0)

            # Strand scores
            strand_map = {f"Strand-{entry['name']}": entry["percentage"] for entry in json.loads(perf.strand_scores or "[]")}
            for s in strands:
                row[s] = strand_map.get(s, 0.0)

            # Sub-strand scores
            sub_map = {f"SubStrand-{entry['name']}": entry["percentage"] for entry in json.loads(perf.sub_strand_scores or "[]")}
            for s in sub_strands:
                row[s] = sub_map.get(s, 0.0)

            rows.append(row)

        with open(output_file, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

        self.stdout.write(self.style.SUCCESS(f"Exported {len(rows)} rows to {output_file}"))


        
        # export_bloom_skill_per_strand
        strand_skill_output_file = SKILL_STRAND_OUTPUT_FILE
        answers = StudentExamSessionAnswer.objects.filter(session__exam__id=exam_id)

        results = answers.values("question__strand", "question__bloom_skill").annotate(
            avg_score=Avg("score")
        ).order_by("question__strand", "question__bloom_skill")

        with open(strand_skill_output_file, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["strand", "bloom_skill", "avg_score"])
            writer.writeheader()

            for row in results:
                writer.writerow({
                    "strand": row["question__strand"],
                    "bloom_skill": row["question__bloom_skill"],
                    "avg_score": round(row["avg_score"] or 0.0, 2)
                })

        self.stdout.write(self.style.SUCCESS(f"Exported {len(results)} rows to {strand_skill_output_file}"))