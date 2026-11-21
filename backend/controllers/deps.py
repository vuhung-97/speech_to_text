"""FastAPI dependencies: expose the services created in the app lifespan."""

from __future__ import annotations

import re
from typing import Annotated

from fastapi import Depends, Header, Request

from ..adapters.storage.sqlite import SqliteAuditLog, SqliteSessionRepository
from ..config.settings import Settings
from ..ports.faq import FaqOutlineParser, QueryLog
from ..services.audio_sessions import AudioSessionHub
from ..services.event_service import EventBus
from ..services.faq_audio_service import FaqAudioService
from ..services.faq_documents import FaqDocumentsService
from ..services.faq_service import FaqService
from ..services.qa_service import QaService
from ..services.replay_service import ReplayService
from ..services.transcription_service import LivePipeline
from ..services.tts_service import TtsService
from ..utils.errors import ApiError

DEFAULT_TENANT = "local"
_TENANT_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")


def get_pipeline(request: Request) -> LivePipeline:
    return request.app.state.pipeline


def get_settings_store(request: Request) -> Settings:
    return request.app.state.settings


def get_replay(request: Request) -> ReplayService:
    return request.app.state.replay


def get_bus(request: Request) -> EventBus:
    return request.app.state.bus


def get_tts(request: Request) -> TtsService:
    return request.app.state.tts


def get_qa(request: Request) -> QaService:
    return request.app.state.qa


def get_sessions(request: Request) -> SqliteSessionRepository:
    return request.app.state.sessions


def get_query_log(request: Request) -> QueryLog:
    return request.app.state.query_log


def get_faq_service(request: Request) -> FaqService:
    return request.app.state.faq_service


def get_faq_audio(request: Request) -> FaqAudioService:
    return request.app.state.faq_audio


def get_faq_documents(request: Request) -> FaqDocumentsService:
    return request.app.state.faq_documents


def get_outline_parser(request: Request) -> FaqOutlineParser:
    return request.app.state.outline_parser


def get_audit(request: Request) -> SqliteAuditLog:
    return request.app.state.audit


def get_audio_hub(request: Request) -> AudioSessionHub:
    return request.app.state.audio_hub


def current_tenant(
    x_workspace: str | None = Header(default=None, alias="X-Workspace"),
) -> str:
    """Resolve the tenant from the request, defaulting to the local workspace.

    The header is a UX hint, never an authorisation claim: once real accounts
    exist this dependency must resolve the tenant from the authenticated
    identity and ignore the header value.
    """
    value = (x_workspace or DEFAULT_TENANT).strip().lower()
    if not _TENANT_RE.match(value):
        raise ApiError("workspace không hợp lệ", status_code=400)
    return value


PipelineDep = Annotated[LivePipeline, Depends(get_pipeline)]
SettingsDep = Annotated[Settings, Depends(get_settings_store)]
ReplayDep = Annotated[ReplayService, Depends(get_replay)]
BusDep = Annotated[EventBus, Depends(get_bus)]
TtsDep = Annotated[TtsService, Depends(get_tts)]
TenantDep = Annotated[str, Depends(current_tenant)]
QaDep = Annotated[QaService, Depends(get_qa)]
SessionsRepoDep = Annotated[SqliteSessionRepository, Depends(get_sessions)]
QueryLogDep = Annotated[QueryLog, Depends(get_query_log)]
FaqServiceDep = Annotated[FaqService, Depends(get_faq_service)]
FaqAudioDep = Annotated[FaqAudioService, Depends(get_faq_audio)]
FaqDocumentsDep = Annotated[FaqDocumentsService, Depends(get_faq_documents)]
OutlineParserDep = Annotated[FaqOutlineParser, Depends(get_outline_parser)]
AuditDep = Annotated[SqliteAuditLog, Depends(get_audit)]
AudioHubDep = Annotated[AudioSessionHub, Depends(get_audio_hub)]
