import socket
import threading
import argparse
from protocol import *
from ClientIRC import ClientIRC


# Parsing des arguments de la ligne de commande
parser = argparse.ArgumentParser(description='Interface client de Mini IRC.')
parser.add_argument("nick", type=str, help="Pseudo du client")
parser.add_argument("host", type=str, help="Adresse du serveur IRC")
parser.add_argument("port", type=int, help="Port du serveur IRC")
parser.add_argument("--terminal", "-t", action="store_true", default=False,
    help="Lancer l'interface console plutôt que la GUI")
args = parser.parse_args()


WELCOME = \
f"""Bienvenue <{args.nick}> sur Mini IRC
Tapez /help pour voir les commandes"""

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.connect((args.host, args.port))

### Étape 1 : Protocole d'initialisation de la connexion ###

# On commence par envoyer notre nickname
s.send(args.nick.encode('utf-8'))

# On récupère ensuite le nom du canal par défaut
channel = s.recv(1024)

# Si le nickname est déjà pris il faut en choisir un autre
if channel == NICKNAME_ERROR:
    print(f"Le pseudo <{args.nick}> est déjà utilisé.")
    exit(1)

channel = channel.decode('utf-8')

def prompt():
    return f'{channel} <{args.nick}> '

def clear_line():
    print('\r'+' '*len(prompt()), end='')

# Initialisation de l'interface graphique
client = ClientIRC(s, args.nick, channel, WELCOME) if not args.terminal else None

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
            if not args.terminal: client.set_channel(channel)
            print('\r'+prompt(), end='')

        # Affichage d'un message
        else:
            print('\r'+msg, end='\n'+prompt())
            if not args.terminal: client.print(msg)

threading.Thread(target=recv_msg, daemon=True).start()

### Étape 3 : Envoi de commandes au serveur ###

# On envoie des commandes au serveur en console
if args.terminal:
    print(WELCOME)
    while True:
        cmd = input(prompt()).strip()
        s.send(cmd.encode("utf-8"))
        if cmd.startswith("/exit"):
            break

# Lancement de l'interface graphique
else: client.mainloop()
