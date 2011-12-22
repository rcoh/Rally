#rally.py
#Copyright (C) 2011  Russell Cohen <rcoh@mit.edu>
#
# This file is part of Rally.
#
# Rally is free software: you can redistribute it
# and/or modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# Rally is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Rally.  If not, see
# <http://www.gnu.org/licenses/>.

import threading
import pickle
from threading import Thread
from network import ReliableChatServerSocket, ReliableChatClientSocket 
from model import Message
from util import synchronized, retry_with_backoff, log, get_logger
import logging
"""General principle: 
  Client sends message -> Server replies message to all clients
  Client sends message hash back as ack to server.

  Server will attempt to reliably distribute messages to clients, with 
  exponential backoff retries.

  Server will send clients a compound message containing messages they 
  missed when they rejoin the server.
  
  Clients will also use exponential backoff when sending messages to the 
  server.  Clients will continue attempting to send until they recieve an ack.
"""

class ReliableChatServer(ReliableChatServerSocket):
  
  def __init__(self, port):
    ReliableChatServerSocket.__init__(self, port)
    self.msg_acks = {} #hashcode -> [clients]
    self.sent_msgs = {} #who has been sent what?
    self.all_msgs = {} #hashcode -> msg
    self.identity = {} #socket_ptr -> name
    self.logger = get_logger(self)

  def incoming_message(self, message, client):
    self.logger.info(message)
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
      self.reliable_distribute(
        Message('Server', self.identity[client] + ' has disconnected', 0))

  def client_connected(self, client):
    if client in self.identity:
      self.reliable_distribute(
        Message('Server', self.identity[client] + ' has connected', 0))

  def update_identity(self, message, client):
    self.logger.info('we know that ' + str(client) + ' is ' + message.sender)
    self.identity[client] = message.sender

#  @retry_with_backoff("msg_acked")
  def send_to_client(self, client_ptr, message):
    self.send_msg(client_ptr, message)
  
  def ack_received(self, message, client):
    self.logger.info('got an ack!' +  message.content)
    self.logger.info('num threads: ' + threading.active_count())
    if not message.content in self.msg_acks: #the content of an ack is the hash
      self.msg_acks[message.content] = []
    self.msg_acks[message.content].append(client)

  def msg_acked(self, client, message):
    if message.get_hash() in self.msg_acks:
      return client in self.msg_acks[message.get_hash()]

class ReliableChatClient(ReliableChatClientSocket):
  
  def __init__(self, user_name, server_loc):
    self.logger = get_logger(self)
    super(ReliableChatClient, self).__init__(*server_loc)
    self.user_name = user_name
    self.msg_stack = [] #(timestmap, msg), kept sorted
    self.acked_messages = {}
    self.queue_lock = threading.Lock() 
    self.connected = False
  
  def start(self):
    self.try_connect()

  @retry_with_backoff("message_acked")
  def say_require_ack(self, message):
    if not (message.timestamp, message) in self.msg_stack:
      self.msg_stack.append((message.timestamp, message))

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
          self.acked_messages[missed_message.get_hash()] = message
      self.say(Message.ack_for(message))
      self.data_changed_ptr()
  
    elif not (message.timestamp, message) in self.msg_stack:
      self.msg_stack.append((message.timestamp, message))
      self.new_content_message(message)

    self.acked_messages[message.get_hash()] = message
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

  def message_acked(self, message):
    return message.get_hash() in self.acked_messages

  def data_changed_ptr(self):
    self.maintain_stack()
    messages = [message for timestamp, message in self.msg_stack]
    return self.data_changed(messages, self.acked_messages)

  def new_content_message(self, message):
    """To be overriden"""
    pass

  def data_changed(self, messages, acked_dict):
    """To be overriden"""
    pass

  #TODO: bug -- we can get in an infinite connect / disconnect loop
  @retry_with_backoff("is_connected") 
  def try_connect(self):
    try:
      self.connect()
      self.send_new_connection_message()
      self.connected = True
    except Exception as e: 
      self.connected = False

  def is_connected(self):
    return self.connected

  def disconnected(self):
    self.connected = False
    self.try_connect()

