import socket
import sys
import time
from threading import Thread
from threading import Lock
from queue import Queue

PARAM_DEBUG = True

PARAM_MAX_QUEUED_CONNECTIONS = 5
PARAM_RECV_BUFFER_SIZE = 1024

PARAM_SERVER_IP = "127.0.0.1"
PARAM_PORT_PRODUCER = 5000
PARAM_PORT_CONSUMER = 5001


def parse_arguments():
    global PARAM_SERVER_IP, PARAM_PORT_PRODUCER, PARAM_PORT_CONSUMER

    if len(sys.argv) <= 1 + 0:
        print("no args")
    elif len(sys.argv) > 1 + 3:
        print("too many args")
    else:
        for i in range(len(sys.argv)):
            if i == 1:
                PARAM_SERVER_IP = sys.argv[i]
            if i == 2:
                PARAM_PORT_PRODUCER = sys.argv[i]
            if i == 3:
                PARAM_PORT_CONSUMER = sys.argv[i]


producer_connection_socket = None
consumer_connection_socket = None

producer_list = []
producer_threads = []
producer_list_lock = Lock()
nproducer = 0
consumer_list = []
consumer_threads = []
consumer_list_lock = Lock()
nconsumer = 0

event_queue = Queue()
event_queue_lock = Lock()

print_lock = Lock()  # for print synchronization


def server_init():
    global producer_connection_socket, consumer_connection_socket

    producer_connection_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    producer_connection_socket.bind((PARAM_SERVER_IP, PARAM_PORT_PRODUCER))
    producer_connection_socket.listen(PARAM_MAX_QUEUED_CONNECTIONS)
    consumer_connection_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    consumer_connection_socket.bind((PARAM_SERVER_IP, PARAM_PORT_CONSUMER))
    consumer_connection_socket.listen(PARAM_MAX_QUEUED_CONNECTIONS)


def sercver_cleanup():
    global producer_connection_socket, consumer_connection_socket

    producer_connection_socket.close()
    consumer_connection_socket.close()


def producer_worker(client_socket, client_addr, producer_indx):
    global event_queue, event_queue_lock, producer_list, producer_list_lock, nproducer

    while True:
        data = client_socket.recv(PARAM_RECV_BUFFER_SIZE).decode()

        # no data = client disconnected
        if not data:
            producer_list_lock.acquire()

            try:
                producer_list[producer_indx] = None
                nproducer -= 1
            finally:
                producer_list_lock.release()

            client_socket.close()

            print_lock.acquire()
            print(f"[ DCNT ] producer disconnected: {client_addr}")
            print_lock.release()

            break

        # data = event(s)
        else:
            # acquire lock bc we are modifying shared resources
            event_queue_lock.acquire()
            size = -1

            # put events into queue
            try:
                for ch in data:
                    event_queue.put(ch)
                # cache size for print (we do it outside of the critical section to save time)
                size = event_queue.qsize()
            finally:
                event_queue_lock.release()

            # print stuff (critical section because we cant have multiple prints at the same time)
            print_lock.acquire()
            print(f"[ EVNT ] events created: {len(data)} event(s)")
            print(f"[ INFO ] remaining events in queue: {size}")
            print_lock.release()


def consumer_worker(client_socket, client_addr, consumer_indx):
    global event_queue, event_queue_lock, consumer_list, consumer_list_lock, nconsumer

    while True:
        data = client_socket.recv(PARAM_RECV_BUFFER_SIZE).decode()

        # pull event
        if data == "PULL EVENT":
            event_queue_lock.acquire()
            try:
                if not event_queue.empty():
                    event = event_queue.get()
                    client_socket.send(event.encode())
                else:
                    client_socket.send("\nempty".encode())
            finally:
                event_queue_lock.release()

        # no data = client disconnected
        elif not data:
            consumer_list_lock.acquire()
            try:
                consumer_list[consumer_indx] = None
                nconsumer -= 1
            finally:
                consumer_list_lock.release()
            client_socket.close()

            print_lock.acquire()
            print(f"[ DCNT ] consumer disconnected: {client_addr}")
            print_lock.release()

            break


def producer_connection_handler():
    global producer_connection_socket, producer_list, producer_list_lock, nproducer

    while True:
        socket, addr = producer_connection_socket.accept()

        indx = 0

        producer_list_lock.acquire()
        try:
            # find first empty slot in list
            for p in producer_list:
                if p is None:
                    break
                indx += 1

            if indx == len(producer_list):
                producer_list.append((socket, addr))
            else:
                producer_list[indx] = (socket, addr)
            nproducer += 1

        finally:
            producer_list_lock.release()

        # send index to producer as part of the initalzation process
        socket.send(f"indx:{indx}".encode())

        print_lock.acquire()
        print(f"[ CNCT ] prodcuer {indx} connected")
        print(f"[ INFO ] producer online")
        print_lock.release()

        # dispatch worker thread
        producer_thread = Thread(target=producer_worker, args=(socket, addr, indx))
        producer_thread.start()


def consumer_connection_handler():
    global consumer_connection_socket, consumer_list, consumer_list_lock

    while True:
        socket, addr = consumer_connection_socket.accept()

        indx = 0

        consumer_list_lock.acquire()
        try:
            # find first empty slot in list
            for c in consumer_list:
                if c is None:
                    break
                indx += 1

            if indx == len(consumer_list):
                consumer_list.append((socket, addr))
            else:
                consumer_list[indx] = (socket, addr)
            nconsumer += 1

        finally:
            consumer_list_lock.release()

        # send index to consumer as part of the initalzation process
        socket.send(f"indx:{indx}".encode())

        print_lock.acquire()
        print(f"[ CNCT ] consumer {indx} connected")
        print(f"[ INFO ] {nconsumer} consumer(s) online")
        print_lock.release()

        # dispatch worker thread
        worker_thread = Thread(target=consumer_worker, args=(socket, addr, indx))
        worker_thread.start()


if __name__ == "__main__":
    if not PARAM_DEBUG:
        parse_arguments()

    # initialize sockets and stuff
    server_init()

    # dispatch connect handling threads
    producer_connection_thread = Thread(target=producer_connection_handler)
    producer_connection_thread.start()
    consumer_connection_thread = Thread(target=consumer_connection_handler)
    consumer_connection_thread.start()

    try:
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        sercver_cleanup()
