import logging

from fastapi import APIRouter, Depends, HTTPException, UploadFile

from app.dependencies import get_input_service
from app.models.script import (
    AnalyzeImageRequest,
    AnalyzeImageResponse,
    GenerateImageRequest,
    GenerateImageResponse,
    ImageUploadResponse,
    SampleProduct,
)
from app.services.input_service import InputService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/input", tags=["input"])

MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10 MB


@router.post("/upload-image", response_model=ImageUploadResponse)
async def upload_image(
    file: UploadFile,
    svc: InputService = Depends(get_input_service),
):
    """Upload a product image (max 10MB). Returns the image URL path."""
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    data = await file.read()
    if len(data) > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=400, detail="File exceeds 10MB limit")

    image_url = await svc.upload_image(data, file.filename or "upload.png")
    return ImageUploadResponse(image_url=image_url)


@router.post("/generate-image", response_model=GenerateImageResponse)
async def generate_image(
    request: GenerateImageRequest,
    svc: InputService = Depends(get_input_service),
):
    """Generate a product image from a text description using AI."""
    try:
        image_url = await svc.generate_product_image(request.description)
    except Exception as exc:
        logger.error("Image generation failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))
    return GenerateImageResponse(image_url=image_url)


@router.post("/analyze-image", response_model=AnalyzeImageResponse)
async def analyze_image(
    request: AnalyzeImageRequest,
    svc: InputService = Depends(get_input_service),
):
    """Analyze a product image and extract name + specifications."""
    try:
        result = await svc.analyze_image(request.image_url)
    except Exception as exc:
        logger.error("Image analysis failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))
    return AnalyzeImageResponse(
        product_name=result.get("product_name", ""),
        specifications=result.get("specifications", ""),
    )


@router.post("/samples")
async def list_samples(svc: InputService = Depends(get_input_service)) -> dict:
    """Return the list of sample products."""
    samples = svc.list_samples()
    return {"samples": [SampleProduct(**s) for s in samples]}
