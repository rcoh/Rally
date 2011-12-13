#test.py
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

from util import retry_with_backoff
from model import Message
class retry_tester(object):
  def __init__(self):
    self.valid = 4
  
  @retry_with_backoff("success", 2, 1, 2)
  def some_method(self, arg1, arg2):
    print arg1, arg2, self.valid

  def success(self, arg1, arg2):
    print 'trying to validate', arg1, arg2
    self.valid -= 1
    return self.valid == 0

m = Message('rcoh', 'hey', 0)
ms = list(m.serialize())
md, leftover = Message.deserialize(ms)
assert m == md

m2 = Message('rcoh', 'hey2', 0)

total = ms + list(m2.serialize())
m1d, left = Message.deserialize(total)
m2d, more = Message.deserialize(left)
assert m == m1d
assert m2d == m2

m = Message('blah', 'blah', 5)
print m.get_hash()
