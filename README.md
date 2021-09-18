# pyscript-ruuvi-gateway

Python script for the pyscript addon in Home Assistant. It watches a MQTT topic for messages from a [Ruuvi Gateway](https://ruuvi.com), decodes and processes them, and sends the data back to MQTT formatted for Home Assistant auto-discovery.

## Installation and Use

### Configuring Home Assistant
1. Install the [pyscript addon](https://hacs-pyscript.readthedocs.io/en/latest/)
2. Copy ruuvi-gateway.py to /config/pyscript/apps
3. Add ruuvi_decoders (the [ruuvi_decoders Python module](https://github.com/ruuvi-friends/ruuvi-decoders)) to requirements.txt in the /config/pyscript folder.
4. Add your application configuration to config/configuration.yaml (see the [configuration-sample.yaml](configuration-sample.yaml)) file for an example)
5. Reload the pyscript addon

### Configuring the Ruuvi Gateway
1. Select *Custom server* under Advanced when prompted to configure where to send Ruuv Tag data
2. Select MQTT and configure it as follows:
   * Server - the IP address (or resolvable FQDN) of your MQTT broker
   * Port - the port your MQTT broker is listening for non-SSL requests on; usually this is 1883
   * User name - the user to use when connecting to your MQTT broker
   * Password - the password to use when connecting to your MQTT broker
   * Client name - the client name used when connecting to the MQTT server (MAC address default is fine)
   * Topic prefix - the high-level topic prefix must match what's configured for MQTT_TOPIC_PREFIX in the script
3. Once finished, power cycle the gateway to begin sending any received sensor beacons to MQTT

### Basic Metric Transformations
Note that you can use a rudimentary arithmetic expression to modify a metric value by including a "transform" element for the metric in the config file. This is best-effort; i.e. it works for the two simple use-cases I had (convert C to F, and calculate a sort-of battery level remaining percentage). I took the code directly from Stack Overflow, it's pretty much guaranteed to be fragile, YMMV, etc.. 

### Troubleshooting
One utility that's extremely helpful if using the Mosquitto MQTT broker addon for Home Assistant is *mosquitto_sub* (installed by default with Mosquitto). 

E.g. to view messages being sent from the gateway to the MQTT top-level topic "ruuvi", Open an SSH terminal to your Home Assistant instance and enter:
```
mosquitto_sub -h <MQTT_BROKER_IP> -u <MQTT_USERNAME> -P "<MQTT_PASSWORD>" -v -t "ruuvi/#"
```

This will subscribe you to the topic and allow you to view messages as they come in to the broker. To check whether the messages are being correctly processed and submitted back to MQTT, replace "ruuvi" in the topic with "homeassist/sensor".


