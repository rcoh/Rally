from rally import *
try:
  server = ReliableChatServer(1235)
  server.serve_forever()
except KeyboardInterrupt:
  server.shutdown()
