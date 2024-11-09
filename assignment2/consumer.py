import socket, time
import sys

PARAM_DEBUG = True
PARAM_RECEIVE_BUFFER_SIZE = 128

PARAM_IP = "127.0.0.1"
PARAM_PORT = 5001


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


# making this a class so i can launch multiple consumers later for testing
class Consumer:

    # initialize consumer
    def __init__(self, host, port):
        global PARAM_RECEIVE_BUFFER_SIZE

        # alloc reference to socket
        self.sc = None
        try:
            self.sc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sc.settimeout(10)
            self.sc.connect((host, port))
        except Exception as e:
            print(f"socket creation failed: {e}")
            exit(1)

        self.indx = 0
        data = None
        try:
            data = self.recv(PARAM_RECEIVE_BUFFER_SIZE).decode()
            # parse index (indx:***)
            self.indx = int(data.split(":")[1])
        except Exception as e:
            print(f"index retreival failed: {e}")
            self.sc.close()
            exit(1)

        print(f"connected, consumer {self.indx}")

    # cleanup resources
    def __del__(self):
        if self.sc is not None:
            self.sc.close()

    # return pulled event
    def pull_event(self):
        global PARAM_RECEIVE_BUFFER_SIZE

        self.sc.send("PULL EVENT".encode())
        msg = self.sc.recv(PARAM_RECEIVE_BUFFER_SIZE).decode()

        return msg

    # retrieve data from server, print it
    def consumer_loop(self):
        while True:
            event = self.pull_event()
            if event == "\nempty":
                print("no event in Queue")
            else:
                print(f"event {event} is processed in consumer {self.indx}")
            time.sleep(1)


if __name__ == "__main__":
    consumer = Consumer(PARAM_IP, PARAM_PORT)

    try:
        consumer.consumer_loop()
    except KeyboardInterrupt:
        # cleanup consumer
        if consumer is not None:
            del consumer

        # exit msg
        print("\nexiting on SIGINT (ctrl+c)")
