import socket
import threading
import sys

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(("localhost", 9999))
s.listen(1)
sc, ip_client = s.accept()

def run():
    while True:
        msg = sc.recv(1024)
        print('\r'+msg.decode('utf-8'), end='\n> ')

threading.Thread(target=run, daemon=True).start()

while True:
    sc.send(input("> ").encode("utf-8"))
