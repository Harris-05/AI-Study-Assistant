from rest_framework import serializers

from .models import Quiz


class QuizSerializer(serializers.ModelSerializer):
    class Meta:
        model = Quiz
        fields = ["id", "num_mcq", "num_short", "num_long", "data", "created_at"]
        read_only_fields = fields


class QuizGenerateSerializer(serializers.Serializer):
    num_mcq = serializers.IntegerField(min_value=0, max_value=50, required=False)
    num_short = serializers.IntegerField(min_value=0, max_value=30, required=False)
    num_long = serializers.IntegerField(min_value=0, max_value=15, required=False)
