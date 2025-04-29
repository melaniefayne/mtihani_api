from django.http import JsonResponse
from permissions import IsAdmin
from .models import BloomSkill, Strand, SubStrand, Skill, AssessmentRubric
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from learner.models import Student
from django.db.models import Q


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


def build_curriculum_queryset(grades=None, search=None):
    grades = grades or Strand.objects.values_list('grade', flat=True).distinct().order_by('grade')
    curriculum = []

    for grade in grades:
        strands = Strand.objects.filter(grade=grade).order_by('number')

        if search:
            strands = strands.filter(
                Q(name__icontains=search) |
                Q(sub_strands__name__icontains=search)
            ).distinct()

        strand_data = []

        for strand in strands:
            sub_strands = strand.sub_strands.all().order_by('number')

            if search:
                sub_strands = sub_strands.filter(name__icontains=search)

            sub_strand_data = []

            for ss in sub_strands:
                skills = ss.skills.all()
                skill_data = []

                for skill in skills:
                    rubrics = skill.rubrics.all().values('expectation', 'description')
                    skill_data.append({
                        "id": skill.id,
                        "skill": skill.skill,
                        "rubrics": list(rubrics)
                    })

                sub_strand_data.append({
                    "id": ss.id,
                    "name": ss.name,
                    "number": ss.number,
                    "lesson_count": ss.lesson_count,
                    "key_inquiries": ss.key_inquiries,
                    "learning_outcomes": ss.learning_outcomes,
                    "learning_experiences": ss.learning_experiences,
                    "descriptions": ss.descriptions,
                    "core_competencies": ss.core_competencies,
                    "values": ss.values,
                    "pertinent_issues": ss.pertinent_issues,
                    "other_learning_areas": ss.other_learning_areas,
                    "learning_materials": ss.learning_materials,
                    "non_formal_activities": ss.non_formal_activities,
                    "skills": skill_data
                })

            if sub_strand_data:
                strand_data.append({
                    "id": strand.id,
                    "grade": strand.grade,
                    "name": strand.name,
                    "number": strand.number,
                    "sub_strands": sub_strand_data
                })

        if strand_data:
            curriculum.append({
                "grade": grade,
                "strands": strand_data
            })

    return curriculum


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def full_curriculum(request):
    search = request.GET.get('search', '').lower()
    grade_filter = request.GET.get('grade')

    grade_filter_list = grade_filter.split(',') if grade_filter else None
    curriculum = build_curriculum_queryset(grades=grade_filter_list, search=search)

    return Response(curriculum, status=200)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def cbc_my_grade(request):
    try:
        student = Student.objects.select_related('classroom').get(user=request.user)
    except Student.DoesNotExist:
        return Response({"error": "Student profile not found."}, status=404)

    current_grade = student.classroom.grade
    relevant_grades = relevant_grades = list(range(7, current_grade + 1))

    search = request.GET.get('search', '').lower()
    curriculum = build_curriculum_queryset(grades=relevant_grades, search=search)

    return Response(curriculum, status=200)