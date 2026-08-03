from django.contrib import admin

from .models import ChatMessage


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ("lecture", "question", "created_at")
    search_fields = ("question", "answer")
    readonly_fields = ("created_at",)
