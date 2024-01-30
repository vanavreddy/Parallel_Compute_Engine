"""EpiHiper projection setup parser."""

from pathlib import Path

from pydantic import BaseModel


def is_epihiper_config_dir(p: Path):
    if not (p / "traits").exists():
        return False
    if not (p / "initialization").exists():
        return False
    if not (p / "intervention").exists():
        return False
    if not (p / "diseaseModel").exists():
        return False
    if not (p / "runParameters.json").exists():
        return False
    return True


class ProjectionPlace(BaseModel):
    place_name: str
    priority: int


class ProjectionCell(BaseModel):
    cell_name: str
    places: list[ProjectionPlace]


class ProjectionSetup(BaseModel):
    setup_name: str
    cells: list[ProjectionCell]


def parse_projection_cell(dir_path: Path) -> ProjectionCell:
    cell_name = dir_path.name

    places: list[ProjectionPlace] = []
    for child in dir_path.iterdir():
        if child.is_dir() and is_epihiper_config_dir(child):
            place_name = child.name
            priority_file = child / "priority"
            if priority_file.exists():
                priority = int(priority_file.read_text())
            else:
                priority = 1
            places.append(ProjectionPlace(place_name=place_name, priority=priority))

    return ProjectionCell(cell_name=cell_name, places=places)


def parse_projection_setup(dir_path: Path) -> ProjectionSetup:
    setup_name = dir_path.name
    cells = []

    for child in dir_path.iterdir():
        if child.is_dir():
            cells.append(parse_projection_cell(child))

    return ProjectionSetup(setup_name=setup_name, cells=cells)
