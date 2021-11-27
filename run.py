#!/usr/bin/env python
import asyncio
import json
import uuid
from typing import Union

from pytradfri.util import load_json, save_json
from pytradfri.const import ATTR_ID
from octoprint_ikea_tradfri_v2.octoprint_ikea_tradfri_v2_plugin import TradfriClient
from pytradfri.error import ServerError
from pytradfri.device import Device

from octoprint_ikea_tradfri_v2.tradfri_client import CommonTradfriDeviceWrapper, generate_psk

CONFIG = "run_conf.json"


def device_infos(devs: list[Union[Device, CommonTradfriDeviceWrapper]]):
    print("=" * 96)
    print("Sockets (and infos) are:")
    for socket in sockets:
        print("-" * 10)
        print(socket)
        print("-" * 10)
        print(socket.raw)
        print("-" * 10)
        print(json.dumps(socket.raw, indent=2))
        print("-" * 10)
        print(socket.device_info.raw)
        print("-" * 10)
        print(socket.device_info.manufacturer)
        print("-" * 10)
        print("ID: '%s | %s', Name: '%s', Type: '%s'" % (socket.path, socket.raw.get(ATTR_ID), socket.name, 'Outlet'))
    print("=" * 96)


# Note:
# When a identity is used to create a psk this psk can only be used TOGETHER with the
# generated identity!

args = {
    "gateway": "192.168.0.124",
    "security_code": "Nh1aEgM5okubRdRI",
    "identity": "my_tradfri_test-%s" % uuid.uuid1().hex[:3],
}

cfg = load_json(CONFIG)

# Credits: https://stackoverflow.com/a/6159329
if cfg and all(x in cfg[args["gateway"]] for x in ["psk", "identity"]):
    psk = cfg[args["gateway"]]["psk"]
    args = {
        "identity": cfg[args["gateway"]]["identity"],
        "gateway": args["gateway"]
    }
    print("Using existing psk from config json")
else:
    try:
        psk = generate_psk(gateway=args["gateway"], identity=args["identity"],
                                         security_code=args["security_code"])
        print("Got initial PSK as: '%s'" % psk)
        print("=" * 96)
        save_json(CONFIG, {args["gateway"]: {"identity": args["identity"], "psk": psk}})
    except (TypeError, ServerError) as e:
        print("    Error: %s" % e)
        print("=" * 96)
        print("    Seems something is wrong with the combination of identity (%s)" % args["identity"])
        if 'psk' in locals():
            print("    with psk (%s) is not valid (anymore). Remove config for host: '%s' and retry!" % (
                psk, args["gateway"]))
        else:
            print("    with psk (%s) is not valid (anymore). Remove config for host: '%s' and retry!" % (
                'psk undefined', args["gateway"]))
        print("    IMPORTANT: Most likely you must change the identity too!")
        print("=" * 96)
        exit(1)

print(
    "Using gateway: '%s' and identity: '%s' with psk: '%s' to create client" % (args["gateway"], args["identity"], psk))

with (TradfriClient.setup(gw_ip=args["gateway"], identity=args["identity"], psk=psk)) as client:
    devices = client.list_devices()
    sockets = client.get_sockets()

print(f"Devices: {devices}")
print(f"Sockets: {sockets}")

# device_infos(devs=sockets)
# device_infos(devs=devices)

import yaml


def to_yaml(data):
    store = {'devs': data}
    print(f"Devices store: {store}")
    with open('config_test.yaml', "w", encoding="utf-8") as file:
        yaml.safe_dump(
            # yaml.dump(
            store,
            file,
            default_flow_style=False,
            indent=2,
            allow_unicode=True,
        )


to_yaml({
    'devices': [dev.to_dict() for dev in devices],
    'sockets': [sock.to_dict() for sock in sockets]
})


def from_yaml():
    with open('config_test.yaml', "r", encoding="utf-8") as file:
        return yaml.safe_load(
        # return yaml.load(
            file,
        )


print(from_yaml())
