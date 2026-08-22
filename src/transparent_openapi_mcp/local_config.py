"""The local mounted config file (R-DEPLOY-002).

Small and separate from ConfigList (config_model.py): this is what
`podman run -v <local file>:<path>:ro` mounts into the container. It
tells the server where to fetch the real config list from, and
optionally which config to preselect (R-BOOT-001) - taking
precedence over the config list's own `preselected` field, per
ServerState.boot()'s preselected_override parameter.
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class LocalConfig(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    config_list_url: str
    preselected: str | None = None


def load_local_config(path: str) -> LocalConfig:
    """Read and parse the mounted local config file at path."""
    with open(path, encoding="utf-8") as f:
        return LocalConfig.model_validate_json(f.read())
