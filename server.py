import socket
import threading
import sys
import time

help = \
"""
/away [message]  Signale son absence quand on nous envoie un message en privé
                 (en réponse un message peut être envoyé).
                 Une nouvelle commande /away réactive l’utilisateur.

/help  Affiche la liste des commandes disponibles

/invite <nick>  Invite un utilisateur sur le canal où on se trouve

/join <canal> [clé]  Permet de rejoindre un canal (protégé éventuellement par une clé).
                     Le canal est créé s’il n’existe pas.

/list  Affiche la liste des canaux sur IRC

/msg [canal|nick] message  Pour envoyer un message à un utilisateur ou sur un canal (où on est
                           présent ou pas). Les arguments canal ou nick sont optionnels.

/names [channel]  Affiche les utilisateurs connectés à un canal. Si le canal n’est pas spécifié,
                  affiche tous les utilisateurs de tous les canaux.
"""

default_error = "DEFAULT_ERROR"

def exec_cmd(sc):
    while True:
        # Comment déterminer la taille adéquate ?
        # Comment savoir si le message dépasse la taille maximale ?
        # sys.getsizeof(...)
        cmd = sc.recv(1024).decode('utf-8')
        # Exécution de la commande
        if cmd.startswith("/help"):
            sc.send(help.encode('utf-8'))
        else:
            sc.send(default_error.encode('utf-8'))
        # On fermera la connexion avec le client dans l'architecture pair à pair

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(("localhost", 9999))
# Le serveur peut traiter jusqu'à 100 connexions
s.listen(100)
# Attente de clients
while True:
    sc, ip_client = s.accept()
    # Lorsqu'on accepte un client on traite sa requête dans un thread séparé
    threading.Thread(target=exec_cmd, args=(sc,)).start()
