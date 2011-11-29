import socket
import SocketServer
import thread
import threading
from util import *
from model import *
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
    #try:
      data = self.sock.recv(1024)
      if not data:
        self.disconnected()
      else:
        self.buffer_new_data(data)
        self.read()
    #except Exception as ex:
    #  print ex
#  @synchronized("b_lock")
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
    print message
    print 'implement me!'

  def send_message(self, message):
    self.sock.send(message.serialize())

  def disconnected(self):
    """Override me!"""
    print 'disconnected'
    
class ReliableChatServerSocket(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
  def __init__(self, port):
    self.allow_reuse_address = True
    SocketServer.TCPServer.__init__(self,
                                    (SERVER_LOC, port),
                                    ReliableChatRequestHandler)
    self.client_ptrs = []
    self.client_lock = threading.Lock()

  @synchronized("client_lock")
  def add_client(self, write_ptr):
    print 'adding client'
    self.client_ptrs.append(write_ptr)

  @synchronized("client_lock")
  def remove_client(self, write_ptr):
    self.client_ptrs.remove(write_ptr)

  @synchronized("client_lock")
  def send_msg(self, client_ptr, message):
    client_ptr.write(message.serialize())

  def incoming_message(self, msg, client_ptr):
    print msg
  

class ReliableChatRequestHandler(SocketServer.StreamRequestHandler):
  def handle(self):
    self.buf = ''
    while 1:
      print 'about to read'
      chunk = self.connection.recv(1024)
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
    print 'trying to setup'
    SocketServer.StreamRequestHandler.setup(self)
    self.server.add_client(self.wfile)

  def finish(self):
    self.server.remove_client(self.wfile)
    SocketServer.StreamRequestHandler.finish(self)

