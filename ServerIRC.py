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
        # Contrainte: Les utilisateurs peuvent être supprimés
        self.lock_users = threading.Lock()
        self.users = dict()

        # Dictionnaire des canaux avec ensemble des utilisateurs connectés
        # Simplification: Les canaux ne peuvent pas être supprimés
        self.lock_channels = threading.Lock()
        self.channels = {default_channel: {"key": None, "users": set()}}


    def __socket(self, nick: str) -> Tuple[socket.socket, threading.Lock]:
        """
        Permet d'obtenir le socket et le verrou associé à un client.

        :param nick: Pseudo de l'utilisateur
        :return: (socket, verrou) du client
        """
        return (self.users[nick]["socket"], self.users[nick]["lock_socket"])


    def __send(self, msg: bytes, nick: str, check_nick=False):
        """
        Permet d'envoyer un message à un client en verrouillant son socket.
        Si le socket est brisé alors le message n'est simplement pas envoyé
        et l'erreur n'est pas remontée.

        :param msg: Message binaire à envoyer
        :param nick: Pseudo de l'utilisateur destinataire
        :param check_nick: Si True alors si le client n'existe pas
        aucune erreur n'est remontée sinon une erreur est remontée.

        Par défaut check_nick=False puisqu'un client pour lequel on exécute
        une commande ne peut pas être supprimé car son code est exécuté
        séquentiellement dans un seul thread. Or, il ne pourra être supprimé
        que lors de l'appel à la commande /exit.

        Par contre il faut choisir check_nick=True si on envoie un message
        à un autre utilisateur que l'expéditeur vivant dans un thread séparé
        car il peut potentiellement être supprimé.
        """
        # Il faut s'assurer que le destinataire n'est pas supprimé
        # pendant que l'on récupère son socket
        if check_nick: self.lock_users.acquire()
        # Si le client n'existe pas on ne fait rien
        if not check_nick or nick in self.users:
            sc, lock_sc = self.__socket(nick)
            if check_nick: self.lock_users.release()
            # On verrouille l'accès au socket du client
            with lock_sc:
                try: sc.send(msg)
                # Si le socket est brisé le message n'est pas envoyé
                # L'erreur n'est pas remontée pour éviter d'interrompre le thread
                except BrokenPipeError: pass
            return
        self.lock_users.release()


    def __broadcast(self, msg: bytes, exp_nick: str, dest_users: List[str]):
        """
        Permet de diffuser un message à un ensemble d'utilisateurs.

        :param msg: Message binaire à envoyer
        :param exp_nick: Pseudo de l'expéditeur
        :param dest_users: Pseudo des clients destinataires
        """
        for dest_nick in dest_users: self.__send(msg, dest_nick, check_nick=True)


    def add_user(self, socket_client: socket.socket, nick: str) -> bool:
        """
        Permet d'ajouter un nouvel utilisateur qui vient de se connecter.

        :param socket_client: Prise pour communiquer avec le client
        :param nick: Pseudo de l'utilisateur

        :return: True si le client a bien été ajouté False sinon
        """
        # Enregistrement de l'utilisateur s'il n'existe pas déjà
        # Deux clients choisissant le même nickname ne doivent pas passer
        # en même temps cette section critique
        self.lock_users.acquire()
        if nick in self.users:
            self.lock_users.release()
            socket_client.send(NICKNAME_ERROR)
            socket_client.close()
            return False

        self.users[nick] = {
            "channel": self.default_channel,
            "away_msg": "",
            "socket": socket_client,
            "lock_socket": threading.Lock()}
        self.lock_users.release()

        # Envoi au client du nom du canal par défaut
        socket_client.send(self.default_channel.encode('utf-8'))

        # Ajout de l'utilisateur au canal par défaut
        self.channels[self.default_channel]["users"].add(nick)
        return True


    def exit(self, nick: str):
        """
        Pour quitter le serveur IRC proprement.

        :param nick: Pseudo de l'utilisateur
        """
        sc, lock_sc = self.__socket(nick)

        # On retire l'utilisateur du canal sur lequel il est connecté
        self.channels[self.users[nick]["channel"]]["users"].remove(nick)

        # On supprime l'utilisateur
        # Il faut verrouiller pour ne pas faire échouer l'envoi de message
        with self.lock_users: self.users.pop(nick)

        # On ferme la connexion et on arrête le thread
        with lock_sc: sc.close()


    def unknown_cmd(self, nick: str):
        """
        Permet de signaler au client que la commande soumise est inconnue.

        :param nick: Pseudo de l'utilisateur
        """
        self.__send(UNKNOWN_CMD_ERROR, nick)


    def argument_error(self, nick: str):
        """
        Permet de signaler au client que les arguments de la commande sont incorrects.

        :param nick: Pseudo de l'utilisateur
        """
        self.__send(ARGUMENT_ERROR, nick)


    def away(self, cmd, nick: str):
        """
        Signale son absence quand on nous envoie un message en privé
        (en réponse un message peut être envoyé).
        Une nouvelle commande /away réactive l’utilisateur.

        :param cmd: Liste de la commande décomposée selon les espaces
        :param nick: Pseudo de l'utilisateur
        """
        # Nombre d'arguments invalide
        if len(cmd) > 2:
            self.__send(ARGUMENT_ERROR, nick)
            return

        # L'utilisateur prévient qu'il n'est plus absent
        if len(cmd) == 1 and self.users[nick]["away_msg"] != "":
            self.users[nick]["away_msg"] = ""
        # L'utilisateur prévient qu'il est absent
        else:
            # Message par défaut
            away_msg = "Je suis absent pour le moment."
            # Message personnalisé
            if len(cmd) == 2: away_msg = cmd[1]
            self.users[nick]["away_msg"] = away_msg


    def help(self, nick: str):
        """
        Affiche la liste des commandes disponibles.

        :param nick: Pseudo de l'utilisateur
        """
        self.__send(self.help_msg, nick)


    def invite(self, cmd: List[str], nick: str):
        """
        Invite un utilisateur sur le canal où on se trouve.

        :param cmd: Liste de la commande décomposée selon les espaces
        :param nick: Pseudo de l'utilisateur
        """
        # Nombre d'arguments invalide
        if len(cmd) != 2:
            self.__send(ARGUMENT_ERROR, nick)
            return

        dest_nick = cmd[1] # Pseudo du destinataire
        # Le destinataire n'existe pas
        if dest_nick not in self.users:
            self.__send(NICKNAME_ERROR, nick)
            return

        # Canal courant de l'utilisateur invitant
        chan = self.users[nick]["channel"]

        key = self.channels[chan]["key"]
        invite = f"<{nick}> Bonjour <{dest_nick}> je t'invite à me rejoindre sur le canal {chan}."
        # Le canal est-il protégé par une clé de sécurité ?
        if key is not None:
            invite += f"\nMot de passe : [{key}]."
        # Envoi de l'invitation au destinataire
        self.__send(invite.encode('utf-8'), dest_nick, check_nick=True)


    def join(self, cmd: List[str], nick: str):
        """
        Permet de rejoindre un canal (protégé éventuellement par une clé).
        Le canal est créé s’il n’existe pas.

        :param cmd: Liste de la commande décomposée selon les espaces
        :param nick: Pseudo de l'utilisateur
        """
        # Nombre d'arguments invalide
        if not (2 <= len(cmd) <= 3):
            self.__send(ARGUMENT_ERROR, nick)
            return

        # Reformatage du nom de canal
        chan = '#'+cmd[1].replace('#', '')

        key = None
        if len(cmd) == 3:
            key = cmd[2]

        # Création éventuelle du canal
        with self.lock_channels:
            if chan not in self.channels:
                self.channels[chan] = {"key": key, "users": set()}

        # La clé de sécurité est incorrecte
        if self.channels[chan]["key"] != key:
            self.__send(CHANNEL_KEY_ERROR, nick)
            return

        # Ajout de l'utilisateur au canal
        self.channels[chan]["users"].add(nick)

        # Déconnexion de l'utilisateur du canal précédent
        if self.users[nick]["channel"] != chan:
            self.channels[self.users[nick]["channel"]]["users"].remove(nick)

        # Connexion de l'utilisateur au canal choisi
        self.users[nick]["channel"] = chan

        # Envoi du canal au client
        self.__send(("/join "+chan).encode('utf-8'), nick)


    def list(self, nick: str):
        """
        Affiche la liste des canaux sur IRC.

        :param nick: Pseudo de l'utilisateur
        """
        list_channels = '\n'.join(list(self.channels.keys())).encode('utf-8')
        self.__send(list_channels, nick)


    def msg(self, cmd: List[str], nick: str):
        """
        Pour envoyer un message à un utilisateur ou sur un canal (où on est
        présent ou pas). Les arguments canal ou nick sont optionnels.

        :param cmd: Liste de la commande décomposée selon les espaces
        :param nick: Pseudo de l'utilisateur
        """
        # Nombre d'arguments invalide
        if not (2 <= len(cmd) <= 3):
            self.__send(ARGUMENT_ERROR, nick)
            return

        msg = cmd[-1]
        dest_users = []

        # Seul le message a été renseigné ou bien un canal
        if len(cmd) == 2 or cmd[1].startswith('#'):
            chan = (
                # Canal courant de l'expéditeur
                self.users[nick]["channel"] if len(cmd) == 2
                # Canal renseigné dans la commande
                else cmd[1])

            if len(cmd) == 3 and cmd[1].startswith('#'):
                # Est-ce que le canal existe ?
                if chan not in self.channels:
                    self.__send(CHANNEL_ERROR, nick)
                    return

                # On ne peut pas envoyer un message sur un canal privé
                if self.channels[chan]["key"] is not None:
                    self.__send(CHANNEL_KEY_ERROR, nick)
                    return

            msg = f"{chan} <{nick}> "+msg
            # Envoi du message à tous les utilisateurs connectés au canal
            dest_users = self.channels[chan]["users"]

        # Destinataire renseigné sans canal
        else:
            dest_nick = cmd[1]

            self.lock_users.acquire()
            # Est-ce que le destinataire existe ?
            if dest_nick not in self.users:
                self.lock_users.release()
                self.__send(NICKNAME_ERROR, nick)
                return

            away_msg = self.users[dest_nick]["away_msg"]
            self.lock_users.release()

            # Le destinataire est absent
            if away_msg != "":
                msg = f"<{dest_nick}> "+away_msg
                dest_users = [nick]

            # Le destinataire est présent
            else:
                msg = f"<{nick}> "+msg
                dest_users = [dest_nick]

        # Diffusion du message
        self.__broadcast(msg.encode('utf-8'), nick, dest_users)


    def names(self, cmd, nick):
        """
        Affiche les utilisateurs connectés à un canal. Si le canal n’est pas spécifié,
        affiche tous les utilisateurs de tous les canaux.

        :param cmd: Liste de la commande décomposée selon les espaces
        :param nick: Pseudo de l'utilisateur
        """
        list_names = ""

        # Nombre d'aguments invalide
        if len(cmd) > 2:
            self.__send(ARGUMENT_ERROR, nick)

        # Canal spécifié
        elif len(cmd) == 2:
            chan = '#'+cmd[1].replace('#', '')
            # Est-ce que le canal existe ?
            if chan not in self.channels:
                self.__send(CHANNEL_ERROR, nick)
                return
            list_names = '\n'.join(self.channels[chan]["users"])

        # Pas de canal spécifié
        else:
            list_names = '\n'.join(self.users.keys())

        self.__send(list_names.encode('utf-8'), nick)
