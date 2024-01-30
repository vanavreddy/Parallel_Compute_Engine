"""Configuration for the command line interface."""

import sys
from typing import Optional

from pydantic import BaseSettings, FilePath, ValidationError


class CmdConfig(BaseSettings):
    key_file: FilePath
    cert_file: FilePath

    controller_host: str
    controller_port: int

    class Config:
        env_prefix = "CMD_"


_CMD_CONIFG: Optional[CmdConfig] = None


def get_cmd_config() -> CmdConfig:
    global _CMD_CONIFG

    if _CMD_CONIFG is None:
        try:
            _CMD_CONIFG = CmdConfig()  # type: ignore
        except ValidationError as e:
            print("Failed to obtain valid command line config: %s" % e)
            sys.exit(1)

    return _CMD_CONIFG


if __name__ == "__main__":
    from rich import print

    print(get_cmd_config())
