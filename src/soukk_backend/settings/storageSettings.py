from pydantic_settings import BaseSettings, SettingsConfigDict


class StorageSettings(BaseSettings):
    """Object storage (Cloudflare R2, S3-compatible) for user images. API only."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # S3 API endpoint of the account, without the bucket name.
    storage_endpoint: str
    storage_region: str
    storage_access_key: str
    storage_secret_key: str
    storage_bucket: str

    # Public base URL the bucket is served from; image URLs are this plus the key.
    image_base_url: str
    # Key of the image shown for users who haven't set one.
    default_image_key: str
    # Largest upload accepted, in bytes.
    image_max_bytes: int
    # Uploaded images are cropped to a square of this many pixels.
    image_size_px: int
