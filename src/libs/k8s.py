import os
import json
import base64
import configparser
from kubernetes import client, config
from dotenv import load_dotenv

from helpers.handle_exceptions import *
from datetime import datetime

load_dotenv()


class K8s:

    def __init__(self):

        if os.getenv('K8S_IN_CLUSTER_MODE').lower() == 'true':
            config.load_incluster_config()
        else:
            self.kube_config_file = os.getenv('KUBE_CONFIG_FILE')
            config.load_kube_config(config_file=self.kube_config_file)

        self.v1 = client.CoreV1Api()
        self.client = client.CustomObjectsApi()

    @handle_exceptions_instance_method
    def get_ns(self):

        # Get namespaces list
        namespace_list = self.v1.list_namespace()
        # Extract namespace list
        namespaces = [namespace.metadata.name for namespace in namespace_list.items]

        return namespaces

    @handle_exceptions_instance_method
    def get_resources(self):
        # TODO: not working yet, get all resource type name for populate multiselect in front end
        resource_list = self.client.get_api_resources(group='*', version='*')
        return resource_list

    @handle_exceptions_async_method
    async def update_velero_schedule(self, new_data):

        namespace = os.getenv('K8S_VELERO_NAMESPACE')

        velero_resource_name = new_data['oldName']

        try:
            # get resource velero
            velero_resource = self.client.get_namespaced_custom_object(
                group='velero.io',
                version='v1',
                name=velero_resource_name,
                namespace=namespace,
                plural='schedules',
            )

            # update field
            velero_resource['spec']['schedule'] = new_data['schedule']
            if 'includedNamespaces' in new_data:
                velero_resource['spec']['template']['includedNamespaces'] = new_data['includedNamespaces']
            if 'excludedNamespaces' in new_data:
                velero_resource['spec']['template']['excludedNamespaces'] = new_data['excludedNamespaces']
            if 'includedResources' in new_data:
                velero_resource['spec']['template']['includedResources'] = new_data['includedResources']
            if 'excludedResources' in new_data:
                velero_resource['spec']['template']['excludedResources'] = new_data['excludedResources']

            if 'includeClusterResources' in new_data:
                if new_data['includeClusterResources'] == 'true':
                    velero_resource['spec']['template']['includeClusterResources'] = True
                elif new_data['includeClusterResources'] == 'false':
                    velero_resource['spec']['template']['includeClusterResources'] = False
                else:
                    velero_resource['spec']['template']['includeClusterResources'] = None

            if 'backupLocation' in new_data:
                velero_resource['spec']['template']['storageLocation'] = new_data['backupLocation']

            if 'snapshotLocation' in new_data:
                velero_resource['spec']['template']['volumeSnapshotLocations'] = new_data['snapshotLocation']

            if 'snapshotVolumes' in new_data:
                velero_resource['spec']['template']['snapshotVolumes'] = new_data['snapshotVolumes']

            if 'defaultVolumesToFsBackup' in new_data:
                velero_resource['spec']['template']['defaultVolumesToFsBackup'] = new_data['defaultVolumesToFsBackup']

            if 'backupLevel' in new_data and 'selector' in new_data:
                if new_data['backupLabel'] != '' and new_data['selector'] != '':
                    if 'labelSelector' not in velero_resource['spec']['template']:
                        velero_resource['spec']['template']['labelSelector'] = {}
                    if 'matchLabels' not in velero_resource['spec']['template']['labelSelector']:
                        velero_resource['spec']['template']['labelSelector'] = {}
                    velero_resource['spec']['template']['labelSelector']['matchLabels'] = {
                        new_data['backupLabel']: new_data['selector']}

            # execute update data
            self.client.replace_namespaced_custom_object(
                group='velero.io',
                version='v1',
                name=velero_resource_name,
                namespace=namespace,
                plural='schedules',
                body=velero_resource,
            )

            print(f"Velero's schedule '{velero_resource_name}' successfully updated.")
            return {'data': 'done'}
        except Exception as e:
            print(f"Error in updating Velero's schedule '{velero_resource_name}': {e}")
            return {'error': {'title': 'Error',
                              'description': f"error: {e}"}
                    }

    def parse_config_string(self, config_string):

        # Create a ConfigParser object
        config_parser = configparser.ConfigParser()

        # read string
        config_parser.read_string(config_string)

        # extract values
        aws_access_key_id = config_parser.get('default', 'aws_access_key_id', fallback=None)
        aws_secret_access_key = config_parser.get('default', 'aws_secret_access_key', fallback=None)

        # crete dict
        result = {
            'aws_access_key_id': aws_access_key_id,
            'aws_secret_access_key': aws_secret_access_key
        }

        return result

    @handle_exceptions_async_method
    async def get_credential(self, secret_name, secret_key):
        if not secret_name or not secret_key:
            return {'error': {'title': 'Error',
                              'description': 'Secret name and secret key are required'
                              }
                    }
        api_instance = self.v1

        secret = api_instance.read_namespaced_secret(name=secret_name, namespace='velero')
        if secret.data and secret_key in secret.data:
            value = secret.data[secret_key]
            decoded_value = base64.b64decode(value)
            return {'data': self.parse_config_string(decoded_value.decode('utf-8'))}
        else:
            return json.dumps({'error': 'Secret key not found'}, indent=2)

    @handle_exceptions_async_method
    async def get_default_credential(self):
        label_selector = 'app.kubernetes.io/name=velero'
        api_instance = self.v1

        secret = api_instance.list_namespaced_secret('velero', label_selector=label_selector)

        if secret.items[0].data:
            value = secret.items[0].data['cloud']
            decoded_value = base64.b64decode(value)
            return {'data': self.parse_config_string(decoded_value.decode('utf-8'))}
        else:
            return json.dumps({'error': 'Secret key not found'}, indent=2)

    @handle_exceptions_async_method
    async def get_k8s_online(self):
        ret = False
        try:
            # Listing the cluster nodes
            node_list = self.v1.list_node()
            if node_list is not None:
                ret = True
        except Exception as Ex:
            ret = False
        return {'error': {
            'status': ret,
            'timestamp': datetime.utcnow()}
        }
