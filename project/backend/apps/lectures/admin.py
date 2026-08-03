from django.contrib import admin

from .models import Lecture


@admin.register(Lecture)
class LectureAdmin(admin.ModelAdmin):
    list_display = ("title", "lecture_id", "status", "duration_seconds", "num_chunks", "created_at")
    list_filter = ("status", "output_language")
    search_fields = ("title", "lecture_id", "course", "instructor")
    readonly_fields = ("lecture_id", "created_at", "updated_at")
