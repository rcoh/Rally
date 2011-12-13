#model.py
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

import pickle
import time
import hashlib
from util import log 

CONTENT_MESSAGE = 0
ACK_MESSAGE = 1
NEW_CONNECTION = 2
VERIFY_STATE = 3

PICKLE_TYPE = 2
class Message(object):
  
  def __init__(self, sender, content, msg_type):
    """
    Creates a new Message.  sender and content are recast as strings.
    """
    self.sender = str(sender)
    self.content = str(content)
    self.timestamp = time.time()
    self.type = msg_type

  def get_hash(self):
    return hashlib.md5(str(self.sender) + str(self.content) + 
                       str(self.timestamp)).hexdigest()
  
  def serialize(self):
    msg = pickle.dumps(self, PICKLE_TYPE)
    total_len = len(msg)
    return str(total_len) + '!' + msg
  
  def is_ack(self):
    return self.type == ACK_MESSAGE

  def is_new_connect(self):
    return self.type == NEW_CONNECTION

  @staticmethod
  def ack_for(msg):
    return Message(msg.sender, msg.get_hash(), ACK_MESSAGE)

  @staticmethod
  def deserialize(data):
    """
    deserialize takes a list containing binary data.  If it finds a message, 
    it will return it, along with any leftovers in the data stream.  
    If it doesn't find a message, it will return None, along with leftovers in the
    data stream.
    """
    #TODO: for efficiency, we should use an index based system for
    #handling left over data to avoid copying messages when we don't have to.
    data = ''.join(data) #string for convenience
    delim = data.index('!')
    expected_len = int(data[0:delim])
    msg = data[delim+1:delim+1+expected_len]
    leftovers = data[delim+1+expected_len:]
    if expected_len != len(msg):
      leftovers = data
      return None, leftovers
    try:
      message = pickle.loads(msg) #strip newline character
      log('good message' + data) 
      return message, leftovers
   
    except Exception as ex:
      log('bad' + data)
      return Message('message parsing failed', 'failure', 0)

  def message_set_hash(message_set):
    """
    message_set is a list of messages.  The hash value is composed by sorting all the hashcodes
    of the underlying messages and hashing them
    """
    hashes = [m.get_hash() for m in message_set]
    hashes.sort()
    return hashlib.md5(''.join(hashes))

  def __hash__(self):
    return self.get_hash()

  def __repr__(self):
    return "Sender: %s Content:%s Timestamp:%s" % (self.sender, 
                                                   self.content, self.timestamp)
  def __eq__(self, other):
    return self.sender == other.sender and self.content == other.content and \
      self.timestamp == other.timestamp

  def __ne__(self, other):
    return not self.__eq__(other)
