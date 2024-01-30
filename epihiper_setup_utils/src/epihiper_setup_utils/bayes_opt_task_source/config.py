"""Configuration for the Bayesian Optimizer Task Source."""

import sys
from typing import Optional

from pydantic import BaseSettings, DirectoryPath, FilePath, ValidationError

class BayesOptTaskSourceConfig(BaseSettings):
    key_file: FilePath
    cert_file: FilePath
    controller_host: str
    controller_port: int

    work_dir: DirectoryPath

    run_name: str
    setup_dir: DirectoryPath
    multiplier: int
    max_runtime: str

    init_evals: int
    explore_evals: int
    exploit_evals: int
    parallel_evals: int
    kappa_initial: float
    kappa_scale: float

    class Config:
        env_prefix = "BOTS_"


_BOTS_CONFIG: Optional[BayesOptTaskSourceConfig] = None


def get_bots_config() -> BayesOptTaskSourceConfig:
    global _BOTS_CONFIG

    if _BOTS_CONFIG is None:
        try:
            _BOTS_CONFIG = BayesOptTaskSourceConfig()  # type: ignore
        except ValidationError as e:
            print("Failed to obtain valid Bayesian Minimizer Task Source config: %s" % e)
            sys.exit(1)

    return _BOTS_CONFIG


if __name__ == "__main__":
    from rich import print
    print(get_bots_config())
