# -*- coding: utf-8 -*-
import asyncio
import concurrent.futures
import logging
from asyncio import AbstractEventLoop
from logging import config
from time import sleep
from typing import Optional, Coroutine, List

from pytradfri.command import Command

from pytradfri import Gateway
from pytradfri.api.aiocoap_api import APIFactory
from pytradfri.device import Device
from pytradfri.error import PytradfriError

from .threaded_worker import ThreadedWorker
from .tradfri_device import CommonTradfriSocketWrapper, CommonTradfriDeviceWrapper


class TradfriClientError(PytradfriError):
    pass


def generate_psk(gateway: str, identity: str, security_code: str) -> str:
    pool = concurrent.futures.ThreadPoolExecutor()

    try:
        _api_factory = pool.submit(asyncio.run, APIFactory.init(host=gateway, psk_id=identity)).result(
            TradfriClient.TIMEOUT_IN_SEC)
        psk = pool.submit(asyncio.run, _api_factory.generate_psk(security_key=security_code)).result(
            TradfriClient.TIMEOUT_IN_SEC)
        return psk
    except TimeoutError as e:
        #  TODO Probably call myself a few more times with increased timeout
        #   (ie. 3 times each increase the timeout by 0.5 or 1 second)
        #   Always log these tries!
        logging.getLogger(__name__).debug("Run into timeout when generating psk!", e)
    finally:
        pool.shutdown(wait=True)


# TODO Still needed?!
def find_a_loop(logger: logging.Logger = logging.getLogger(__name__)) -> AbstractEventLoop:
    try:
        loop = asyncio.get_event_loop()
        logger.debug(f"Use get_event_loop() loop.")
    except RuntimeError as e:
        logger.warning(f"No get_event_loop()! Message: {e.__repr__()}")
        try:
            loop = asyncio.new_event_loop()
            logger.debug(f"Use get_new_loop() loop.")
        except RuntimeError as e:
            logger.warning(f"No get_new_loop()! Message: {e.__repr__()}")
            raise TradfriClientError(f"Failed to acquire loop to run shutdown!", e)
    return loop


_SENTINEL = object()


class TradfriClient:
    _instance: Optional['TradfriClient'] = None

    TIMEOUT_IN_SEC = 1

    def __init__(self, gw_ip: str, identity: str, psk: str, logger=logging.getLogger(__name__), internal=None):
        if internal is not _SENTINEL:
            raise TradfriClientError(f"Constructor not public! Use {TradfriClient.__class__.__name__}.instance(...).")

        self._host_ip = gw_ip
        self._identity = identity
        self._psk = psk
        self._api_factory: Optional[APIFactory] = None
        self._worker: Optional[ThreadedWorker] = None
        self._logger = logger

    @classmethod
    def instance(cls) -> 'TradfriClient':
        if cls._instance is None:
            raise TradfriClientError(f"{TradfriClient.__class__.__name__} not yet setup! Please execute first "
                                     f"{TradfriClient.__class__.__name__}.setup(...).")
        logging.getLogger(cls.__name__).debug("Returning existing instance of client from class member.")
        return cls._instance

    @classmethod
    def setup(cls, gw_ip: str, identity: str, psk: str, logger=logging.getLogger(__name__)) -> 'TradfriClient':
        # TODO Could also have a _instance: dict to keep different client instances depending on args!?
        if cls._instance is None:
            logging.getLogger(cls.__name__).debug("No instance of client available on class (ie. not yet setup) "
                                                  "Create one now...")
            cls._instance = cls(gw_ip=gw_ip, identity=identity, psk=psk, logger=logger, internal=_SENTINEL)
        logging.getLogger(cls.__name__).debug("Class member initialized with instance. Return said instance now.")
        return cls._instance

    def _get_worker(self) -> ThreadedWorker:
        if self._worker is None:
            self._logger.debug(f"No worker initialized yet.")
            self._worker = ThreadedWorker()  # Could createa async init method (classmethod) on worker and wait (there)?
            self._logger.debug(f"Client self is here: {self.__class__.__name__}")
            while self._worker.is_initializing():
                self._logger.debug(f"Worker still initializing...")
                sleep(0.1)
            self._logger.debug(f"Worker initialized with thread name: {self._worker.name}")
        return self._worker

    def get_sockets(self) -> List[CommonTradfriSocketWrapper]:
        self._logger.debug(f"Running: get_sockets")
        return [CommonTradfriSocketWrapper(dev) for dev in self._checked_execution(self._get_sockets())]

    def list_devices(self) -> List[CommonTradfriDeviceWrapper]:
        self._logger.debug(f"Running: list_devices")
        return [CommonTradfriDeviceWrapper(dev) for dev in self._checked_execution(self._get_devices())]

    def get_by_id(self, device_id: str) -> CommonTradfriDeviceWrapper:
        self._logger.debug(f"Getting device with id: '{device_id}")
        return CommonTradfriDeviceWrapper(self._checked_execution(self._get_by_id(device_id)))

    def intern_run_command(self, command: Command):
        return self._checked_execution(self._run_command(command=command))

    def _checked_execution(self, method: Coroutine):
        self._logger.debug(f"Try to executed (checked) the method: {method.__name__}")
        try:
            return asyncio \
                .run_coroutine_threadsafe(method, self._get_worker().get_loop()) \
                .result(self.TIMEOUT_IN_SEC)
        except Exception as e:
            self._logger.error("Failed to checked call method: '%s'!" % method, e)

    async def _get_sockets(self) -> List[Device]:
        self._logger.debug(f"Running: _get_sockets")
        devices = await self._get_devices()
        return [dev for dev in devices if dev.has_socket_control]

    async def _get_devices(self) -> List[Device]:
        self._logger.debug(f"Running: _get_devices")
        devices_command = Gateway().get_devices()
        devices_commands = await self._call_api(devices_command)
        return await self._call_api(devices_commands)

    async def _get_by_id(self, device_id: str):
        get_device_command = Gateway().get_device(device_id)
        return await self._call_api(get_device_command)

    async def _run_command(self, command: Command):
        return await self._call_api(command)

    async def _call_api(self, command):
        try:
            api_factory = await self._get_api_factory()

            return await api_factory.request(command)
        except AttributeError as err:
            raise PytradfriError("Failed to call the API of the Tradfri gateway at ip: %s!" % self._host_ip, err)

    async def _get_api_factory(self):
        if self._api_factory is None:
            self._logger.debug("Factory not yet available...")
            self._api_factory = await APIFactory.init(host=self._host_ip, psk_id=self._identity, psk=self._psk)
        return self._api_factory

    async def shutdown(self):
        self._logger.debug("Shutting down the tradfri_client!")
        try:
            await self._api_factory.shutdown()
        except Exception as e:
            self._logger.warning(f"Failed to shutdown {self._api_factory.__class__.__name__}! Message: {e.__repr__()}")
        finally:
            self._logger.debug(f"Finally!")
            pending = asyncio.all_tasks(self._worker.get_loop())
            self._logger.debug(f"There are now {len(pending)} pending tasks! {pending}")
            self._api_factory = None

        try:
            self._worker.close()
        except Exception as e:
            self._logger.warning(f"Failed to shutdown {self._worker.__class__.__name__}! Message: {e.__repr__()}")
        finally:
            self._worker = None

        self.__class__._instance = None

    # TODO Provide async shutdown AND sync close() (maybe close with param to use async ie. return coroutine?!)
    # TODO As above for some other methods?

    def __exit__(self, exc_type, exc_val, exc_tb):
        find_a_loop(self._logger).run_until_complete(self.shutdown())

    def __enter__(self):
        self._logger.debug("Enter the client!")
        return self
