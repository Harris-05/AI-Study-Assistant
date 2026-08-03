from django.urls import path

from .views import LectureChatView

urlpatterns = [
    path("<str:lecture_id>/chat/", LectureChatView.as_view(), name="lecture-chat"),
]
