import os
from dataclasses import dataclass


@dataclass
class Settings:
    gcp_project_id: str = os.getenv("GCP_PROJECT_ID", "general-ak")
    gcp_location: str = os.getenv("GCP_LOCATION", "us-central1")
    rag_corpus_resource_name: str = os.getenv(
        "RAG_CORPUS_RESOURCE_NAME",
        "projects/general-ak/locations/us-central1/ragCorpora/2305843009213693952",
    )
    stt_model: str = os.getenv("STT_MODEL", "chirp_3")
    stt_location: str = os.getenv("STT_LOCATION", "us")
    stt_language: str = os.getenv("STT_LANGUAGE", "auto")
    llm_model: str = os.getenv("LLM_MODEL", "gemini-2.5-flash")


settings = Settings()
