from django.http import JsonResponse
from permissions import IsAdmin
from .models import BloomSkill, Strand, SubStrand, Skill, AssessmentRubric
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdmin])
def upload_curriculum(request):
    data = request.data

    grade = data.get("grade")
    strands = data.get("strands", [])

    for strand_data in strands:
        strand, _ = Strand.objects.update_or_create(
            grade=grade,
            number=strand_data["number"],
            defaults={"name": strand_data["name"]}
        )

        for ss in strand_data.get("sub_strands", []):
            sub_strand, _ = SubStrand.objects.update_or_create(
                strand=strand,
                number=ss["number"],
                defaults={
                    "name": ss["name"],
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
                skill, _ = Skill.objects.update_or_create(
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


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdmin])
def upload_bloom_skills(request):
    data = request.data
    bloom_skills = data.get("bloom_skills", [])

    for bloom_skill in bloom_skills:
        BloomSkill.objects.update_or_create(
        name=bloom_skill["name"],
        defaults={
            "description": bloom_skill["description"],
            "examples": bloom_skill["examples"]
        }
    )


    return JsonResponse({"status": "success"}, status=201)


# @api_view(['GET'])
# @permission_classes([IsAuthenticated, CanViewCBC])
# def get_strands(request):
#     strands = Strand.objects.all()
#     serializer = StrandSerializer(strands, many=True)
#     return Response(serializer.data)