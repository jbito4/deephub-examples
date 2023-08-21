
print ("abc")
from email import message
#from ossaudiodev import SNDCTL_DSP_BIND_CHANNEL


def callback_on_open (ws):
  body = '{"event": "subscribe", "topic" : "location_updates"}'
  ws.send (body)
  body = '{"event": "subscribe", "topic" : "fence_events"}'
  ws.send (body)
  body = '{"event": "subscribe", "topic" : "trackable_motions"}'
  ws.send (body)
  body = '{"event": "subscribe", "topic" : "collision_events"}'
  ws.send (body)

def callback_on_close (ws):
  print ("### Connection to " + ws.url + " was closed.")

def callback_on_message (ws, message):
  import json
  messageAsJson = json.loads (message)
  print (messageAsJson)


def callback_on_error (ws, error):
  if error:
    print (error)


#
# MAIN
#

# subscribe to location updates and wait for events
  # Import WebSocket client library

  # Connect to WebSocket with no timeout
deephub_ws_url   = 'ws://localhost:8081/deephub'

import websocket
ws = websocket.WebSocketApp(deephub_ws_url + "/v1/ws/socket",
                              on_message = callback_on_message, 
                              on_error   = callback_on_error, 
                              on_open    = callback_on_open,
                              on_close   = callback_on_close)

ws.run_forever (ping_interval = 30)


  # Infinite loop waiting and dumping for WebSocket data
while True:
    print (ws.recv())


