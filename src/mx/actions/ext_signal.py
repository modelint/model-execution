""" ext_signal.py -- Executes an External Signal Action as defined in the SM Metamodel """

# System
import logging
from typing import TYPE_CHECKING, NamedTuple

from mx.mxtypes import StateMachineType

if TYPE_CHECKING:
    from mx.activity_execution import ActivityExecution

# Model Integration
from pyral.relation import Relation
from pyral.relation import _relation  # For table_msg
from pyral.database import Database  # Diagnostics

# MX
from mx.log_table_config import TABLE, log_table
from mx.message import *
from mx.db_names import mmdb
from mx.actions.action_execution import ActionExecution
from mx.actions.flow import ActiveFlow
from mx.completion_event import CompletionEvent
from mx.interaction_event import InteractionEvent
from mx.rvname import declare_rvs
from mx.mxtypes import *

_logger = logging.getLogger(__name__)


class MMRVs(NamedTuple):
    ext_signal_action: str


# This wrapper calls the imported declare_rvs function to generate a NamedTuple instance with each of our
# variables above as a member.
def declare_mm_rvs(owner: str) -> MMRVs:
    rvs = declare_rvs(mmdb, owner,
                      "ext_signal_action",
                      )
    return MMRVs(*rvs)


class ExtSignal(ActionExecution):
    """
    See the Signal Action subsystem class model to find all referenced classes in the comments
    in this python module.
    """
    def __init__(self, action_id: str, activity_execution: "ActivityExecution"):
        super().__init__(activity_execution=activity_execution, action_id=action_id)

        # Do not execute this Action if it is not enabled, see comment in Action class
        if self.disabled:
            return

        # Get a NamedTuple with a field for each relation variable name
        self.mmrv = declare_mm_rvs(owner=self.owner)

        Relation.semijoin(db=mmdb, rname1=self.action_mmrv, rname2="External Signal Action",
                                                svar_name=self.mmrv.ext_signal_action)
        # We need to add the implicit boolean attribute from External Event via R1281
        ext_signal_action_r = Relation.join(db=mmdb, rname1=self.mmrv.ext_signal_action, rname2="External Event",
                            attrs={"External_event": "Name", "EE": "EE", "Domain": "Domain"},
                            svar_name=self.mmrv.ext_signal_action)
        log_table(_logger, table_msg(db=mmdb, variable_name=self.mmrv.ext_signal_action))

        # Unpack ext signal action tuple
        t = ext_signal_action_r.body[0]
        self.ee_name = t['EE']
        self.ee = activity_execution.domain.ee[self.ee_name]
        self.ext_event_name = t['External_event']
        self.implicit = t['Implicit'].strip().lower() == 'true'

        # Resolve source of ext signal
        # Determine the source type
        sm_type = self.activity_execution.state_machine.state_model
        sm_name = self.activity_execution.state_machine.state_model
        self.ext_event_source = InternalAddress(
            domain_name=self.activity_execution.domain.name,
            domain_alias=self.activity_execution.domain.alias,
            sm_name=sm_name,
            sm_alias=self.activity_execution.domain.class_aliases.get( sm_name, sm_name),
            sm_type=sm_type,
            instance_id=self.activity_execution.state_machine.instance_id if sm_type != StateMachineType.SA else None
        )

        # Process outgoing event params
        external_param_r = Relation.semijoin(db=mmdb,
                                             rname1=self.mmrv.ext_signal_action, rname2='External Signal Parameter',
                                             attrs={'ID': 'Signal_action', 'Activity': 'Activity', 'Domain': 'Domain'})
        self.params: dict[str, tuple[str, str]] = {}
        for t in external_param_r.body:
            pname, fname = t['Parameter'], t['Flow']
            pval, _, scalar = self.activity_execution.flows[fname]
            self.params[pname] = (pval, scalar)

        # Hand off to the EE for bridging
        self.ee.process_ext_signal(ext_signal=self)

        if self.activity_execution.domain.announce_external_events:
            # Monitoring is on for this action type. Announce completion.
            self.make_announcement()

        self.complete()

    def make_announcement(self):
        """
        Report monitor status and completion of this action as a formatted message for transfer
        to a supervisor such as the model debugger.
        """
        sm_name = self.ext_event_source.sm_name
        ee_sent = ExternalEvent_Announcement(
            domain=self.ext_event_source.domain_alias,
            ee=self.ee_name,
            source=InternalAddress(
                domain_name=self.ext_event_source.domain_name,
                domain_alias=self.ext_event_source.domain_alias,
                sm_name=sm_name,
                sm_alias=self.activity_execution.domain.class_aliases.get(sm_name, sm_name),
                sm_type=self.activity_execution.state_machine.sm_type,
                instance_id=self.ext_event_source.instance_id,
            ),
            event=self.ext_event_name,
            params=self.params,
            implicit=self.implicit
        )
        self.activity_execution.domain.system.announcements.append(ee_sent)