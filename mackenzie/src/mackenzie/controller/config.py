"""Configuration for the controller."""

import sys
from typing import Optional

from pydantic import BaseSettings, DirectoryPath, FilePath, ValidationError


class ControllerConfig(BaseSettings):
    key_file: FilePath
    cert_file: FilePath
    setup_root: DirectoryPath

    task_timeout: int

    controller_host: str
    controller_port: int

    class Config:
        env_prefix = "CONTROLLER_"


_CONTROLLER_CONFIG: Optional[ControllerConfig] = None


def get_controller_config() -> ControllerConfig:
    global _CONTROLLER_CONFIG

    if _CONTROLLER_CONFIG is None:
        try:
            _CONTROLLER_CONFIG = ControllerConfig()  # type: ignore
        except ValidationError as e:
            print("Failed to obtain valid controller config: %s" % e)
            sys.exit(1)

    return _CONTROLLER_CONFIG


if __name__ == "__main__":
    from rich import print

    print(get_controller_config())
