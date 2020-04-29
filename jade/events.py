"""
This module contains StructuredLogEvent and EventSummary classes.
"""

import json
import os
import re
import sys
from datetime import datetime

from prettytable import PrettyTable

from jade.common import JOBS_OUTPUT_DIR
from jade.utils.utils import dump_data, get_filenames_in_path, load_data


EVENTS_FILENAME = "events.json"

EVENT_CATEGORY_ERROR = "Error"
EVENT_CATEGORY_HPC = "HPC"
EVENT_CATEGORY_RESOURCE_UTIL = "ResourceUtilization"

EVENT_NAME_HPC_SUBMIT = "hpc_submit"
EVENT_NAME_HPC_JOB_ASSIGNED = "hpc_job_assigned"
EVENT_NAME_HPC_JOB_STATE_CHANGE = "hpc_job_state_change"
EVENT_NAME_CPU_STATS = "cpu_stats"
EVENT_NAME_DISK_STATS = "disk_stats"
EVENT_NAME_MEMORY_STATS = "mem_stats"
EVENT_NAME_NETWORK_STATS = "net_stats"
EVENT_NAME_UNHANDLED_ERROR = "error"


class StructuredLogEvent(object):
    """
    A class for recording structured log events.
    """
    def __init__(self, source, category, name, message, **kwargs):
        """
        Initialize the class

        Parameters
        ----------
        source: str,
            The source of the event.
        category: str,
            An event category given by the user.
        name: str,
            An event name given by the user.
        message:
            An event message given the user.

        kwargs:
            Other information that the user needs to record into event.
        """
        self.source = source
        self.category = category
        self.name = name
        self.message = message

        if "timestamp" in kwargs:
            self.timestamp = kwargs.pop("timestamp")
        else:
            self.timestamp = str(datetime.now())

        self.data = kwargs

    def base_field_names(self):
        """Return the base field names for the event.

        Returns
        -------
        list

        """
        return self._base_field_names()

    def _base_field_names(self):
        return ["timestamp", "source"]

    def field_names(self):
        """Return all field names for the event.

        Returns
        -------
        list

        """
        return self.base_field_names() + list(self.data.keys())

    def values(self):
        """Return the values for all fields in the event.

        Returns
        -------
        list

        """
        values = [self.__getattribute__(x) for x in self.base_field_names()]
        # Account for events generated with different versions of code.
        values += [self.data.get(x, "") for x in self.data.keys()]
        return values

    @classmethod
    def deserialize(cls, record):
        """Deserialize event from JSON.

        Parameters
        ----------
        record : dict

        Returns
        -------
        StructuredLogEvent

        """
        # TODO: this only creates StructuredLogEvent...not subtypes.
        return cls(
            source=record.get("source", ""),
            category=record.get("category", ""),
            name=record.get("name", ""),
            message=record.get("message", ""),
            timestamp=record.get("timestamp", ""),
            **record["data"]
        )

    def __str__(self):
        """To format a event instance to string"""
        return json.dumps(self.__dict__, sort_keys=True)

    def to_dict(self):
        """Convert event object to dict"""
        return self.__dict__


class StructuredErrorLogEvent(StructuredLogEvent):
    """Event specific to exceptions"""

    def __init__(self, **kwargs):
        """Must be called in an exception context."""
        super().__init__(**kwargs)
        self._parse_traceback()

    def base_field_names(self):
        return self._base_field_names() + ["message"]

    def _parse_traceback(self):
        """
        Parse the system exception information - exception, filename, and lineno.
        """
        exc_type, exc_obj, tb = sys.exc_info()
        assert tb is not None, "must be called in an exception context"

        self.data["exception"] = str(exc_type)
        self.data["error"] = str(exc_obj).strip()
        self.data["filename"] = os.path.basename(tb.tb_frame.f_code.co_filename)
        self.data["lineno"] = tb.tb_lineno


class EventsSummary(object):
    """Provides summary of all events."""

    def __init__(self, output_dir):
        """
        Initialize EventsSummary class

        Parameters
        ----------
        output_dir: str
            Path of jade output directory.

        """
        self._output_dir = output_dir
        self._job_outputs_dir = os.path.join(output_dir, JOBS_OUTPUT_DIR)
        self._summary_file = os.path.join(output_dir, EVENTS_FILENAME)
        if os.path.exists(self._summary_file):
            self._events = [
                StructuredLogEvent.deserialize(x) for x in load_data(self._summary_file)
            ]
        else:
            self._events = self._consolidate_events()
            self._save_events_summary()

    def _most_recent_event_files(self):
        """
        Find most recent event log files in job outputs directory.

        Examples
        --------
        a/events.log
        a/events.log.1
        a/events.log.2

        b/events.log
        b/events.log.1
        b/events.log.2
        ...
        event_files = [a/events.log, b/events.log]

        Returns
        -------
        list, a list of event log files.
        """
        regex = re.compile(r"\w*events.log")
        return get_filenames_in_path(self._output_dir, regex, is_regex=True)

    def _consolidate_events(self):
        """Find most recent event log files, and merge event data together."""
        events = []
        for event_file in self._most_recent_event_files():
            with open(event_file, "r") as f:
                for line in f.readlines():
                    record = json.loads(line)
                    event = StructuredLogEvent.deserialize(record)
                    events.append(event)
        events.sort(key=lambda x: x.timestamp)
        return events

    def _save_events_summary(self):
        """Save all events data to a JSON file"""
        dict_events = [event.to_dict() for event in self._events]
        dump_data(dict_events, self._summary_file)

    @property
    def events(self):
        """Return the events.

        Returns
        -------
        list
            list of StructuredLogEvent

        """
        return self._events

    def to_json(self):
        """Return the events in JSON format.

        Returns
        -------
        str

        """
        return json.dumps([x.to_dict() for x in self._events], indent=4)

    def list_events(self, name):
        """Return the events of type name.

        Returns
        -------
        list
            list of StructuredLogEvent

        """
        return [x for x in self._events if x.name == name]

    def list_unique_names(self):
        """Return the unique event names in the log.

        Returns
        -------
        list

        """
        names = set()
        for event in self._events:
            names.add(event.name)

        names = list(names)
        names.sort()
        return names

    def _iter_events(self, name):
        for event in self._events:
            if event.name == name:
                yield event

    def show_events(self, name):
        """Print tabular events in terminal"""
        table = PrettyTable()

        field_names = None
        count = 0
        for event in self._iter_events(name):
            if field_names is None:
                field_names = event.field_names()
            table.add_row(event.values())
            count += 1

        if count == 0:
            print(f"No events of type {name}")
            return

        table.field_names = field_names
        print(f"Events of type {name} from directory: {self._output_dir}")
        print(table)
        print(f"Total events: {count}\n")

    def show_event_names(self):
        """Show the unique event names in the log."""
        print("Names:  {}".format(" ".join(self.list_unique_names())))
