import socket, time

class Producer:
    def __init__(self, host, port):
        self.sc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sc.connect((host, port))

    def send(self, event):
        self.sc.send(event.encode())
while True:
    events = input()
    sc.send(events.encode())
