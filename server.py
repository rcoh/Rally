from rally import ReliableChatServer 
try:
  server = ReliableChatServer(5959)
  server.serve_forever()
except KeyboardInterrupt:
  server.shutdown()
