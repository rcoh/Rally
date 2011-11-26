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

  def connect(self):
    self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    self.sock.connect((self.target_address, self.target_port))
    self.read()
  
  @async 
  def read(self):
    try:
      data = self.sock.recv(1024)
      if not data:
        print "i'm disconnected!"
        self.disconnected()
      else:
        self.read()
        self.rcv_message(Message.deserialize(data))
    except Exception as ex:
      print ex
    
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
  def __init__(self):
    SocketServer.TCPServer.__init__(self,
                                    (SERVER_LOC, SERVER_PORT),
                                    ReliableChatRequestHandler)
    self.client_ptrs = []
    self.client_lock = threading.RLock()

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
    buf = ''
    while 1:
      line = self.rfile.readline()
      if not line:
        break
      elif Message.is_eom(line):
        buf += line
        self.server.incoming_message(Message.deserialize(buf), self.wfile) 
        buf = ''
      else:
        buf += line

  def setup(self):
    print 'trying to setup'
    SocketServer.StreamRequestHandler.setup(self)
    self.server.add_client(self.wfile)

  def finish(self):
    self.server.remove_client(self.wfile)
    SocketServer.StreamRequestHandler.finish(self)

