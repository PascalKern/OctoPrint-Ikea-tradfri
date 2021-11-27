# -*- coding: utf-8 -*-
import logging
from typing import Union, TYPE_CHECKING, Optional
from enum import Enum

import octoprint_ikea_tradfri_v2.tradfri_client
from pytradfri.device import Device, DeviceInfo, SocketControl, LightControl
from pytradfri.error import PytradfriError


class TradfriDeviceType(Enum):
    # class TradfriDeviceTypeMapper:
    #     def __init__(self, value: str):
    #         self._value = value

    # OUTLET = TradfriDeviceTypeMapper("Outlet")
    OUTLET = "Outlet"
    LIGHT = "Light"
    BLIND = "Blind"
    OTHER = "Other"

    def _mapper(self):
        return {
            'OUTLET': {
                "control": "socket_control",  # To be used (ie) as: getattr(OUTLET['get_object']().state
                "entity": "sockets"
            },
            'LIGHT': {
                "control": "light_control",
                "entity": "lights"
            },
            'BLIND': {
                "control": "blind_control",
                "entity": "blinds"
            }
        }

    def ctrl(self):
        return self._mapper()[self.name]['control']

    def entity(self):
        return self._mapper()[self.name]['entity']


# TODO Can I make this generic for CommonTradfriDevice|Socket ?!
class CommonTradfriDeviceWrapper:
    _control: Optional['CommonTradfriDeviceControl'] = None

    def __init__(self, device_obj: Device, logger=logging.getLogger(__name__)):
        if device_obj is None:
            raise PytradfriError("Can not create a TradfriDevice from None!")
        self._device_obj = device_obj
        self._logger = logger

    @property
    def id(self):
        return self._device_obj.id

    @property
    def name(self):
        return self._device_obj.name

    @property
    def type(self) -> TradfriDeviceType:
        if self._device_obj.has_light_control:
            return TradfriDeviceType.LIGHT
        elif self._device_obj.has_socket_control:
            return TradfriDeviceType.OUTLET
        elif self._device_obj.has_blind_control:
            return TradfriDeviceType.BLIND
        return TradfriDeviceType.OTHER

    @property
    def control(self):
        if self._control is None:
            self._control = CommonTradfriDeviceControl(self)
        return self._control

    def get_state(self) -> bool:
        return self.control.get_state()

    def get_info(self) -> DeviceInfo:
        return self._device_obj.device_info

    def refresh(self) -> Union['CommonTradfriDeviceWrapper', 'CommonTradfriSocketWrapper']:   # TODO Make Generic!
        self._device_obj = octoprint_ikea_tradfri_v2.tradfri_client.TradfriClient.instance().get_by_id(self.id)._device_obj
        self._control = None
        return self

    def to_dict(self):
        return {'id': self.id, 'type': self.type.value, 'name': self.name}

    def __repr__(self):
        return f"<{self.__class__.__name__} - {self.id} - {self.name} ({self._device_obj.device_info.model_number})>"


class CommonTradfriSocketWrapper(CommonTradfriDeviceWrapper):
    def __init__(self, device_obj: Device):
        super().__init__(device_obj=device_obj, logger=logging.getLogger(__name__))


# TODO Can I make this generic for CommonTradfriDevice|Socket ?!
class CommonTradfriDeviceControl:
    def __init__(self, device: Union[CommonTradfriDeviceWrapper, CommonTradfriSocketWrapper], logger=logging.getLogger(__name__)):
        self._device = device
        self._logger = logger

    def switch_on(self):
        self._set_state(True)

    def switch_off(self):
        self._set_state(False)

    def toggle_state(self):
        if self.get_state():
            self.switch_off()
        else:
            self.switch_on()

    def get_state(self):
        if hasattr(self._get_controls(), self._device.type.entity()):
            return getattr(self._get_controls(), self._device.type.entity())[0].state
        else:
            raise TradfriDeviceError(f"State for device type: {self._device.type} is not yet available!")

    def _set_state(self, new_state: bool):
        set_state_command = self._get_controls().set_state(new_state)
        octoprint_ikea_tradfri_v2.tradfri_client.TradfriClient.instance().intern_run_command(set_state_command)
        self._device = self._device.refresh()

    def _get_controls(self) -> Union[SocketControl, LightControl]:   # (TODO Make Generic!)
        if hasattr(self._device._device_obj, self._device.type.ctrl()):
            return getattr(self._device._device_obj, self._device.type.ctrl())
        else:
            raise TradfriDeviceError(f"Control for device type: {self._device.type} is not yet possible!")

    def __repr__(self):
        return f"<{self.__class__.__name__} - ({self._device._device_obj.device_info.model_number}) State: {self.get_state()}>"


class TradfriDeviceError(BaseException):
    pass
