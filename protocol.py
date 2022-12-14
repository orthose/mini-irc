# Constantes pour le protocole de communication entre serveur et client

# Le pseudo choisi par l'utilisateur est déjà utilisé
# L'utilisateur n'existe pas donc on ne peut pas l'inviter
NICKNAME_ERROR = "NICKNAME_ERROR".encode('utf-8')

# Les arguments de la commande sont incorrects
ARGUMENT_ERROR = "ARGUMENT_ERROR".encode('utf-8')

# Le canal n'existe pas
CHANNEL_ERROR = "CHANNEL_ERROR".encode('utf-8')

# La clé de sécurité du canal est incorrecte
CHANNEL_KEY_ERROR = "CHANNEL_KEY_ERROR".encode('utf-8')

# La commande est inconnue
UNKNOWN_CMD_ERROR = "UNKNOWN_CMD_ERROR".encode('utf-8')
