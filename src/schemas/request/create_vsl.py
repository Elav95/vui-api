from pydantic import BaseModel, Field
from typing import Optional, Dict
from configs.config_boot import config_app


class CreateVslRequestSchema(BaseModel):
    name: str = Field(..., description="The name of the BSL.")
    namespace: Optional[str] = config_app.k8s.velero_namespace
    provider: str = Field(..., description="The name of the provider.")

    config: Optional[Dict[str, str]] = Field(None, description="Configuration fields.")

    credentialName: str = Field(..., description="The name of the existing secret containing credentials.")
    credentialKey: str = Field(..., description="The key within the secret for the credentials.")
