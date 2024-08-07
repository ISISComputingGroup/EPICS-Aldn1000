import functools
from collections import OrderedDict
from threading import RLock

from lewis.devices import StateMachineDevice

from .states import (
    InfusingState,
    PausePhaseState,
    PumpingProgramPausedState,
    PumpingProgramStoppedState,
    UserWaitState,
    WithdrawingState,
)

states = OrderedDict(
    [
        ("I", InfusingState()),
        ("W", WithdrawingState()),
        ("S", PumpingProgramStoppedState()),
        ("P", PumpingProgramPausedState()),
        ("T", PausePhaseState()),
        ("U", UserWaitState()),
    ]
)


def lockmethod(method):
    @functools.wraps(method)
    def wrapper(*args, **kwargs):
        with args[0]._lock:
            return method(*args, **kwargs)

    return wrapper


class SimulatedAldn1000(StateMachineDevice):
    def __init__(self):
        self._lock = RLock()
        super().__init__()

    @lockmethod
    def _initialize_data(self):
        """
        Initialize all of the device's attributes.
        """
        self.connected = True
        self.input_correct = True

        self._pump_on = False
        self.program_function = "RAT"

        self.address = 0
        self._diameter = 0.0
        self.volume_target = 0.0
        self.volume_infused = 0.0  # Cumulative infused volume
        self.volume_withdrawn = 0.0  # Cumulative withdrawn volume
        self.volume_dispensed = 0.0  # Dispensed volume for a single pump run
        self._direction = "INF"
        self.rate = 0.0
        self.units = "UM"
        self.volume_units = "UL"
        self._new_action = False

    @lockmethod
    def clear_volume(self, volume_type):
        if volume_type == "INF":
            self.volume_infused = 0.0
        elif volume_type == "WDR":
            self.volume_withdrawn = 0.0

    def normalised_rate(self):
        """
        Returns the normalises the rate to volume units per second.
        """
        rate = self.rate
        if self.units[0] == "U" and self.volume_units[0] == "M":
            rate /= 1000.0
        if self.units[0] == "M" and self.volume_units[0] == "U":
            rate *= 1000.0
        rate /= 60.0  # As will at least be in minutes
        if self.units[1] == "H":
            rate /= 60.0
        return rate

    @property
    @lockmethod
    def new_action(self):
        return self._new_action

    @new_action.setter
    @lockmethod
    def new_action(self, yesno):
        self._new_action = yesno

    @property
    @lockmethod
    def pump_on(self):
        return self._pump_on

    @pump_on.setter
    @lockmethod
    def pump_on(self, action):
        if action == "STP":
            self._pump_on = False
        elif action == "RUN":
            self._pump_on = True
        else:
            print("An error occurred while trying to start/stop the pump")
        self.new_action = True  # Check used for On -> Paused / Paused -> Off state transition.

    @property
    def diameter(self):
        return self._diameter

    @diameter.setter
    @lockmethod
    def diameter(self, new_value):
        if (
            new_value > 14.0
        ):  # Device changes the volume units automatically based on the diameter set
            self.volume_units = "ML"
        else:
            self.volume_units = "UL"
        self._diameter = new_value

    @property
    def direction(self):
        return self._direction

    @direction.setter
    @lockmethod
    def direction(self, new_direction):
        if new_direction == "REV":  # Reverse
            if self._direction == "INF":  # Infuse
                self._direction = "WDR"  # Withdraw
            else:
                self._direction = "INF"
        else:
            self._direction = new_direction

    def reset(self):
        self._initialize_data()
        # make sure state machine returns to initial state
        self._csm.reset()

    @property
    def state(self):
        return self._csm.state

    def _get_state_handlers(self):
        return states

    def _get_initial_state(self):
        return "S"

    def _get_transition_handlers(self):
        return OrderedDict(
            [
                (("S", "I"), lambda: self.pump_on is True and self.direction == "INF"),
                (("S", "W"), lambda: self.pump_on is True and self.direction == "WDR"),
                (("I", "P"), lambda: self.pump_on is False),
                (("W", "P"), lambda: self.pump_on is False),
                (("I", "S"), lambda: self.volume_dispensed == self.volume_target),
                (("W", "S"), lambda: self.volume_dispensed == self.volume_target),
                (("P", "S"), lambda: self.pump_on is False and self.new_action is True),
                (("P", "I"), lambda: self.pump_on is True and self.direction == "INF"),
                (("P", "W"), lambda: self.pump_on is True and self.direction == "WDR"),
            ]
        )
