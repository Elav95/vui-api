from typing import Optional, Dict, List

from pydantic import BaseModel
from configs.config_boot import config_app


class CreateScheduleRequestSchema(BaseModel):
    name: str
    namespace: Optional[str] = config_app.k8s.velero_namespace

    # spec
    schedule: str
    paused: Optional[bool] = False
    useOwnerReferencesInBackup: Optional[bool] = False

    # spec.template
    csiSnapshotTimeout: Optional[str] = "10m"
    includedNamespaces: Optional[List[str]] = None
    excludedNamespaces: Optional[List[str]] = None
    includedResources: Optional[List[str]] = None
    excludedResources: Optional[List[str]] = None
    orderedResources: Optional[Dict[str, List[str]]] = None
    includeClusterResources: Optional[bool] = None
    excludedClusterScopedResources: Optional[List[str]] = None
    includedClusterScopedResources: Optional[List[str]] = None
    excludedNamespaceScopedResources: Optional[List[str]] = None
    includedNamespaceScopedResources: Optional[List[str]] = None
    snapshotVolumes: Optional[bool] = None
    storageLocation: Optional[str] = None
    volumeSnapshotLocations: Optional[List[str]] = None
    ttl: Optional[str] = "24h"
    defaultVolumesToFsBackup: Optional[bool] = None
    snapshotMoveData: Optional[bool] = None
    datamover: Optional[str] = None

    # spec childs
    labelSelector: Optional[Dict[str, str]] = None  # "matchLabels": {"app": "velero", "component": "server"},
    parallelFilesUpload: Optional[int] = 10
