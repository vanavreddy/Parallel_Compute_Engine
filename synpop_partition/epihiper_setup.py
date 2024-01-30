"""EpiHiper setup."""

import json

import click

from epihiper_setup_common import (
    ensure_absolute,
    copy_file_and_return_new_path,
    opt_ContactNetworkFile,
    opt_PersontraitFile,
    opt_CellConfigDir,
    opt_DbHost,
    opt_Replicate,
    opt_LogLevel,
    opt_OutputDir,
)


@click.command()
@opt_ContactNetworkFile
@opt_PersontraitFile
@opt_CellConfigDir
@opt_DbHost
@opt_Replicate
@opt_LogLevel
@opt_OutputDir
def main(
    contact_network_file,
    persontrait_file,
    cell_config_dir,
    db_host,
    replicate,
    log_level,
    output_dir,
):
    """Setup output diectory for an EpiHiper run."""
    contact_network_file = ensure_absolute(contact_network_file)
    persontrait_file = ensure_absolute(persontrait_file)
    cell_config_dir = ensure_absolute(cell_config_dir)
    output_dir = ensure_absolute(output_dir)

    # Get all necessary config files
    traits_file = cell_config_dir / "traits"
    disease_model_file = cell_config_dir / "diseaseModel"
    initialization_file = cell_config_dir / "initialization"
    intervention_file = cell_config_dir / "intervention"
    input_run_params_file = cell_config_dir / "runParameters.json"

    # Copy over all the config files
    traits_file = copy_file_and_return_new_path(traits_file, output_dir)
    disease_model_file = copy_file_and_return_new_path(disease_model_file, output_dir)
    initialization_file = copy_file_and_return_new_path(initialization_file, output_dir)
    intervention_file = copy_file_and_return_new_path(intervention_file, output_dir)

    add_noise_file = cell_config_dir / "addNoise.sh"
    if add_noise_file.exists():
        copy_file_and_return_new_path(add_noise_file, output_dir)

    # Create the scenario.json file
    scenario = {
        "epiHiperSchema": "https://github.com/NSSAC/EpiHiper-Schema/blob/master/schema/modelScenarioSchema.json",
        "contactNetwork": contact_network_file,
        "personTraitDB": [persontrait_file],
        "traits": traits_file,
        "diseaseModel": disease_model_file,
        "initialization": initialization_file,
        "intervention": intervention_file,
    }

    scenario_file = output_dir / "scenario.json"
    scenario_file.write_text(json.dumps(scenario, default=str), encoding="utf-8")

    # Create the config.json file
    # Read input config from the input run params file
    # Update it with the stuff we want to update it with
    # Write it out as config.json
    run_parameters = json.loads(input_run_params_file.read_text())
    run_parameters_update = {
        "epiHiperSchema": "https://github.com/NSSAC/EpiHiper-Schema/blob/master/schema/runParametersSchema.json",
        "modelScenario": scenario_file,
        "output": output_dir / "output.csv",
        "replicate": replicate,
        "dbHost": db_host,
        "logLevel": log_level,
        "summaryOutput": output_dir / "outputSummary.csv",
        "status": output_dir / "status.json",
        "dbMaxRecords": 1000000,
        "dbConnectionTimeout": 20,
        "dbConnectionRetries": 10,
        "dbConnectionMaxDelay": 10000,
    }
    run_parameters.update(run_parameters_update)
    output_run_params_file = output_dir / "config.json"
    output_run_params_file.write_text(
        json.dumps(run_parameters, default=str), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
