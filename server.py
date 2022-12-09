import sys
import socket
import threading
import datetime as dt
import shlex
from ServerIRC import ServerIRC


host = sys.argv[1]
port = int(sys.argv[2])

def logging(msg):
    print(f"[{dt.datetime.now().strftime('%Y-%d-%m %H:%M:%S')}] {msg}")

HELP = \
"""/away [message]  Signale son absence quand on nous envoie un message en privé
                 (en réponse un message peut être envoyé).
                 Une nouvelle commande /away réactive l’utilisateur.

/help  Affiche la liste des commandes disponibles.

/invite <nick>  Invite un utilisateur sur le canal où on se trouve.

/join <canal> [clé]  Permet de rejoindre un canal (protégé éventuellement par une clé).
                     Le canal est créé s’il n’existe pas.

/list  Affiche la liste des canaux sur IRC.

/msg [canal|nick] message  Pour envoyer un message à un utilisateur ou sur un canal (où on est
                           présent ou pas). Les arguments canal ou nick sont optionnels.

/names [channel]  Affiche les utilisateurs connectés à un canal. Si le canal n’est pas spécifié,
                  affiche tous les utilisateurs de tous les canaux.

/exit  Pour quitter le serveur IRC proprement.""".encode('utf-8')

DEFAULT_CHANNEL = "#default"


# Initialisation du seveur IRC
server = ServerIRC(help_msg=HELP, default_channel=DEFAULT_CHANNEL)

def exec_cmd(sc):
    global server
    ### Étape 1 : Protocole d'initialisation de la connexion ###

    # Récupération du nickname
    nick = sc.recv(1024).decode('utf-8')

    # Enregistrement du nouvel utilisateur
    if not server.add_user(sc, nick): return

    ### Étape 2 : Réception et exécution des commandes client ###

    logging(f"<{nick}> is connected")
    while True:
        # On ne gère pas les messages tronqués pour le moment
        raw_cmd = sc.recv(1024).decode('utf-8').strip()
        cmd = raw_cmd.split()
        logging(f"<{nick}> {raw_cmd}")

        # Si la commande est vide alors le socket est brisé
        if len(cmd) == 0:
            cmd.append("/exit")

        # Exécution de la commande
        if cmd[0] == "/help":
            server.help(nick)

        elif cmd[0] == "/away":
            # Reformatage de la commande pour prendre en compte les quotes
            try:
                cmd = shlex.split(raw_cmd, posix=True)
            except ValueError:
                server.argument_error(nick)
                continue
            server.away(cmd, nick)

        elif cmd[0] == "/invite":
            server.invite(cmd, nick)

        elif cmd[0] == "/join":
            server.join(cmd, nick)

        elif cmd[0] == "/list":
            server.list(nick)

        elif cmd[0] == "/msg":
            # Reformatage de la commande pour prendre en compte les quotes
            try:
                cmd = shlex.split(raw_cmd, posix=True)
            except ValueError:
                server.argument_error(nick)
                continue
            server.msg(cmd, nick)

        elif cmd[0] == "/names":
            server.names(cmd, nick)

        elif cmd[0] == "/exit":
            logging(f"<{nick}> is disconnected")
            server.exit(nick)
            break

        # Commande inconnue
        else:
            server.unknown_cmd(nick)


s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind((host, port))
# Le serveur peut traiter jusqu'à 100 connexions
s.listen(100)

logging("Serveur Mini IRC démarré en attente de clients...")
# Attente de clients
while True:
    sc, ip_client = s.accept()
    # Lorsqu'on accepte un client on traite sa requête dans un thread séparé
    threading.Thread(target=exec_cmd, args=(sc,)).start()
