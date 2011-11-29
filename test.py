from util import *
from rally import *
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
