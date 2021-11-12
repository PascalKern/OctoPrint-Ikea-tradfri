# -*- coding: utf-8 -*-
import asyncio
import uuid
from dataclasses import dataclass
from typing import Optional

from pytradfri import Gateway
from pytradfri.device import Device
from pytradfri.api.aiocoap_api import APIFactory
from pytradfri.error import PytradfriError


@dataclass
class Args:
    host: str
    key: str
    psk: str = Optional[str]
    identity: uuid.UUID = Optional[uuid.UUID]


class TradfriClientError(PytradfriError):
    pass


class TradfriClient:
    _api_factory = None
    _loop = None
    _args = None

    def __init__(self, gw_ip: str, gw_sec_key: str, psk: Optional[str] = None, identity: uuid.UUID = uuid.uuid4()):
        try:
            self._loop = asyncio.get_event_loop()
        except DeprecationWarning as e:
            raise TradfriClientError("Failed to create async loop for TradfriClient!", e)

        # Generate PSK here if not exist! See that this class is an singleton or at least it's arg's related to
        # host+identity combination
        self._args = Args(
            host=gw_ip,
            key=gw_sec_key,
            psk=psk,
            identity=identity
        )

    def get_sockets(self) -> list[Device]:
        return self._loop.run_until_complete(self._get_sockets())

    def list_devices(self) -> list[Device]:
        return self._loop.run_until_complete(self._get_devices())

    def get_settings(self) -> Args:
        return self._args

    def get_psk(self) -> str:
        #return self._loop.run_until_complete(self._generate_psk())
        return asyncio.ensure_future(self._generate_psk())

    async def _get_sockets(self):
        devices = await self._get_devices()
        return [dev for dev in devices if dev.has_socket_control]

    async def _get_devices(self):
        devices_command = Gateway().get_devices()
        devices_commands = await self._call_api(devices_command)
        return await self._call_api(devices_commands)

    async def _call_api(self, command):
        try:
            if self._args.psk is None:
                self.get_psk()
            api_factory = await self._get_api_factory(self._args.psk)
            return await api_factory.request(command)
        except AttributeError as err:
            raise PytradfriError("Failed to call tha API of your Tradfri gateway!", err)

    async def _get_api_factory(self, psk: str = None):
        if self._api_factory is None and psk is None:
            print("No factory nor psk yet available...")
            self._api_factory = await APIFactory.init(host=self._args.host, psk_id=self._args.identity.hex)
        elif self._api_factory and psk:
            print("Factory nor psk available...")
            await APIFactory.init(host=self._args.host, psk_id=self._args.identity.hex, psk=psk)
        return self._api_factory

    async def _generate_psk(self) -> str:
        if self._args.psk is None:
            factory = await self._get_api_factory()
            self._args.psk = await factory.generate_psk(self._args.identity.hex)
            print("Generated PSK: '%s' for IP: %s." % (self._args.psk, self._args.host))
        return self._args.psk

    async def _shutdown(self):
        """Deprecated!"""
        await self._api_factory.shutdown()
        self._api_factory = None

    def __del__(self):
        try:
            if self._loop and self._api_factory:
                self._loop.run_until_complete(self._api_factory.shutdown())
            print("Closed the pytradfri factory in destructor!")
        except PytradfriError as err:
            print("Failed to close pytradfri factory!", err)
