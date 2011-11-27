import curses
from curses import wrapper
import util
from rally import *
from model import Message
chat_height = 5

class RallyClient(object):
  user_name = 'rcoh' 
  def __init__(self):
    self.client = ReliableChatClient(self.user_name, ('raptor-lights.mit.edu', 5959))
    self.ui = RallyCursesUI()
    self.ui.user_message = self.user_message #late-binding
    self.client.got_new_message = self.ui.incoming_message
    try:
      self.ui.start()
    finally:
      curses.endwin()

  def user_message(self, message):
    self.client.say_require_ack(Message(self.user_name, message, 0))
  

class RallyCursesUI(object):

  def __init__(self):
    pass

#  @async
  def start(self):
    self.stdscr = curses.initscr()
    curses.cbreak()
    curses.echo()
    self.maxyx = self.stdscr.getmaxyx()
    my, mx = self.maxyx
    self.new_msg_panel = curses.newwin(chat_height, mx, my-chat_height, 0)
    self.old_chats = curses.newwin(my-chat_height, mx, 0, 0)
    self.add_context_str()
    self.old_chats.refresh()
    while 1:
      self.read_next_message()

  def add_context_str(self):
    self.new_msg_panel.box()

  def incoming_message(self, message):
    self.old_chats.addstr(message.sender + ': ' + message.content + '\n')
    self.old_chats.refresh()

  def user_message(self, message):
    """To be overriden"""
    self.old_chats.addstr(message)
    cy, cx = self.old_chats.getyx()
    self.old_chats.addstr(cy+1, 0, '')
    self.old_chats.refresh()

  def read_next_message(self):
    msg = self.new_msg_panel.getstr(1,1)
    self.user_message(msg)
    self.new_msg_panel.addstr(1,1, '')
    self.new_msg_panel.clrtoeol()
    self.new_msg_panel.refresh()

if __name__ == "__main__":
  u = RallyClient()
