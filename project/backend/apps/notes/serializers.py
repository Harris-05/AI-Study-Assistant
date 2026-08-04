from rest_framework import serializers

from .models import Notes


class NotesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notes
        fields = ["id", "num_sections", "num_key_terms", "data", "created_at"]
        read_only_fields = fields
