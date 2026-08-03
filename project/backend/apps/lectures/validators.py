from pathlib import Path

from django.conf import settings
from rest_framework.exceptions import ValidationError


def validate_upload_file(uploaded_file) -> None:
    """Extension whitelist + size cap, enforced before we ever touch ffmpeg
    or spend money on a transcription API call."""
    ext = Path(uploaded_file.name).suffix.lower()
    if ext not in settings.ALLOWED_UPLOAD_EXTENSIONS:
        raise ValidationError(
            f"Unsupported file type '{ext}'. Allowed: "
            f"{', '.join(sorted(settings.ALLOWED_UPLOAD_EXTENSIONS))}"
        )

    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if uploaded_file.size > max_bytes:
        raise ValidationError(
            f"File too large ({uploaded_file.size / 1024 / 1024:.1f}MB). "
            f"Max allowed is {settings.MAX_UPLOAD_SIZE_MB}MB on this deployment."
        )
