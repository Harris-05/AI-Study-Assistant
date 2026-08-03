from django.contrib import admin

from .models import Quiz


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ("lecture", "num_mcq", "num_short", "num_long", "created_at")
    readonly_fields = ("created_at",)
