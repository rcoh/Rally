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
ms = m.serialize()
md = Message.deserialize(ms)
print md
print ms
