import curses
import sys
import math
from curses import wrapper
import util
from rally import *
from model import Message
import threading
chat_height = 3

class RallyClient(object):
  def __init__(self, server, port):
    self.user_name = raw_input('user name?')
    self.client = ReliableChatClient(self.user_name, (server, port))
    self.ui = RallyCursesUI()
    self.ui.user_message = self.user_message #late-binding
    self.client.data_changed = self.ui.render_chats
    try:
      self.ui.start()
    finally:
      curses.endwin()

  def user_message(self, message):
    self.client.say_require_ack(Message(self.user_name, message, 0))
  

class RallyCursesUI(object):

  def __init__(self):

    self.ui_lock = threading.RLock()

  def start(self):
    self.stdscr = curses.initscr()
    curses.start_color()
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

  def total_lines_required(self, messages, width):
    return sum([self.lines_required(m, width) for m in messages])

  def lines_required(self, message, width):
    return int(math.ceil((len(self.get_message_text(message)) +
                          message.content.count('\n'))/float(width)))

  def get_message_text(self, message):
    return message.sender + ': ' + message.content

  @synchronized("ui_lock")
  def render_chats(self, message_pile, acked_dict):
    height,width = self.old_chats.getmaxyx()
    self.old_chats.erase()
    if self.total_lines_required(message_pile, width) < height: 
      #we can render top down
      for message in message_pile:
        color = curses.COLOR_BLACK if message.get_hash() in acked_dict else curses.COLOR_RED
        #TODO: this could lead to overflow
        extra = '' if message.get_hash() in acked_dict else ' *unreceived*'
        
        self.old_chats.addstr(self.get_message_text(message) + extra + '\n', color)
    else:
      #we have to render bottom up
      cur_y = height
      message_index = -1
      while cur_y > 0 and message_index * -1 < len(message_pile):
        lines_required = self.lines_required(message_pile[message_index], width)
        cur_y -= lines_required
        if cur_y >= 0:
          color = curses.COLOR_BLACK if message_pile[message_index].get_hash() in acked_dict else curses.COLOR_RED
          extra = '' if message_pile[message_index].get_hash() in acked_dict else ' *unreceived*'
          self.old_chats.addstr(cur_y, 0, self.get_message_text(message_pile[message_index]) + extra, color)
          cur_y -= (lines_required-1)
        message_index -= 1

#    self.new_msg_panel.addstr(1,1,'')
    self.old_chats.refresh()
    self.new_msg_panel.refresh()

  def user_message(self, message):
    """To be overriden"""
    raise NotImplementedError

  def read_next_message(self):
    msg = self.new_msg_panel.getstr(1,1)
    self.ui_lock.acquire()
    self.user_message(msg)
    self.new_msg_panel.addstr(1,1, '')
    self.new_msg_panel.clrtoeol()
    self.new_msg_panel.refresh()
    self.ui_lock.release()

if __name__ == "__main__":
  server = 'raptor-lights.mit.edu'
  port = 5959
  if len(sys.argv) >= 2:
    server = sys.argv[1]
  if len(sys.argv) == 3:
    port = int(sys.argv[2])

  u = RallyClient(server, port)
