from django.urls import path

from .views import LectureQuizExportView, LectureQuizListCreateView

urlpatterns = [
    path("<str:lecture_id>/quiz/", LectureQuizListCreateView.as_view(), name="lecture-quiz"),
    path("<str:lecture_id>/quiz/<int:quiz_id>/export/", LectureQuizExportView.as_view(), name="lecture-quiz-export"),
]
