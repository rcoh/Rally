from rally import *
client = ReliableChatClient('rcoh', ('localhost', 5959))
m = Message('rcoh', 'testcontent', 0)
client.say_require_ack(m)
while 1:
  pass
