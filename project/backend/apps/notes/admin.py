from django.contrib import admin

from .models import Notes


@admin.register(Notes)
class NotesAdmin(admin.ModelAdmin):
    list_display = ("lecture", "num_sections", "num_key_terms", "created_at")
    readonly_fields = ("created_at",)
