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
    port = sys.argv[1]
  start(port)
 
