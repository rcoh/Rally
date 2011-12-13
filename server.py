#server.py
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

from rally import ReliableChatServer 
import sys
def start(port):
  try:
    server = ReliableChatServer(port)
    server.serve_forever()
  except KeyboardInterrupt:
    server.shutdown()

if __name__ == "__main__":
  if len(sys.argv) == 1:
    port = 5959
  else:
    port = int(sys.argv[1])
  start(port)
 
