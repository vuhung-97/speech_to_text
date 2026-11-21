"""Text-to-speech internals: engine loader, voice catalog, job store.

``backend.services.tts_service`` stays the public facade; nothing outside this
package should import these modules directly.
"""

from .errors import TtsBusy, TtsCancelled, TtsStorageError, TtsUnavailable
from .job_store import SpeechJob, TtsJobStore
from .voice_catalog import VoiceCatalog

__all__ = [
    "SpeechJob",
    "TtsBusy",
    "TtsCancelled",
    "TtsJobStore",
    "TtsStorageError",
    "TtsUnavailable",
    "VoiceCatalog",
]
