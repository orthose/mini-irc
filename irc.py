import socket
import threading
import sys

nickname = sys.argv[1]

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.connect(("localhost", 9999))

# On attend que le serveur nous envoie des messages
def recv_msg():
    while True:
        msg = s.recv(1024)
        print('\r'+msg.decode('utf-8'), end='\n> ')

threading.Thread(target=recv_msg, daemon=True).start()

# On commence par envoyer notre nickname
s.send(nickname.encode('utf-8'))
# On envoie des commandes au serveur
while True:
    s.send(input("> ").encode("utf-8"))
