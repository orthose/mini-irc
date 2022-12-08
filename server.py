import socket
import threading
import datetime as dt

def logging(msg):
    print(f"[{dt.datetime.now().strftime('%Y-%d-%m %H:%M:%S')}] {msg}")

help = \
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

/exit  Quitte l'IRC en fermant la connexion avec le serveur."""

default_channel = "#default"

nickname_error = "NICKNAME_ERROR"

argument_error = "ARGUMENT_ERROR"

channel_key_error = "CHANNEL_KEY_ERROR"

default_error = "DEFAULT_ERROR"

# ATTENTION: Les collections ne sont pas thread-safe
# et doivent être verrouillées en lecture / écriture / suppression

# Dictionnaire des canaux avec ensemble des utilisateurs connectés
lock_channels = threading.Lock()
channels = {default_channel: {
        "key": None,
        "users": set(), "lock_users": threading.Lock(),
        "msg": [], "lock_msg": threading.Lock()
    }
}
# Dictionnaire du canal courant d'un utilisateur
lock_users = threading.Lock()
users = dict()

# TODO: Décomposer en sous-fonction chaque commande
def exec_cmd(sc):
    ### Étape 1 : Protocole d'initialisation de la connexion ###

    # Récupération du nickname
    nickname = sc.recv(1024).decode('utf-8')

    # Enregistrement de l'utilisateur s'il n'existe pas déjà
    lock_users.acquire()
    if nickname in users:
        lock_users.release()
        sc.send(nickname_error.encode('utf-8'))
        sc.close()
        return
    else:
        users[nickname] = {"channel": default_channel, "msg": dict(), "lock_msg": threading.Lock()}
        lock_users.release()
        sc.send(default_channel.encode('utf-8'))

    # Ajout de l'utilisateur au canal par défaut
    with channels[default_channel]["lock_users"]:
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
            sc.send(help.encode('utf-8'))

        elif cmd[0] == "/join":
            if not (2 <= len(cmd) <= 3):
                sc.send(argument_error.encode('utf-8'))
            else:
                chan = '#'+cmd[1].replace('#', '')

                key = None
                if len(cmd) == 3:
                    key = cmd[2]

                # Création du canal
                with lock_channels:
                    if chan not in channels:
                        channels[chan] = {
                            "key": key,
                            "users": set(), "lock_users": threading.Lock(),
                            "msg": [], "lock_msg": threading.Lock()
                        }

                # Connexion au canal
                if channels[chan]["key"] == key:
                    with channels[chan]["lock_users"]:
                        channels[chan]["users"].add(nickname)

                    # Déconnexion de l'utilisateur du canal précédent
                    with channels[users[nickname]["channel"]]["lock_users"]:
                        channels[users[nickname]["channel"]]["users"].remove(nickname)

                    # Connexion de l'utilisateur au canal choisi
                    users[nickname]["channel"] = chan

                    # Envoi du canal au client
                    sc.send(chan.encode('utf-8'))

                # La clé de sécurité est incorrecte
                else:
                    sc.send(channel_key_error.encode('utf-8'))

        # Si le socket est brisé il faudra réaliser les mêmes opérations
        elif cmd[0] == "/exit":
            logging(f"<{nickname}> is disconnected")

            # On retire l'utilisateur du canal sur lequel il est connecté
            with channels[users[nickname]["channel"]]["lock_users"]:
                channels[users[nickname]["channel"]]["users"].remove(nickname)

            # On supprime l'utilisateur
            with lock_users:
                users.pop(nickname)

            # On ferme la connexion et on arrête le thread
            sc.close()
            break

        else:
            sc.send(default_error.encode('utf-8'))
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
