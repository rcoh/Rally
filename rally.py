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
    self.live_messages = {} #hash -> Message
    self.dead_messages = {} #hash -> Message
    self.msg_acks = {}
    self.sent_msgs = {}
  
  def incoming_message(self, message, client):
    print 'incoming!', message
    if message.is_ack():
      self.ack_received(message, client) 
    else:
      for ptr in self.client_ptrs:
        if not message.get_hash() in self.sent_msgs:
          self.sent_msgs[message.get_hash()] = []

        if not ptr in self.sent_msgs[message.get_hash()]:
          self.send_to_client(ptr, message)
          self.sent_msg[message.get_hash()].append(ptr)
 
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

  def new_msg(self, message):
    message.require_acks(self.clients.keys[:])
    self.live_messages[message.get_hash()] = message
    self.distribute(message)

  def check_for_missed_messages(self):
    pass


class ReliableChatClient(ReliableChatClientSocket):
  
  def __init__(self, name, server_loc):
    super(ReliableChatClient, self).__init__(*server_loc)
    self.send_queue = [] #messages that have not been acked
    self.rcv_queue = [] #messages that have been acked / messages from others
    self.live_pile = {}
    self.dead_pile = {}
    self.queue_lock = threading.RLock() 
    self.connected = False
    self.try_connect()

  @retry_with_backoff("message_acked")
  def say_require_ack(self, message):
    self.send_queue.append(message)
    self.live_pile[message.get_hash()] = message
    self.say(message)
    
  def say(self, message):
    self.send_message(message)

  @synchronized("queue_lock")
  def rcv_message(self, message):
    if not message in self.rcv_queue: #TODO: doesn't work until equals is overridden
      self.rcv_queue.append(message)
      self.got_new_message(message)

    if message in self.send_queue:
      self.send_queue.remove(message)

    if message.get_hash() in self.live_pile:
      del self.live_pile[message.get_hash()]
    
    self.dead_pile[message.get_hash()] = message
    self.say(Message.ack_for(message))

  def message_acked(self, message):
    return message.get_hash() in self.dead_pile

  def got_new_message(self, message):
    print message, 'override!'
  
  @retry_with_backoff("is_connected")
  def try_connect(self):
    try:
      self.connect()
    except Exception as e: #TODO: actual exception types
      print 'tried to connect, but failed'
      print e
      return

    self.connected = True

  def is_connected(self):
    return self.connected

  def disconnected(self):
    self.try_connect()

