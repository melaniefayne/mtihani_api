from django.db import models
from django.contrib.auth.models import User

DOC_CHUNK_STATUSES = [
    ("Unapproved", "Unapproved"),
    ("Chunking", "Chunking"),
    ("Success", "Success"),
    ("Failed", "Failed"),
]

class TeacherDocument(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    file = models.FileField(upload_to='teacher_documents/')
    extension = models.CharField(max_length=10, blank=True)  # NEW FIELD
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='uploaded_documents')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    approved_for_rag = models.BooleanField(default=False)
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='approved_documents')
    # 
    status = models.CharField(
        max_length=25, choices=DOC_CHUNK_STATUSES, default="Unapproved")
    is_chunking = models.BooleanField(default=False)
    generation_error = models.TextField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if self.file and not self.extension:
            name = self.file.name
            ext = name.split('.')[-1].lower()
            self.extension = ext
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title
    
    def update_to_chunking(self):
        self.status = "Chunking"
        self.is_chunking = True
        self.save(update_fields=["status", "is_chunking"])

    def update_to_success(self):
        self.status = "Success"
        self.is_chunking = False
        self.generation_error = ""
        self.save(update_fields=["status", "is_chunking", "generation_error"])
    

class SubStrandReference(models.Model):
    strand = models.CharField(max_length=100)
    sub_strand = models.CharField(max_length=100, unique=True)
    reference_text = models.TextField(
        help_text="Paste in sample questions, model answers, key facts, etc., aligned to this CBC sub-strand.")
    created_from = models.ForeignKey(
        TeacherDocument, null=True, blank=True, on_delete=models.SET_NULL, related_name='created_references')
    created_at = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.strand} - {self.sub_strand}"