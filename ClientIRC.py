import tkinter as tk
import socket


class ClientIRC(tk.Tk):
    """
    Classe fournissant l'interface graphique côté client
    pour interagir plus facilement avec le serveur IRC.
    """
    def __init__(self, socket_client: socket.socket, nick: str, channel: str, welcome: str):
        super().__init__()

        # Configuration de la fenêtre
        self.title("Internet Relay Chat")
        self.configure(bg="white")
        width = int(self.winfo_screenwidth()/1.5)
        height = int(self.winfo_screenheight()/1.5)
        self.geometry(f"{width}x{height}")

        # Zone d'affichage des messages
        self.msg_text = tk.Text(self, bg="white", fg="black", relief="solid")
        self.msg_text.pack(anchor="n", expand=True, fill="both", padx=10, pady=10)
        self.print(welcome)

        # Affichage du canal est de l'utilisateur
        self.channel = tk.StringVar()
        self.channel.set(channel)
        self.channel_label = tk.Label(textvariable=self.channel, bg="white", fg="black")
        self.channel_label.pack(side="left", pady=(0, 11))
        self.nick_label = tk.Label(text=f"<{nick}>", bg="white", fg="black")
        self.nick_label.pack(side="left", pady=(0, 11))

        # Zone de saisie des commandes
        self.cmd = tk.StringVar()
        self.cmd_entry = tk.Entry(self, textvariable=self.cmd,
            bg="white", fg="black", relief="solid")
        self.cmd_entry.pack(expand=True, fill="x", padx=10, pady=(0, 10))

        # Envoi de la commande lorsqu'on presse entrée
        def send_cmd(event):
            cmd = self.cmd.get().strip()
            self.print(cmd)
            self.cmd.set("")
            socket_client.send(cmd.encode("utf-8"))
            if cmd.startswith("/exit"):
                self.destroy()

        self.cmd_entry.bind("<Return>", send_cmd)


    def set_channel(self, channel):
        self.channel.set(channel)


    def print(self, msg: str):
        self.msg_text["state"] = "normal"
        self.msg_text.insert(tk.END, msg+'\n')
        self.msg_text["state"] = "disabled"
        self.msg_text.see("end")
