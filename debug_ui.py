import sys
import util
from rally import *
from model import Message
import threading

class DebugRallyClient(object):
  def __init__(self, server, port):
    self.user_name = raw_input('user name?')
    self.client = ReliableChatClient(self.user_name, (server, port))
    self.client.data_changed = self.new_data
    self.client.try_connect()
    while 1:
      self.user_message(raw_input(''))

  def new_data(self, msgs, acks):
    pass
    #print 'we got some new data'

  def user_message(self, message):
    self.client.say_require_ack(Message(self.user_name, message, 0))

if __name__ == "__main__":
  server = 'raptor-lights.mit.edu'
  port = 5959
  if len(sys.argv) >= 2:
    server = sys.argv[1]
  if len(sys.argv) == 3:
    port = int(sys.argv[2])

  u = DebugRallyClient(server, port)
