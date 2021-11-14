from octoprint.plugin import TemplatePlugin, SettingsPlugin


class IkeaTradfriPluginTemplate(
    TemplatePlugin,
    SettingsPlugin
):

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
                    i) + ", dev: settings.settings.plugins.ikea_tradfri.selected_devices()[" + str(i) + "] }",
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
