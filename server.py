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

default_error = "DEFAULT_ERROR"

def exec_cmd(sc):
    # Récupération du nickname
    nickname = sc.recv(1024).decode('utf-8')
    logging(f"<{nickname}> is connected")
    while True:
        # Comment déterminer la taille adéquate ?
        # Comment savoir si le message dépasse la taille maximale ?
        # sys.getsizeof(...)
        # On peut avertir l'utilisateur que la taille du message est tronquée
        # si elle dépasse un certain nombre de caractères
        # Mais en UTF-8 le nombre de bytes par caractère n'est pas fixe
        cmd = sc.recv(1024).decode('utf-8').strip()
        logging(f"<{nickname}> {cmd}")
        # Exécution de la commande
        if cmd.startswith("/help"):
            sc.send(help.encode('utf-8'))
        elif cmd.startswith("/exit"):
            logging(f"<{nickname}> is disconnected")
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
