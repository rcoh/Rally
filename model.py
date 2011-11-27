import pickle
import time
EOM = '\n' + '-EOM-' + '\n'

CONTENT_MESSAGE = 0
ACK_MESSAGE = 1
NEW_CONNECTION = 2
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
    return abs(hash(str(self.sender) + str(self.content) + str(self.timestamp)))
  
  def serialize(self):
    return pickle.dumps(self, 2) + EOM 
  
  def __repr__(self):
    return "Sender: %s Content:%s Timestamp:%s" % (self.sender, 
                                                     self.content, self.timestamp)

  def __eq__(self, other):
    return self.sender == other.sender and self.content == other.content and \
      self.timestamp == other.timestamp
  
  def is_ack(self):
    return self.type == ACK_MESSAGE

  def is_new_connect(self):
    return self.type == NEW_CONNECTION

  @staticmethod
  def is_eom(line):
    return '-EOM-' in line

  @staticmethod
  def ack_for(msg):
    return Message(msg.sender, msg.get_hash(), ACK_MESSAGE)

  @staticmethod
  def deserialize(data):
    return pickle.loads(data[:-len(EOM)]) #strip newline character



