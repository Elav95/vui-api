from fastapi.responses import JSONResponse

from configs.config_boot import config_app

from schemas.response.successful_request import SuccessfulRequest
from schemas.request.create_cloud_credentials import CreateCloudCredentialsRequestSchema

from service.k8s import (get_namespaces_service,
                         get_storage_classes_service,
                         get_resource_manifest_service)
from service.k8s_secret import get_velero_secret_service, get_secret_keys_service
from service.location_credentials import (get_credential_service, get_default_credential_service,
                                          create_cloud_credentials_secret_service)


async def get_ns_handler():
    payload = await get_namespaces_service()

    response = SuccessfulRequest(payload=payload)
    return JSONResponse(content=response.model_dump(), status_code=200)


async def get_resources_handler():
    payload = await get_namespaces_service()

    response = SuccessfulRequest(payload=payload)
    return JSONResponse(content=response.model_dump(), status_code=200)


async def get_credential_handler(secret_name, secret_key):
    payload = await get_credential_service(secret_name, secret_key)

    response = SuccessfulRequest(payload=payload)
    return JSONResponse(content=response.model_dump(), status_code=200)


async def get_default_credential_handler():
    payload = await get_default_credential_service()

    response = SuccessfulRequest(payload=payload)
    return JSONResponse(content=response.model_dump(), status_code=200)


async def get_k8s_storage_classes_handler():
    payload = await get_storage_classes_service()

    response = SuccessfulRequest(payload=payload)
    return JSONResponse(content=response.model_dump(), status_code=200)


async def get_logs_handler(lines=100, follow=False):
    payload = await get_logs_handler(lines=lines, follow=follow)

    response = SuccessfulRequest(payload=payload)
    return JSONResponse(content=response.model_dump(), status_code=200)


async def create_cloud_credentials_handler(cloud_credentials: CreateCloudCredentialsRequestSchema):
    payload = await create_cloud_credentials_secret_service(cloud_credentials.newSecretName,
                                                            cloud_credentials.newSecretKey,
                                                            cloud_credentials.awsAccessKeyId,
                                                            cloud_credentials.awsSecretAccessKey)

    response = SuccessfulRequest(payload=payload)
    return JSONResponse(content=response.model_dump(), status_code=200)


async def get_velero_secret_handler():
    payload = await get_velero_secret_service()

    response = SuccessfulRequest(payload=payload)
    return JSONResponse(content=response.model_dump(), status_code=200)


async def get_velero_secret_key_handler(secret_name):
    payload = await get_secret_keys_service(config_app.k8s.velero_namespace, secret_name)

    response = SuccessfulRequest(payload=payload)
    return JSONResponse(content=response.model_dump(), status_code=200)


async def get_manifest_handler(resource_type, resource_name):
    payload = await get_resource_manifest_service(resource_type=resource_type, resource_name=resource_name)

    response = SuccessfulRequest(payload=payload)
    return JSONResponse(content=response.model_dump(), status_code=200)
