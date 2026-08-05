"""Tests for lecture access control, upload validation and the model.

Deliberately scoped to things that need no network: no Supabase, no Groq, no
Gemini, no ffmpeg. CI must be able to run these on a clean machine with only
requirements.txt installed.
"""
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.exceptions import ValidationError

from .models import Lecture
from .validators import validate_upload_file


class LectureAccessControlTests(TestCase):
    """The API is authenticated by default. If that ever silently breaks,
    every user's lectures become readable by anyone -- so it gets a test."""

    URL = "/api/lectures/"

    def test_anonymous_request_is_refused(self):
        response = self.client.get(self.URL)
        # 401 or 403 depending on whether DRF emits a WWW-Authenticate
        # header; both mean "refused". What matters is that it is not 200.
        self.assertIn(response.status_code, (401, 403))

    def test_anonymous_request_returns_no_lecture_data(self):
        self.assertNotIn("results", self.client.get(self.URL).json())

    def test_errors_use_the_shared_response_envelope(self):
        # apps/common/exceptions.py normalises every error to this shape so
        # the frontend can handle failures generically.
        body = self.client.get(self.URL).json()
        self.assertIn("error", body)
        self.assertIn("code", body["error"])
        self.assertIn("message", body["error"])


class UploadValidatorTests(TestCase):
    """Guards that run before ffmpeg or any paid API call is touched."""

    def _upload(self, name, size_mb=1):
        upload = SimpleUploadedFile(name, b"placeholder")
        upload.size = int(size_mb * 1024 * 1024)
        return upload

    def test_accepts_a_supported_audio_file(self):
        validate_upload_file(self._upload("lecture.mp3"))

    def test_accepts_a_supported_video_file(self):
        validate_upload_file(self._upload("lecture.mp4"))

    def test_extension_matching_is_case_insensitive(self):
        validate_upload_file(self._upload("LECTURE.MP3"))

    def test_rejects_an_unsupported_extension(self):
        with self.assertRaises(ValidationError):
            validate_upload_file(self._upload("malware.exe"))

    def test_rejects_a_file_with_no_extension(self):
        with self.assertRaises(ValidationError):
            validate_upload_file(self._upload("lecture"))

    def test_rejects_a_file_over_the_size_limit(self):
        oversize = settings.MAX_UPLOAD_SIZE_MB + 1
        with self.assertRaises(ValidationError):
            validate_upload_file(self._upload("lecture.mp3", size_mb=oversize))

    def test_accepts_a_file_exactly_at_the_size_limit(self):
        # Boundary case: the limit is inclusive.
        validate_upload_file(
            self._upload("lecture.mp3", size_mb=settings.MAX_UPLOAD_SIZE_MB)
        )


class LectureModelTests(TestCase):
    """Also serves as a migration smoke test -- these fail if the migrations
    do not apply cleanly to an empty database."""

    def _lecture(self, title="Test lecture"):
        return Lecture.objects.create(title=title, original_filename="lecture.mp3")

    def test_lecture_id_is_generated_automatically(self):
        self.assertEqual(len(self._lecture().lecture_id), 12)

    def test_lecture_ids_are_unique(self):
        self.assertNotEqual(self._lecture().lecture_id, self._lecture().lecture_id)

    def test_new_lectures_start_pending(self):
        self.assertEqual(self._lecture().status, Lecture.STATUS_PENDING)

    def test_default_output_language_is_mixed(self):
        self.assertEqual(self._lecture().output_language, "mixed")

    def test_str_includes_title_and_id(self):
        lecture = self._lecture(title="Week 1")
        self.assertIn("Week 1", str(lecture))
        self.assertIn(lecture.lecture_id, str(lecture))
