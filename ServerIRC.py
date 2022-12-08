from protocol import *
import threading
import socket
from typing import List, Tuple


class ServerIRC:
    """
    Classe fournissant les commandes exécutables par le serveur IRC.

    On n'enregistre pas les messages de manière persistante.
    Le rôle du serveur est simplement de router les messages entre les clients :
        1. De client à client pour les conversations privées.
        2. Par diffusion à tous les clients d'un canal.

    Le serveur utilise en interne des collections qui sont supposées thread-safe en CPython.
    Cependant pour éviter des collisions de clé des verrous sont nécessaires :
        1. Pour l'enregistrement d'un nouvel utilisateur
        2. Pour la création d'un nouveau canal

    Chaque client garde sa connexion ouverte avec le serveur.
    Le serveur peut envoyer plusieurs messages simultanément à un même client.
    Or, les sockets ne sont pas thread-safe et devront donc être verrouillés.
    """
    def __init__(self, help_msg: bytes, default_channel: str):
        """
        :param help: Message d'aide à envoyer au client
        :param default_channel: Nom du canal par défaut lorsqu'un client se connecte
        """
        self.help_msg = help_msg
        self.default_channel = default_channel

        # Dictionnaire des informations utilisateurs
        self.lock_users = threading.Lock()
        self.users = dict()

        # Dictionnaire des canaux avec ensemble des utilisateurs connectés
        self.lock_channels = threading.Lock()
        self.channels = {default_channel: {"key": None, "users": set()}}


    def __socket(self, nickname: str) -> Tuple[socket.socket, threading.Lock]:
        return (self.users[nickname]["socket"], self.users[nickname]["lock_socket"])


    def __send(self, msg: bytes, nickname: str):
        sc, lock_sc = self.__socket(nickname)
        with lock_sc: sc.send(msg)


    def __broadcast(self, msg: bytes, dest_users: List[str]):
        # Envoi du message à un ensemble d'utilisateurs
        for dest_nick in dest_users:
            # Il faut s'assurer que le destinataire n'est pas supprimé
            with self.lock_users:
                if dest_nick in self.users: self.__send(msg, dest_nick)


    def add_user(self, socket_client: socket.socket, nickname: str) -> bool:
        """
        Permet d'ajouter un nouvel utilisateur qui vient de se connecter.

        :param socket_client: Prise pour communiquer avec le client
        :param nickname: Pseudo de l'utilisateur

        :return: True si le client a bien été ajouté False sinon
        """
        # Enregistrement de l'utilisateur s'il n'existe pas déjà
        # Deux clients choisissant le même nickname ne peuvent passer
        # en même temps cette section critique
        self.lock_users.acquire()
        if nickname in self.users:
            self.lock_users.release()
            socket_client.send(NICKNAME_ERROR)
            socket_client.close()
            return False
        else:
            self.users[nickname] = {
                "channel": self.default_channel,
                "socket": socket_client,
                "lock_socket": threading.Lock()}
            self.lock_users.release()

            # Envoi au client du nom du canal par défaut
            socket_client.send(self.default_channel.encode('utf-8'))

        # Ajout de l'utilisateur au canal par défaut
        self.channels[self.default_channel]["users"].add(nickname)
        return True


    def exit(self, nickname: str):
        """
        Pour quitter le serveur IRC proprement.

        :param nickname: Pseudo de l'utilisateur
        """
        sc, lock_sc = self.__socket(nickname)

        # On retire l'utilisateur du canal sur lequel il est connecté
        self.channels[self.users[nickname]["channel"]]["users"].remove(nickname)

        # On supprime l'utilisateur
        self.users.pop(nickname)

        # On ferme la connexion et on arrête le thread
        with lock_sc: sc.close()


    def unknown_cmd(self, nickname: str):
        """
        Permet de signaler au client que la commande soumise est inconnue.

        :param nickname: Pseudo de l'utilisateur
        """
        self.__send(UNKNOWN_CMD_ERROR, nickname)


    def help(self, nickname: str):
        """
        Affiche la liste des commandes disponibles.

        :param nickname: Pseudo de l'utilisateur
        """
        self.__send(self.help_msg, nickname)


    def invite(self, cmd: List[str], nickname: str):
        """
        Invite un utilisateur sur le canal où on se trouve.

        :param cmd: Liste de la commande décomposée selon les espaces
        :param nickname: Pseudo de l'utilisateur
        """
        # Nombre d'arguments invalide
        if len(cmd) != 2:
            self.__send(ARGUMENT_ERROR, nickname)
        else:
            dest_nick = cmd[1]  # Pseudo du destinataire
            # Il ne faut pas que le client destinataire soit supprimé
            # pendant cette section critique
            self.lock_users.acquire()
            # Le destinataire n'existe pas
            if dest_nick not in self.users:
                self.lock_users.release()
                self.__send(NICKNAME_ERROR, nickname)
            else:
                # Canal courant de l'utilisateur invitant
                chan = self.users[nickname]["channel"]
                key = self.channels[chan]["key"]
                invite = f"<{nickname}> Bonjour <{dest_nick}> je t'invite à me rejoindre sur le canal {chan}."
                # Le canal est-il protégé par une clé de sécurité ?
                if key is not None:
                    invite += f"\nMot de passe : [{key}]."
                # Envoi de l'invitation au destinataire
                self.__send(invite.encode('utf-8'), dest_nick)
                self.lock_users.release()


    def join(self, cmd: List[str], nickname: str):
        """
        Permet de rejoindre un canal (protégé éventuellement par une clé).
        Le canal est créé s’il n’existe pas.

        :param cmd: Liste de la commande décomposée selon les espaces
        :param nickname: Pseudo de l'utilisateur
        """
        # Nombre d'arguments invalide
        if not (2 <= len(cmd) <= 3):
            self.__send(ARGUMENT_ERROR, nickname)
        else:
            chan = '#'+cmd[1].replace('#', '')

            key = None
            if len(cmd) == 3:
                key = cmd[2]

            # Création éventuelle du canal
            with self.lock_channels:
                if chan not in self.channels:
                    self.channels[chan] = {"key": key, "users": set()}

            # Connexion au canal
            if self.channels[chan]["key"] == key:
                self.channels[chan]["users"].add(nickname)

                # Déconnexion de l'utilisateur du canal précédent
                if self.users[nickname]["channel"] != chan:
                    self.channels[self.users[nickname]["channel"]]["users"].remove(nickname)

                # Connexion de l'utilisateur au canal choisi
                self.users[nickname]["channel"] = chan

                # Envoi du canal au client
                self.__send(("/join "+chan).encode('utf-8'), nickname)

            # La clé de sécurité est incorrecte
            else:
                self.__send(CHANNEL_KEY_ERROR, nickname)


    def list(self, nickname: str):
        """
        Affiche la liste des canaux sur IRC.

        :param nickname: Pseudo de l'utilisateur
        """
        list_channels = '\n'.join(list(self.channels.keys())).encode('utf-8')
        self.__send(list_channels, nickname)


    def msg(self, cmd: List[str], nickname: str):
        """
        Pour envoyer un message à un utilisateur ou sur un canal (où on est
        présent ou pas). Les arguments canal ou nick sont optionnels.

        :param cmd: Liste de la commande décomposée selon les espaces
        :param nickname: Pseudo de l'utilisateur
        """
        # Nombre d'arguments invalide
        if not (2 <= len(cmd) <= 3):
            self.__send(ARGUMENT_ERROR, nickname)
        else:
            msg = cmd[-1]
            dest_users = []

            # Seul le message a été renseigné ou bien un canal
            if len(cmd) == 2 or cmd[1].startswith('#'):
                chan = (
                    # Canal courant de l'expéditeur
                    self.users[nickname]["channel"] if len(cmd) == 2
                    # Canal renseigné dans la commande
                    else cmd[1])

                if len(cmd) == 3 and cmd[1].startswith('#'):
                    # Est-ce que le canal existe ?
                    if chan not in self.channels:
                        self.__send(CHANNEL_ERROR, nickname)
                        return
                    # On ne peut pas envoyer un message sur un canal privé
                    if self.channels[chan]["key"] is not None:
                        self.__send(CHANNEL_KEY_ERROR, nickname)
                        return

                msg = f"{chan} <{nickname}> "+msg
                # Envoi du message à tous les utilisateurs connectés au canal
                dest_users = self.channels[chan]["users"]

            # Destinataire renseigné sans canal
            else:
                # Est-ce que l'utilisateur existe ?
                if cmd[1] not in self.users:
                    self.__send(NICKNAME_ERROR, nickname)
                msg = f"<{nickname}> "+msg
                dest_users = [cmd[1]]

            # Diffusion du message
            self.__broadcast(msg.encode('utf-8'), dest_users)
