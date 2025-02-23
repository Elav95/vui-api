import os
import sys
import configparser
import base64

from fastapi import HTTPException
from kubernetes import client, config
from kubernetes.client import ApiException
from datetime import datetime

from configs.config_boot import config_app
from utils.k8s_tracer import trace_k8s_async_method

from utils.logger_boot import logger




def _parse_config_string(config_string):
    # Create a ConfigParser object
    config_parser = configparser.ConfigParser()

    # read string
    config_parser.read_string(config_string)

    # extract values
    aws_access_key_id = config_parser.get('default', 'aws_access_key_id', fallback=None)
    aws_secret_access_key = config_parser.get('default', 'aws_secret_access_key', fallback=None)

    # crete dict
    result = {'aws_access_key_id': aws_access_key_id, 'aws_secret_access_key': aws_secret_access_key}

    return result


def _transform_logs_to_json(logs):
    json_logs = []
    for log_line in logs.split("\n"):
        if log_line.strip():
            log_entry = {"log": log_line}
            json_logs.append(log_entry)
    return json_logs


async def _get_node_list(only_problem=False):
    """
    Obtain K8S nodes
    :param only_problem:
    :return: List of nodes
    """
    try:
        total_nodes = 0
        retrieved_nodes = 0
        add_node = True
        nodes = {}
        active_context = ''
        # Listing the cluster nodes
        node_list = client.CoreV1Api().list_node()
        for node in node_list.items:
            total_nodes += 1
            node_details = {}

            node_details['context'] = active_context
            node_details['name'] = node.metadata.name
            if 'kubernetes.io/role' in node.metadata.labels:
                node_details['role'] = node.metadata.labels['kubernetes.io/role']

                node_details['role'] = 'control-plane'
            version = node.status.node_info.kube_proxy_version
            node_details['version'] = version

            node_details['architecture'] = node.status.node_info.architecture

            node_details['operating_system'] = node.status.node_info.operating_system

            node_details['kernel_version'] = node.status.node_info.kernel_version

            node_details['os_image'] = node.status.node_info.os_image

            node_details['addresses'] = node.status.addresses
            condition = {}
            for detail in node.status.conditions:
                condition[detail.reason] = detail.status

                if only_problem:
                    if add_node:
                        if detail.reason == 'KubeletReady':
                            if not bool(detail.status):
                                add_node = False
                        else:
                            if bool(detail.status):
                                add_node = False
                else:
                    add_node = True
            node_details['conditions'] = condition

            if add_node:
                retrieved_nodes += 1
                nodes[node.metadata.name] = node_details

        return total_nodes, retrieved_nodes, nodes

    except Exception as Ex:
        return 0, 0, None


@trace_k8s_async_method(description="get online data")
async def get_k8s_online_service():
    ret = False
    total_nodes = 0
    retr_nodes = 0
    try:
        total_nodes, retr_nodes, nodes = await _get_node_list(only_problem=True)
        if nodes is not None:
            ret = True

    except Exception as Ex:
        ret = False

    output = {'cluster_online': ret, 'nodes': {'total': total_nodes, 'in_error': retr_nodes},

              'timestamp': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f')}
    return output


@trace_k8s_async_method(description="get namespaces")
async def get_namespaces_service():
    # Get namespaces list
    namespace_list = client.CoreV1Api().list_namespace()
    # Extract namespace list
    namespaces = [namespace.metadata.name for namespace in namespace_list.items]
    return namespaces


@trace_k8s_async_method(description="get resources")
async def get_resources_service():
    logger.info(f"load_resources")
    try:

        valid_resources = []

        k8s_client = client
        # Initialize the API client
        api_client = k8s_client.ApiClient()

        # # Retrieve the list of available API groups
        # discovery = k8s_client.ApisApi(api_client)
        # api_groups = discovery.get_api_versions().groups

        # Retrieve the list of available API groups
        discovery = k8s_client.ApisApi(api_client)
        try:
            api_groups = discovery.get_api_versions().groups
            logger.debug(f"Retrieved API groups with success")
        except ApiException as e:
            logger.error(f"Exception when retrieving API groups {str(e)}")
            return valid_resources

        for group in api_groups:
            logger.debug(f"find. apihist  group: {group.name}")
            for version in group.versions:
                group_version = f"{group.name}/{version.version}" if group.name else version.version
                try:
                    logger.debug(f"API group version: {group_version}")
                    # Get the resources for the group version
                    # api_resources = api_client.call_api(
                    #     f'/apis/{group_version}', 'GET',
                    #     response_type='object')[0]['resources']
                    #
                    # for resource in api_resources:
                    #     if '/' not in resource['name']:  # Only include resource names, not sub-resources
                    #         if resource['name'] not in valid_resources:
                    #             valid_resources.append(resource['name'])
                    # Use the Kubernetes client to get the resources
                    api_instance = k8s_client.CustomObjectsApi(api_client)
                    api_resources = api_instance.list_cluster_custom_object(group=group.name,
                                                                            version=version.version, plural='').get(
                        'resources', [])

                    for resource in api_resources:
                        if '/' not in resource['name']:  # Only include resource names, not sub-resources
                            if resource['name'] not in valid_resources:
                                valid_resources.append(resource['name'])

                except k8s_client.exceptions.ApiException as e:
                    logger.error(
                        f"Exception when calling ApisApi->get_api_resources for {group_version}: {e}")
                    continue

        # Get core API resources
        core_api = k8s_client.CoreV1Api(api_client)
        core_resources = core_api.get_api_resources().resources
        for resource in core_resources:
            if '/' not in resource.name:  # Only include resource names, not sub-resources
                # valid_resources.append(resource.name)
                if resource.name not in valid_resources:
                    valid_resources.append(resource.name)

        # If you want to maintain the order of elements as they were added to the set
        if len(valid_resources):
            res_list_ordered = sorted(list(valid_resources))
            logger.debug(f"load_resources:{res_list_ordered}")
            return res_list_ordered
        else:
            logger.warning(f"load_load_resources:No load_resources found")
            raise HTTPException(status_code=400, detail="No load_resources found")

    except Exception as Ex:
        logger.error(f"{sys.exc_info()} {str(Ex)}")
        raise HTTPException(status_code=400, detail=f"{str(Ex)}")


@trace_k8s_async_method(description="get logs")
async def get_logs_service(lines=100, follow=False):
    # Get env variable data
    namespace = config_app.k8s_pod_namespace_in() or []
    pod_name = config_app.k8s_pod_name() or []
    in_cluster_mode = config_app.k8s_in_cluster_mode()

    if lines < 10:
        lines = 100
    elif lines > 500:
        lines = 500

    if in_cluster_mode:
        if len(namespace) > 0 and len(pod_name) > 0:
            # Retrieve logs from the pod
            logs = client.CoreV1Api().read_namespaced_pod_log(namespace=namespace,
                                                              name=pod_name,
                                                              pretty=True,
                                                              # If the pod has only one container, you can omit this
                                                              container=None,
                                                              # Include timestamps in the logs
                                                              timestamps=False,
                                                              # Number of lines to retrieve from the end of the logs
                                                              tail_lines=lines,
                                                              # Set to True if you want to follow the logs
                                                              # continuously
                                                              follow=follow)
            if logs is not None:
                # Transform logs to JSON format
                json_logs = _transform_logs_to_json(logs)
                return json_logs
            else:
                raise HTTPException(status_code=400, detail=f"No logs retrieved "
                                                            f"pod name {pod_name} in"
                                                            f" the namespace {namespace}")

        else:
            raise HTTPException(status_code=400, detail=f"No logs retrieved "
                                                        f"pod name {pod_name} o"
                                                        f" namespace {namespace} not defined")
    else:
        raise HTTPException(status_code=400, detail=f"the application is not running in container mode")


@trace_k8s_async_method(description="get resource manifest")
async def get_resource_manifest_service(resource_type, resource_name):
    # Create an instance of the API client
    api_instance = client.CustomObjectsApi()

    # Namespace in which Velero is operating
    namespace = "velero"

    # Group, version and plural to access Velero backups
    group = "velero.io"
    version = "v1"
    plural = resource_type

    try:
        # API call to get backups
        backups = api_instance.list_namespaced_custom_object(group, version, namespace, plural)

        # Filter objects by label velero.io/backup-uid
        filtered_items = [
            item for item in backups.get('items', [])
            if item.get('metadata', {}).get('name') == resource_name
        ] if resource_name else backups.get('items', [])

        # Return only filtered objects
        return filtered_items[0]
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise HTTPException(status_code=400, detail=f"{str(e)}")


@trace_k8s_async_method(description="get a configmap")
async def get_config_map_service(namespace, configmap_name):
    # Kubernetes API client
    core_api = client.CoreV1Api()

    # Specify the namespace and the name of the ConfigMap you want to read
    # namespace = app_config.get_k8s_velero_ui_namespace()
    # configmap_name = 'velero-api-config'

    try:
        # Retrieve the ConfigMap
        configmap = core_api.read_namespaced_config_map(name=configmap_name, namespace=namespace)

        # Access the data in the ConfigMap
        data = configmap.data
        if not data:
            raise HTTPException(status_code=400, detail=f"Error get config map service")
        kv = {}
        # Print out the data
        for key, value in data.items():
            if (key.startswith('SECURITY_TOKEN_KEY') or key.startswith('EMAIL_PASSWORD') or
                    key.startswith('TELEGRAM_TOKEN')):
                value = value[0].ljust(len(value) - 1, '*')
            kv[key] = value
        return kv
    except client.exceptions.ApiException as e:
        logger.warning(f"Exception when calling CoreV1Api->read_namespaced_config_map: {e}")
        # raise HTTPException(status_code=400, detail=f"Exception when calling "
        #                                             f"CoreV1Api->read_namespaced_config_map: {e}")
        return None


@trace_k8s_async_method(description="create or update a configmap")
async def create_or_update_configmap_service(namespace, configmap_name, key, value):
    """
     Create or update a ConfigMap in Kubernetes.

    Args:
        namespace (str): The namespace of the ConfigMap.
        configmap_name (str): The name of the ConfigMap.
        key (str): The key to be updated.
        value (str): The value to be assigned to the key.

    Returns:
        dict: The updated or created ConfigMap.
    """

    v1 = client.CoreV1Api()

    try:
        # Try retrieving the existing ConfigMap
        existing_configmap = v1.read_namespaced_config_map(name=configmap_name, namespace=namespace)
        print(f"ConfigMap '{configmap_name}' found, update in progress...")

        # Update the value of the key
        if existing_configmap.data is None:
            existing_configmap.data = {}

        existing_configmap.data[key] = value
        updated_configmap = v1.replace_namespaced_config_map(name=configmap_name, namespace=namespace,
                                                             body=existing_configmap)
        print(f"ConfigMap '{configmap_name}' updated with {key}: {value}")

    except ApiException as e:
        if e.status == 404:
            print(f"ConfigMap '{configmap_name}' not found, creation in progress...")

            # Creating the ConfigMap
            configmap = client.V1ConfigMap(
                metadata=client.V1ObjectMeta(name=configmap_name),
                data={key: value}
            )

            created_configmap = v1.create_namespaced_config_map(namespace=namespace, body=configmap)
            print(f"ConfigMap '{configmap_name}' created with {key}: {value}")
            return created_configmap
        else:
            print(f"Error while accessing ConfigMap: {e}")
            return None

    return updated_configmap


@trace_k8s_async_method(description="remove a key from configmap")
async def remove_key_from_configmap_service(namespace, configmap_name, key):
    """
    Removes a key from a ConfigMap in Kubernetes.

    Args:
        namespace (str): The namespace of the ConfigMap.
        configmap_name (str): The name of the ConfigMap.
        key (str): The key to be removed.

    Returns:
        dict | None: The updated ConfigMap or None if the ConfigMap has been deleted or does not exist.
    """
    # Upload Kubernetes configuration
    # config.load_kube_config()  # Use for local execution with kubectl configured


    v1 = client.CoreV1Api()

    try:
        # Retrieve the ConfigMap
        configmap = v1.read_namespaced_config_map(name=configmap_name, namespace=namespace)

        # Check if the key exists
        if configmap.data is None or key not in configmap.data:
            print(f"The key '{key}' does not exist in the ConfigMap '{configmap_name}'.")
            return configmap

        # Removes the specified key
        del configmap.data[key]
        print(f"Key '{key}' removed from ConfigMap '{configmap_name}'.")

        # If the ConfigMap is empty, you can choose to delete it
        # if not configmap.data:  # If there are no more keys
        #     print(f"The ConfigMap '{configmap_name}' is empty. Deleting it...")
        #     v1.delete_namespaced_config_map(name=configmap_name, namespace=namespace)
        #     return None  # Indicates that the ConfigMap has been deleted

        # Otherwise, update the ConfigMap
        updated_configmap = v1.replace_namespaced_config_map(name=configmap_name, namespace=namespace,
                                                             body=configmap)
        return updated_configmap

    except ApiException as e:
        if e.status == 404:
            print(f"ConfigMap '{configmap_name}' not found in namespace '{namespace}'.")
        else:
            print(f"Error while accessing ConfigMap: {e}")
        return None


@trace_k8s_async_method(description="create a configmap")
async def create_configmap_service(namespace, configmap_name, data):
    """
    Create a ConfigMap in Kubernetes.

    Args:
        namespace (str): The namespace of the ConfigMap.
        configmap_name (str): The name of the ConfigMap.
        data (dict): A dictionary with the keys and values to be included in the ConfigMap.

    Returns:
        dict: The ConfigMap created, or None if it already exists.
    """
    # Upload Kubernetes configuration
    # config.load_kube_config()  # Use this for local execution
    # config.load_incluster_config()  # Use this if the code is executed inside a pod

    v1 = client.CoreV1Api()

    # Defines the ConfigMap
    configmap = client.V1ConfigMap(
        metadata=client.V1ObjectMeta(name=configmap_name),
        data=data
    )

    try:
        # Check if the ConfigMap already exists
        v1.read_namespaced_config_map(name=configmap_name, namespace=namespace)
        print(f"The ConfigMap '{configmap_name}' already exists in the namespace '{namespace}'.")
        return None  # Does not create a new ConfigMap if it already exists

    except ApiException as e:
        if e.status == 404:
            # If the ConfigMap does not exist, it creates it
            created_configmap = v1.create_namespaced_config_map(namespace=namespace, body=configmap)
            print(f"ConfigMap '{configmap_name}' successfully created in the namespace '{namespace}'.")
            return created_configmap
        else:
            print(f"Error while creating the ConfigMap: {e}")
            return None


@trace_k8s_async_method(description="get velero secret list names")
async def get_velero_secret_service():
    try:
        secrets = client.CoreV1Api().list_namespaced_secret(config_app.get_k8s_velero_namespace())
        return [secret.metadata.name for secret in secrets.items]
    except Exception as e:
        print(f"Can't get secret: {e}")
        raise HTTPException(status_code=400, detail=f"No secret retrieved")


@trace_k8s_async_method(description="get secret's keys")
async def get_secret_keys_service(namespace: str, secret_name: str):
    try:
        secret = client.CoreV1Api().read_namespaced_secret(name=secret_name,
                                                           namespace=namespace)
        if secret.data:
            return list(secret.data.keys())
        else:
            return []
    except client.exceptions.ApiException as e:
        print(f"Error API Kubernetes: {e}")
        raise HTTPException(status_code=400, detail=f"Error API Kubernetes: {e}")
    except Exception as e:
        print(f"Error while obtaining Secret keys: {e}")
        raise HTTPException(status_code=400, detail=f"Error while obtaining Secret keys: {e}")


@trace_k8s_async_method(description="get secret content")
async def get_secret_service(namespace: str, secret_name: str):
    try:
        secret = client.CoreV1Api().read_namespaced_secret(name=secret_name,
                                                           namespace=namespace)
        if secret.data:
            decoded_data = {key: base64.b64decode(value).decode('utf-8') for key, value in secret.data.items()}
            return decoded_data
        else:
            return []
    except client.exceptions.ApiException as e:
        print(f"Error API Kubernetes: {e}")
        # raise HTTPException(status_code=400, detail=f"Error API Kubernetes: {e}")
        return None

    except Exception as e:
        print(f"Error while obtaining Secret keys: {e}")
        # raise HTTPException(status_code=400, detail=f"Error while obtaining Secret keys: {e}")
        return None


@trace_k8s_async_method(description="add or update key:value in secret")
async def add_or_update_key_in_secret_service(namespace, secret_name, key, value):
    """
    Adds or updates a key in a Secret Kubernetes.

    Args:
        namespace (str): The namespace of the Secret.
        secret_name (str): The name of the Secret.
        key (str): The key to be added or updated.
        value (str): The value of the key (not base64 encoded).

    Returns:
        dict | None: The updated Secret, or None in case of an error
    """
    # Upload Kubernetes configuration
    # config.load_kube_config()

    v1 = client.CoreV1Api()

    try:
        secret = v1.read_namespaced_secret(name=secret_name, namespace=namespace)

        if secret.data is None:
            secret.data = {}

        # Encode value in base64
        secret.data[key] = base64.b64encode(value.encode()).decode()

        updated_secret = v1.replace_namespaced_secret(name=secret_name, namespace=namespace, body=secret)
        print(f"Key '{key}' added/updated in Secret '{secret_name}'.")
        return updated_secret

    except ApiException as e:
        if e.status == 404:
            print(f"Secret '{secret_name}' not found in namespace '{namespace}'. Create it before adding key")
            # Create the Secret with the key and the value
            secret_data = {key: base64.b64encode(value.encode()).decode()}
            new_secret = client.V1Secret(
                metadata=client.V1ObjectMeta(name=secret_name),
                data=secret_data,
                type="Opaque"
            )

            created_secret = v1.create_namespaced_secret(namespace=namespace, body=new_secret)
            print(f"Secret '{secret_name}' created with key '{key}'.")
            return created_secret
        else:
            print(f"Error when updating Secret: {e}")
        return None


@trace_k8s_async_method(description="remove key from secret")
def remove_key_from_secret_service(namespace, secret_name, key):
    """
    Removes a key from a Secret Kubernetes.

    Args:
        namespace (str): The namespace of the Secret.
        secret_name (str): The name of the Secret.
        key (str): The key to be removed.

    Returns:
        dict | None: The updated Secret or None if the Secret has been deleted or does not exist.
    """
    # Upload Kubernetes configuration
    # config.load_kube_config()

    v1 = client.CoreV1Api()

    try:
        secret = v1.read_namespaced_secret(name=secret_name, namespace=namespace)

        if secret.data is None or key not in secret.data:
            print(f"The key '{key}' does not exist in Secret '{secret_name}'.")
            return secret

        # Removes the key
        del secret.data[key]
        print(f"Key '{key}' removed from Secret '{secret_name}'.")

        # If Secret is empty, it deletes it
        if not secret.data:
            print(f"The Secret '{secret_name}' is now empty. Deleting it...")
            v1.delete_namespaced_secret(name=secret_name, namespace=namespace)
            return None

        updated_secret = v1.replace_namespaced_secret(name=secret_name, namespace=namespace, body=secret)
        return updated_secret

    except ApiException as e:
        if e.status == 404:
            print(f"Secret '{secret_name}' not found in namespace '{namespace}'.")
        else:
            print(f"Error while accessing Secret: {e}")
        return None


@trace_k8s_async_method(description="get storage classes")
async def get_storage_classes_service():
    storage_classes = {}

    storage_classes_list = client.StorageV1Api().list_storage_class()

    if storage_classes_list is not None:
        for sc in storage_classes_list.items:
            v_class = {'name': sc.metadata.name, 'provisioner': sc.provisioner, 'parameters': sc.parameters, }
            storage_classes[sc.metadata.name] = v_class

        return storage_classes
    else:
        raise HTTPException(status_code=400, detail=f"Error when getting storage classes")


@trace_k8s_async_method(description="get velero secret")
async def delete_volume_snapshot_location_service(location_name):
    try:
        api_instance = client.CustomObjectsApi()

        group = "velero.io"
        version = "v1"
        plural = "volumesnapshotlocations"

        # api call to delete resource
        api_instance.delete_namespaced_custom_object(group=group, version=version,
                                                     namespace=config_app.get_k8s_velero_namespace(),
                                                     plural=plural, name=location_name)

        print(
            f"VolumeSnapshotLocation '{location_name}' deleted '"
            f"{config_app.get_k8s_velero_namespace()}'.")
        return True
    except Exception as e:
        print(f"Error: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Error: {str(e)}")


@trace_k8s_async_method(description="get cron schedule")
async def get_watchdog_cron_schedule_service(namespace, job_name):
    try:
        api_instance = client.BatchV1Api()
        logger.debug(f"namespace {namespace} job_name {job_name}")
        cronjob = api_instance.read_namespaced_cron_job(name=job_name, namespace=namespace)

        cron_schedule = cronjob.spec.schedule

        return cron_schedule

    except Exception as e:
        logger.error(f"Error get cronjob '{job_name}': {e}")
        raise HTTPException(status_code=400, detail=f"Error get cronjob '{job_name}': {e}")


async def get_pod_volume_backups_service():
    # Create an instance of the API client
    api_instance = client.CustomObjectsApi()

    # Namespace in which Velero is operating
    namespace = "velero"

    # Get Velero's backup items
    group = "velero.io"
    version = "v1"
    plural = "podvolumebackups"

    try:
        # API call to get backups
        backups = api_instance.list_namespaced_custom_object(group, version, namespace, plural)

        # Convert the result to JSON
        # backups_json = json.dumps(backups, indent=4)

        return backups
    except Exception as e:
        print(f"Error: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Error {str(e)}")


async def get_pod_volume_backup_service(backup_name=None):
    # Create an instance of the API client
    api_instance = client.CustomObjectsApi()

    # Namespace in which Velero is operating
    namespace = "velero"

    # Group, version and plural to access Velero backups
    group = "velero.io"
    version = "v1"
    plural = "podvolumebackups"

    try:
        # API call to get backups
        backups = api_instance.list_namespaced_custom_object(group, version, namespace, plural)

        # Filter objects by label velero.io/backup-uid
        filtered_items = [
            item for item in backups.get('items', [])
            if item.get('metadata', {}).get('labels', {}).get('velero.io/backup-name') == backup_name
        ] if backup_name else backups.get('items', [])

        # Return only filtered objects
        return filtered_items
    except Exception as e:
        print(f"Error: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Error {str(e)}")


#
# velero resource bsl e vsl
#

@trace_k8s_async_method(description="get s3 credential")
async def get_credential_service(secret_name, secret_key):
    api_instance = client.CoreV1Api()

    # LS 2024.20.22 use env variable
    # secret = api_instance.read_namespaced_secret(name=secret_name, namespace='velero')
    secret = api_instance.read_namespaced_secret(name=secret_name,
                                                 namespace=os.getenv('K8S_VELERO_NAMESPACE', 'velero'))
    if secret.data and secret_key in secret.data:
        value = secret.data[secret_key]
        decoded_value = base64.b64decode(value)
        payload = _parse_config_string(decoded_value.decode('utf-8'))
        return payload
    else:
        raise HTTPException(status_code=400, detail=f"Secret key not found")


@trace_k8s_async_method(description="get default s3 credential")
async def get_default_credential_service():
    label_selector = 'app.kubernetes.io/name=velero'
    api_instance = client.CoreV1Api()

    secret = api_instance.list_namespaced_secret(namespace=os.getenv('K8S_VELERO_NAMESPACE', 'velero'),
                                                 label_selector=label_selector)

    if secret.items[0].data:
        value = secret.items[0].data['cloud']
        decoded_value = base64.b64decode(value)

        payload = _parse_config_string(decoded_value.decode('utf-8'))

        return payload
    else:
        raise HTTPException(status_code=400, detail=f"Secret key not found")


@trace_k8s_async_method(description="create cloud credentials")
async def create_cloud_credentials_secret_service(secret_name: str, secret_key: str, aws_access_key_id: str,
                                                  aws_secret_access_key: str):
    namespace = config_app.get_k8s_velero_namespace()

    # Base64 content encode
    credentials_content = f"""
[default]
aws_access_key_id={aws_access_key_id}
aws_secret_access_key={aws_secret_access_key}
"""
    credentials_base64 = base64.b64encode(credentials_content.encode("utf-8")).decode("utf-8")

    # Create Secret
    secret = client.V1Secret(metadata=client.V1ObjectMeta(name=secret_name, namespace=namespace),
                             data={f"""{secret_key}""": credentials_base64}, type="Opaque")

    # API client 4 Secrets
    api_instance = client.CoreV1Api()

    try:
        # Create Secret
        api_instance.create_namespaced_secret(namespace=namespace, body=secret)
        print(f"Secret '{secret_name}' create in '{namespace}' namespace.")
        return True

    except client.exceptions.ApiException as e:
        raise HTTPException(status_code=400, detail=f"Exception when create cloud credentials: {e}")


