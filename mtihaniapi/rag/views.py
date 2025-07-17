from celery import shared_task
from rest_framework.status import *
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rag.utils import *
from rag.serializers import TeacherDocumentSerializer
from rag.models import TeacherDocument, SubStrandReference
from permissions import IsAdmin, IsTeacherOrAdmin
from rest_framework.response import Response
from django.utils import timezone
from gen.curriculum import get_strand_sub_strand_pairs
from gen.utils import generate_llm_strand_context_list


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsTeacherOrAdmin])
def upload_teacher_document(request):
    try:
        file = request.FILES.get('file')
        title = request.data.get('title')
        description = request.data.get('description', '')

        if not file or not title:
            return Response({"message": "File and title are required."}, status=HTTP_400_BAD_REQUEST)

        TeacherDocument.objects.create(
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
        approved_param = request.GET.get('approved')

        docs = TeacherDocument.objects.all()
        if mine:
            docs = docs.filter(uploaded_by=request.user)

        if approved_param == 'true':
            docs = docs.filter(approved_for_rag=True)
        elif approved_param == 'false':
            docs = docs.filter(approved_for_rag=False)

        return Response({
            "documents": TeacherDocumentSerializer(docs, many=True, context={'request': request}).data
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

        # Delete the file from storage first
        if doc.file:
            doc.file.delete(save=False)
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

        if doc.approved_for_rag and doc.status == "Success":
            return Response({"message": "Document already approved."}, status=HTTP_400_BAD_REQUEST)

        doc.approved_for_rag = True
        doc.approved_by = request.user
        doc.approved_at = timezone.now()
        doc.save()

        # Trigger background task
        generate_doc_samples.delay(doc.id)

        return Response({"message": "Document approved for RAG."}, status=HTTP_200_OK)

    except Exception as e:
        print(f"Error approving document: {e}")
        return Response({"message": "Something went wrong while approving the document."}, status=HTTP_500_INTERNAL_SERVER_ERROR)


# ==================================================================== RAG

# =============================================
# ==========ANY CHANGE TO THIS=================
# =======!!!!RESTART CELERY!!!=================
# =============================================

@shared_task
def generate_doc_samples(doc_id):
    try:
        doc = TeacherDocument.objects.get(id=doc_id)
        doc.update_to_chunking()

        cbc_data = get_strand_sub_strand_pairs()
        doc_text = extract_text_from_file(doc)
        extract_res = generate_llm_strand_context_list(
            cbc_data=cbc_data,
            reference_text=doc_text
        )

        if not isinstance(extract_res, list):
            doc.status = "Failed"
            doc.generation_error = extract_res.get(
                "error", "Unknown LLM error")
            doc.save()
            return
        
        for ref in extract_res:
            sub_strand = ref.get("sub_strand")
            strand = ref.get("strand")
            samples = ref.get("samples", [])

            if not samples:
                continue

            new_text = samples_to_text(samples)

            try:
                obj = SubStrandReference.objects.get(sub_strand=sub_strand)
                combined_text = (obj.reference_text or "") + "\n\n" + new_text
                obj.reference_text = deduplicate_by_question(combined_text)
                obj.last_updated = timezone.now()
                obj.save()
            except SubStrandReference.DoesNotExist:
                SubStrandReference.objects.create(
                    strand=strand,
                    sub_strand=sub_strand,
                    reference_text=new_text,
                    created_from=doc,
                )
                
        doc.update_to_success()

    except Exception as e:
        doc.status = "Failed"
        doc.generation_error = f"Unexpected error: {str(e)}"
        doc.save()
        print(f"Background Sample Generation failed for Doc ID {doc.id}: {e}")


