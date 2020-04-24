"""CLI to automatically create a configuration."""

import logging
import sys

import click

from jade.common import CONFIG_FILE
from jade.loggers import setup_logging
from jade.exceptions import InvalidExtension
from jade.extensions.registry import Registry, ExtensionClassType
from jade.jobs.job_post_process import JobPostProcess
from jade.utils.utils import load_data


# TODO: need one group command for auto-config; this should be a subcommand.


@click.command()
@click.argument("extension")
@click.argument("inputs", nargs=-1)
@click.option(
    "-p",
    "--job-post-process-config-file",
    type=click.Path(exists=True),
    is_eager=True,
    help="The path of job-based post-process config file.",
)
@click.option(
    "-d",
    "--previous-stage-outputs",
    type=click.Path(exists=True),
    multiple=True,
    default=[],
    help="One or more previous stage output direcotries."
)
@click.option(
    "-c",
    "--config-file",
    default=CONFIG_FILE,
    show_default=True,
    help="config file to generate.",
)
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    default=False,
    show_default=True,
    help="Enable verbose log output.",
)
def auto_config(
        extension,
        inputs,
        job_post_process_config_file,
        previous_stage_outputs,
        config_file,
        verbose):
    """Automatically create a configuration."""
    level = logging.DEBUG if verbose else logging.WARNING
    setup_logging("auto_config", None, console_level=level)

    if job_post_process_config_file is not None:
        module, class_name, data = JobPostProcess.load_config_from_file(
            job_post_process_config_file
        )
        JobPostProcess(module, class_name, data)  # ensure everything ok
        job_post_process_config = {"module": module, "class_name": class_name, "data": data}
    else:
        job_post_process_config = None

    # User extension
    registry = Registry()
    if not registry.is_registered(extension):
        raise InvalidExtension(f"Extension '{extension}' is not registered.")

    cli = registry.get_extension_class(extension, ExtensionClassType.CLI)
    try:
        config = cli.auto_config(
            *inputs,
            job_post_process_config=job_post_process_config
        )
    except TypeError as err:
        docstring = cli.auto_config.__doc__
        print(
            f"\nERROR:  Auto-config parameter mismatch for extension {extension}." + \
            f"Its docstring is below.\n\n{docstring}\n\nPlease try again with the current parameters"
        )
        sys.exit(1)

    print(f"Created configuration with {config.get_num_jobs()} jobs.")
    config.dump(config_file)
    print(f"Dumped configuration to {config_file}.\n")
