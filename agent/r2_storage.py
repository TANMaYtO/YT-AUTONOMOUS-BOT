"""Cloudflare R2 storage bridge using S3-compatible boto3 client.

Provides functions to upload, download, and delete video files in Cloudflare R2.
"""

import logging
import os
from pathlib import Path
from typing import Any

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


def _get_r2_client() -> Any:
    """Create and return an authenticated boto3 S3 client for Cloudflare R2."""
    account_id = os.getenv("R2_ACCOUNT_ID")
    access_key = os.getenv("R2_ACCESS_KEY_ID")
    secret_key = os.getenv("R2_SECRET_ACCESS_KEY")

    if not all([account_id, access_key, secret_key]):
        raise RuntimeError(
            "Cloudflare R2 credentials missing from environment. "
            "Please ensure R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, and R2_SECRET_ACCESS_KEY are set."
        )

    endpoint_url = f"https://{account_id}.r2.cloudflarestorage.com"

    return boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        config=Config(signature_version="s3v4"),
    )


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
def upload_file_to_r2(local_file_path: str | Path, storage_key: str) -> str:
    """Upload a local file to Cloudflare R2.

    Args:
        local_file_path: Path to the local file (e.g., output/test.mp4).
        storage_key: R2 object key (e.g., videos/user_id/run_id.mp4).

    Returns:
        The storage key that was uploaded.
    """
    bucket_name = os.getenv("R2_BUCKET_NAME", "cronus-videos")
    client = _get_r2_client()

    logger.info(f"[r2_storage] Uploading {local_file_path} -> R2 bucket '{bucket_name}' key '{storage_key}'...")
    try:
        client.upload_file(str(local_file_path), bucket_name, storage_key)
        logger.info(f"[r2_storage] Successfully uploaded to R2: {storage_key}")
        return storage_key
    except ClientError as e:
        logger.error(f"[r2_storage] Failed to upload {storage_key} to R2: {e}")
        raise


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
def download_file_from_r2(storage_key: str, destination_path: str | Path) -> Path:
    """Download an object from Cloudflare R2 to a local file path.

    Args:
        storage_key: R2 object key (e.g., videos/user_id/run_id.mp4).
        destination_path: Local path where the file should be saved.

    Returns:
        Path object pointing to the downloaded file.
    """
    bucket_name = os.getenv("R2_BUCKET_NAME", "cronus-videos")
    client = _get_r2_client()

    dest = Path(destination_path)
    dest.parent.mkdir(parents=True, exist_ok=True)

    logger.info(f"[r2_storage] Downloading R2 key '{storage_key}' -> {dest}...")
    try:
        client.download_file(bucket_name, storage_key, str(dest))
        logger.info(f"[r2_storage] Successfully downloaded: {dest}")
        return dest
    except ClientError as e:
        logger.error(f"[r2_storage] Failed to download {storage_key} from R2: {e}")
        raise


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
def delete_file_from_r2(storage_key: str) -> bool:
    """Delete an object from Cloudflare R2.

    Args:
        storage_key: R2 object key (e.g., videos/user_id/run_id.mp4).

    Returns:
        True if successfully deleted.
    """
    bucket_name = os.getenv("R2_BUCKET_NAME", "cronus-videos")
    client = _get_r2_client()

    logger.info(f"[r2_storage] Deleting R2 key '{storage_key}'...")
    try:
        client.delete_object(Bucket=bucket_name, Key=storage_key)
        logger.info(f"[r2_storage] Successfully deleted from R2: {storage_key}")
        return True
    except ClientError as e:
        logger.error(f"[r2_storage] Failed to delete {storage_key} from R2: {e}")
        raise
