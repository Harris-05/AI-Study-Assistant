import uuid

from django.db import models


def generate_lecture_id() -> str:
    """Short, URL-safe, filesystem-safe unique id -- doubles as the Chroma
    collection name and the on-disk folder name for this lecture's files."""
    return uuid.uuid4().hex[:12]


class Lecture(models.Model):
    STATUS_PENDING = "pending"
    STATUS_PROCESSING = "processing"
    STATUS_COMPLETED = "completed"
    STATUS_FAILED = "failed"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_PROCESSING, "Processing"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_FAILED, "Failed"),
    ]

    OUTPUT_LANGUAGE_CHOICES = [
        ("mixed", "Mixed"),
        ("urdu", "Urdu"),
        ("english", "English"),
        ("arabic", "Arabic"),
    ]

    lecture_id = models.SlugField(max_length=32, unique=True, default=generate_lecture_id, editable=False)

    title = models.CharField(max_length=255)
    course = models.CharField(max_length=255, blank=True)
    instructor = models.CharField(max_length=255, blank=True)
    semester = models.CharField(max_length=100, blank=True)
    lecture_date = models.DateField(null=True, blank=True)

    original_filename = models.CharField(max_length=255)
    stored_file_path = models.CharField(max_length=500, blank=True)
    duration_seconds = models.FloatField(null=True, blank=True)

    output_language = models.CharField(max_length=20, choices=OUTPUT_LANGUAGE_CHOICES, default="mixed")
    language_code_hint = models.CharField(max_length=10, blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    error_message = models.TextField(blank=True)
    num_chunks = models.PositiveIntegerField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} ({self.lecture_id})"
