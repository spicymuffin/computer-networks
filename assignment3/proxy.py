import socket
import sys
import threading
import time

PARAM_IP = "127.0.0.1"
PARAM_PORT = 9001
PARAM_MAX_QUEUED_CONNECTIONS = 5

PARAM_RECV_BUF_SIZE = 1024 * 1024

PARAM_DEBUG = True

PARAM_REDIRECT_TRIGGER = "internettrend"
PARAM_REDIRECT_URL = "http://mnet.yonsei.ac.kr/"
PARAM_REDIRECT_HOST = "mnet.yonsei.ac.kr"

REDIRECT_FLAG = False


IMAGE_FILTER_STATE = False

IMAGE_FILTER_ENABLE_OPT = "image_off"
IMAGE_FILTER_DISABLE_OPT = "image_on"


def parse_arguments():
    global PARAM_PORT
    nargs = 1

    if len(sys.argv) < 1 + nargs:
        print("not enough args")
        exit(1)
    elif len(sys.argv) > 1 + nargs:
        print("too many args")
        exit(1)
    else:
        for i in range(len(sys.argv)):
            if i == 1:
                PARAM_PORT = sys.argv[i]


transaction_counter = 1


def print_param_line(ip, port, redirected, filtered):
    global transaction_counter
    print("--------------------------------------------")
    print(f"CLI connected to {ip}:{port}")
    print(
        f"{transaction_counter} Redirected [{'X' if redirected == False else 'O'}] Image Filter [{'X' if filtered == False else 'O'}]"
    )
    transaction_counter += 1


def print_stage_line(stage):
    if stage == 0:
        print("[CLI ==> PRX --- SRV]")
    elif stage == 1:
        print("[CLI --- PRX ==> SRV]")
    elif stage == 2:
        print("[CLI --- PRX <== SRV]")
    elif stage == 3:
        print("[CLI <== PRX --- SRV]")


accept_socket = None


def request_handler(sock, addr):
    global PARAM_DEBUG, PARAM_IP, PARAM_PORT, PARAM_MAX_QUEUED_CONNECTIONS
    global PARAM_RECV_BUF_SIZE
    global accept_socket
    global PARAM_REDIRECT_TRIGGER, PARAM_REDIRECT_URL, REDIRECT_FLAG
    global IMAGE_FILTER_STATE, IMAGE_FILTER_DISABLE_OPT, IMAGE_FILTER_ENABLE_OPT

    data = sock.recv(PARAM_RECV_BUF_SIZE)

    print(data)
    print(data.decode())

    header_decoded = data.split(b"\r\n\r\n")[0].decode()

    # example request
    """
    GET http://mnet.yonsei.ac.kr/hw/sample3.html HTTP/1.1
    Host: mnet.yonsei.ac.kr
    User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0
    Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8
    Accept-Language: en-US,en;q=0.5
    Accept-Encoding: gzip, deflate
    Connection: keep-alive
    Upgrade-Insecure-Requests: 1
    Priority: u=0, i

    """

    # determine if we have to redirect or not
    split_data = header_decoded.split("\n")
    request_line = split_data[0].split(" ")
    request_host = split_data[1].split(" ")[1]
    request_url = request_line[1]

    if PARAM_REDIRECT_TRIGGER in request_url:
        REDIRECT_FLAG = True

    url_options = request_url.split("?")
    if len(url_options) > 0:
        for option in url_options:
            if option == IMAGE_FILTER_ENABLE_OPT:
                IMAGE_FILTER_STATE = True
            elif option == IMAGE_FILTER_DISABLE_OPT:
                IMAGE_FILTER_STATE = False

    print_param_line(addr[0], addr[1], REDIRECT_FLAG, IMAGE_FILTER_STATE)

    # decide where to make the request
    if REDIRECT_FLAG:
        request_host = PARAM_REDIRECT_HOST
        request_url = PARAM_REDIRECT_URL


def cleanup():
    global accept_socket
    if accept_socket is not None:
        accept_socket.close()


def accept_connections():
    global accept_socket

    while True:
        sock, addr = accept_socket.accept()
        request_handler_thread = threading.Thread(target=request_handler)
        request_handler_thread.daemon = True
        request_handler_thread.start()


if __name__ == "__main__":
    try:
        # parse arguments if not debug launch
        if not PARAM_DEBUG:
            parse_arguments()

        print(f"Starting proxy server on port {PARAM_PORT}")

        # create connection accpet socket
        accept_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        accept_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        accept_socket.bind((PARAM_IP, PARAM_PORT))
        accept_socket.listen(PARAM_MAX_QUEUED_CONNECTIONS)

        # start accepting connections in a separate thread
        accept_thread = threading.Thread(target=accept_connections)

        while True:
            input()
            time.sleep(0.5)

    except KeyboardInterrupt:
        print("exiting on SIGINT")
        sys.exit(0)
