#!/srv/homeassistant/bin/python3

import socket
import struct
import paho.mqtt.client as mqtt
import json

def get_config():
    with open('dash_button.json') as f:
        return json.load(f)

def mac_addr(mac):
    return "".join(map(lambda m: "%.2X" % m, mac))

cfg = get_config()
rawSocket = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(0x0003))
mqtt_client = mqtt.Client(client_id="dash_button_py", clean_session=False)
mqtt_client.connect(cfg['mqtt'], cfg['port'], 60)
mqtt_client.loop_start()
while True:
    packet = rawSocket.recvfrom(2048)
    ethernet_header = packet[0][:14]
    ethernet_detailed = struct.unpack("!6s6s2s", ethernet_header)
    # skip non-ARP packets
    ethertype = ethernet_detailed[2]
    if ethertype[0] != 0x08 or ethertype[1] != 0x06:
        continue
    arp_header = packet[0][14:42]
    arp_detailed = struct.unpack("2s2s1s1s2s6s4s6s4s", arp_header)
    source_mac = mac_addr(arp_detailed[5])
    macs = cfg['dash_buttons']
    if source_mac in macs:
        mqtt_client.publish("dashbutton/%s" % macs[source_mac], "")
        print("%s pressed" % macs[source_mac])
    elif cfg['discover']:
        print("Unknown MAC " + source_mac)
