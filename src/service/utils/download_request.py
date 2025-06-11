import tempfile
import tarfile
import aiohttp
import aiofiles
import asyncio

from fastapi import HTTPException
from kubernetes import client
from typing import Optional

from constants.velero import VELERO
from constants.resources import RESOURCES, ResourcesNames
from vui_common.configs.config_proxy import config_app
from vui_common.logger.logger_proxy import logger

from service.utils.cleanup_requests import cleanup_server_request

custom_objects = client.CustomObjectsApi()


async def create_download_request(resource_name: str, resource_kind: str) -> Optional[str]:
    """
    Creates a Velero DownloadRequest to download the requested data.
    If a request already exists, reuses or deletes it and creates a new one.

    :param resource_name: Name of the resource (e.g., backup_name).
    :param resource_kind: Type of the resource (BackupLog, BackupContents, etc.).
    :return: URL for download or None if it fails
    """
    logger.info(f"Create download request download-{resource_name}-{resource_kind.lower()}")
    download_request_name = f"download-{resource_name}-{resource_kind.lower()}"

    try:
        # Check if a DownloadRequest already exists
        existing_request = custom_objects.get_namespaced_custom_object(
            group=VELERO["GROUP"],
            version=VELERO["VERSION"],
            namespace=config_app.k8s.velero_namespace,
            plural=RESOURCES[ResourcesNames.DOWNLOAD_REQUEST].plural,
            name=download_request_name
        )

        # If it exists and is Processed, we reuse its URL
        if existing_request.get("status", {}).get("phase") == "Processed":
            logger.info(f"Download request from existing url {existing_request.get('status', {}).get('downloadURL')}")
            return existing_request.get("status", {}).get("downloadURL")

        # If it exists but is not Processed, we delete it and recreate it
        logger.info(f"DownloadRequest ‘{download_request_name}’ already exists but is not Processed. By deleting it...")
        cleanup_server_request(resource_name, RESOURCES[ResourcesNames.DOWNLOAD_REQUEST].plural)

    except client.exceptions.ApiException as e:
        if e.status != 404:  # Ignoriamo l'errore 404 (not found)
            logger.error(f"Error while checking DownloadRequest ‘{download_request_name}’: {e}")
            raise HTTPException(status_code=400,
                                detail=f"Error while checking DownloadRequest ‘{download_request_name}’: {e}")

    try:
        # Creating the new DownloadRequest
        logger.info("Creating the new DownloadRequest")
        download_request_body = {
            "apiVersion": f"{VELERO['GROUP']}/{VELERO['VERSION']}",
            "kind": "DownloadRequest",
            "metadata": {
                "name": download_request_name,
                "namespace": config_app.k8s.velero_namespace
            },
            "spec": {
                "target": {
                    "kind": resource_kind,
                    "name": resource_name
                }
            }
        }

        custom_objects.create_namespaced_custom_object(
            group=VELERO["GROUP"],
            version=VELERO["VERSION"],
            namespace=config_app.k8s.velero_namespace,
            plural=RESOURCES[ResourcesNames.DOWNLOAD_REQUEST].plural,
            body=download_request_body
        )

        # Wait up to 5 attempts for the request to be processed
        for _ in range(5):
            await asyncio.sleep(5)
            download_request = custom_objects.get_namespaced_custom_object(
                group=VELERO["GROUP"],
                version=VELERO["VERSION"],
                namespace=config_app.k8s.velero_namespace,
                plural=RESOURCES[ResourcesNames.DOWNLOAD_REQUEST].plural,
                name=download_request_name
            )

            if download_request.get("status", {}).get("phase") == "Processed":
                return download_request.get("status", {}).get("downloadURL")

    except Exception as e:
        logger.error(f"Error in DownloadRequest for ‘{resource_name}’: {e}")
        raise HTTPException(status_code=400,
                            detail=f"Error in DownloadRequest for ‘{resource_name}’: {e}")


async def download_and_extract_backup(download_url: str) -> Optional[str]:
    logger.info(f"Download and extract backup from {download_url}")
    try:
        # Download the file asynchronously
        async with aiohttp.ClientSession() as session:
            async with session.get(download_url) as response:
                if response.status != 200:
                    logger.error(f"Backup download error: {response.status}")
                    raise HTTPException(status_code=400,
                                        detail=f"Backup download error: {response.status}")

                # Writes the contents to a temporary file
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".tar.gz")
                temp_file_path = temp_file.name
                temp_file.close()  # Close to write async

                async with aiofiles.open(temp_file_path, 'wb') as f:
                    async for chunk in response.content.iter_chunked(1024 * 1024):
                        await f.write(chunk)

        # Creates a temporary folder for extraction
        extract_folder = tempfile.mkdtemp()

        # Extract the .tar.gz file in a separate thread (to avoid blockages)
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, extract_tarfile, temp_file_path, extract_folder)

        return extract_folder

    except Exception as e:
        logger.error(f"Error while downloading and extracting backup: {e}")
        raise HTTPException(status_code=400,
                            detail=f"Error while downloading and extracting backup: {e}")

def extract_tarfile(tar_path: str, extract_to: str):
    with tarfile.open(tar_path, "r:gz") as tar:
        tar.extractall(path=extract_to)