#!/usr/bin/env python3


import argparse
import logging
import paho.mqtt.client as mqtt

from collections import namedtuple
from rpi_rf import RFDevice


logging.basicConfig(level=logging.INFO, datefmt='%Y-%m-%d %H:%M:%S',
                    format='%(asctime)-15s - [%(levelname)s] %(module)s: %(message)s',)

parser = argparse.ArgumentParser(description='Sends mqtt commands to GPIO RF switches')
parser.add_argument('-g', dest='gpio', type=int, default=17,
                    help="GPIO pin (Default: 17)")
parser.add_argument('-p', dest='pulselength', type=int, default=None,
                    help="Pulselength (Default: 350)")
parser.add_argument('-t', dest='protocol', type=int, default=None,
                    help="Protocol (Default: 1)")
parser.add_argument('-r', dest='repeat', type=int, default=40,
                    help="Repeat (Default: 40)")
args = parser.parse_args()

rfdevice = RFDevice(args.gpio, tx_repeat=args.repeat)
rfdevice.enable_tx()
client = mqtt.Client(client_id="mqtt_rf_py", clean_session=False)

SWITCHES = {
  'living_room': dict(on=5330227, off=5330236),
  'tv': dict(on=5330371, off=5330380),
  'bedroom' : dict(on=5330691, off=5330700),
  'speaker' : dict(on=5332227, off=5332236),
}

def on_message(client, userdata, message):
  topic_seg = message.topic.strip().split('/')
  payload = message.payload.decode().strip()
  logging.info('received message: {0}:{1}'.format(message.topic.strip(), payload))
  handle_message(switch_name=topic_seg[2], state=payload)

def handle_message(switch_name, state):
  if not switch_name in SWITCHES:
    logging.error('Unknown switch: {0}'.format(switch_name))
    return
  if not state in SWITCHES[switch_name]:
    logging.error('Unknown state: {0}'.format(state))
    return
   
  tx_code = SWITCHES[switch_name][state]
  logging.info('Sending {0} [protocol: {1}, pulselength: {2}]'.format(
      tx_code, args.protocol, args.pulselength))
  rfdevice.tx_code(int(tx_code), args.protocol, args.pulselength)
  

client.connect("localhost", port=1883, keepalive=60)
client.subscribe("home/switch/#")
client.on_message = on_message
client.loop_forever()

