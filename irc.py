import socket
import threading
import sys
from protocol import *

nickname = sys.argv[1]

WELCOME = \
f"""Bienvenue <{nickname}> sur Mini IRC
Tapez /help pour voir les commandes"""

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.connect(("localhost", 9999))

### Étape 1 : Protocole d'initialisation de la connexion ###

# On commence par envoyer notre nickname
s.send(nickname.encode('utf-8'))

# On récupère ensuite le nom du canal par défaut
channel = s.recv(1024)

# Si le nickname est déjà pris il faut en choisir un autre
if channel == NICKNAME_ERROR:
    print(f"Le pseudo <{nickname}> est déjà utilisé.")
    exit(1)

channel = channel.decode('utf-8')

def prompt():
    return f'{channel} <{nickname}> '

def clear_line():
    print('\r'+' '*len(prompt()), end='')

### Étape 2 : Attente des messages du serveur ###

# On attend que le serveur nous envoie des messages
def recv_msg():
    global channel
    while True:
        msg = s.recv(1024).decode('utf-8')
        clear_line()

        # Exécution éventuelle du retour de commande du serveur
        if msg.startswith("/join"):
            channel = msg.split()[1]
            print('\r'+prompt(), end='')

        # Affichage d'un message
        else:
            print('\r'+msg, end='\n'+prompt())

threading.Thread(target=recv_msg, daemon=True).start()

### Étape 3 : Envoi de commandes au serveur ###

# On envoie des commandes au serveur
print(WELCOME)
while True:
    cmd = input(prompt()).strip()
    s.send(cmd.encode("utf-8"))
    if cmd.startswith("/exit"):
        break
