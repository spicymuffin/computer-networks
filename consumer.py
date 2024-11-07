import socket, time

DEBUG = True


class Consumer:
    def __init__(self, host, port):
        self.sc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sc.connect((host, port))

    def pull_event(self):
        self.sc.send("PULL EVENT".encode())
        msg = self.sc.recv(100).decode()
        return msg

    def consumer_loop():
        while True:
            event = self.pull_event()
            if DEBUG:
                print(f"Event received: {event}")
            time.sleep(1)


if __name__ == "__main__":
    if DEBUG:
        print("Consumer started")
