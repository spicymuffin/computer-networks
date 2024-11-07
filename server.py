import socket, sys
from threading import Thread
from queue import Queue


def producer_worker():
    # …
    pass


def consumer_worker(args):
    # …
    pass


if __name__ == "__main__":
    producer_thread = Thread(target=producer_worker)
    producer_thread.start()
    while True:
        # …
        worker_thread = Thread(target=consumer_worker, args=(1,))
        worker_thread.start()
        # …