from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from .models import BloomSkill, Strand, SubStrand, Skill, AssessmentRubric

@csrf_exempt
def upload_curriculum(request):
    if request.method == 'POST':
        data = json.loads(request.body)

        grade = data.get("grade")
        strands = data.get("strands", [])

        for strand_data in strands:
            strand, created = Strand.objects.get_or_create(
                name=strand_data["name"],
                number=strand_data["number"],
                grade=grade,
            )

            for ss in strand_data.get("sub_strands", []):
                sub_strand, created = SubStrand.objects.get_or_create(
                    strand=strand,
                    name=ss["name"],
                    number=ss["number"],
                    defaults={
                        "lesson_count": ss["lesson_count"],
                        "descriptions": ss["descriptions"],
                        "learning_outcomes": ss["learning_outcomes"],
                        "learning_experiences": ss["learning_experiences"],
                        "key_inquiries": ss["key_inquiries"],
                        "core_competencies": ss["core_competencies"],
                        "values": ss["values"],
                        "pertinent_issues": ss["pertinent_issues"],
                        "other_learning_areas": ss["other_learning_areas"],
                        "learning_materials": ss["learning_materials"],
                        "non_formal_activities": ss["non_formal_activities"]
                    }
                )

                for skill_data in ss.get("skills", []):
                    skill, created = Skill.objects.get_or_create(
                        sub_strand=sub_strand,
                        skill=skill_data["skill"]
                    )

                    for expectation, description in skill_data["rubrics"].items():
                        # We assume rubrics are always safe to re-create or update
                        AssessmentRubric.objects.update_or_create(
                            skill=skill,
                            expectation=expectation,
                            defaults={"description": description}
                        )

        return JsonResponse({"status": "success"}, status=201)

    return JsonResponse({"error": "Invalid method"}, status=405)

@csrf_exempt
def upload_bloom_skills(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        skills = data.get("skills", [])

        for skill in skills:
            BloomSkill.objects.update_or_create(
                name=skill["name"],
                description=skill["description"],
                examples=skill['examples']
            )

        return JsonResponse({"status": "success"}, status=201)

    return JsonResponse({"error": "Invalid method"}, status=405)
