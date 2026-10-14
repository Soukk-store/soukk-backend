import boto3
from botocore.config import Config
from fastapi.concurrency import run_in_threadpool

from soukk_backend.settings.appSettings import settings

# boto3 clients are thread safe, so one is shared by every request.
_client = boto3.client(
    "s3",
    endpoint_url=settings.storage_endpoint,
    region_name=settings.storage_region,
    aws_access_key_id=settings.storage_access_key,
    aws_secret_access_key=settings.storage_secret_key,
    config=Config(
        signature_version="s3v4",
        connect_timeout=5,
        read_timeout=10,
        retries={"max_attempts": 3, "mode": "standard"},
    ),
)

# Every upload gets a new key, so the stored object never changes and browsers
# and the CDN may cache it for good.
IMMUTABLE_CACHE = "public, max-age=31536000, immutable"


async def put(key: str, data: bytes, content_type: str) -> None:
    # boto3 is blocking; run it off the event loop.
    await run_in_threadpool(
        _client.put_object,
        Bucket=settings.storage_bucket,
        Key=key,
        Body=data,
        ContentType=content_type,
        CacheControl=IMMUTABLE_CACHE,
    )


async def delete(key: str) -> None:
    await run_in_threadpool(_client.delete_object, Bucket=settings.storage_bucket, Key=key)


def public_url(key: str) -> str:
    return f"{settings.image_base_url.rstrip('/')}/{key}"
