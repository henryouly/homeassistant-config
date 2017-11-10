#!/usr/bin/env python3

import logging
import paho.mqtt.client as mqtt

from paho.mqtt.client import Client, MQTT_ERR_SUCCESS
from tornado.ioloop import IOLoop
from tornado.web import RequestHandler, Application
from tornado.escape import json_decode

PREFACE = "smartthings"
PORT = 15382
client = Client(client_id="mqtt_bridge", clean_session=False)
subscriptions = []
callback = ""
history = {}

class MainHandler(RequestHandler):
  def get(self):
    self.write("This message comes from Tornado ^_^")


class PushHandler(RequestHandler):
  """
  * @param  {String}  req.body.name  Device Name (e.g. "Bedroom Light")
  * @param  {String}  req.body.type  Device Property (e.g. "state")
  * @param  {String}  req.body.value Value of device (e.g. "on")
  """
  def post(self):
    logging.info("/push: {0}".format(self.request.body))
    data = json_decode(self.request.body)
    name = data["name"]
    type = data["type"]
    value = data["value"]
    topic = "/".join([PREFACE, name, type])
    logging.info("Incoming message from SmartThings: {0} = {1}".format(topic, value))
    res, mid = client.publish(topic, value, retain=True)
    if res == MQTT_ERR_SUCCESS:
      self.write({"status": "OK"})

class SubscribeHandler(RequestHandler):
  def post(self):
    logging.info("/subscribe: {0}".format(self.request.body))
    data = json_decode(self.request.body)
    global subscriptions
    subscriptions = []
    devices = data["devices"]
    for property in devices:
      for device in devices[property]:
        topic = "/".join([PREFACE, device, property])
        subscriptions.append(topic)
    global callback
    callback = data["callback"]
    logging.info("Received callback: {0}".format(callback))
      
    logging.info("Subscribing to {0}".format(",".join(subscriptions)))
    for topic in subscriptions:
      client.subscribe(topic)
    self.write({"status": "OK"})

def on_message(client, userdata, message):
  logging.info("Incoming message from MQTT: {0} = {1}".format(message.topic, message.payload.decode()))
  pieces = message.topic.strip().split('/') 
  device = pieces[1]
  property = pieces[2]
  topicState = "/".join([PREFACE, device, property])
  topicSwitchState = "/".join([PREFACE, device, "switch"])
  topicLevelCommand = "/".join([PREFACE, device, "level"])
  
  logging.info("Sending message to {0}".format(callback))
  import requests
  res = requests.post('http://' + callback, json={"name": device, "type": property, "value": message.payload.decode().strip()})
  if res.status_code >= 300:
    logging.error("Error from SmartThings Hub: {0}".format(res.status_code))

def on_connect(client, userdata, flags, rc):
  logging.info("Connected to MQTT, code {0}".format(rc))
  if len(subscriptions) > 0:
    client.subscribe(subscripts)

def connectToMQTT(host):
  logging.info("Connecting to MQTT at {0}".format(host))
  client.on_message = on_message
  client.on_connect = on_connect
  client.connect(host, port=1883)
  client.loop_start()

def make_app():
  return Application([
      (r"/", MainHandler),
      (r"/push", PushHandler),
      (r"/subscribe", SubscribeHandler),
  ])

if __name__ == "__main__":
  logging.basicConfig(level=logging.INFO, datefmt='%Y-%m-%d %H:%M:%S',
                      format='%(asctime)-15s - [%(levelname)s] %(module)s: %(message)s',)
  app = make_app()
  app.listen(PORT)
  logging.info("Listening at http://localhost:{0}".format(PORT))
  connectToMQTT("localhost")
  IOLoop.current().start()
