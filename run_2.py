#!/usr/bin/env python
from time import sleep
from benedict import benedict

from octoprint_ikea_tradfri_v2.tradfri_client import TradfriClient, find_a_loop
from octoprint_ikea_tradfri_v2 import logging
from pytradfri.util import load_json


def ip_as_key():
    return GW_IP.replace(".", "_")


CONFIG = "run_2_conf.json"
GW_IP = "192.168.0.124"

logger = logging.get_logger(__name__)


cfg = benedict(load_json(CONFIG))
if f'{ip_as_key()}.psk' not in cfg:
    raise "Missing PSK in cfg!"


def display_things(client, devices, sockets):
    logger.info(f"Devices: {devices}")
    logger.info(f"Sockets: {sockets}")
    logger.info("Show state per index in devices/sockets array...")
    device_index = 2
    logger.info(
        f"Device at index {device_index} ({devices[device_index].name}) has state: {devices[device_index].get_state()}")
    socket_index = 1
    logger.info(
        f"Socket at index {socket_index} ({sockets[socket_index].name}) has state: {sockets[socket_index].get_state()}")
    logger.info("Show state by device ids...")
    entree_light_id = '65561'
    entree_light = client.get_by_id(entree_light_id)
    logger.info(f"Device with id: {entree_light_id} ({entree_light.name}) has state: {entree_light.get_state()}")
    library_outlet_id = '65576'
    library_outlet = client.get_by_id(library_outlet_id)
    library_current_stete = library_outlet.get_state()
    logger.info(f"Socket with id: {library_outlet_id} ({library_outlet.name}) has state: {library_current_stete}")
    return library_outlet


def activate_things(library_outlet, manual: bool = False):
    logger.info(f"{'*' * 32} Using {'MANUAL' if manual else 'TOGGLE'} to activate the device {'*' * 32}")
    if manual:
        library_outlet.control.switch_on()
    else:
        library_outlet.control.toggle_state()
    logger.info(f"Toggle library outlet for 5 sec...")
    logger.info(f"New state after first toggle for device: {library_outlet.name} is: {library_outlet.get_state()}")
    sleep(5)
    # TODO Seems not to be awaited but already going to close the client!
    logger.info(f"Toggle library outlet back")
    if manual:
        library_outlet.control.switch_off()
    else:
        library_outlet.control.toggle_state()


def run_things(manual=False):
    logger.info(f"*************** Run WITHOUT with resources!")

    client = TradfriClient.setup(gw_ip=GW_IP, identity=cfg.get(f"{ip_as_key()}.identity"),
                                 psk=cfg.get(f"{ip_as_key()}.psk"))
    devices = client.list_devices()
    sockets = client.get_sockets()

    assert ((sockets, devices) != (None, None))

    try:
        library_outlet = display_things(client, devices, sockets)
        activate_things(library_outlet, manual)
    finally:
        logger.info("Shutting down the client...")
        try:
            find_a_loop().run_until_complete(client.shutdown())
            logger.info("Client shutdown Done")
        except RuntimeError as e:
            logger.error(f"Error shutting down the client! {e}")


def run_things_with(manual=False):
    logger.info(f"*************** Run with resources!")

    TradfriClient.setup(gw_ip=GW_IP, identity=cfg.get(f"{ip_as_key()}.identity"),
                        psk=cfg.get(f"{ip_as_key()}.psk"))
    with (TradfriClient.instance()) as client:
        devices = client.list_devices()
        sockets = client.get_sockets()

        assert ((sockets, devices) != (None, None))

        library_outlet = display_things(client, devices, sockets)
        activate_things(library_outlet, manual)

    logger.info(f"Assume client is closed here!")


use_with = True
logger.info("-" * 36)
if use_with:
    run_things_with(False)
    logger.info("-" * 36)
    run_things_with(True)
else:
    run_things(True)
    logger.info("-" * 36)
    run_things(False)
logger.info("-" * 36)
