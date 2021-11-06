# -*- coding: utf-8 -*-
import asyncio
import uuid
from dataclasses import dataclass

from pytradfri import Gateway
from pytradfri.api.aiocoap_api import APIFactory
from pytradfri.error import PytradfriError


@dataclass
class Args:
    host: str
    key: str
    psk: str = None
    identity: str = None


class TradfriClient():
    _api_factory = None
    _loop = None
    args = None

    def __init__(self, gw_ip, gw_sec_key):
        self.args = Args(
            gw_ip,  # '192.168.0.124',
            gw_sec_key  # 'Nh1aEgM5okubRdRI'
        )
        try:
            self._loop = asyncio.get_event_loop()
        except DeprecationWarning:
            pass

    def get_sockets(self):
        return self._loop.run_until_complete(self.__get_sockets__())

    def list_devices(self):
        return self._loop.run_until_complete(self._get_devices())

    async def _get_devices(self):
        devices_command = Gateway().get_devices()
        devices_commands = await self._call_api(devices_command)
        return await self._call_api(devices_commands)

    async def __get_sockets__(self):
        devices = await self._get_devices()
        return [dev for dev in devices if dev.has_socket_control]

    async def _call_api(self, command):
        try:
            api_factory = await self._get_api_factory()
            return await api_factory.request(command)
        except AttributeError as err:
            raise PytradfriError("Please provide the 'Security Code' on the back of your Tradfri gateway!", err)

    async def _get_api_factory(self):
        if self._api_factory is None:
            if self.args.psk is None:
                self.args.identity = uuid.uuid4().hex
                self._api_factory = await APIFactory.init(host=self.args.host, psk_id=self.args.identity)
                await self._generate_psk(self._api_factory)
            else:
                self._api_factory = await APIFactory.init(host=self.args.host, psk_id=self.args.identity, psk=self.args.psk)
        return self._api_factory

    async def _generate_psk(self, api_factory):
        self.args.psk = await api_factory.generate_psk(self.args.key)
        print("Generated PSK: '%s' for IP: %s." % (self.args.psk, self.args.host))

    async def _shutdown(self):
        """Deprecated!"""
        await self._api_factory.shutdown()
        self._api_factory = None

    def __del__(self):
        try:
            self._loop.run_until_complete(self._api_factory.shutdown())
            print("Closed the pytradfri factory in destructor!")
        except PytradfriError as err:
            print("Failed to close pytradfri factory!", err)
