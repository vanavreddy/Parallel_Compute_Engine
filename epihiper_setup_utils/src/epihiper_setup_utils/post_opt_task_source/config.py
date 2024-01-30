"""Configuration for the Post Optimizer Run Task Source."""

import sys
from typing import Optional

from pydantic import BaseSettings, DirectoryPath, FilePath, ValidationError

class PostOptTaskSourceConfig(BaseSettings):
    key_file: FilePath
    cert_file: FilePath
    controller_host: str
    controller_port: int

    run_name: str
    setup_dir: DirectoryPath
    multiplier: int
    max_runtime: str

    num_evals: int
    opt_status_file: FilePath

    class Config:
        env_prefix = "POTS_"


_POTS_CONFIG: Optional[PostOptTaskSourceConfig] = None


def get_pots_config() -> PostOptTaskSourceConfig:
    global _POTS_CONFIG

    if _POTS_CONFIG is None:
        try:
            _POTS_CONFIG = PostOptTaskSourceConfig()  # type: ignore
        except ValidationError as e:
            print("Failed to obtain valid Post Optimizer Run Task Source config: %s" % e)
            sys.exit(1)

    return _POTS_CONFIG


if __name__ == "__main__":
    from rich import print
    print(get_pots_config())
