import socket
import sys
import threading
import time

PARAM_IP = "127.0.0.1"
PARAM_PORT = 9001
PARAM_MAX_QUEUED_CONNECTIONS = 5

PARAM_RECV_BUF_SIZE = 4096

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


def print_client_connected(ip, port):
    print(f"[CLI connected to {ip}:{port}]")


def print_server_connected(ip, port):
    print(f"[SRV connected to {ip}:{port}]")


def print_client_disconnected():
    print(f"[CLI disconnected]")


def print_server_disconnected():
    print(f"[SRV disconnected]")


# 1 [X] Redirected [O] Image filter
# [CLI connected to 127.0.0.1:4994]


def print_param_line(ip, port, redirected, filtered):
    global transaction_counter
    print("--------------------------------------------")
    print(
        f"{transaction_counter} [{'X' if redirected == False else 'O'}] Redirected [{'X' if filtered == False else 'O'}] Image filter"
    )
    print(f"[CLI connected to {ip}:{port}]")
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


def parse_header_user_agent(user_agent):
    values = []

    space0 = user_agent.find(" ")
    values.append(user_agent[:space0])

    parenthesis0_idx = user_agent.find("(")
    parenthesis1_idx = user_agent.find(")")
    values.append(user_agent[parenthesis0_idx : parenthesis1_idx + 1])

    remaining = user_agent[parenthesis1_idx + 1 :].strip()
    parts = remaining.split(" ")
    values.extend(parts)

    return values


def request_handler(client_sock, client_addr):
    global PARAM_DEBUG, PARAM_IP, PARAM_PORT, PARAM_MAX_QUEUED_CONNECTIONS
    global PARAM_RECV_BUF_SIZE
    global accept_socket
    global PARAM_REDIRECT_TRIGGER, PARAM_REDIRECT_URL, REDIRECT_FLAG
    global IMAGE_FILTER_STATE, IMAGE_FILTER_DISABLE_OPT, IMAGE_FILTER_ENABLE_OPT

    try:
        # read the request from the socket
        data = b""

        while True:
            chunk = client_sock.recv(PARAM_RECV_BUF_SIZE)
            if not chunk:
                break
            data += chunk

        if not data:
            # no data received, something bad happened
            client_sock.close()
            return

        # parse the request into header and data
        request_header = data.split(b"\r\n\r\n")[0]
        request_data = data.split(b"\r\n\r\n")[1]

        request_header_decoded = data.split(b"\r\n\r\n")[0].decode()

        # split the header into lines
        lines = request_header_decoded.split("\n")

        # parse request line
        request_line = lines[0]
        request_method = request_line.split(" ")[0].strip()
        request_url = request_line.split(" ")[1].strip()
        request_protocol = request_line.split(" ")[2].strip()

        # parse headers
        request_headers = {}
        for line in lines[1:]:
            if ":" in line:
                # only split on the first colon
                key, value = line.split(":", 1)
                request_headers[key.strip()] = value.strip()

        request_host = None
        request_user_agent = None

        if "Host" in request_headers:
            request_host = request_headers["Host"]

        if "User-Agent" in request_headers:
            request_user_agent = request_headers["User-Agent"]

        # check if we have to redirect
        if PARAM_REDIRECT_TRIGGER in request_url:
            REDIRECT_FLAG = True

        # check if we have to enable or disable image filter
        url_options = request_url.split("?")
        url_options = url_options[1:]
        print(url_options)
        if len(url_options) > 0:
            for option in url_options:
                if option == IMAGE_FILTER_ENABLE_OPT:
                    IMAGE_FILTER_STATE = True
                elif option == IMAGE_FILTER_DISABLE_OPT:
                    IMAGE_FILTER_STATE = False

        # print the parameters
        print_param_line(
            client_addr[0], client_addr[1], REDIRECT_FLAG, IMAGE_FILTER_STATE
        )

        # print the request
        print_stage_line(0)
        print(f"  > {request_method} {request_url}")

        # parse user agent to print
        if request_user_agent is not None:
            request_user_agent_parsed = parse_header_user_agent(request_user_agent)
        if (
            request_user_agent_parsed is not None
            and len(request_user_agent_parsed) >= 2
        ):
            print(f"  > {request_user_agent_parsed[0]} {request_user_agent_parsed[1]}")
        else:
            print(f"the user agent header had less than 2 elements or was not present")

        if PARAM_DEBUG:
            print("received request:")
            print(request_headers)
            print(request_data)

        # TODO: test that the parsing from URL works
        # if host was missing then try to extract it from the url
        if request_host is None:
            request_host = request_url[7:].split("/")[0]

        # if redirect flag is set then change the host and url
        if REDIRECT_FLAG:
            request_host = PARAM_REDIRECT_HOST
            request_url = PARAM_REDIRECT_URL

        # if the host is still missing then return
        if request_host is None:
            print("critical error: host information is missing")
            return

        # create a new socket to make the request
        request_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        request_sock.connect((request_host, 80))

        # print the server connection
        print_server_connected(request_host, 80)

        # hop-by-hop headers
        hop_by_hop_headers = [
            "Connection",
            "Keep-Alive",
            "Proxy-Authenticate",
            "Proxy-Authorization",
            "TE",
            "Trailer",
            "Transfer-Encoding",
            "Upgrade",
        ]

        # remove the hop-by-hop headers
        for request_header in hop_by_hop_headers:
            if request_header in request_headers:
                del request_headers[request_header]

        # # add connection close header
        # request_headers["Connection"] = "close"

        path = None

        if request_protocol == "HTTP/1.1":
            # extract only the path
            if request_url.startswith("http://"):
                without_scheme = request_url[7:]
                slash_idx = without_scheme.find("/")
                if slash_idx != -1:
                    path = without_scheme[slash_idx:]
                else:
                    # no path means just '/'
                    path = "/"
            else:
                # URL doesn't start with http://, assume it's already a relative path
                path = request_url
        else:
            path = request_url

        if PARAM_DEBUG:
            print("forwarding request:")
            print(request_headers)
            print(request_data)

        # create the new request
        forwarded_request = f"{request_method} {path} {request_protocol}\r\n".encode()

        # add the headers
        for key, value in request_headers.items():
            forwarded_request += f"{key}: {value}\r\n".encode()

        # add the end of the headers
        forwarded_request += b"\r\n"

        # add the request data
        forwarded_request += request_data

        # send the request to the server
        request_sock.send(forwarded_request)

        # print the forwarded request
        print_stage_line(1)
        print(f"  > {request_method} {path}")
        print(f"  > {request_user_agent_parsed[0]} {request_user_agent_parsed[1]}")

        data = b""

        # read the response from the socket
        while True:
            chunk = request_sock.recv(PARAM_RECV_BUF_SIZE)
            if not chunk:
                break
            data += chunk

        # parse the response
        response_header = data.split(b"\r\n\r\n")[0]
        response_data = data.split(b"\r\n\r\n")[1]

        response_header_decoded = response_header.decode()

        # split the header into lines
        lines = response_header_decoded.split("\n")

        # parse response line
        response_line = lines[0]
        response_protocol = response_line.split(" ")[0].strip()
        response_status = response_line.split(" ")[1].strip()
        response_status_text = response_line.split(" ")[2].strip()

        # parse headers
        response_headers = {}
        for line in lines[1:]:
            if ":" in line:
                # only split on the first colon
                key, value = line.split(":", 1)
                response_headers[key.strip()] = value.strip()

        if PARAM_DEBUG:
            print("received response:")
            print(response_headers)
            print(response_data)

        # print the response
        print_stage_line(2)
        print(f"  > {response_status} {response_status_text}")
        if "Content-Type" in response_headers and "Content-Length" in response_headers:
            print(
                f"  > {response_headers['Content-Type']} {response_headers['Content-Length']} bytes"
            )
        else:
            # if either of the headers is missing then we stay silent
            if PARAM_DEBUG:
                print("  > the response did not contain MIME Type or Content-Length")

        response_content_type = None
        if "Content-Type" in response_headers:
            response_content_type = response_headers["Content-Type"]

        # if image filter is enabled then send 404
        if (
            IMAGE_FILTER_STATE
            and response_content_type is not None
            and "image" in response_content_type
        ):
            # modify the response to send 404

            # modify the response line
            # do not modify the protocol
            response_protocol = response_protocol
            # set the status to 404
            response_status = 404
            # set the status text to not found
            response_status_text = "Not Found"

            # flush the headers first
            response_headers = {}

            # data is empty
            response_data = b""

        # reassemble the response
        forwarded_response = (
            f"{response_protocol} {response_status} {response_status_text}\r\n"
        ).encode()

        # add the headers
        for key, value in response_headers.items():
            forwarded_response += f"{key}: {value}\r\n".encode()

        # add the end of the headers
        forwarded_response += b"\r\n"

        # add the response data
        forwarded_response += response_data

        # send the response to the client
        client_sock.send(forwarded_response)

        print("IM GAYYYYYYYYYYYYYYYYYYY: ", forwarded_response == data)

        if PARAM_DEBUG:
            print("forwarding response:")
            print(response_headers)
            print(response_data)

        # print the forwarded response
        print_stage_line(3)
        print(f"  > {response_status} {response_status_text}")
        if "Content-Type" in response_headers and "Content-Length" in response_headers:
            print(
                f"  > {response_headers['Content-Type']} {response_headers['Content-Length']} bytes"
            )
        else:
            # if either of the headers is missing then we stay silent
            if PARAM_DEBUG:
                print("  > the response did not contain MIME Type or Content-Length")

        # close the sockets
        client_sock.close()
        request_sock.close()

        # print disconnect messages
        print_client_disconnected()
        print_server_disconnected()

        return

    except Exception as e:
        print(f"an error occured: ({e})\nmaybe the request was using HTTP/2+?")
        return


if __name__ == "__main__":

    sock = None

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

        while True:
            sock, addr = accept_socket.accept()

            # handle request
            request_handler(sock, addr)

    except KeyboardInterrupt:
        print("exiting on SIGINT")

        # cleanup
        if accept_socket is not None:
            accept_socket.close()

        if sock is not None:
            sock.close()

        sys.exit(0)
