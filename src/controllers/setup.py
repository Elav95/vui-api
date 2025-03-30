import os
from fastapi.responses import JSONResponse

from configs.config_boot import config_app

from schemas.response.successful_request import SuccessfulRequest

from service.k8s_configmap import get_config_map_service
from service.velero import get_velero_version_service, get_pods_service


async def get_env_handler():
    if os.getenv('K8S_IN_CLUSTER_MODE').lower() == 'true':
        env_data = await get_config_map_service(namespace=config_app.k8s.vui_namespace,
                                                configmap_name='velero-api-config')

    else:
        env_data = config_app.get_env_variables()

    response = SuccessfulRequest(payload=env_data)
    return JSONResponse(content=response.model_dump(), status_code=200)


async def get_velero_version_handler():
    payload = await get_velero_version_service()

    response = SuccessfulRequest(payload=payload)
    return JSONResponse(content=response.model_dump(), status_code=200)


async def get_velero_pods_handler():
    label_selectors_by_type = {
        "velero": "name=velero",
        "node-agent": "name=node-agent"
    }
    payload = await get_pods_service(label_selectors_by_type=label_selectors_by_type,
                                     namespace=config_app.k8s.velero_namespace)

    response = SuccessfulRequest(payload=payload)
    return JSONResponse(content=response.model_dump(), status_code=200)


async def get_vui_pods_handler():
    label_selectors_by_type = {
        "API": "layer=api",
        "UI": "layer=webserver",
        "WATCHDOG": "app=velero-watchdog",
    }
    payload = await get_pods_service(label_selectors_by_type, namespace=config_app.k8s.vui_namespace)

    response = SuccessfulRequest(payload=payload)
    return JSONResponse(content=response.model_dump(), status_code=200)
