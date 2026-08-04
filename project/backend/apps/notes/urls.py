from django.urls import path

from .views import LectureNotesExportView, LectureNotesListCreateView

urlpatterns = [
    path("<str:lecture_id>/notes/", LectureNotesListCreateView.as_view(), name="lecture-notes"),
    path("<str:lecture_id>/notes/<int:notes_id>/export/", LectureNotesExportView.as_view(), name="lecture-notes-export"),
]
