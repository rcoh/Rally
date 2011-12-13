#debug_ui.py
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

import sys
from rally import ReliableChatClient 
from model import Message

class DebugRallyClient(object):
  def __init__(self, server, port):
    self.user_name = raw_input('user name?')
    self.client = ReliableChatClient(self.user_name, (server, port))
    self.client.data_changed = self.new_data
    self.client.try_connect()
    print 'connected'
    while 1:
      self.user_message(raw_input('what?'))

  def new_data(self, msgs, acks):
    pass
    #print 'we got some new data'

  def user_message(self, message):
    self.client.say_require_ack(Message(self.user_name, message, 0))

if __name__ == "__main__":
  server = 'raptor-lights.mit.edu'
  port = 5959
  if len(sys.argv) >= 2:
    server = sys.argv[1]
  if len(sys.argv) == 3:
    port = int(sys.argv[2])

  u = DebugRallyClient(server, port)
