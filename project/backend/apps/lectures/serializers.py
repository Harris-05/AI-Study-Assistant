from rest_framework import serializers

from .models import Lecture
from .validators import validate_upload_file


class LectureSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lecture
        fields = [
            "lecture_id", "title", "course", "instructor", "semester", "lecture_date",
            "original_filename", "duration_seconds", "output_language", "language_code_hint",
            "status", "error_message", "num_chunks", "created_at", "updated_at",
        ]
        read_only_fields = fields


class LectureCreateSerializer(serializers.Serializer):
    file = serializers.FileField()
    title = serializers.CharField(max_length=255)
    course = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")
    instructor = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")
    semester = serializers.CharField(max_length=100, required=False, allow_blank=True, default="")
    lecture_date = serializers.DateField(required=False, allow_null=True, default=None)
    output_language = serializers.ChoiceField(
        choices=["mixed", "urdu", "english", "arabic"], required=False, default="mixed"
    )
    language_code_hint = serializers.CharField(max_length=10, required=False, allow_blank=True, default="")

    def validate_file(self, value):
        validate_upload_file(value)
        return value
