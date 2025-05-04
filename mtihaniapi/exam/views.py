from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.status import *
from gen.curriculum import get_exam_curriculum
from gen.utils import generate_llm_question_list
from permissions import IsTeacher
from rest_framework.response import Response
import json
from typing import List, Dict, Any


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsTeacher])
def create_exam(request) -> Response:
    try:
        strand_ids = request.data.get("strand_ids", [])
        question_count = request.data.get("question_count", 25)

        # Build the curriculum-based breakdown for the LLM
        question_brd = get_exam_curriculum(
            strand_ids=strand_ids, question_count=question_count)

        try:
            exam_items = generate_llm_question_list(input_data=question_brd)
            # Check if it's a list of dicts with expected key
            if not isinstance(exam_items, list):
                return Response({
                    "message": "LLM response structure is invalid.",
                    "raw": exam_items
                }, status=HTTP_400_BAD_REQUEST)

            # Proceed with formatting
            response_data = []
            for i, item in enumerate(question_brd):
                if i >= len(exam_items):
                    break
                response_data.append({
                    "number": item.get("number"),
                    "grade": item.get("grade"),
                    "strand": item.get("strand"),
                    "sub_strand": item.get("sub_strand"),
                    "bloom_skills": item.get("bloom_skills"),
                    "questions": exam_items[i].get("questions", []),
                    "answers": exam_items[i].get("expected_answers", []),
                })

            return Response(response_data, status=HTTP_200_OK)

        except Exception as e:
            return Response({"message": f"LLM generation failed: {str(e)}"}, status=HTTP_400_BAD_REQUEST)

    except Exception as e:
        print(f"Error: {e}")
        return Response({"message": "Something went wrong on our side :( Please try again later."}, status=HTTP_500_INTERNAL_SERVER_ERROR)
