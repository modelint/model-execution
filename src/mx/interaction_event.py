""" dispatched_event.py """

# System
from datetime import datetime
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from mx.domain import Domain

# Model Integration
from pyral.relation import Relation
from pyral.relvar import Relvar


# MX
from mx.dispatched_event import DispatchedEvent
from mx.mxtypes import NamedValues, StateMachineType


class InteractionEvent(DispatchedEvent):

    def __init__(self, sm_type: StateMachineType, event_spec, params, domain, source,
                 to_instance: Optional[NamedValues]=None,
                 to_class: Optional[str]= None, partitioning_instance:Optional[NamedValues]=None,
                 partitioning_class: Optional[str] = None, to_rnum: Optional[str] = None):
        """

        """
        # Validate target state machine type
        sm = None
        match sm_type:
            case StateMachineType.LIFECYCLE:
                sm = to_class
                if not (to_instance and to_class):
                    pass # TODO: Raise exception
            case StateMachineType.SA:
                sm = to_rnum
                if not to_rnum:
                    pass  # TODO: Raise exception
            case StateMachineType.MA:
                sm = to_rnum
                if not (to_rnum and partitioning_class and partitioning_instance):
                    pass  # TODO: Raise exception
            case _:
                pass  # TODO: Raise exception

        super().__init__(source=source, event_spec=event_spec, state_model=sm, sm_type=sm_type,
                         to_instance=to_instance,
                         partitioning_class=partitioning_class, partitioning_instance=partitioning_instance,
                         params=params, domain=domain)

        self.arrival_time = datetime.now()
        self.dispatch()

    def dispatch(self):
        # Look up the target state machine and put this event in its set
        match self.sm_type:
            case StateMachineType.LIFECYCLE:
                # Find the target instance id
                R = ", ".join([f"{a}:<{v}>" for a, v in self.to_instance.items()])
                inst_id_r = Relation.restrict(db=self.domain.alias, relation=f"{self.state_model}_i", restriction=R)
                target_inst_id = inst_id_r.body[0]["_instance"]
                # Look up the lifecycle state machine object for that instance
                sm = self.domain.lifecycles[self.state_model][target_inst_id]
                sm.accept_interaction_event(event=self)
                pass
            case StateMachineType.MA:
                pass
            case StateMachineType.SA:
                pass

        pass

    @classmethod
    def to_lifecycle(cls, event_spec: str, to_instance: NamedValues, to_class: str,
                     params: NamedValues, domain: "Domain", source: Optional[str] = None):
        return cls(sm_type=StateMachineType.LIFECYCLE, event_spec=event_spec, params=params, domain=domain,
                   source=source, to_instance=to_instance, to_class=to_class)

    @classmethod
    def to_single_assigner(cls, event_spec: str, to_rnum: str,
                           params: NamedValues, domain: "Domain", source: Optional[str] = None):
        return cls(sm_type=StateMachineType.SA, event_spec=event_spec, params=params, domain=domain,
                   source=source, to_rnum=to_rnum)

    @classmethod
    def to_multiple_assigner(cls, event_spec: str, paritioning_instance: NamedValues,
                             partitioning_class: str, to_rnum: str, params: NamedValues, domain: "Domain", source: Optional[str] = None):
        return cls(sm_type=StateMachineType.MA, event_spec=event_spec, params=params, domain=domain, source=source,
                   partitioning_instance=paritioning_instance, partitioning_class=partitioning_class, to_rnum=to_rnum)

