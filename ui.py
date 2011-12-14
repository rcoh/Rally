#ui.py
#Copyright (C) 2011  Russell Cohen <rcoh@mit.edu>
#                    Ally Gale <allygale@gmail.com>
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

import curses
import curses.ascii
import sys
import time
import math
from curses import wrapper
from util import synchronized, async
from rally import ReliableChatClient 
from model import Message
import threading
import thread
import notify
from Queue import Queue
chat_height = 3

class RallyCursesUI(object):

  def __init__(self):
    self.ready = threading.Semaphore(0)
    self.ui_lock = threading.RLock()
    self.last_state = ([], {})
    notify.init('Rally')

  def notify(self, title, msg):
    """Desktop notifications"""
    notify.send(title, msg)
  
  def start(self):
    self.init_curses()
    self.ready.release()
    self.die = False
    self.main_loop()

  def init_curses(self):
    self.stdscr = curses.initscr()
    curses.start_color()
    curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_RED)
    curses.cbreak()
    self.maxyx = self.stdscr.getmaxyx()
    self.create_panels()

  def create_panels(self):
    my, mx = self.maxyx
    self.new_msg_panel = curses.newwin(chat_height, mx, my-chat_height, 0)
    self.new_msg_panel.keypad(1)
    self.old_chats = curses.newwin(my-chat_height, mx, 0, 0)
    self.draw_input_box()
    self.old_chats.refresh()


  def main_loop(self):
    while 1:
      self.read_next_message()

  def close(self):
    curses.nocbreak()
    self.stdscr.keypad(0)
    curses.echo()
    curses.endwin()

  def draw_input_box(self):
    self.new_msg_panel.box()

  def total_lines_required(self, messages, acked_dict, width):
    return sum([self.lines_required(m, m.get_hash() in acked_dict, width) for m in messages])

  def lines_required(self, message, acked, width):
    return int(math.ceil((len(self.get_message_text(message, acked)) +
                          message.content.count('\n'))/float(width)))

  def get_message_text(self, message, acked):
    localtime = time.localtime(message.timestamp)
    base = message.sender + '(' + time.strftime("%H:%M", localtime) + '): ' + message.content
    if acked: 
      return base
    else:
      return base + ' *unreceived'

  def render_chats(self, message_pile, acked_dict):
    self.block_until_ready()
    with self.ui_lock:
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

  def block_until_ready(self):
    self.ready.acquire()
    self.ready.release()

  def new_outgoing_message(self, message):
    """To be overriden"""
    raise NotImplementedError

  def new_content_message(self, message):
    self.notify(message.sender + ' says:', message.content)


  def handle_resize(self):
    self.ready.acquire() #we aren't ready
    curses.endwin()
    self.init_curses() 
    self.ready.release()
    self.render_chats(*self.last_state)

  def get_str_scrolling(self, window, start):
    """
    reads a str.  it will call instance functions on scrolling etc.
    """
    chars = ''
    xpos, ypos = start
    while 1:
      curses.noecho()
      new_chr = self.new_msg_panel.getch(ypos, xpos)
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
      elif new_chr == curses.KEY_BACKSPACE or new_chr == curses.ascii.DEL: #checking ascii.DEL for mac compatibility 
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
        continue
      else:
        chr_str = ''
        if new_chr < 255 and new_chr > 0:
          chr_str = chr(new_chr)
          chars = chars[:xpos-1] + chr_str + chars[xpos-1:]
          xpos += 1
      self.new_msg_panel.addstr(1, 1, '')
      self.new_msg_panel.addstr(start[0], start[1], chars + ' ')
      self.new_msg_panel.refresh()
    return chars

  def read_next_message(self):
    msg = self.get_str_scrolling(self.new_msg_panel, (1,1))
    if msg == None:
      return True 
    with self.ui_lock:
      self.new_outgoing_message(msg)
      self.new_msg_panel.addstr(1, 1, '')
      self.new_msg_panel.clrtoeol()
      self.draw_input_box()
      self.new_msg_panel.refresh()
    return True

