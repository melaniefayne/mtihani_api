from django.contrib import admin
from django.utils import timezone
from .models import TeacherDocument, SubStrandReference


@admin.register(TeacherDocument)
class TeacherDocumentAdmin(admin.ModelAdmin):
    list_display = ('title', 'uploaded_by', 'uploaded_at',
                    'approved_for_rag', 'approved_at', 'approved_by', 'status', 'generation_error')
    list_filter = ('approved_for_rag', 'uploaded_by', 'extension')
    search_fields = ('title', 'description')
    readonly_fields = ('uploaded_at', 'uploaded_by',
                       'approved_at', 'approved_by')

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


@admin.register(SubStrandReference)
class SubStrandReferenceAdmin(admin.ModelAdmin):
    list_display = ('sub_strand', 'strand', 'reference_text', 'created_at')
    list_filter = ('strand',)
    search_fields = ('strand', 'sub_strand', 'reference_text')
    readonly_fields = ('created_at', 'last_updated')
    fieldsets = (
        (None, {
            'fields': ('strand', 'sub_strand', 'reference_text', 'created_from')
        }),
        ("Timestamps", {
            'fields': ('created_at', 'last_updated')
        })
    )
