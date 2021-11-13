# -*- coding: utf-8 -*-
import asyncio
import logging
import threading
import uuid
from dataclasses import dataclass
from typing import Coroutine, Any, Optional

from pytradfri import Gateway
from pytradfri.device import Device
from pytradfri.api.aiocoap_api import APIFactory
from pytradfri.error import PytradfriError, ServerError


class TradfriClientError(PytradfriError):
    pass


# Deprecated or use it only here (without class!)
def g_generate_psk(gateway: str, identity: str, security_code: str) -> str:
    return asyncio.get_event_loop().run_until_complete(
        TradfriClient._generate_psk(gateway=gateway, identity=identity, security_code=security_code)
    )


# Try to patch the APIFactory for issue with try to regenerate a psk with existing identity
# old__get_response = APIFactory._get_response
# async def new__get_response(self, msg):
#     # Here should modify to pr_resp = await pr_req.response_raising instead of response!
#     print("------- It Worked!")
#     return await old__get_response(self, msg)
# APIFactory._get_response = new__get_response

# # Second try - might work...
# import ast
# import inspect
# # from pytradfri.api.aiocoap_api import APIFactory as OldAPIFactory
# # source = inspect.getsource(APIFactory)
# source = inspect.getsource(APIFactory._get_response)
# # source = inspect.getsource(APIFactory._get_response)
# # print("Source: ", source)
# src = source.split('\n')
# # print("Src: ", src)
# indent = len(src[0]) - len(src[0].lstrip())
# # print("Indent: ", indent)
# s = '\n'.join(i[indent:] for i in src)
# # print("S: ", s)
# tree = ast.parse(s)
# # tree = ast.parse(source=source)
# # print("Tree: ", tree)
# n_s = ast.parse("pr_resp = await pr_req.response_raising")
# # tree.body[0].body[8].body[1].body[2] = n_s.body[0]  # In whole class
# tree.body[0].body[1].body[2] = n_s.body[0]  # Only _get_response
# exec(compile(tree, 'aiocoap_api_edit.py', 'exec'))
# # exec(compile(tree, '<string>', 'exec'))
# APIFactory._get_response = _get_response  # The right hand part is the function generated in global namespace by exec(compile(
# del _get_response
# # APIFactory = APIFactory
# # APIFactory = OldAPIFactory
# # del OldAPIFactory
#
# # from pytradfri.api.aiocoap_api import APIFactory


class TradfriClient:
    _api_factory: APIFactory = None

    def __init__(self, gw_ip: str, identity: str, psk: str, logger=logging.getLogger(__name__)):
        self._host_ip = gw_ip
        self._identity = identity
        self._psk = psk
        self._api_factory: Optional[APIFactory] = None
        self._logger = logger
        if threading.current_thread() is threading.main_thread():
            self._loop = asyncio.get_event_loop()
        else:
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)

    @staticmethod
    def generate_psk(gateway: str, identity: str, security_code: str) -> str:
        return asyncio.get_event_loop().run_until_complete(
            TradfriClient._generate_psk(gateway=gateway, identity=identity, security_code=security_code)
        )

    @staticmethod
    async def _generate_psk(gateway: str, identity: str, security_code: str) -> str:
        _api_factory = await APIFactory.init(host=gateway, psk_id=identity)
        try:
            psk = await _api_factory.generate_psk(security_key=security_code)
        except ServerError as e:
            raise e
        await asyncio.sleep(0.1)
        await _api_factory.shutdown()
        return psk

    def get_sockets(self) -> list[Device]:
        return asyncio.run(self._get_sockets())

    async def _get_sockets(self) -> list[Device]:
        devices = await self._get_devices()
        return [dev for dev in devices if dev.has_socket_control]

    def list_devices(self) -> list[Device]:
        return self._loop.run_until_complete(self._get_devices())

    async def _get_devices(self):
        devices_command = Gateway().get_devices()
        devices_commands = await self._call_api(devices_command)
        return await self._call_api(devices_commands)

    async def _call_api(self, command):
        try:
            api_factory = await self._get_api_factory()
            return await api_factory.request(command)
        except AttributeError as err:
            raise PytradfriError("Failed to call the API of the Tradfri gateway at ip: %s!" % self._host_ip, err)

    async def _get_api_factory(self):
        if self._api_factory is None:
            print("Factory not yet available...")
            self._api_factory = await APIFactory.init(host=self._host_ip, psk_id=self._identity, psk=self._psk)
        return self._api_factory

    async def _shutdown(self):
        """Deprecated!"""
        await self._api_factory.shutdown()
        self._api_factory = Optional[APIFactory]

    def __del__(self):
        try:
            if self._loop and self._api_factory:
                self._loop.run_until_complete(self._api_factory.shutdown())
            print("Closed the pytradfri factory in destructor!")
        except PytradfriError as err:
            print("Failed to close pytradfri factory!", err)
