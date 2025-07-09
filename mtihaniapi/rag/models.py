from django.db import models
from django.contrib.auth.models import User

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

    def save(self, *args, **kwargs):
        if self.file and not self.extension:
            name = self.file.name
            ext = name.split('.')[-1].lower()
            self.extension = ext
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title