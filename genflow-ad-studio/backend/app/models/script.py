from pydantic import BaseModel, Field


class CustomerProfile(BaseModel):
    """Optional customer segment profile used to personalise the ad script."""
    segment: str = Field(default="", description="e.g. Young Professional, HNI, Senior Citizen, NRI, Student")
    age_group: str = Field(default="", description="e.g. 22-30, 31-45, 46-60, 60+")
    income_tier: str = Field(default="", description="e.g. Mass Market, Emerging Affluent, HNI, UHNI")
    life_stage: str = Field(default="", description="e.g. First Job, Newly Married, New Parent, Pre-Retirement")
    key_motivation: str = Field(default="", description="e.g. Wealth Growth, Tax Saving, Home Ownership, Legacy Planning")
    language_preference: str = Field(default="English", description="e.g. English, Hindi, Hinglish, Tamil")
    location_type: str = Field(default="", description="e.g. Metro, Tier-2 City, Rural")


class ScriptRequest(BaseModel):
    product_name: str
    specifications: str
    image_url: str
    scene_count: int = Field(default=3, ge=2, le=6)
    ad_tone: str = Field(default="sophisticated")
    gemini_model: str | None = None
    max_dialogue_words_per_scene: int = Field(default=25, ge=10, le=50)
    custom_instructions: str = Field(default="")
    customer_profile: CustomerProfile = Field(default_factory=CustomerProfile)
    run_id: str | None = None  # Pre-generated run_id for SSE log streaming


class AvatarProfile(BaseModel):
    gender: str
    age_range: str
    attire: str
    tone_of_voice: str
    visual_description: str
    voice_style: str = ""
    ethnicity: str = ""


class Scene(BaseModel):
    model_config = {"extra": "ignore"}

    scene_number: int
    duration_seconds: int
    scene_type: str
    shot_type: str
    camera_movement: str
    lighting: str
    visual_background: str
    avatar_action: str
    avatar_emotion: str
    product_visual_integration: str
    script_dialogue: str
    sound_design: str
    voice_style: str = Field(default="")
    detailed_avatar_description: str = Field(default="")
    negative_elements: str = Field(default="")
    transition_type: str = Field(default="cut")
    transition_duration: float = Field(default=0.5, ge=0.0, le=2.0)
    audio_continuity: str = Field(default="")


class VideoScript(BaseModel):
    video_title: str
    total_duration: int = 30
    avatar_profile: AvatarProfile
    scenes: list[Scene]
    negative_elements: str = ""
    voice_style: str = ""


class ScriptUpdateRequest(BaseModel):
    run_id: str
    script: VideoScript


class ScriptResponse(BaseModel):
    status: str = "success"
    run_id: str
    product_image_path: str
    script: VideoScript


# ---------------------------------------------------------------------------
# Input step models
# ---------------------------------------------------------------------------


class SampleProduct(BaseModel):
    id: str
    product_name: str
    specifications: str
    image_url: str
    thumbnail: str


class ImageUploadResponse(BaseModel):
    status: str = "success"
    image_url: str


class GenerateImageRequest(BaseModel):
    description: str


class GenerateImageResponse(BaseModel):
    status: str = "success"
    image_url: str


class AnalyzeImageRequest(BaseModel):
    image_url: str


class AnalyzeImageResponse(BaseModel):
    status: str = "success"
    product_name: str
    specifications: str
