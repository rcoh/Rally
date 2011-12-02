import socket
import SocketServer
import threading
from util import async, synchronized, log
from model import Message 
SERVER_PORT = 5959
SERVER_LOC = '' 
class ReliableChatClientSocket(object):
  """
  Fairly standard client socket class.  Offers abstract methods
  to be overriden by inheriting class.  Handles parsing of message objects.
  """
  def __init__(self, target_address, target_port):
    self.target_address = target_address
    self.target_port = target_port
    self.sock = None
    self.buffer = []
    self.b_lock = threading.Lock()

  def connect(self):
    self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    self.sock.connect((self.target_address, self.target_port))
    self.read()
  
  @async 
  def read(self):
    data = self.sock.recv(1024)
    if not data:
      self.disconnected()
    else:
      self.buffer_new_data(data)
      self.read()

  def buffer_new_data(self, data):
    self.buffer += data
    while self.buffer:
      new_msg, leftover = Message.deserialize(self.buffer)
      if new_msg:
        self.rcv_message(new_msg)
        self.buffer = leftover
      else:
        #we have part of a message
        break

  def shutdown(self):
    self.sock.close()
    
  def rcv_message(self, message):
    """To be overriden.  Called by parent when a new message is recieved"""
    pass

  def send_message(self, message):
    try:
      self.sock.send(message.serialize())
    except Exception:
      #we got disconnected or message serialization failed
      self.disconnected()

  def disconnected(self):
    """Called when the client is disconnected from the server"""
    
class ReliableChatServerSocket(SocketServer.ThreadingMixIn, 
                               SocketServer.TCPServer):
  def __init__(self, port):
    self.allow_reuse_address = True
    self.daemon_threads = True
    SocketServer.TCPServer.__init__(self,
                                    (SERVER_LOC, port),
                                    ReliableChatRequestHandler)
    self.client_ptrs = []
    self.client_lock = threading.RLock()

  @synchronized("client_lock")
  def add_client(self, write_ptr):
    self.client_ptrs.append(write_ptr)

  @synchronized("client_lock")
  def remove_client(self, write_ptr):
    self.client_ptrs.remove(write_ptr)
    self.client_disconnected(write_ptr)

  @synchronized("client_lock")
  def send_msg(self, client_ptr, message):
    try:
      client_ptr.write(message.serialize())
    except Exception as ex:
      #this client died
      self.client_ptrs.remove(client_ptr)
      log('client died')
      log(ex)

  def incoming_message(self, msg, client_ptr):
    """To be overriden."""
    pass

  def client_disconnected(self, client_ptr):
    """To be overriden."""
    pass
  
class ReliableChatRequestHandler(SocketServer.StreamRequestHandler):
  def handle(self):
    self.buf = ''
    while 1:
      try:
        chunk = self.connection.recv(1024)
      except Exception as ex:
        log(ex)
        break
      if not chunk:
        break
      else:
        self.buf += chunk 
        self.buffer_new_data()
  
  def buffer_new_data(self):
    while self.buf:
      new_msg, leftover = Message.deserialize(self.buf)
      if new_msg:
        self.server.incoming_message(new_msg, self.wfile)
        self.buf = leftover

  def setup(self):
    SocketServer.StreamRequestHandler.setup(self)
    self.server.add_client(self.wfile)

  def finish(self):
    self.server.remove_client(self.wfile)
    SocketServer.StreamRequestHandler.finish(self)

