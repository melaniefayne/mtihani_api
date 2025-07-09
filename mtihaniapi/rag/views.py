from django.shortcuts import render
from rest_framework.status import *
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rag.serializers import TeacherDocumentSerializer
from rag.models import TeacherDocument
from permissions import IsAdmin, IsTeacherOrAdmin
from rest_framework.response import Response
from django.utils import timezone


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsTeacherOrAdmin])
def upload_teacher_document(request):
    try:
        file = request.FILES.get('file')
        title = request.data.get('title')
        description = request.data.get('description', '')

        if not file or not title:
            return Response({"message": "File and title are required."}, status=HTTP_400_BAD_REQUEST)

        doc = TeacherDocument.objects.create(
            title=title,
            description=description,
            file=file,
            uploaded_by=request.user
        )

        return Response({"message": "Document uploaded successfully."}, status=HTTP_201_CREATED)

    except Exception as e:
        print(f"Error uploading document: {e}")
        return Response({"message": "Something went wrong while uploading the document."}, status=HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsTeacherOrAdmin])
def list_teacher_documents(request):
    try:
        mine = request.GET.get('mine') == 'true'
        approved = request.GET.get('approved') == 'true'

        docs = TeacherDocument.objects.all()
        if mine:
            docs = docs.filter(uploaded_by=request.user)
        if approved:
            docs = docs.filter(approved_for_rag=True)

        return Response({
            "documents": TeacherDocumentSerializer(docs, many=True).data
        }, status=HTTP_200_OK)

    except Exception as e:
        print(f"Error listing documents: {e}")
        return Response({"message": "Something went wrong while fetching documents."}, status=HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsTeacherOrAdmin])
def delete_teacher_document(request):
    try:
        doc_id = request.GET.get("doc_id")
        try:
            doc = TeacherDocument.objects.get(id=doc_id)
        except TeacherDocument.DoesNotExist:
            return Response({"message": "Document not found."}, status=HTTP_404_NOT_FOUND)

        if doc.uploaded_by != request.user:
            return Response({"message": "You can only delete your own documents."}, status=HTTP_403_FORBIDDEN)

        doc.delete()
        return Response({"message": "Document deleted successfully."}, status=HTTP_200_OK)

    except Exception as e:
        print(f"Error deleting document: {e}")
        return Response({"message": "Something went wrong while deleting the document."}, status=HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdmin])
def approve_teacher_document(request):
    doc_id = request.GET.get("doc_id")

    if not request.user.is_staff:
        return Response({"message": "Only admins can approve documents."}, status=HTTP_403_FORBIDDEN)

    try:
        try:
            doc = TeacherDocument.objects.get(id=doc_id)
        except TeacherDocument.DoesNotExist:
            return Response({"message": "Document not found."}, status=HTTP_404_NOT_FOUND)

        if doc.approved_for_rag:
            return Response({"message": "Document already approved."}, status=HTTP_400_BAD_REQUEST)

        doc.approved_for_rag = True
        doc.approved_by = request.user
        doc.approved_at = timezone.now()
        doc.save()

        return Response({"message": "Document approved for RAG."}, status=HTTP_200_OK)

    except Exception as e:
        print(f"Error approving document: {e}")
        return Response({"message": "Something went wrong while approving the document."}, status=HTTP_500_INTERNAL_SERVER_ERROR)
