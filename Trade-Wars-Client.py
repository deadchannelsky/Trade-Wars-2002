import socket


FORMAT = "utf-8"
HEADER = 64  # First message from clients will always be a message of 64 bytes that tells us the len of the message that will come next
# number followed by padding so that it is 64 bytes long
#
DISCONNECT_MESSAGE = "!DISCONNECT"
PROMPT_INPUT = "!INPUT"

SERVER = "10.0.0.162"  # IPV4 address for local host connections

PORT = 5050
ADDR = (SERVER, PORT)

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

client.connect(ADDR)


def send(msg):

    message = msg.encode(FORMAT)

    msg_length = len(message)

    send_length = str(msg_length).encode(FORMAT)

    send_length += b" " * (HEADER-len(send_length))

    client.send(send_length)

    client.send(message)


while True:

    try:
        msg_length = client.recv(HEADER).decode(FORMAT)
    except ConnectionResetError:
        print("\n\n\n\n\nServer is shutting down")
        break

    if msg_length:

        msg_length = int(msg_length)

        msg = client.recv(msg_length).decode(FORMAT)

        if msg == DISCONNECT_MESSAGE:
            client.close()
            break  # Ensure that clients disconnect cleanly
        elif msg.startswith(PROMPT_INPUT):
            response = input(msg.removeprefix(PROMPT_INPUT))
            send(response)
        else:
            print(msg)
    else:
        client.close()
        break
