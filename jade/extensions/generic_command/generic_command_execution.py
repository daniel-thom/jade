"""The job execution class and methods for generic_command."""

import logging

from jade.jobs.job_execution_interface import JobExecutionInterface


logger = logging.getLogger(__name__)


class GenericCommandExecution(JobExecutionInterface):
    """A class used for executing a generic_command."""
    def __init__(self, job, output):
        """Init generic_command execution class

        Parameters
        ----------
        job: :obj:`GenericCommandParameters`
            The instance of :obj:`GenericCommandParameters`
        output: str,
            The path to the output directory.

        """
        self._job = job
        self._output = output

    @property
    def results_directory(self):
        return self._output

    @classmethod
    def create(cls, _, job, output):
        return cls(job, output)

    @staticmethod
    def generate_command(job, output, config_file, verbose=False):
        # These jobs already have a command and are not run with jade-internal.
        return job.command

    def list_results_files(self):
        return []

    def post_process(self, **kwargs):
        pass

    def run(self):
        assert False
