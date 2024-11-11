import socket, time
import sys

PARAM_DEBUG = False
PARAM_RECEIVE_BUFFER_SIZE = 128

PARAM_IP = "127.0.0.1"
PARAM_PORT = 5001


def parse_arguments():
    global PARAM_IP, PARAM_PORT

    if len(sys.argv) < 1 + 2:
        print("not enough args")
        exit(1)
    elif len(sys.argv) > 1 + 2:
        print("too many args")
        exit(1)
    else:
        for i in range(len(sys.argv)):
            if i == 1:
                PARAM_IP = sys.argv[i]
            if i == 2:
                PARAM_PORT = int(sys.argv[i])


# making this a class so i can launch multiple consumers later for testing
class Consumer:
    # initialize consumer
    def __init__(self, host, port):
        global PARAM_RECEIVE_BUFFER_SIZE

        # alloc reference to socket
        self.sc = None
        try:
            self.sc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sc.connect((host, port))
        except Exception as e:
            print(f"[ ERRO ] socket creation failed: {e}")
            self.cleanup()
            exit(1)

        self.indx = 0
        data = None
        try:
            data = self.sc.recv(PARAM_RECEIVE_BUFFER_SIZE).decode()
            # parse index (indx:***)
            self.indx = int(data.split(":")[1])
        except Exception as e:
            print(f"[ ERRO ] index retreival failed: {e}")
            self.cleanup()
            exit(1)

        print(f"[ INFO ] connected, consumer {self.indx}")

    def cleanup(self):
        if self.sc is not None:
            self.sc.shutdown(socket.SHUT_RDWR)
            if PARAM_DEBUG:
                print(f"[ DEBG ] closing socket")
            self.sc.close()
            self.sc = None

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
                print("[ PULL ] no event in queue")
            else:
                print(f"[ PULL ] event {event} is processed in consumer {self.indx}")
            time.sleep(1)


consumer = None

if __name__ == "__main__":
    # parse arguments
    if not PARAM_DEBUG:
        parse_arguments()

    # initialize consumer
    consumer = Consumer(PARAM_IP, PARAM_PORT)

    try:
        consumer.consumer_loop()

    except KeyboardInterrupt:
        # cleanup consumer
        if consumer is not None:
            consumer.cleanup()

        # exit msg
        print("\nexiting on SIGINT (ctrl+c)")
