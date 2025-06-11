from fastapi import HTTPException
from kubernetes import client
from vui_common.configs.config_proxy import config_app
from vui_common.logger.logger_proxy import logger

from constants.velero import VELERO

custom_objects = client.CustomObjectsApi()


def cleanup_server_request(resource_name: str, plural: str):
    """
    Deletes the resource after use to avoid accumulation in the cluster.

    :param resource_name: Name of the resource associated plural.
    :param plural: plural associated with the resource name.
    """
    logger.info(f"Cleanup {plural}:{resource_name}")
    try:
        custom_objects.delete_namespaced_custom_object(
            group=VELERO["GROUP"],
            version=VELERO["VERSION"],
            namespace=config_app.k8s.velero_namespace,
            plural=plural,
            name=resource_name
        )
        logger.info(f"{plural} '{resource_name}' successfully deleted.")
    except client.exceptions.ApiException as e:
        if e.status == 404:
            logger.error(f"DownloadRequest '{resource_name}' does not exist, no deletion required.")
            raise HTTPException(status_code=400,
                                detail=f"DownloadRequest '{resource_name}' does not exist, no deletion "
                                       f"required.")

        else:
            logger.error(f"Error while deleting DownloadRequest '{resource_name}': {e}")
            raise HTTPException(status_code=400,
                                detail=f"Error while deleting DownloadRequest '{resource_name}': {e}")
