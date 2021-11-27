from __future__ import absolute_import, division, print_function, unicode_literals

import concurrent.futures
import json
import math
import threading
import time

from pytradfri.const import ATTR_ID

import flask

import octoprint.plugin

from flask_babel import gettext
from octoprint.access import ADMIN_GROUP

from .mixins.wizzard_impl import IkeaTradfriPluginWizard
from .tradfri_client import TradfriClient


class IkeaTradfriPlugin(
    octoprint.plugin.EventHandlerPlugin,
    octoprint.plugin.SimpleApiPlugin,
    octoprint.plugin.StartupPlugin,
    octoprint.plugin.AssetPlugin,
    octoprint.plugin.TemplatePlugin,
    # IkeaTradfriPluginTemplate,
    octoprint.plugin.BlueprintPlugin,
    # octoprint.plugin.SettingsPlugin,
    IkeaTradfriPluginWizard
):
    psk = None
    devices = []
    status = 'waiting'
    error_message = ''
    shutdownAt = dict()
    stopTimer = dict()
    stopCooldown = dict()
    pool = concurrent.futures.ThreadPoolExecutor()
    baseTopic = None

    def __init__(self):
        # super().__init__()  # TODO Needed / wanted or does fail!
        self.mqtt_publish = lambda *args, **kwargs: None
        self.mqtt_subscribe = lambda *args, **kwargs: None
        self.mqtt_unsubscribe = lambda *args, **kwargs: None

        self._tradfri_client = None

    # TODO Do keep the client "inside" the client class accessable by static method
    #   Keep the client thread safe and only keep instances of clients initialized with a PSK.
    # TODO Use on_shutdown to close the client and all it's dependencies (ie. pool etc.)
    def _get_tradfri_client(self):
        if self._tradfri_client is None:
            gateway_ip = self._settings.get(["gateway_ip"])
            identity = self._settings.get(["identity"])
            psk = self._settings.get(["psk"])

            self._logger.info("Init tradfri client for plugin with ip: %s and identity: %s" % (gateway_ip, identity))
            self._tradfri_client = TradfriClient.setup(gw_ip=gateway_ip, identity=identity, psk=psk, logger=self._logger)
        return self._tradfri_client

    def save_settings(self):
        self._settings.set(['status'], self.status)
        self._settings.set(['error_message'], self.error_message)
        self._settings.set(['devices'], self.devices)
        self._settings.save()
        self._logger.debug('Settings saved')

    def load_devices(self, startup=False):
        args = {
            'gw_ip': self._settings.get(['gateway_ip']),
            'identity': self._settings.get(['identity']),
            'psk': self._settings.get(['psk'])
        }
        self.devices = []
        if args.get('psk'):
            self._logger.debug(f"Load devices. Startup: '{startup}' with args: '{args}")
            if startup:
                with(TradfriClient.setup(**args)) as client:
                    devices = client.list_devices()
            else:
                devices = self._get_tradfri_client().list_devices()
            if devices is None:
                self._logger.debug("No devices found!")
                return
            self._logger.debug("Fond devices. '%s'" % [d.name for d in devices])

            for device in devices:
                self.devices.append(dict(id=device.id, name=device.name, type=device.type.value))

        if len(self.devices):
            self.status = 'ok'
        else:
            self.status = 'no_devices'
        self.save_settings()

    # --- SettingsPlugin ---

    def on_settings_save(self, data):
        # keyAsNumber = ['postponeDelay', 'stop_timer', 'connection_timer']
        # for key in data:
        #     if key in keyAsNumber:
        #         data[key] = int(data[key])

        self._logger.info("Going to (try) saving data: '%s'" % data)

        octoprint.plugin.SettingsPlugin.on_settings_save(self, data)
        self.load_devices()

    # --- StartupPlugin ---

    def on_after_startup(self):
        helpers = self._plugin_manager.get_helpers("mqtt", "mqtt_publish", "mqtt_subscribe", "mqtt_unsubscribe")
        if helpers:
            if 'mqtt_publish' in helpers:
                self.mqtt_publish = helpers['mqtt_publish']
            if 'mqtt_subscribe' in helpers:
                self.mqtt_subscribe = helpers['mqtt_subscribe']
            if 'mqtt_unsubscribe' in helpers:
                self.mqtt_unsubscribe = helpers['mqtt_unsubscribe']

            if 'mqtt' in self._plugin_manager.enabled_plugins:
                mqttPlugin = self._plugin_manager.plugins['mqtt'].implementation
                if mqttPlugin:
                    self.baseTopic = mqttPlugin._settings.get(['publish', 'baseTopic'])

        if self.baseTopic:
            self._logger.info('Enable MQTT')
            self.mqtt_subscribe('%s%s' % (self.baseTopic, 'plugin/ikea_tradfri_v2/#'), self.on_mqtt_sub)

        try:
            self.load_devices(startup=True)
        except Exception as e:
            self._logger.error("Failed to get devices on startup! Error: %s", e)

        self.getStateData()

    def on_mqtt_sub(self, topic, message, retain=None, qos=None, *args, **kwargs):
        self._logger.debug("Receive mqtt message %s" % (topic))
        if self.baseTopic is None:
            return

        if topic == '%s%s%s' % (self.baseTopic, 'plugin/ikea_tradfri_v2/', 'turnOn'):
            self._logger.info('MQTT request turn on : %s', message)
            payload = json.loads(message)
            if 'id' in payload:
                dev = self.getDeviceFromId(payload['id'])
                if dev is not None:
                    self._logger.info('MQTT turn on : %s', dev['name'])
                    self.turnOn(dev)
        elif topic == '%s%s%s' % (self.baseTopic, 'plugin/ikea_tradfri_v2/', 'turnOff'):
            self._logger.info('MQTT request turn off : %s', message)
            payload = json.loads(message)
            if 'id' in payload:
                dev = self.getDeviceFromId(payload['id'])
                if dev is not None:
                    self._logger.info('MQTT turn off : %s', dev['name'])
                    self.turnOff(dev)
        elif topic == '%s%s%s' % (self.baseTopic, 'plugin/ikea_tradfri_v2/', 'state'):
            self.getStateData()

    def mqtt_publish_ikea(self, topic, payload):
        if self.baseTopic is None:
            return

        self.mqtt_publish('%s%s%s' % (self.baseTopic, 'plugin/ikea_tradfri_v2/', topic), payload)

    # ~~ SettingsPlugin mixin

    def get_settings_defaults(self):
        return dict(
            # put your plugin's default settings here
            identity="",
            gateway_ip="",
            psk="",
            selected_devices=[],
            status='',
            error_message='',
            devices=[],
            config_version_key=1
        )

    # ~~ TemplatePlugin mixin

    def get_template_configs(self):
        configs = [
            dict(type="settings", custom_bindings=True),
            dict(type="wizard", custom_bindings=True),
            dict(type="sidebar", custom_bindings=True)
        ]
        devices = self._settings.get(['selected_devices'])
        for i in range(len(devices)):
            dev = devices[i]
            hidden = not dev['nav_name'] and not dev['nav_icon']
            item = dict(
                type="navbar",
                custom_bindings=True,
                suffix="_" + str(dev['id']),
                data_bind="let: {idev: " + str(
                    i) + ", dev: settings.settings.plugins.ikea_tradfri_v2.selected_devices()[" + str(i) + "] }",
                classes=["dropdown navbar_plugin_ikea_tradfri"]
            )
            if hidden:
                item['classes'].append("navbar_plugin_ikea_tradfri_hidden")
            configs.append(item)

        return configs

    def get_template_vars(self):
        return dict(
            devices=self.devices,
            status=self.status,
            shutdownAt=self.shutdownAt,
            hasPalette2='palette2' in self._plugin_manager.enabled_plugins
        )

    # ~~ AssetPlugin mixin

    def get_assets(self):
        # Define your plugin's asset files to automatically include in the
        # core UI here.
        return dict(
            js=["js/ikea-tradfri.js"],
            css=["css/ikea-tradfri.css"],
            less=["less/ikea-tradfri.less"]
        )

    # ~~ Softwareupdate hook

    def get_update_information(self):
        # Define the configuration for your plugin to use with the Software Update
        # Plugin here. See https://github.com/foosel/OctoPrint/wiki/Plugin:-Software-Update
        # for details.
        return dict(
            ikea_tradfri=dict(
                displayName="Ikea Tradfri Plugin v2",
                displayVersion=self._plugin_version,

                # version check: github repository
                type="github_release",
                user="PascalKern",
                repo="OctoPrint-Ikea-tradfri",
                current=self._plugin_version,
                prerelease=True,

                stable_branch=dict(
                    name="Stable", branch="master", comittish=["master"]
                ),
                prerelease_branches=[
                    dict(
                        name="Unstable / Develop",
                        branch="develop",
                        comittish=["develop", "master"],
                    )
                ],

                # update method: pip
                pip="https://github.com/PascalKern/OctoPrint-Ikea-tradfri/archive/{target_version}.zip"
            )
        )

    def navbarInfoData(self):
        return dict(
            state=self.getStateData()
        )

    def planStop(self, dev, force_postpone=False):
        if dev['id'] in self.stopTimer and self.stopTimer[dev['id']] is not None:
            self.stopTimer[dev['id']].cancel()
            self.stopTimer[dev['id']] = None

        if dev['id'] in self.stopCooldown and self.stopCooldown[dev['id']] is not None:
            self.stopCooldown[dev['id']].cancel()
            self.stopCooldown[dev['id']] = None

        if dev['turn_off_mode'] == "time" or force_postpone:
            delay = int(dev['stop_timer'])
            if force_postpone:
                delay = int(dev['postpone_delay'])

            self.planStopTimeMode(dev, delay)
        else:
            self.planStopCooldown(dev)

    def planStopCooldown(self, dev):

        hotend_request = int(dev['cooldown_hotend'])
        bed_request = int(dev['cooldown_bed'])

        def wrapper():
            temps = self._printer.get_current_temperatures()

            ready_for_stop = True

            if -1 < bed_request < temps['bed']['actual']:
                ready_for_stop = False
            if -1 < hotend_request < temps['tool0']['actual'] and 'tool0' in temps:
                ready_for_stop = False

            if ready_for_stop:
                self.turnOff(dev)
                self.stopCooldown[dev['id']] = None
            else:
                self.stopCooldown[dev['id']] = threading.Timer(5, wrapper)
                self.stopCooldown[dev['id']].start()
            self._send_message("sidebar", self.sidebarInfoData())

        self.stopCooldown[dev['id']] = threading.Timer(5, wrapper)
        self.stopCooldown[dev['id']].start()
        self._send_message("sidebar", self.sidebarInfoData())

    def planStopTimeMode(self, dev, delay):
        now = math.ceil(time.time())

        if self.shutdownAt[dev['id']] is not None:
            self.shutdownAt[dev['id']] += delay
        else:
            self.shutdownAt[dev['id']] = now + delay
        stopIn = (self.shutdownAt[dev['id']] - now)
        self._logger.info("Schedule turn off in %d s" % stopIn)

        def wrapper():
            self.turnOff(dev)

        self.stopTimer[dev['id']] = threading.Timer(stopIn, wrapper)
        self.stopTimer[dev['id']].start()

        self._send_message("sidebar", self.sidebarInfoData())

    def connect_palette2(self):
        try:
            palette2Plugin = self._plugin_manager.plugins['palette2'].implementation
            palette2Plugin.palette.connectOmega(None)
        except:
            self._logger.error('Failed to connect to palette')

    def turnOn(self, device):
        if 'type' not in device or device['type'] == 'Outlet':
            self.turnOnOutlet(device['id'])
        else:
            self.turnOnLight(device['id'])

        connection_timer = int(device['connection_timer'])

        def connect():
            if 'connect_palette2' in device and device['connect_palette2']:
                self.connect_palette2()
            else:
                self._printer.connect()

        if connection_timer >= -1:
            c = threading.Timer(connection_timer, connect)
            c.start()

        self._send_message("sidebar", self.sidebarInfoData())
        self._send_message("navbar", self.navbarInfoData())

    def turnOnOutlet(self, deviceId):
        self._get_tradfri_client().get_by_id(deviceId).control.switch_on()

    def turnOnLight(self, deviceId):
        self._get_tradfri_client().get_by_id(deviceId).control.switch_off()

    def turnOff(self, device):
        self.shutdownAt[device['id']] = None
        if device['id'] in self.stopTimer and self.stopTimer[device['id']] is not None:
            self.stopTimer[device['id']].cancel()
            self.stopTimer[device['id']] = None
        if device['id'] in self.stopCooldown and self.stopCooldown[device['id']] is not None:
            self.stopCooldown[device['id']].cancel()
            self.stopCooldown[device['id']] = None

        self._send_message("sidebar", self.sidebarInfoData())
        if self._printer.is_printing():
            self._logger.warn("Don't turn off outlet because printer is printing !")
            return
        elif self._printer.is_pausing() or self._printer.is_paused():
            self._logger.warn("Don't turn off outlet because printer is in pause !")
            return
        elif self._printer.is_cancelling():
            self._logger.warn("Don't turn off outlet because printer is cancelling !")
            return

        # From commit: 426acc0d7de64499e6a57eff8caf027a28ae6396
        if not ('connect_palette2' in device and device['connect_palette2']):
            self._printer.disconnect()

        self._logger.debug('stop')
        if 'type' not in device or device['type'] == 'Outlet':
            self.turnOffOutlet(device['id'])
        else:
            self.turnOffLight(device['id'])
        self._send_message("navbar", self.navbarInfoData())

    def turnOffOutlet(self, deviceId):
        self._get_tradfri_client().get_by_id(deviceId).control.switch_off()

    def turnOffLight(self, deviceId):
        self._get_tradfri_client().get_by_id(deviceId).control.switch_off()

    def get_api_commands(self):
        return dict(
            turnOn=[], turnOff=[], checkStatus=[]
        )

    def getDeviceFromId(self, id):
        selected_devices = self._settings.get(['selected_devices']);
        device = None
        for dev in selected_devices:
            if dev['id'] == id:
                return dev
        return None

    def on_api_command(self, command, data):
        import flask
        if command == "turnOn":
            if 'dev' in data:
                self.turnOn(data['dev'])
            elif 'ip' in data:  # Octopod ?
                device = self.getDeviceFromId(int(data['ip']))
                if device is None:
                    pass
                else:
                    self.turnOn(device)
                    status = self.getStateDataById(device['id'])
                    res = dict(ip=str(device['id']), currentState=("on" if status['state'] else "off"))
                    return flask.jsonify(res)
            else:
                self._logger.warn('turn on without device data')
        elif command == "turnOff":
            if 'dev' in data:
                self.turnOff(data['dev'])
            elif 'ip' in data:  # Octopod ?
                device = self.getDeviceFromId(int(data['ip']))
                if device is None:
                    pass
                else:
                    self.turnOff(device)
                    status = self.getStateDataById(device['id'])
                    res = dict(ip=str(device['id']), currentState=("on" if status['state'] else "off"))
                    return flask.jsonify(res)
            else:
                self._logger.warn('turn off without device data')
        elif command == "checkStatus":
            status = None
            if 'dev' in data:
                status = self.getStateDataById(data["dev"]['id'])
                return flask.jsonify(status)
            elif 'ip' in data:  # Octopod ?
                device = self.getDeviceFromId(int(data['ip']))
                if device is None:
                    pass
                else:
                    status = self.getStateDataById(device['id'])
                    res = dict(ip=str(device['id']), currentState=("on" if status['state'] else "off"))
                    return flask.jsonify(res)
            else:
                self._logger.warn('checkStatus without device data')

    def get_additional_permissions(self):
        return [
            dict(key="ADMIN",
                 name="Admin",
                 description=gettext("Allow user to set config."),
                 default_groups=[ADMIN_GROUP],
                 roles=["admins"])
        ]

    @octoprint.plugin.BlueprintPlugin.route("/navbar/info", methods=["GET"])
    def navbarInfo(self):
        data = self.navbarInfoData()
        return flask.make_response(json.dumps(data), 200)

    ##Sidebar

    def sidebarInfoData(self):
        # TODO : info stop cooldown
        selected_devices = self._settings.get(['selected_devices'])
        cooldown_wait = dict()
        for dev in selected_devices:
            if dev['id'] not in self.shutdownAt:
                self.shutdownAt[dev['id']] = None
            if dev['turn_off_mode'] == "cooldown":
                val = None
                if dev['id'] in self.stopCooldown and self.stopCooldown[dev['id']] is not None:
                    val = True
                cooldown_wait[dev['id']] = val

        return dict(
            shutdownAt=self.shutdownAt,
            cooldown_wait=cooldown_wait
        )

    @octoprint.plugin.BlueprintPlugin.route("/sidebar/info", methods=["GET"])
    def sidebarInfo(self):
        data = self.sidebarInfoData()
        return flask.make_response(json.dumps(data), 200)

    @octoprint.plugin.BlueprintPlugin.route("/sidebar/postpone", methods=["POST"])
    def sidebarPostponeShutdown(self):
        dev = flask.request.json['dev']
        self.planStop(dev, True)

        self._send_message("sidebar", self.sidebarInfoData())

        return self.sidebarInfo()

    @octoprint.plugin.BlueprintPlugin.route("/sidebar/cancelShutdown", methods=["POST"])
    def sidebarCancelShutdown(self):
        device = flask.request.json['dev']
        if device['id'] in self.stopTimer and self.stopTimer[device['id']] is not None:
            self.shutdownAt[device['id']] = None
            self.stopTimer[device['id']].cancel()
            self.stopTimer[device['id']] = None
        if device['id'] in self.stopCooldown and self.stopCooldown[device['id']] is not None:
            self.stopCooldown[device['id']].cancel()
            self.stopCooldown[device['id']] = None
        self._send_message("sidebar", self.sidebarInfoData())
        return self.sidebarInfo()

    @octoprint.plugin.BlueprintPlugin.route("/sidebar/shutdownNow", methods=["POST"])
    def sidebarShutdownNow(self):
        device = flask.request.json['dev']
        self.turnOff(device)
        self._send_message("sidebar", self.sidebarInfoData())
        return self.sidebarInfo()

    @octoprint.plugin.BlueprintPlugin.route("/devices", methods=["GET"])
    def listDevices(self):
        self.load_devices()
        return flask.make_response(json.dumps(self.devices, indent=4), 200)

    @octoprint.plugin.BlueprintPlugin.route("/device/save", methods=["POST"])
    def saveDevice(self):
        if not "device" in flask.request.json:
            return flask.make_response("Missing device", 400)

        device = flask.request.json['device']

        for ikDev in self.devices:
            if ikDev['id'] == device['id']:
                device['type'] = ikDev['type']

        selected_devices = self._settings.get(['selected_devices'])
        index = -1
        for i in range(len(selected_devices)):
            dev = selected_devices[i]
            if dev['id'] == device['id']:
                index = i
                break
        if index >= 0:
            selected_devices[index] = device
        else:
            selected_devices.append(device)

        self._settings.set(['selected_devices'], selected_devices)
        self._settings.save()

        return flask.make_response(json.dumps(selected_devices, indent=4), 200)

    @octoprint.plugin.BlueprintPlugin.route("/device/delete", methods=["POST"])
    def deleteDevice(self):
        if not "device_id" in flask.request.json:
            return flask.make_response("Missing device", 400)

        device_id = flask.request.json['device_id']

        selected_devices = self._settings.get(['selected_devices'])
        index = -1
        for i in range(len(selected_devices)):
            dev = selected_devices[i]
            if dev['id'] == device_id:
                index = i
                break
        if index >= 0:
            selected_devices.remove(selected_devices[index])

        self._settings.set(['selected_devices'], selected_devices)
        self._settings.save()

        return flask.make_response(json.dumps(selected_devices, indent=4), 200)

    def getStateData(self):
        res = dict()

        selected_devices = self._settings.get(['selected_devices'])
        for device in selected_devices:
            if 'id' not in device or device['id'] is None:
                continue
            res[device['id']] = self.getStateDataById(device['id'])
            self.mqtt_publish_ikea('state/%s' % (device['id']), res[device['id']])

        return res

    def getStateDataById(self, device_id):

        device = self.getDeviceFromId(device_id)
        self._logger.debug(f"Getting state for device: '{device}")

        res = dict(
            state=self._get_tradfri_client().get_by_id(device_id).control.get_state()
        )
        return res

    def _send_message(self, msg_type, payload):
        self._logger.debug("send message type {}".format(msg_type))
        self._plugin_manager.send_plugin_message(
            self._identifier,
            dict(type=msg_type, payload=payload))

    def get_settings_version(self):
        return 5

    def on_settings_migrate(self, target, current=None):
        self._logger.info("Update version from {} to {}".format(current, target))
        settings_changed = False

        if current is None or current < 2:
            currentOutletId = self._settings.get(['selected_outlet'])
            stopTimer = self._settings.get(['stop_timer']) or 30
            postponeDelay = self._settings.get(['postponeDelay']) or 30
            connectionTimer = self._settings.get(['connection_timer']) or 5
            on_done = self._settings.get(['on_done']) or False
            on_failed = self._settings.get(['on_failed']) or False
            icon = self._settings.get(['icon']) or "plug"
            devices = [
                dict(
                    name="Printer",
                    id=currentOutletId,
                    type="Outlet",
                    connection_timer=connectionTimer,
                    stop_timer=stopTimer,
                    postpone_delay=postponeDelay,
                    on_done=on_done,
                    on_failed=on_failed,
                    icon=icon,
                    nav_name=False,
                    nav_icon=True
                )
            ]
            self._settings.set(['selected_devices'], devices)
            settings_changed = True

        selected_devices = self._settings.get(['selected_devices'])
        for dev in selected_devices:
            if 'nav_icon' not in dev:
                dev['nav_icon'] = True
                settings_changed = True
            if 'nav_name' not in dev:
                dev['nav_name'] = False
                settings_changed = True
            if 'connect_palette2' not in dev:
                dev['connect_palette2'] = False
                settings_changed = True
            if 'turn_off_mode' not in dev:
                dev['turn_off_mode'] = 'time'
                settings_changed = True
            if 'cooldown_bed' not in dev:
                dev['cooldown_bed'] = -1
                settings_changed = True
            if 'cooldown_hotend' not in dev:
                dev['cooldown_hotend'] = 50
                settings_changed = True

        self._settings.set(['selected_devices'], selected_devices)
        if settings_changed:
            self._settings.save()

    def on_event(self, event, payload):
        self._logger.info("Got event: '%s' with payload: '%s'" % (event, payload))

        devices = self._settings.get(['selected_devices'])
        for dev in devices:
            schedule_stop = False
            if event == 'PrintDone' and dev['on_done']:
                schedule_stop = True
            if event == 'PrintFailed' and dev['on_failed']:
                schedule_stop = True
            if schedule_stop:
                self.planStop(dev)
            elif event == 'PrintStarted':
                if dev['id'] in self.stopTimer and self.stopTimer[dev['id']] is not None:
                    self.stopTimer[dev['id']].cancel()
                    self.stopTimer[dev['id']] = None
                if dev['id'] in self.stopCooldown and self.stopCooldown[dev['id']] is not None:
                    self.stopCooldown[dev['id']].cancel()
                    self.stopCooldown[dev['id']] = None