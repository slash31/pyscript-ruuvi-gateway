#----------------------------------------------------------------------------
# Author  : Aaron Finney
# Created : September 14, 2021
# Updated : September 21, 2021
# Version : 0.1.2
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
    elif isinstance(node, ast.Constant): # <constant>
        return node.n
    elif isinstance(node, ast.BinOp): # <left> <operator> <right>
        return operators[type(node.op)](eval_(node.left), eval_(node.right))
    elif isinstance(node, ast.UnaryOp): # <operator> <operand> e.g., -1
        return operators[type(node.op)](eval_(node.operand))
    else:
        raise TypeError(node)


@mqtt_trigger(f"{pyscript.app_config['mqtt_topic_prefix']}/#")
def mqtt_msg(topic=None, payload=None, payload_obj=None):
    ruuvitags = pyscript.app_config['ruuvitags']
    measurement_config = pyscript.app_config['measurements']
    # get the MAC from the topic because data format 3 doesn't include it
    raw_mac = topic.split('/')[-1]
    mac = raw_mac.lower().replace(':','')
    if mac not in ruuvitags:
        # this sensor is not in the list of tags to process, ignore
        log.warning(f"MAC addres {mac} not in ruuvitags, ignoring tag")
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
            # add rssi to the data structure
            data['rssi'] = payload_obj.get("rssi")

            for m_type in measurement_config:
                value = data.get(measurement_config[m_type]["source_metric"])
                if "transform" in measurement_config[m_type]:
                    value = eval_(ast.parse(f"{measurement_config[m_type]['transform']['expression']}".replace("<VALUE>",str(value)), mode='eval').body)
                    if "min_val" in measurement_config[m_type]['transform']:
                        value = min(value, measurement_config[m_type]['transform']['max_val'])
                    if "max_val" in measurement_config[m_type]['transform']:
                        value = max(value, measurement_config[m_type]['transform']['min_val'])

                if isinstance(value,float):
                    if "precision" in measurement_config[m_type]:
                        value = round(value, measurement_config[m_type]['precision'])
                        if measurement_config[m_type]['precision'] == 0:
                            value = int(value)

                if not sensor_exists(mac):
                    config_topic = f"homeassistant/sensor/{mac}/{m_type}/config"
                    config_payload = dumps(measurement_config[m_type]['config']).replace('<MAC>',mac).replace('<TAG_NAME>', ruuvitags[mac])
                    attributes_topic = f"homeassistant/sensor/{mac}/{m_type}/attributes"
                    attributes_payload = dumps(measurement_config[m_type]['attributes']).replace('<MAC>',mac)
                    mqtt.publish(topic=config_topic, payload=config_payload, retain='True')
                    mqtt.publish(topic=attributes_topic, payload=attributes_payload, retain='True')

                state_topic = f"homeassistant/sensor/{mac}/{m_type}/state"
                mqtt.publish(topic=state_topic, payload=value, retain='True')

        except (AttributeError, ValueError, TypeError) as err:
            log.warning(f'Error --> {payload}')
            log.warning(f'Error code -> {err}')
