"""Configuration for the Projection Optimizer Task Source."""

import sys
from typing import Optional

from pydantic import BaseSettings, DirectoryPath, FilePath, ValidationError

class ProjTaskSourceConfig(BaseSettings):
    key_file: FilePath
    cert_file: FilePath
    controller_host: str
    controller_port: int

    run_name: str
    setup_dir: DirectoryPath
    multiplier: int
    max_runtime: str

    start_batch: int
    num_replicates: list[int]

    class Config:
        env_prefix = "PTS_"


_PTS_CONFIG: Optional[ProjTaskSourceConfig] = None


def get_pts_config() -> ProjTaskSourceConfig:
    global _PTS_CONFIG

    if _PTS_CONFIG is None:
        try:
            _PTS_CONFIG = ProjTaskSourceConfig()  # type: ignore
        except ValidationError as e:
            print("Failed to obtain valid Bayesian Minimizer Task Source config: %s" % e)
            sys.exit(1)

    return _PTS_CONFIG


if __name__ == "__main__":
    from rich import print
    print(get_pts_config())
