"""
Single place where the standalone `pipeline/` package (unchanged from the
CLI project) is imported from.

pipeline/*.py use flat imports by design (`import config`, not
`from pipeline import config`) -- see pipeline/README.md's note that they
must be run from inside pipeline/. core.settings adds pipeline/ to
sys.path at import time (before any app loads), so these flat imports
resolve correctly here.

Import pipeline functionality from THIS module elsewhere in the Django
code (`from apps.common.pipeline_bridge import pipeline_chat`, etc.), not
via a direct `import chat` / `import quiz` -- keeps the sys.path dependency
in one place, and avoids confusion with the Django apps.chat / apps.quiz
packages which share the same short names.
"""
import config as pipeline_config
import audio_extractor
import transcriber
import cleaner
import chunker
import vectorstore
import chat as pipeline_chat
import quiz as pipeline_quiz
import main as pipeline_main

__all__ = [
    "pipeline_config",
    "audio_extractor",
    "transcriber",
    "cleaner",
    "chunker",
    "vectorstore",
    "pipeline_chat",
    "pipeline_quiz",
    "pipeline_main",
]
