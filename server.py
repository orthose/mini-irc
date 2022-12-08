import socket
import threading
import datetime as dt
from protocol import *

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

/exit  Quitte l'IRC en fermant la connexion avec le serveur.""".encode('utf-8')

default_channel = "#default"

# Les collections sont supposées thread-safe en CPython
# Cependant pour éviter des collisions de clé des verrous sont nécessaires:
# 1. Pour l'enregistrement d'un nouvel utilisateur
# 2. Pour la création d'un nouveau canal

# Les sockets ne sont pas thread-safe et devront être verrouillés

# On n'enregistre pas les messages de manière persistante
# Le rôle du serveur est simplement de router les messages entre les clients
# pour les conversations privées ou de les diffuser à plusieurs clients pour les canaux

# Dictionnaire des informations utilisateurs
lock_users = threading.Lock()
users = dict()
# Dictionnaire des canaux avec ensemble des utilisateurs connectés
lock_channels = threading.Lock()
channels = {default_channel: {"key": None, "users": set()}}

# TODO: Décomposer en sous-fonction chaque commande
def exec_cmd(sc):
    global lock_channels, channels, lock_users, users
    ### Étape 1 : Protocole d'initialisation de la connexion ###

    # Récupération du nickname
    nickname = sc.recv(1024).decode('utf-8')

    # Enregistrement de l'utilisateur s'il n'existe pas déjà
    lock_users.acquire()
    if nickname in users:
        lock_users.release()
        sc.send(NICKNAME_ERROR)
        sc.close()
        return
    else:
        users[nickname] = {"channel": default_channel, "socket": sc, "lock_socket": threading.Lock()}
        lock_users.release()
        sc.send(default_channel.encode('utf-8'))

    # Ajout de l'utilisateur au canal par défaut
    channels[default_channel]["users"].add(nickname)

    ### Étape 2 : Réception et exécution des commandes client ###

    logging(f"<{nickname}> is connected")
    while True:
        print(channels)
        print(users)
        # Comment déterminer la taille adéquate ?
        # Comment savoir si le message dépasse la taille maximale ?
        # sys.getsizeof(...)
        # On peut avertir l'utilisateur que la taille du message est tronquée
        # si elle dépasse un certain nombre de caractères
        # Mais en UTF-8 le nombre de bytes par caractère n'est pas fixe
        cmd = sc.recv(1024).decode('utf-8').split()
        logging(f"<{nickname}> {' '.join(cmd)}")

        # Exécution de la commande
        if cmd[0] == "/help":
            sc.send(HELP)

        elif cmd[0] == "/join":
            if not (2 <= len(cmd) <= 3):
                sc.send(ARGUMENT_ERROR)
            else:
                chan = '#'+cmd[1].replace('#', '')

                key = None
                if len(cmd) == 3:
                    key = cmd[2]

                # Création éventuelle du canal
                with lock_channels:
                    if chan not in channels:
                        channels[chan] = {"key": key, "users": set()}

                # Connexion au canal
                if channels[chan]["key"] == key:
                    channels[chan]["users"].add(nickname)

                    # Déconnexion de l'utilisateur du canal précédent
                    if users[nickname]["channel"] != chan:
                        channels[users[nickname]["channel"]]["users"].remove(nickname)

                    # Connexion de l'utilisateur au canal choisi
                    users[nickname]["channel"] = chan

                    # Envoi du canal au client
                    sc.send(("/join "+chan).encode('utf-8'))

                # La clé de sécurité est incorrecte
                else:
                    sc.send(CHANNEL_KEY_ERROR)

        # Si le socket est brisé il faudra réaliser les mêmes opérations
        elif cmd[0] == "/exit":
            logging(f"<{nickname}> is disconnected")

            # On retire l'utilisateur du canal sur lequel il est connecté
            channels[users[nickname]["channel"]]["users"].remove(nickname)

            # On supprime l'utilisateur
            users.pop(nickname)

            # On ferme la connexion et on arrête le thread
            sc.close()
            break

        # Commande inconnue
        else:
            sc.send(UNKNOWN_CMD_ERROR)
        # On fermera la connexion avec le client dans l'architecture pair à pair

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(("localhost", 9999))
# Le serveur peut traiter jusqu'à 100 connexions
s.listen(100)

logging("Serveur Mini IRC démarré en attente de clients...")
# Attente de clients
while True:
    sc, ip_client = s.accept()
    # Lorsqu'on accepte un client on traite sa requête dans un thread séparé
    threading.Thread(target=exec_cmd, args=(sc,)).start()
