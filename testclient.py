from rally import *
from model import Message

def new_message(message):
  print message.sender + ': ' + message.content

user_name = raw_input('username?')
print 'just type and hit enter to talk'
client = ReliableChatClient(user_name, ('raptor-lights.mit.edu', 5959))
client.got_new_message = new_message
while 1:
  new_message = raw_input('')
  client.say_require_ack(Message(user_name, new_message, 0))

