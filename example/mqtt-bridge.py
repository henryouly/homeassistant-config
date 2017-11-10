#!/usr/bin/env python3

import json
import logging
import paho.mqtt.client as mqtt

from paho.mqtt.client import Client, MQTT_ERR_SUCCESS
from tornado.ioloop import IOLoop
from tornado.web import RequestHandler, Application
from tornado.escape import json_decode

CONFIG_FILE = "config.json"
STATE_FILE = "state.json"
client = Client(client_id="mqtt_bridge", clean_session=False)
subscriptions = []
callback = ""
config = {"host":"localhost", "port":15382, "preface":"smartthings"}

class PushHandler(RequestHandler):
  """
  * @param  {String}  req.body.name  Device Name (e.g. "Bedroom Light")
  * @param  {String}  req.body.type  Device Property (e.g. "state")
  * @param  {String}  req.body.value Value of device (e.g. "on")
  """
  def post(self):
    data = json_decode(self.request.body)
    value = data["value"]
    topic = getTopicFor(data["name"], data["type"])
    logging.info("Incoming message from SmartThings: {0} = {1}".format(topic, value))
    res, mid = client.publish(topic, value, retain=True)
    if res == MQTT_ERR_SUCCESS:
      self.write({"status": "OK"})

class SubscribeHandler(RequestHandler):
  def post(self):
    data = json_decode(self.request.body)
    global subscriptions,callback
    subscriptions = []
    devices = data["devices"]
    for property in devices:
      for device in devices[property]:
        topic = getTopicFor(device, property)
        subscriptions.append(topic)
    logging.info("Subscribing to {0}".format(subscriptions))
    global callback
    callback = data["callback"]
    logging.info("Received callback: {0}".format(callback))
      
    for topic in subscriptions:
      client.subscribe(topic)
    self.write({"status": "OK"})
    saveState()

def on_message(client, userdata, message):
  topic = message.topic
  value = message.payload.decode()
  logging.info("Incoming message from MQTT: {0} = {1}".format(topic, value))
  _, device, property = topic.strip().split('/') 
  topicState = getTopicFor(device, property)
  topicSwitchState = getTopicFor(device, "switch")
  topicLevelCommand = getTopicFor(device, "level")
  
  logging.info("Sending message to {0}".format(callback))
  import requests
  res = requests.post('http://' + callback, json={"name": device, "type": property, "value": value.strip()})
  if res.status_code >= 300:
    logging.error("Error from SmartThings Hub: {0}".format(res.status_code))

def on_connect(client, userdata, flags, rc):
  logging.info("Connected to MQTT, code {0}".format(rc))
  for topic in subscriptions:
    client.subscribe(topic)

def connectToMQTT(host):
  logging.info("Connecting to MQTT at {0}".format(host))
  client.on_message = on_message
  client.on_connect = on_connect
  client.connect(host, port=1883)
  client.loop_start()

def getTopicFor(device, property):
  return "/".join([config["preface"], device, property])

def loadConfig():
  try:
    with open(CONFIG_FILE) as f:
      global config
      config = json.load(f)
  except IOError as e:
    logging.info("Not loading config {0}: {1}".format(CONFIG_FILE, e))

def loadSavedState():
  try:
    with open(STATE_FILE) as f:
      state = json.load(f)
      global callback,subscriptions
      subscriptions = state["subscriptions"]
      callback = state["callback"]
  except IOError as e:
    logging.info("Not loading state {0}: {1}".format(STATE_FILE, e))

def saveState():
  try:
    with open(STATE_FILE, "w") as out:
      state = {"subscriptions":subscriptions, "callback":callback}
      json.dump(state, out)
  except IOError as e:
    logging.info("Not saving state: {0}".format(e))

if __name__ == "__main__":
  logging.basicConfig(level=logging.INFO, datefmt='%Y-%m-%d %H:%M:%S',
                      format='%(asctime)-15s - [%(levelname)s] %(module)s: %(message)s',)
  app = Application([
      (r"/push", PushHandler),
      (r"/subscribe", SubscribeHandler),
  ])
  loadConfig()
  port = config["port"]
  app.listen(port)
  logging.info("Listening at http://localhost:{0}".format(port))
  loadSavedState()
  connectToMQTT(config["host"])
  IOLoop.current().start()
