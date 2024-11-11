import socket
import sys
import time
from threading import Thread
from threading import Lock
from queue import Queue

PARAM_DEBUG = False

PARAM_MAX_QUEUED_CONNECTIONS = 5
PARAM_RECV_BUFFER_SIZE = 1024

PARAM_SERVER_IP = "127.0.0.1"
PARAM_PORT_PRODUCER = 5000
PARAM_PORT_CONSUMER = 5001


def parse_arguments():
    global PARAM_SERVER_IP, PARAM_PORT_PRODUCER, PARAM_PORT_CONSUMER

    if len(sys.argv) < 1 + 3:
        print("not enough args")
        exit(1)
    elif len(sys.argv) > 1 + 3:
        print("too many args")
        exit(1)
    else:
        for i in range(len(sys.argv)):
            if i == 1:
                PARAM_SERVER_IP = sys.argv[i]
            if i == 2:
                PARAM_PORT_PRODUCER = int(sys.argv[i])
            if i == 3:
                PARAM_PORT_CONSUMER = int(sys.argv[i])


producer_connection_socket = None  # socket for producer connections
consumer_connection_socket = None  # socket for consumer connections

producer_list = []  # list of producer sock, addr references
producer_list_lock = Lock()  # lock for producer list
nproducer = 0  # number of producers

consumer_list = []  # list of consumer sock, addr references
consumer_list_lock = Lock()  # lock for consumer list
nconsumer = 0  # number of consumers

event_queue = Queue()  # event queue
event_queue_lock = Lock()  # lock for event queue

print_lock = Lock()  # lock for print


def server_init():
    global producer_connection_socket, consumer_connection_socket

    producer_connection_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    producer_connection_socket.bind((PARAM_SERVER_IP, PARAM_PORT_PRODUCER))
    producer_connection_socket.listen(PARAM_MAX_QUEUED_CONNECTIONS)
    producer_connection_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    consumer_connection_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    consumer_connection_socket.bind((PARAM_SERVER_IP, PARAM_PORT_CONSUMER))
    consumer_connection_socket.listen(PARAM_MAX_QUEUED_CONNECTIONS)
    consumer_connection_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)


def producer_worker(client_socket, client_addr, producer_indx):
    global event_queue, event_queue_lock, producer_list, producer_list_lock, nproducer

    while True:
        data = None
        try:
            data = client_socket.recv(PARAM_RECV_BUFFER_SIZE).decode()
        except Exception as e:
            print_lock.acquire()
            print(f"[ ERRO ] producer {producer_indx} abruptly closed: {e}")
            print_lock.release()

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
            print(f"[ DCNT ] producer {producer_indx} disconnected")
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
        data = None
        try:
            data = client_socket.recv(PARAM_RECV_BUFFER_SIZE).decode()
        except Exception as e:
            print_lock.acquire()
            print(f"[ ERRO ] consumer {consumer_indx} abruptly closed: {e}")
            print_lock.release()

        empty_flag = False
        size = -1
        _nconsumer = -1

        # no data = client disconnected
        if not data:
            consumer_list_lock.acquire()
            try:
                consumer_list[consumer_indx] = None
                nconsumer -= 1
                _nconsumer = nconsumer
            finally:
                consumer_list_lock.release()
            client_socket.close()

            print_lock.acquire()
            print(f"[ DCNT ] consumer {consumer_indx} disconnected")
            print(f"[ INFO ] {_nconsumer} consumer(s) online")
            print_lock.release()

            break

        # pull event
        elif data == "PULL EVENT":
            event_queue_lock.acquire()
            try:
                if not event_queue.empty():
                    event = event_queue.get()
                    client_socket.send(event.encode())
                    size = event_queue.qsize()
                else:
                    client_socket.send("\nempty".encode())
                    empty_flag = True
            finally:
                event_queue_lock.release()
                print_lock.acquire()
                if not empty_flag:
                    print(f"[ PULL ] event pulled. remaining events in queue: {size}")
                print_lock.release()


def producer_connection_handler():
    global producer_connection_socket, producer_list, producer_list_lock, nproducer

    while True:
        socket, addr = producer_connection_socket.accept()

        indx = 0
        _nproducer = -1

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
            _nproducer = nproducer

        finally:
            producer_list_lock.release()

        # send index to producer as part of the initalzation process
        socket.send(f"indx:{indx}".encode())

        print_lock.acquire()
        print(f"[ CNCT ] prodcuer {indx} connected")
        print(f"[ INFO ] {_nproducer} producer(s) online")
        print_lock.release()

        # dispatch worker thread
        producer_thread = Thread(
            target=producer_worker, args=(socket, addr, indx), daemon=True
        )
        producer_thread.start()


def consumer_connection_handler():
    global consumer_connection_socket, consumer_list, consumer_list_lock, nconsumer

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
        try:
            socket.send(f"indx:{indx}".encode())
        except Exception as e:

            # clean up consumer entry in the list
            consumer_list_lock.acquire()
            consumer_list[indx] = None
            nconsumer -= 1
            consumer_list_lock.release()

            print_lock.acquire()
            print(f"[ ERRO ] consumer {indx} failed to connect: {e}")
            print_lock.release()
            continue

        print_lock.acquire()
        print(f"[ CNCT ] consumer {indx} connected")
        print(f"[ INFO ] {nconsumer} consumer(s) online")
        print_lock.release()

        # dispatch worker thread
        worker_thread = Thread(
            target=consumer_worker, args=(socket, addr, indx), daemon=True
        )
        worker_thread.start()


def server_cleanup():
    global producer_connection_socket, consumer_connection_socket, producer_list, consumer_list

    producer_connection_socket.close()
    consumer_connection_socket.close()

    for cl in producer_list:
        if cl is not None:
            cl[0].close()

    for cl in consumer_list:
        if cl is not None:
            cl[0].close()


if __name__ == "__main__":
    if not PARAM_DEBUG:
        parse_arguments()

    # initialize sockets and stuff
    server_init()

    # dispatch connect handling threads
    producer_connection_thread = Thread(target=producer_connection_handler, daemon=True)
    producer_connection_thread.start()
    consumer_connection_thread = Thread(target=consumer_connection_handler, daemon=True)
    consumer_connection_thread.start()

    try:
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        server_cleanup()

        # exit msg
        print("\nexiting on SIGINT (ctrl+c)")
