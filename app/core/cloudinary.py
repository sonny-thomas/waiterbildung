import cloudinary
import cloudinary.uploader

from app.core.config import Settings

settings = Settings()


class Cloudinary:
    def __init__(self):
        cloudinary.config(
            cloud_name=settings.CLOUDINARY_CLOUD_NAME,
            api_key=settings.CLOUDINARY_API_KEY,
            api_secret=settings.CLOUDINARY_API_SECRET,
            secure=settings.CLOUDINARY_SECURE,
        )

    def upload(self, file_path, public_id):
        upload_result = cloudinary.uploader.upload(
            file_path, public_id=public_id, folder=settings.ENVIRONMENT
        )

        return f"https://res.cloudinary.com/{settings.CLOUDINARY_CLOUD_NAME}/image/upload/f_auto,q_auto/{upload_result['public_id']}"

    def delete(self, public_id):
        cloudinary.uploader.destroy(public_id)
