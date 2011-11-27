import threading
import pickle
import time
from threading import Timer
import SocketServer
from threading import Thread
from socket import *
from network import *
from model import *
"""General principle: 
  Client sends message -> Server replies message to all clients
  Client sends hash back as ack to server.

  Server keeps queue of messages to be distributed.  Messages are removed from queue when all
  clients have acked.
  Messages on the queue are periodically resent to unacked recipients.
    Consume all messages on the queue, resending 

  Client pushes sent messages onto Queue.  When it recieves an ACK, remove message from queue.
  "*" message to indicate receipt.
"""

class ReliableChatServer(ReliableChatServerSocket):
  
  def __init__(self, port):
    ReliableChatServerSocket.__init__(self)
    self.msg_acks = {}
    self.sent_msgs = {}
    self.all_msgs = {} #timestamp -> msg
  
  def incoming_message(self, message, client):
    print 'incoming!', message
    if message.is_ack():
      self.ack_received(message, client) 
    #TODO: hashing scheme to provide proof of no-missed-messages
    elif message.is_new_connect(): #catch clients up on missed messages
      latest = float(message.content)
      for ts in self.all_msgs:
        if ts > latest:
          self.send_to_client(client, self.all_msgs[ts])

    else:
      self.all_msgs[message.timestamp] = message
      for ptr in self.client_ptrs:
        if not message.get_hash() in self.sent_msgs:
          self.sent_msgs[message.get_hash()] = []

        if not ptr in self.sent_msgs[message.get_hash()]:
          self.send_to_client(ptr, message)
          self.sent_msgs[message.get_hash()].append(ptr)
 
  @retry_with_backoff("msg_acked")
  def send_to_client(self, client_ptr, message):
    self.send_msg(client_ptr, message)
  
  def ack_received(self, message, client):
    print 'got an ack!'
    if not message.content in self.msg_acks:
      self.msg_acks[message.content] = []
    self.msg_acks[message.content].append(client)

  def msg_acked(self, client, message):
    if message.get_hash() in self.msg_acks:
      return client in self.msg_acks[message.get_hash()]

class ReliableChatClient(ReliableChatClientSocket):
  
  def __init__(self, name, server_loc):
    super(ReliableChatClient, self).__init__(*server_loc)
    self.msg_stack = []
    self.live_pile = {}
    self.dead_pile = {}
    self.queue_lock = threading.RLock() 
    self.connected = False
    self.ready_for_messages = False
    self.try_connect()

  @retry_with_backoff("message_acked")
  def say_require_ack(self, message):
    if not (message.timestamp, message) in self.msg_stack:
      self.msg_stack.append((message.timestamp, message))
      self.live_pile[message.get_hash()] = message

    self.say(message)
    self.data_changed_ptr()
    
  def say(self, message):
    self.send_message(message)

  @synchronized("queue_lock")
  def rcv_message(self, message):
    if not (message.timestamp, message) in self.msg_stack:
      self.msg_stack.append((message.timestamp, message))
      self.got_new_message(message)

    if message.get_hash() in self.live_pile:
      del self.live_pile[message.get_hash()]
    
    self.dead_pile[message.get_hash()] = message
    self.say(Message.ack_for(message))
    self.data_changed_ptr()
  
  def maintain_stack(self):
    self.msg_stack.sort()

  def send_new_connection_message(self): #TODO: specific ack + retry logic
    if self.msg_stack:
      last_received, message = self.msg_stack[-1]
    else:
      last_received = -1

    self.say(Message('', last_received, 2)) #TODO: use constant
    self.ready_for_messages = True

  def message_acked(self, message):
    return message.get_hash() in self.dead_pile

  def got_new_message(self, message):
    pass

  def data_changed_ptr(self):
    self.maintain_stack()
    msgs = [m for t,m in self.msg_stack]
    return self.data_changed(msgs, self.dead_pile)

  def data_changed(self, messages, acked_dict):
    print 'override!'
  
  @retry_with_backoff("is_connected")
  def try_connect(self):
    #try:
      self.connect()
      self.send_new_connection_message()
      self.connected = True
      return
    #except Exception as e: 
      print 'tried to connect, but failed'
      print e
      self.connected = False
      return


  def is_connected(self):
    return self.connected

  def disconnected(self):
    self.connected = False
    self.try_connect()

