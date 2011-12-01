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
    ReliableChatServerSocket.__init__(self, port)
    self.msg_acks = {}
    self.sent_msgs = {}
    self.all_msgs = {} #hashcode -> msg
    self.identity = {} #socket_ptr -> name
  
  def incoming_message(self, message, client):
    log(message)
    if message.is_ack():
      self.ack_received(message, client) 
    #TODO: hashing scheme to provide proof of no-missed-messages
    elif message.is_new_connect(): #catch clients up on missed messages
      self.update_identity(message, client)
      latest = float(message.content)
      missed_messages = []
      for hashcode in self.all_msgs:
        if self.all_msgs[hashcode].timestamp > latest:
          missed_messages.append(self.all_msgs[hashcode])

      pickled = pickle.dumps(missed_messages, 2)
      self.send_to_client(client, Message('server', pickled, 2))
      self.client_connected(client)
    else: #its a content message
      self.update_identity(message, client)
      self.reliable_distribute(message)
      self.all_msgs[message.get_hash()] = message
  
  def reliable_distribute(self, message):
    for ptr in self.client_ptrs:
      if not message.get_hash() in self.sent_msgs:
        self.sent_msgs[message.get_hash()] = []

      if not ptr in self.sent_msgs[message.get_hash()]:
        self.send_to_client(ptr, message)
        self.sent_msgs[message.get_hash()].append(ptr)

  def client_disconnected(self, client):
    if client in self.identity:
      self.reliable_distribute(Message('Server', self.identity[client] + ' has disconnected', 0))

  def client_connected(self, client):
    if client in self.identity:
      self.reliable_distribute(Message('Server', self.identity[client] + ' has connected', 0))

  def update_identity(self, message, client):
    print 'we know that ' + str(client) + ' is ' + message.sender
    self.identity[client] = message.sender

#  @retry_with_backoff("msg_acked")
  def send_to_client(self, client_ptr, message):
    self.send_msg(client_ptr, message)
  
  def ack_received(self, message, client):
    print 'got an ack!', message.content
    print 'num threads: ', threading.active_count()
    if not message.content in self.msg_acks: #the content of an ack is the hash
      self.msg_acks[message.content] = []
    self.msg_acks[message.content].append(client)

  def msg_acked(self, client, message):
    print message, message.get_hash()
    if message.get_hash() in self.msg_acks:
      return client in self.msg_acks[message.get_hash()]

class ReliableChatClient(ReliableChatClientSocket):
  
  def __init__(self, user_name, server_loc):
    super(ReliableChatClient, self).__init__(*server_loc)
    self.user_name = user_name
    self.msg_stack = []
    self.live_pile = {}
    self.dead_pile = {}
    self.queue_lock = threading.Lock() 
    self.connected = False
    self.ready_for_messages = False

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
    #we connect, then they send us a message with all old messages as payload
    if message.is_new_connect():
      missed = pickle.loads(message.content)
      for missed_message in missed:
        if not (missed_message.timestamp, missed_message) in self.msg_stack:
          self.msg_stack.append((missed_message.timestamp, missed_message))
          self.dead_pile[missed_message.get_hash()] = message
      self.say(Message.ack_for(message))
      self.data_changed_ptr()

    elif not (message.timestamp, message) in self.msg_stack:
      self.msg_stack.append((message.timestamp, message))
      self.new_content_message(message)
    else:
      pass
      #self.msg_stack.append((message.timestamp, message))

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

    self.say(Message(self.user_name, last_received, 2)) #TODO: use constant
    self.ready_for_messages = True

  def message_acked(self, message):
    return message.get_hash() in self.dead_pile

  def data_changed_ptr(self):
    self.maintain_stack()
    msgs = [m for t,m in self.msg_stack]
    return self.data_changed(msgs, self.dead_pile)

  def new_content_message(self, message):
    print 'override'

  def data_changed(self, messages, acked_dict):
    print 'override!'
  
  @retry_with_backoff("is_connected") #TODO: bug -- we can get in an infinite connect / disconnect loop
  def try_connect(self):
    try:
      self.connect()
      self.send_new_connection_message()
      self.connected = True
      #print 'connect success'
      return
    except Exception as e: 
      self.connected = False
      return


  def is_connected(self):
    #print 'retrying'
    return self.connected

  def disconnected(self):
    self.connected = False
    self.try_connect()

