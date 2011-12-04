import curses
import curses.ascii
import sys
import math
from curses import wrapper
from util import synchronized, async
from rally import ReliableChatClient 
from model import Message
import threading
import notify
chat_height = 3

class RallyClient(object):
  def __init__(self, server, port):
    self.user_name = raw_input('user name?')
    self.client = ReliableChatClient(self.user_name, (server, port))
    self.ui = RallyCursesUI()
    #bind methods:
    self.ui.user_message = self.user_message 
    self.client.data_changed = self.ui.render_chats
    self.client.new_content_message = self.ui.new_content_message
    #start-er-up:
    try:
      self.client.try_connect()
      notify.init('Rally')
      self.ui.start()
      self.ui.read_msgs()
    except KeyboardInterrupt:
      pass
    finally:
      self.ui.close()

  def user_message(self, message):
    self.client.say_require_ack(Message(self.user_name, message, 0))

class RallyCursesUI(object):

  def __init__(self):
    self.ui_lock = threading.RLock()
    self.ui_lock.acquire()
    self.last_state = ([], {})

  def notify(self, title, msg):
    notify.send(title, msg)

  def start(self):
    self.stdscr = curses.initscr()
    curses.start_color()
    curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_RED)
    curses.cbreak()
    curses.echo()
    self.maxyx = self.stdscr.getmaxyx()
    my, mx = self.maxyx
    self.new_msg_panel = curses.newwin(chat_height, mx, my-chat_height, 0)
    self.old_chats = curses.newwin(my-chat_height, mx, 0, 0)
    self.draw_input_box()
    self.old_chats.refresh()
    self.ui_lock.release()
    self.die = False

  def read_msgs(self):
    while not self.die:
      self.read_next_message()

  def close(self):
    curses.endwin()

  def draw_input_box(self):
    self.new_msg_panel.box()

  def total_lines_required(self, messages, acked_dict, width):
    return sum([self.lines_required(m, m.get_hash() in acked_dict, width) for m in messages])

  def lines_required(self, message, acked, width):
    return int(math.ceil((len(self.get_message_text(message, acked)) +
                          message.content.count('\n'))/float(width)))

  def get_message_text(self, message, acked):
    base = message.sender + ': ' + message.content
    if acked: 
      return base
    else:
      return base + ' *unreceived'

  @synchronized("ui_lock")
  def render_chats(self, message_pile, acked_dict):
    self.last_state = (message_pile, acked_dict)
    height, width = self.old_chats.getmaxyx()
    self.old_chats.erase()
    if self.total_lines_required(message_pile, acked_dict, width) < height: 
      #we can render top down
      for message in message_pile:
        acked = message.get_hash() in acked_dict
        color = curses.COLOR_BLACK if acked else curses.color_pair(1) 
        self.old_chats.addstr(self.get_message_text(message, acked) + '\n', color)
    else:
      #we have to render bottom up
      cur_y = height
      message_index = -1
      while cur_y > 0 and message_index * -1 < len(message_pile):
        msg = message_pile[message_index]
        lines_required = self.lines_required(msg, msg.get_hash() in acked_dict,  width)
        cur_y -= lines_required
        if cur_y >= 0:
          color = curses.COLOR_BLACK if msg.get_hash() in acked_dict else curses.color_pair(1) 
          self.old_chats.addstr(cur_y, 0, self.get_message_text(msg, msg.get_hash() in acked_dict), color)
        message_index -= 1

    self.old_chats.refresh()
    self.new_msg_panel.refresh()

  def user_message(self, message):
    """To be overriden"""
    raise NotImplementedError

  def new_content_message(self, message):
    self.notify(message.sender + ' says:', message.content)

  def handle_resize(self):
    self.close()
    self.ui_lock.acquire()
    self.start()
    self.render_chats(*self.last_state)
    self.read_msgs()

  def get_str_scrolling(self, window, start):
    """
    reads a str.  it will call instance functions on scrolling etc.
    """
    chars = ''
    xpos, ypos = start
    window.keypad(1)
    while 1:
      curses.noecho()
      new_chr = window.getch(ypos, xpos)
      if new_chr == curses.KEY_DOWN:
        pass
      elif new_chr == curses.KEY_UP:
        pass
      elif new_chr == curses.KEY_LEFT:
        if xpos > 1:
          xpos -= 1 
      elif new_chr == curses.KEY_RIGHT:
        if xpos <= len(chars):
          xpos += 1
      elif new_chr == curses.KEY_BACKSPACE:
        if xpos > 1:
          xpos -= 1 
        if xpos == len(chars): #deleting from end
          chars = chars[:-1]
        else:
          chars = chars[:xpos] + chars[xpos+1:]
      elif curses.ascii.isalnum(new_chr):
        chars = chars[:xpos-1] + chr(new_chr) + chars[xpos-1:]
        xpos += 1
      elif new_chr == curses.ascii.LF:
        break
      elif new_chr == curses.KEY_RESIZE:
        self.handle_resize()  
      else:
        chr_str = ''
        if new_chr < 255 and new_chr > 0:
          chr_str = chr(new_chr)
        else:
          chr_str = str(new_chr) 
        chars = chars[:xpos-1] + chr_str + chars[xpos-1:]
        xpos += 1
      window.addstr(1, 1, '')
      window.addstr(start[0], start[1], chars + ' ')
      window.refresh()
    window.keypad(0)
    return chars

  def read_next_message(self):
    msg = self.get_str_scrolling(self.new_msg_panel, (1,1))
    with self.ui_lock:
      self.user_message(msg)
      self.new_msg_panel.addstr(1, 1, '')
      self.new_msg_panel.clrtoeol()
      self.draw_input_box()
      self.new_msg_panel.refresh()

if __name__ == "__main__":
  server = 'raptor-lights.mit.edu'
  port = 5959
  if len(sys.argv) >= 2:
    server = sys.argv[1]
  if len(sys.argv) == 3:
    port = int(sys.argv[2])

  u = RallyClient(server, port)
