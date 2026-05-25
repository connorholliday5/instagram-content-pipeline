import os
import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv

load_dotenv()

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True
)


def upload_image(image_path: str) -> str:
    """Upload local image to Cloudinary and return public URL."""
    result = cloudinary.uploader.upload(
        image_path,
        folder="thewatchtower",
        overwrite=True,
        resource_type="image"
    )
    return result["secure_url"]