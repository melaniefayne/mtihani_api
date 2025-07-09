from django.contrib import admin
from django.utils import timezone
from .models import TeacherDocument

@admin.register(TeacherDocument)
class TeacherDocumentAdmin(admin.ModelAdmin):
    list_display = ('title', 'uploaded_by', 'uploaded_at', 'approved_for_rag', 'approved_at', 'approved_by')
    list_filter = ('approved_for_rag', 'uploaded_by', 'extension')
    search_fields = ('title', 'description')
    readonly_fields = ('uploaded_at', 'uploaded_by', 'approved_at', 'approved_by')

    actions = ['approve_selected_documents']

    def approve_selected_documents(self, request, queryset):
        for doc in queryset:
            if not doc.approved_for_rag:
                doc.approved_for_rag = True
                doc.approved_by = request.user
                doc.approved_at = timezone.now()
                doc.save()
        self.message_user(request, f"Approved {queryset.count()} document(s).")

    approve_selected_documents.short_description = "Approve selected documents for RAG"