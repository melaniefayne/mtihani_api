from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.status import *
from exam.models import StudentExamSessionAnswer
from permissions import IsTeacher
from rest_framework.response import Response


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsTeacher])
def edit_answer_score(request):
    try:
        answer_id = request.GET.get("answer_id")
        try:
            answer = StudentExamSessionAnswer.objects.select_related(
                'session').get(id=answer_id)
        except StudentExamSessionAnswer.DoesNotExist:
            return Response({"message": "Answer not found."}, status=HTTP_404_NOT_FOUND)

        if answer.session.status != "Complete":
            return Response(
                {"message": "This session is not complete yet. Scores cannot be updated."},
                status=HTTP_400_BAD_REQUEST
            )
        tr_score = request.data.get("tr_score")

        if tr_score is None:
            return Response({"message": "Missing teacher score field."}, status=HTTP_400_BAD_REQUEST)
        
        answer.tr_score = tr_score
        answer.save(update_fields=["tr_score", "updated_at"])

        return Response({"message": "Answer updated successfully."}, status=HTTP_200_OK)

    except Exception as e:
        print(f"Error updating answer: {e}")
        return Response({"message": "Something went wrong while updating the answer."}, status=HTTP_500_INTERNAL_SERVER_ERROR)
