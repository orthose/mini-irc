# mini-irc
Projet de réalisation d'un IRC (Internet Relay Chat) basique avec une architecture centralisée.

## Exécution
Il faut commencer par lancer le serveur
en précisant l'adresse de l'hôte et le port.
```shell
python3 server.py localhost 9999
```

Les clients peuvent ensuite se connecter au serveur en précisant le pseudo du client,
l'adresse de l'hôte et le port du serveur.
Si l'option `--terminal` est ajoutée alors l'interface sera en console.
Sinon une fenêtre graphique s'ouvre.
l'utilisation de `rlwrap` est facultative mais permet une meilleure ergonomie
de la saisie de commandes en console avec par exemple la possibilité de naviguer
dans l'historique.
```shell
rlwrap python3 irc.py maxime localhost 9999 --terminal
```

# Utilisation
Les clients entrent des commandes pour communiquer aux travers de canaux
ou dans des conversations privées.

Pour afficher la liste des commandes disponibles tapez `/help`.
Ci-après des exemples concrets d'utilisation des commandes.
* `/msg "Hello World!"` envoie le message `Hello World!` dans le canal courant.
* `/msg amelie "Hello Amelie!"` envoie le message `Hello Amelie!` à l'utilisateur `amelie`.
* `/msg #holidays "I love the sun."` envoie le message `I love the sun.` sur la canal `#holidays`.
* `/join holidays` permet de rejoindre ou créer le canal `#holidays`.
* `/join holidays 123` permet de rejoindre ou créer le canal `#holidays`
en renseignant la clé de sécurité `123`.
* `/invite amelie` permet d'inviter l'utilisateur `amelie` sur le canal où on se trouve.
* `/names holidays` permet d'afficher la liste des utilisateurs connectés au canal `#holidays`.
