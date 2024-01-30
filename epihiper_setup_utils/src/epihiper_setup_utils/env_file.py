"""Environmnet file parser."""

import json
from pathlib import Path

from dotenv import dotenv_values
from pydantic import BaseModel, DirectoryPath, FilePath


class EnvFile(BaseModel):
    cluster: str

    partition_cache_dir: DirectoryPath
    synpop_root: DirectoryPath
    dbhost_ip_file: FilePath

    epihiper_log_level: str
    pipeline_sbatch_args: str
    max_fails: int


def place_to_synpop(place: str) -> str:
    if len(place) == 2:
        return f"usa_{place}_2017_SynPop"
    else:
        return place


class EnvironmentConfig:
    def __init__(self, env_file: Path):
        env = dotenv_values(str(env_file))
        env = {k.lower(): v for k, v in env.items()}
        self.env = EnvFile.parse_obj(env)
        self.env_file_contents = env_file.read_text()

    def get_contact_network_file(self, place: str, multipiler: int) -> str:
        synpop = place_to_synpop(place)
        partition_dir = self.env.partition_cache_dir / synpop / str(multipiler)
        contact_network_file = partition_dir / "contact_network.txt"
        assert contact_network_file.exists()
        return str(contact_network_file)

    def get_job_sbatch_args(self, place: str, multipiler: int) -> str:
        synpop = place_to_synpop(place)
        partition_cache_dir = self.env.partition_cache_dir
        sbatch_args_file = (
            partition_cache_dir / synpop / str(multipiler) / "sbatch_args.txt"
        )
        return sbatch_args_file.read_text().strip()

    def get_load(self, place: str, multipiler: int) -> int:
        synpop = place_to_synpop(place)
        partition_dir = self.env.partition_cache_dir / synpop / str(multipiler)
        partition_config_file = partition_dir / "config.json"
        partition_config = partition_config_file.read_text()
        partition_config = json.loads(partition_config)
        load = partition_config["numberOfParts"]
        return load

    def get_persontrait_file(self, place: str) -> str:
        synpop = place_to_synpop(place)
        synpop_dir = self.env.synpop_root / synpop
        persontrait_file = synpop_dir.glob("*_persontrait_epihiper.txt")
        persontrait_file = list(persontrait_file)
        persontrait_file = persontrait_file[0]
        persontrait_file = str(persontrait_file)
        return persontrait_file

    def get_dbhost(self) -> str:
        dbhost_ip_file = self.env.dbhost_ip_file
        dbhost_ip = dbhost_ip_file.read_text().strip()
        return dbhost_ip
