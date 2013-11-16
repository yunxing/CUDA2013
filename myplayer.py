import socket
import json
import struct
import time
import random
import sys
import SocketServer
from termcolor import colored

class Reject:
    def to_json(self):
        return {"type": "reject_challenge"}


class Accept:
    def to_json(self):
        return {"type": "accept_challenge"}


class Play:
    def __init__(self, card):
        self.card = card

    def to_json(self):
        return {"type": "play_card",
                "card": self.card}


class Challenge:
    def to_json(self):
        return {"type": "offer_challenge"}


class Game():
    def __init__(self, id):
        self.id = id
        self.cards_left_num = 104
        self.cards_left = [4 for i in range(0, 14)]
        self.cards_left[0] = 0
        self.first_to_play = False
        self.last_played_card_by_player = 0
        self.f = open('./%d.txt' % id, 'w')

    def set_is_first_to_play(self, b):
        self.first_to_play = b

    def set_last_played_card_by_player(self, c):
        self.last_played_card_by_player = c

    def card_played(self, c):
        self.cards_left_num -= 1
        self.cards_left[c] -= 1

    def write(self, blob):
        self.f.write(blob)

    def finalize(self):
        self.f.close()

    # Utilities
    def query_prob(self, card):
        float(self.cards_left[card]) / self.cards_left_num

    # Fill this out
    def play_card(self, state):
        if state["can_challenge"]:
            return Challenge()
        r = random.choice(state["hand"])
        return Play(r)

    def challenge_offered(self, state):
        return Accept()


def msg_receiver(s):
    s = SocketLayer(s)
    game = None
    while True:
        msg = s.pump()
        if msg["type"] == "error":
            print("The server doesn't know your IP. It saw: " + msg["seen_host"])
            sys.exit(1)
        elif msg["type"] == "request":
            gameId = msg["state"]["game_id"]
            if game:
                if gameId != game.id:
                    print("New game started: " + str(gameId))
                    game.finalize()
                    game = Game(gameId)
            else:
                game = Game(gameId)
            if msg["request"] == "request_card":
                if msg["state"]:
                    game.write(colored('%s\n' % repr(msg), 'green'))

                if "card" in msg["state"]:
                    game.write(colored('''{'type': 'play_card', 'card': %d}'\n''' % msg["state"]["card"],
                                       'green'))
                    game.set_is_first_to_play(False)
                else:
                    game.set_is_first_to_play(True)

                r = game.play_card(msg["state"])

                if isinstance(r, Play):
                    game.card_played(r.card)
                    game.set_last_played_card_by_player(r.card)

                game.write(colored('%s\n' % repr(r.to_json()), 'red'))

                s.send({"type": "move", "request_id": msg["request_id"],
                        "response": r.to_json()})
            elif msg["request"] == "challenge_offered":
                game.write(colored('%s\n' % msg["request"], 'green'))
                r = game.challenge_offered(msg["state"])
                game.write(colored('%s\n' % repr(r.to_json()), 'red'))
                s.send({"type": "move", "request_id": msg["request_id"],
                        "response": r.to_json()})
        elif msg["type"] == "greetings_program":
            print "Connected to the server."
        elif msg["type"] == "ping":
            s.send({"type": "pong"})
        elif msg["type"] == "result":
            if msg["result"]["type"] == "trick_won":
                if game.first_to_play:
                    game.write(colored('''{'type': 'play_card', 'card': %d}'\n''' % msg["result"]["card"],
                                       'green'))
                    game.card_played(msg["result"]["card"])

            if msg["result"]["type"] == "trick_tied":
                if game.first_to_play:
                    game.write(colored('''{'type': 'play_card', 'card': %d}'\n''' % game.last_played_card_by_player,
                                       'green'))
                    game.card_played(game.last_played_card_by_player)
            if msg["result"]["type"] == "hand_done":
                if "by" not in msg["result"]:
                    game.write("You tied a hand!\n")
                elif msg["result"]["by"] == msg["your_player_num"]:
                    game.write("You won one hand\n")
                else:
                    game.write("You lost one hand\n")
                game.write("\n\n")

            print "Ignore result for now"
            s.send({"type": "internal"})


class MyTCPHandler(SocketServer.BaseRequestHandler):
    def handle(self):
        while True:
            try:
                msg_receiver(self.request)
            except KeyboardInterrupt:
                sys.exit(0)

class SocketLayer:
    def __init__(self, socket):
        self.s = socket

    def pump(self):
        """Gets the next message from the socket."""
        sizebytes = self.s.recv(4)
        (size,) = struct.unpack("!L", sizebytes)

        msg = []
        bytesToGet = size
        while bytesToGet > 0:
            b = self.s.recv(bytesToGet)
            bytesToGet -= len(b)
            msg.append(b)

        msg = "".join([chunk.decode('utf-8') for chunk in msg])

        return json.loads(msg)

    def send(self, obj):
        """Send a JSON message down the socket."""
        b = json.dumps(obj)
        length = struct.pack("!L", len(b))
        self.s.send(length + b.encode('utf-8'))

    def raw_send(self, data):
        self.s.send(data)

if __name__ == "__main__":
    SocketServer.TCPServer.allow_reuse_address = True
    server = SocketServer.TCPServer(("0.0.0.0", int(sys.argv[1])), MyTCPHandler)
    server.allow_reuse_address = True
    print "waiting for connection"
    server.serve_forever()
