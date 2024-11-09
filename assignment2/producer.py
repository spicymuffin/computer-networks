import socket, time
import sys

PARAM_DEBUG = True

PARAM_IP = "127.0.0.1"
PARAM_PORT = 5000


def parse_arguments():
    global PARAM_IP, PARAM_PORT

    if len(sys.argv) <= 1 + 0:
        print("no args")
    elif len(sys.argv) > 1 + 2:
        print("too many args")
    else:
        for i in range(len(sys.argv)):
            if i == 1:
                PARAM_IP = sys.argv[i]
            if i == 2:
                PARAM_PORT = sys.argv[i]


class Producer:
    # initialize producer
    def __init__(self, host, port):
        # alloc reference to socket
        self.sc = None
        try:
            self.sc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sc.settimeout(10)
            self.sc.connect((host, port))
        except Exception as e:
            print(f"socket creation failed: {e}")
            exit(1)

    # send string to server
    def send(self, payload):
        self.sc.send(payload.encode())

    def producer_loop(self):
        while True:
            inp = input()
            self.send(inp)
            print(f"{len(inp)} events were created")

    # deallocate resources (close socket)
    def __del__(self):
        if self.sc is not None:
            self.sc.close()


producer = None

if __name__ == "__main__":
    if not PARAM_DEBUG:
        parse_arguments()

    # initialize producer
    producer = Producer(PARAM_IP, PARAM_PORT)

    try:
        producer.producer_loop()

    except KeyboardInterrupt:
        # cleanup producer
        if producer is not None:
            del producer

        # exit msg
        print("\nexiting on SIGINT (ctrl+c)")
