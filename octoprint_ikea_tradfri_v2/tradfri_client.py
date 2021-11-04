# -*- coding: utf-8 -*-
import os
import argparse
import threading
import time
import uuid

from pytradfri import Gateway
from pytradfri.api.aiocoap_api import APIFactory
from pytradfri.error import PytradfriError

import octoprint.plugin

from dataclasses import dataclass

@dataclass
class Args:
    host: str
    key: str

class TradfriClient():
    api_factory = None
    
    def __init__(self, gw_ip, gw_sec_key):
        args = Args(
            gw_ip,      #'192.168.0.124',
            gw_sec_key  #'Nh1aEgM5okubRdRI'
        )

    async def get_devices(self):
        api = await _get_api()
        devices_command = Gateway().get_devices()
        devices_commands = await api(devices_command)
        return await api(devices_commands)
    
    async def get_sockets(self):
        devices = await get_devices()
        return [dev for dev in devices if dev.has_socket_control]
    
    async def shutdown(self):
        await self.api_factory.shutdown()
        self.api_factory = None
    
    
    async def _get_api(self):
        try:
            api_factory = await self._get_api_factory()
            psk = await api_factory.generate_psk(self.args.key)
            self._logger.debug("Generated PSK: '%s' for IP: %s." % (psk, self.args.host))

            # conf[self.args.host] = {"identity": identity, "key": psk}
        except AttributeError:
            raise PytradfriError("Please provide the 'Security Code' on the back of your Tradfri gateway!")

        return api_factory.request

    
    async def _get_api_factory(self):
        if (self.api_factory == None):
            identity = uuid.uuid4().hex
            self._logger.debug("Created ID: '%s'" % identity)
            self.api_factory = await APIFactory.init(host=self.args.host, psk_id=identity)
        return self.api_factory
        

 #   def run(self):
 #       """Run process."""
 #       # Assign configuration variables.
 #       # The configuration check takes care they are present.
 #       conf = load_json(self.CONFIG_FILE)
 #
 #       self._logger.info(conf)
 #       self._logger.info(self.args)
 #
 #       try:
 #           identity = conf[self.args.host].get("identity")
 #           psk = conf[self.args.host].get("key")
 #           api_factory = APIFactory(host=self.args.host, psk_id=identity, psk=psk)
 #       except KeyError:
 #           identity = uuid.uuid4().hex
 #           self._logger.info("Created ID: '%s'" % identity)
 #           api_factory = APIFactory(host=self.args.host, psk_id=identity)
 #
 #           try:
 #               psk = api_factory.generate_psk(self.args.key)
 #               print("Generated PSK: ", psk)
 #               self._logger.info("Generated PSK: ", psk)
 #
 #               conf[self.args.host] = {"identity": identity, "key": psk}
 #               save_json(self.CONFIG_FILE, conf)
 #           except AttributeError:
 #               raise PytradfriError(
 #                   "Please provide the 'Security Code' on the "
 #                   "back of your Tradfri gateway using the "
 #                   "-K flag."
 #               )
 #
 #       api = api_factory.request
 #
 #       gateway = Gateway()
 #
 #       devices_command = gateway.get_devices()
 #       devices_commands = api(devices_command)
 #       devices = api(devices_commands)
 #
 #       sockets = [dev for dev in devices if dev.has_socket_control]
 #
 #       # Print all sockets
##        print(sockets)
 #       self._logger.info("Sockets (outlets): " + sockets)
 #
 #
 #
 #       # Sockets can be accessed by its index, so sockets[1] is the second socket
 #       if sockets:
 #           socket = sockets[0]
 #       else:
 #           print("No sockets found!")
 #           self._logger.info("No sockets found!")
 #           socket = None
 #
 #       def observe_callback(updated_device):
 #       #    socket = updated_device.socket_control.sockets[0]
 #       #    print("Received message for: %s" % socket)
 #       #    self._logger.info("Received message for: %s" % socket)
 #
 #       #def observe_err_callback(err):
 #       #    print("observe error:", err)
 #       #    self._logger.error("observe error:", err)
 #
 #       for socket in sockets:
 #       #    observe_command = socket.observe(
 #       #        observe_callback, observe_err_callback, duration=120
 #       #    )
 #       #    # Start observation as a second task on the loop.
 #       #    asyncio.ensure_future(api(observe_command))
 #       #    # Yield to allow observing to start.
 #        #   time.sleep(0)
 #
 #           if socket:
 #               # Example 1: checks state of the socket (true=on)
 #               print("Is on:", socket.socket_control.sockets[0].state)
 #               self._logger.info("Is on:", socket.socket_control.sockets[0].state)
 #
 #               # Example 2: What is the name of the socket
 #               print("Name:", socket.name)
 #               self._logger.info("Name:", socket.name)
 #
 #               # Example 3: Turn socket on
 #           # state_command = socket.socket_control.set_state(True)
 #           # await api(state_command)
 #
 #       print("Waiting for observation to end (10 secs)")
 #       self._logger.info("Waiting for observation to end (10 secs)")
 #       #time.sleep(10)
 #
 #       #api_factory.shutdown()
 #
    
