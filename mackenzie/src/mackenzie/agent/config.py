"""Configuration for the agent."""

import sys
from typing import Optional

from pydantic import BaseSettings, DirectoryPath, FilePath, ValidationError


class AgentConfig(BaseSettings):
    key_file: FilePath
    cert_file: FilePath
    setup_root: DirectoryPath

    cluster: str
    max_load: int

    controller_host: str
    controller_port: int

    class Config:
        env_prefix = "AGENT_"


_AGENT_CONFIG: Optional[AgentConfig] = None


def get_agent_config() -> AgentConfig:
    global _AGENT_CONFIG

    if _AGENT_CONFIG is None:
        try:
            _AGENT_CONFIG = AgentConfig()  # type: ignore
        except ValidationError as e:
            print("Failed to obtain valid agent config: %s" % e)
            sys.exit(1)

    return _AGENT_CONFIG


if __name__ == "__main__":
    from rich import print

    print(get_agent_config())
