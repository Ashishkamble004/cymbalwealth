from functools import lru_cache

from google import genai
from google.cloud import storage

from app.ai.gemini import GeminiService
from app.ai.gemini_image import GeminiImageService
from app.ai.imagen import ImagenService
from app.ai.veo import VeoService
from app.config import Settings
from app.config import get_settings as _get_settings
from app.db import Database
from app.jobs.events import SSEBroadcaster
from app.jobs.runner import TaskRunner
from app.jobs.store import JobStore
from app.services.avatar_service import AvatarService
from app.services.bulk_service import BulkService
from app.services.input_service import InputService
from app.services.log_service import LogService
from app.services.pipeline_service import PipelineService
from app.services.qc_service import QCService
from app.services.review_service import ReviewService
from app.services.script_service import ScriptService
from app.services.stitch_service import StitchService
from app.services.storyboard_service import StoryboardService
from app.services.video_service import VideoService
from app.storage.gcs import GCSStorage
from app.storage.local import LocalStorage


def get_settings() -> Settings:
    return _get_settings()


@lru_cache
def get_genai_client() -> genai.Client:
    settings = get_settings()
    return genai.Client(
        vertexai=True,
        project=settings.project_id,
        location=settings.region,
    )


@lru_cache
def get_genai_image_client() -> genai.Client:
    """Separate client for image generation — uses image_region (default: global)."""
    settings = get_settings()
    return genai.Client(
        vertexai=True,
        project=settings.project_id,
        location=settings.image_region,
    )


@lru_cache
def get_genai_text_client() -> genai.Client:
    """Separate client for Gemini text models — uses text_region (default: global)."""
    settings = get_settings()
    return genai.Client(
        vertexai=True,
        project=settings.project_id,
        location=settings.text_region,
    )


@lru_cache
def get_storage_client() -> storage.Client:
    settings = get_settings()
    return storage.Client(project=settings.project_id)


# ---------------------------------------------------------------------------
# Singletons for job infrastructure
# ---------------------------------------------------------------------------


@lru_cache
def get_database() -> Database:
    return Database()


@lru_cache
def get_job_store() -> JobStore:
    return JobStore(db=get_database())


@lru_cache
def get_broadcaster() -> SSEBroadcaster:
    return SSEBroadcaster()


@lru_cache
def get_task_runner() -> TaskRunner:
    return TaskRunner()


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------

@lru_cache
def get_local_storage() -> LocalStorage:
    settings = get_settings()
    return LocalStorage(base_dir=settings.output_dir)


@lru_cache
def get_gcs_storage() -> GCSStorage:
    settings = get_settings()
    return GCSStorage(
        bucket_name=settings.gcs_bucket_name,
        project_id=settings.project_id,
    )


# ---------------------------------------------------------------------------
# AI services
# ---------------------------------------------------------------------------

@lru_cache
def get_gemini_service() -> GeminiService:
    return GeminiService(client=get_genai_text_client(), settings=get_settings())


@lru_cache
def get_gemini_image_service() -> GeminiImageService:
    return GeminiImageService(client=get_genai_image_client(), settings=get_settings())


@lru_cache
def get_imagen_service() -> ImagenService:
    return ImagenService(client=get_genai_client(), settings=get_settings())


@lru_cache
def get_veo_service() -> VeoService:
    return VeoService(client=get_genai_client(), settings=get_settings())


# ---------------------------------------------------------------------------
# Application services
# ---------------------------------------------------------------------------

@lru_cache
def get_input_service() -> InputService:
    return InputService(
        gemini=get_gemini_service(),
        gemini_image=get_gemini_image_service(),
        storage=get_local_storage(),
        settings=get_settings(),
    )


@lru_cache
def get_qc_service() -> QCService:
    return QCService(gemini=get_gemini_service(), settings=get_settings())


@lru_cache
def get_script_service() -> ScriptService:
    return ScriptService(
        gemini=get_gemini_service(),
        storage=get_local_storage(),
        settings=get_settings(),
    )


@lru_cache
def get_avatar_service() -> AvatarService:
    return AvatarService(
        gemini_image=get_gemini_image_service(),
        imagen=get_imagen_service(),
        storage=get_local_storage(),
        settings=get_settings(),
    )


@lru_cache
def get_storyboard_service() -> StoryboardService:
    return StoryboardService(
        gemini_image=get_gemini_image_service(),
        qc=get_qc_service(),
        storage=get_local_storage(),
        settings=get_settings(),
    )


@lru_cache
def get_video_service() -> VideoService:
    return VideoService(
        veo=get_veo_service(),
        gcs=get_gcs_storage(),
        qc=get_qc_service(),
        storage=get_local_storage(),
        settings=get_settings(),
    )


@lru_cache
def get_stitch_service() -> StitchService:
    return StitchService(storage=get_local_storage())


@lru_cache
def get_review_service() -> ReviewService:
    return ReviewService(db=get_database())


@lru_cache
def get_log_service() -> LogService:
    return LogService(db=get_database())


def get_pipeline_service() -> PipelineService:
    return PipelineService(
        script_svc=get_script_service(),
        avatar_svc=get_avatar_service(),
        storyboard_svc=get_storyboard_service(),
        video_svc=get_video_service(),
        stitch_svc=get_stitch_service(),
        review_svc=get_review_service(),
        job_store=get_job_store(),
        event_broadcaster=get_broadcaster(),
    )


def get_bulk_service() -> BulkService:
    return BulkService(
        pipeline_svc=get_pipeline_service(),
        job_store=get_job_store(),
    )
