from lewis.core import approaches
from lewis.core.statemachine import State


class InfusingState(State):
    def on_entry(self, dt):
        self._context.volume_dispensed = 0.0
        self.originally_infused = self._context.volume_infused

    def in_state(self, dt):
        device = self._context
        device.volume_dispensed = approaches.linear(device.volume_dispensed, device.volume_target,
                                                    device.normalised_rate(), dt)
        device.volume_infused = self.originally_infused + device.volume_dispensed

    def on_exit(self, dt):
        self._context.new_action = False # need to clear so do not trigger pause -> stop too
        self._context._pump_on = False # we need to make sure we do not set new_action


class WithdrawingState(State):
    def on_entry(self, dt):
        self._context.volume_dispensed = 0.0
        self.originally_withdrawn = self._context.volume_withdrawn

    def in_state(self, dt):
        device = self._context
        device.volume_dispensed = approaches.linear(device.volume_dispensed, device.volume_target,
                                                    device.normalised_rate(), dt)
        device.volume_withdrawn = self.originally_withdrawn + device.volume_dispensed

    def on_exit(self, dt):
        self._context.new_action = False # need to clear so do not trigger pause -> stop too
        self._context._pump_on = False # we need to make sure we do not set new_action


class PumpingProgramStoppedState(State):
    def on_entry(self, dt):
        self._context.new_action = False # need to clear so do not trigger pause -> stop too


class PumpingProgramPausedState(State):
    def on_entry(self, dt):
        self._context.new_action = False # need to clear so do not trigger pause -> stop too


class PausePhaseState(State):
    pass


class UserWaitState(State):
    pass
