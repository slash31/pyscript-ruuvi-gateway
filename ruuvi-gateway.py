#----------------------------------------------------------------------------
# Author  : Aaron Finney
# Created : September 14, 2021
# Updated : September 15, 2021
# Version : 0.0.3
# 
# This script watches an MQTT topic for messages from a Ruuvi Gateway, decodes
# them, performs basic processing (if configured), and re-emits them to MQTT
# in the correct format for Home Assistant to consume as auto-discovered sensors.
#
# ---------------------------------------------------------------------------

from ruuvi_decoders import Df3Decoder, Df5Decoder
from json import dumps
import ast
import operator

# Configuration variables
MQTT_TOPIC_PREFIX = "ruuvi" # this must match what's configured in the Gateway MQTT settings
DECIMAL_PLACES = 2 # number of decimal places for values
BATTERY_RANGE = {"min":2500,"max":3000} # min/max battery range, used to calcuate battery level
# RUUVITAGS defines the tags, by MAC address, that the script will process; any tag not included
# in this dictionary will be ignored by the script. The value for each item is used as the string
# to replace <TAG_NAME> in the emitted MQTT message payload
RUUVITAGS = {"f33c5fc10393":"Living Room Ruuvitag",
            "dc757bb86337":"Middle Bedroom Ruuvitag",
            "f9fd6a322a01":"Front Bedroom Ruuvitag",
            "dc2c241a4b24":"Kitchen Ruuvitag",
            "ef336477a31a":"Back Bedroom Ruuvitag"}
# MEASUREMENT CONFIG specifies which measurements to write back to MQTT, any transformations to be performed
# on the values, and the config payload. The special values <MAC> and <TAG_NAME> are
# replaced prior to emitting the config message to MQTT
MEASUREMENT_CONFIG = {"temperature": 
                        {"config":
                            {"stat_t":"homeassistant/sensor/<MAC>/temperature/state",
                            "json_attr_t":"homeassistant/sensor/<MAC>/temperature/attributes",
                            "name":"<TAG_NAME> Temperature",
                            "unit_of_meas":"\u00b0F",
                            "dev_cla":"temperature",
                            "uniq_id":"ruuvitag_<MAC>_temperature",
                            "device":
                                {"ids":"ruuvitag-<MAC>",
                                "mf":"Ruuvi Innovations Ltd",
                                "mdl": "RuuviTag",
                                "name": "<TAG_NAME>"
                                }
                            },
                        "transform": "(<VALUE>*(9/5))+32",
                        "source_metric": "temperature"},
                      "humidity": 
                        {"config":
                            {"stat_t":"homeassistant/sensor/<MAC>/humidity/state",
                            "json_attr_t":"homeassistant/sensor/<MAC>/humidity/attributes",
                            "name":"<TAG_NAME> Humidity",
                            "unit_of_meas":"%",
                            "dev_cla":"humidity",
                            "uniq_id":"ruuvitag_<MAC>_humidity",
                            "device":
                                {"ids":"ruuvitag-<MAC>",
                                "mf":"Ruuvi Innovations Ltd",
                                "mdl": "RuuviTag",
                                "name": "<TAG_NAME>"
                                }
                            },
                        "transform": None,
                        "source_metric": "humidity"},
                      "battery_level":
                        {"config":
                            {"stat_t":"homeassistant/sensor/<MAC>/battery_level/state",
                            "json_attr_t":"homeassistant/sensor/<MAC>/battery_level/attributes",
                            "name":"<TAG_NAME> Battery Level",
                            "unit_of_meas":"%",
                            "dev_cla":"battery",
                            "uniq_id":"ruuvitag_<MAC>_battery",
                            "device":
                                {"ids":"ruuvitag-<MAC>",
                                "mf":"Ruuvi Innovations Ltd",
                                "mdl": "RuuviTag",
                                "name": "<TAG_NAME>"
                                }
                            },
                        "transform": f"((<VALUE> - {BATTERY_RANGE['min']}) / ({BATTERY_RANGE['max']} - {BATTERY_RANGE['min']})) * 100",
                        "source_metric": "battery"}
                     }


def sensor_exists(mac):
    try:
        sensor = f"sensor.{mac}"
        return state.get(sensor) != "unavailable"
    except (NameError):
        return False

def eval_(node):
    operators = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
                ast.Div: operator.truediv, ast.Pow: operator.pow, ast.BitXor: operator.xor,
                ast.USub: operator.neg}

    if isinstance(node, ast.Num): # <number>
        return node.n
    elif isinstance(node, ast.BinOp): # <left> <operator> <right>
        return operators[type(node.op)](eval_(node.left), eval_(node.right))
    elif isinstance(node, ast.UnaryOp): # <operator> <operand> e.g., -1
        return operators[type(node.op)](eval_(node.operand))
    else:
        raise TypeError(node)


@mqtt_trigger(f"{MQTT_TOPIC_PREFIX}/#")
def mqtt_msg(topic=None, payload=None, payload_obj=None):
    # get the MAC from the topic because data format 3 doesn't include it
    raw_mac = topic.split('/')[-1]
    mac = raw_mac.lower().replace(':','')
    if mac not in RUUVITAGS:
        # this sensor is not in the list of tags to process, ignore
        log.warning(f"MAC addres {mac} not in RUUVITAGS, ignoring tag")
        return
    if payload_obj.get("data") is not None:
        try:
            raw_data = payload_obj.get("data")
            clean_data = raw_data.split("FF9904")[1]

            # decode the data
            format = clean_data[0:2]
            data = {}
            if format == "03":
                decoder = Df3Decoder()
                data = decoder.decode_data(clean_data)
            else:
                decoder = Df5Decoder()
                data = decoder.decode_data(clean_data)

            for m_type in MEASUREMENT_CONFIG:
                value = data.get(MEASUREMENT_CONFIG[m_type]["source_metric"])
                if MEASUREMENT_CONFIG[m_type]["transform"] is not None:
                    value = eval_(ast.parse(f"{MEASUREMENT_CONFIG[m_type]['transform']}".replace("<VALUE>",str(value)), mode='eval').body)
                if isinstance(value,float):
                    value = round(value, DECIMAL_PLACES)

                if not sensor_exists(mac):
                    config_topic = f"homeassistant/sensor/{mac}/{m_type}/config"
                    config_payload = dumps(MEASUREMENT_CONFIG[m_type]['config']).replace('<MAC>',mac).replace('<TAG_NAME>', RUUVITAGS[mac])
                    mqtt.publish(topic=config_topic, payload=config_payload, retain='True')

                state_topic = f"homeassistant/sensor/{mac}/{m_type}/state"
                mqtt.publish(topic=state_topic, payload=value, retain='True')

        except (AttributeError, ValueError, TypeError):
            log.warning(f'Error --> {payload}')
