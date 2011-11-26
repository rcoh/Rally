from threading import Timer
import thread

class synchronized:
  def __init__(self, lockname):
    self.lockname = lockname

  def __call__(self, f):
    lockname = self.lockname
    def wrap(self, *args, **kw):
      lock = getattr(self, lockname)
      lock.acquire()
      try:
        return f(self, *args, **kw)
      finally:
        lock.release()
    return wrap

  def __get__(self, instance, owner):
    self.cls = owner
    self.obj = instance
    return self.__call__

class retry_with_backoff:
  """
  Function decorator that will retry the decorated function with exponential backoff
  until success_func_name returns true.
  """
  def __init__(self, success_func_name, backoff_rate=2, checkback_time=1, max_retries=5):
    self.success_func_name = success_func_name
    self.backoff_rate = backoff_rate
    self.checkback_time = checkback_time
    self.max_retries = max_retries
  
  def __get__(self, instance, owner):
    self.cls = owner
    self.obj = instance
    return self.__call__

  def __call__(self, f):
    backoff_rate = self.backoff_rate
    checkback_time = self.checkback_time
    success_func_name = self.success_func_name
    max_retries = self.max_retries
    def wrap(self, *args, **kw):
      def retry(delay, max_retries, args, kw): #retry callback func
        if max_retries == 0:
          return
        success_func = getattr(self, success_func_name)
        if not success_func(*args, **kw):
          f(self, *args, **kw)
          try_in(delay, retry, [delay*backoff_rate, max_retries - 1, args, kw])
      
      try:
        f(self, *args, **kw)
        try_in(checkback_time, retry, [checkback_time, max_retries-1, args, kw])
      finally:
        pass 
    return wrap

def try_in(t, f, args=[], kw={}):
  Timer(t, f, args, kw).start()

def async(f):
  def wrap(self, *args, **kw):
    if args:
      argtup = (self, args)
    else:
      argtup = (self,)
    thread.start_new_thread(f, argtup, kw)
  return wrap
