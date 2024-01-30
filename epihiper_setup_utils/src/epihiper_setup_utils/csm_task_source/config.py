"""Configuration for the controller."""

import sys
from typing import Optional

from pydantic import BaseSettings, DirectoryPath, FilePath, ValidationError

class CsmTaskSourceConfig(BaseSettings):
    key_file: FilePath
    cert_file: FilePath
    controller_host: str
    controller_port: int

    work_dir: DirectoryPath

    run_name: str
    setup_dir: DirectoryPath
    num_replicates: int
    multiplier: int
    max_runtime: str

    max_evals: int
    n_iter_no_change: int
    min_rel_improvement: float
    make_y_positive: bool

    class Config:
        env_prefix = "CSMTS_"


_CSMTS_CONFIG: Optional[CsmTaskSourceConfig] = None


def get_csmts_config() -> CsmTaskSourceConfig:
    global _CSMTS_CONFIG

    if _CSMTS_CONFIG is None:
        try:
            _CSMTS_CONFIG = CsmTaskSourceConfig()  # type: ignore
        except ValidationError as e:
            print("Failed to obtain valid Convex Scalar Minimizer Task Source config: %s" % e)
            sys.exit(1)

    return _CSMTS_CONFIG


if __name__ == "__main__":
    from rich import print
    print(get_csmts_config())
