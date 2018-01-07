#!/srv/homeassistant/bin/python3

import socket
import struct
import paho.mqtt.client as mqtt
import json
import argparse
import logging

def get_config():
    with open('dash_button.json') as f:
        return json.load(f)

def mac_addr(mac):
    return ":".join(map(lambda m: "%.2X" % m, mac))

def extract_mac(packet):
    ethernet_header = packet[0][:14]
    ethernet_detailed = struct.unpack("!6s6sH", ethernet_header)
    ethertype = ethernet_detailed[2]
    if ethertype == 0x0806:  # ARP
        arp_header = packet[0][14:42]
        arp_detailed = struct.unpack("2s2s1s1s2s6s4s6s4s", arp_header)
        return arp_detailed[5]
    elif ethertype == 0x0800:  # IPv4
        ip_header = packet[0][14:34]
        ip_detailed = struct.unpack("LLBBHLL", ip_header)
        if ip_detailed[3] != 0x11:  # UDP
            return None
        if ip_detailed[5] != 0x00 or ip_detailed[6] != 0xffffffff:
            return None
        logger.debug("UDP broadcast")
        udp_data = packet[0][34:]
        return udp_data[36:42]
    else:
        return None

logging.basicConfig(format="%(relativeCreated)5d %(name)-15s %(levelname)-8s %(message)s")
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--mqtt", dest="mqtt", action="store_const", const=str, default="localhost")
parser.add_argument("--port", dest="port", action="store_const", const=int, default=1883)
parser.add_argument("--discovery", dest="discovery", action="store_true")
parser.add_argument("--debug", dest="loglevel", action="store_const", const=logging.DEBUG, default=logging.INFO)
args = parser.parse_args()
logger = logging.getLogger("dash_button")
logger.setLevel(args.loglevel)
cfg = get_config()
rawSocket = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(0x0003))
mqtt_client = mqtt.Client(client_id="dash_button_py", clean_session=False)
mqtt_client.connect(args.mqtt, args.port, 60)
mqtt_client.loop_start()
logger.info("Listening ARP")
while True:
    packet = rawSocket.recvfrom(2048)
    mac_bytes = extract_mac(packet)
    if mac_bytes is None:
        continue
    source_mac = mac_addr(mac_bytes)
    logger.debug("MAC %s" % source_mac)
    macs = cfg['dash_buttons']
    if source_mac in macs:
        mqtt_client.publish("dashbutton/%s" % macs[source_mac], "")
        logger.info("%s pressed" % macs[source_mac])
    elif args.discovery:
        logger.info("Unknown MAC " + source_mac)
