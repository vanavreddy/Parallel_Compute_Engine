"""EpiHiper Calibration setup parser."""

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


def is_calibration_cell_dir(p: Path):
    if not (p / "range.json").exists():
        return False
    if not (p / "objective").exists():
        return False
    if not (p / "updateParameter").exists():
        return False
    return True


class ParamRange(BaseModel):
    name: str
    min: float
    max: float


class ParamRanges(BaseModel):
    parameters: list[ParamRange]


class CalibrationPlace(BaseModel):
    place_name: str
    priority: int


class CalibrationCell(BaseModel):
    cell_name: str
    param_ranges: ParamRanges
    places: list[CalibrationPlace]


class CalibrationSetup(BaseModel):
    setup_name: str
    cells: list[CalibrationCell]


def parse_calibration_cell(dir_path: Path) -> CalibrationCell:
    cell_name = dir_path.name
    param_ranges = ParamRanges.parse_file(dir_path / "range.json")

    places: list[CalibrationPlace] = []
    for child in dir_path.iterdir():
        if child.is_dir() and is_epihiper_config_dir(child):
            place_name = child.name
            priority_file = child / "priority"
            if priority_file.exists():
                priority = int(priority_file.read_text())
            else:
                priority = 1
            places.append(CalibrationPlace(place_name=place_name, priority=priority))

    return CalibrationCell(
        cell_name=cell_name, param_ranges=param_ranges, places=places
    )


def parse_calibration_setup(dir_path: Path) -> CalibrationSetup:
    setup_name = dir_path.name
    cells = []

    for child in dir_path.iterdir():
        if child.is_dir() and is_calibration_cell_dir(child):
            cells.append(parse_calibration_cell(child))

    return CalibrationSetup(setup_name=setup_name, cells=cells)
