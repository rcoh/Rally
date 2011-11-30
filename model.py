import pickle
import time
import curses
from util import *

CONTENT_MESSAGE = 0
ACK_MESSAGE = 1
NEW_CONNECTION = 2

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
    return str(abs(hash(str(self.sender) + str(self.content) + str(self.timestamp))))
  
  def serialize(self):
    msg = pickle.dumps(self, PICKLE_TYPE)
    total_len = len(msg)
    return str(total_len) + '!' + msg
  
  def __repr__(self):
    return "Sender: %s Content:%s Timestamp:%s" % (self.sender, 
                                                     self.content, self.timestamp)

  def __eq__(self, other):
    return self.sender == other.sender and self.content == other.content and \
      self.timestamp == other.timestamp

  def __ne__(self, other):
    return not self.__eq__(other)
  
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
    deserialize takes a list containing binary data.  If it finds a message, it will return it, along with 
    any leftovers in the data stream.  If it doesn't find a message, it will return None, along with leftovers in the
    data stream.
    """
    #TODO: for efficiency, we should use an index based system for
    #handling left over data to avoid copying messages when we don't have to.
    data = ''.join(data) #strify for convienience
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

