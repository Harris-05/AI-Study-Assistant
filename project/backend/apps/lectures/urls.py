from django.urls import path

from .views import LectureDetailView, LectureListCreateView, LectureTranscriptView

urlpatterns = [
    path("", LectureListCreateView.as_view(), name="lecture-list-create"),
    path("<str:lecture_id>/", LectureDetailView.as_view(), name="lecture-detail"),
    path("<str:lecture_id>/transcript/", LectureTranscriptView.as_view(), name="lecture-transcript"),
]
