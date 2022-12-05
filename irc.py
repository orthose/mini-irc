import socket
import threading

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.connect(("localhost", 9999))

def run():
    while True:
        msg = s.recv(1024)
        print('\r'+msg.decode('utf-8'), end='\n> ')

threading.Thread(target=run, daemon=True).start()

while True:
    s.send(input("> ").encode("utf-8"))
