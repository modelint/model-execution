""" state_machine.py """


class StateMachine:

    external_events = set()
    internal_events = []
    current_state = None
    dest_state = None

    def __init__(self, current_state: str):
        self.current_state = current_state
        pass