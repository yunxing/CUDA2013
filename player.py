#!/usr/bin/python

# This should work in both recent Python 2 and Python 3.
import random
import socket
import json
import struct
import time
import sys

def sample_bot(host, port):
    s = SocketLayer(host, port)

    gameId = None

    while True:
        msg = s.pump()
        if msg["type"] == "error":
            print("The server doesn't know your IP. It saw: " + msg["seen_host"])
            sys.exit(1)
        elif msg["type"] == "request":
            if msg["state"]["game_id"] != gameId:
                gameId = msg["state"]["game_id"]
                print("New game started: " + str(gameId))
            if msg["request"] == "request_card":
                cardToPlay = msg["state"]["hand"][0]
                s.send({"type": "move", "request_id": msg["request_id"],
                    "response": {"type": "play_card", "card": cardToPlay}})
            elif msg["request"] == "challenge_offered":
                s.send({"type": "move", "request_id": msg["request_id"],
                        "response": {"type": "reject_challenge"}})
        elif msg["type"] == "greetings_program":
            print("Connected to the server.")

def loop(player, *args):
    cuda = SocketLayer(*args)
    # fisrt time starting game
    ai_index = get_random_ai_index()
    ai = get_ai(ai_index)
    while True:
        try:
            # proxy the request
            m = cuda.pump()
            if m["type"] == "error":
                print("The server doesn't know your IP. It saw: " + m["seen_host"])
                continue
            if m["type"] == "greetings_program":
                print("Connected to the server.")
                continue

            print "getting %s from the server" % str(m)
            print ""
            ai.send(m)
            reply = ai.pump()
            # update AI
            if m["type"] == "result" and m["result"]["type"] == "game_won":
                if m["result"]["by"] == m["your_player_num"]:
                    ai_won(ai_index)
                else:
                    ai_lost(ai_index)
                ai_index = get_random_ai_index()
                ai = get_ai(ai_index)

            if reply["type"] == "internal":
                continue
            print "sending %s back to server" % str(reply)
            cuda.send(reply)
            print "one roop ends"
            continue
        except KeyboardInterrupt:
            sys.exit(0)
        except Exception as e:
            print(repr(e))
        print "system restarting"
        time.sleep(10)
        print "system restarted"

class SocketLayer:
    def __init__(self, host, port):
        self.s = socket.socket()
        self.s.connect((host, port))

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


def ai_print_results():
    print ""
    print AIs_names
    print AIs_stat
    print "wins"
    print AIs_wins
    print "total"
    print AIs_total
    print ""


def ai_won(ai_index):
    print "ai_won for %s" % AIs_names[ai_index]
    AIs_stat[ai_index] += len(AIs) - 1
    AIs_wins[ai_index] += 1
    AIs_total[ai_index] += 1
    for i in range(len(AIs_stat)):
        if i != ai_index:
            AIs_stat[i] -= 1
            if AIs_stat[i] < 0:
                AIs_stat[i] = 0
    ai_print_results()


def ai_lost(ai_index):
    print "ai_lost for %s" % AIs_names[ai_index]
    AIs_stat[ai_index] -= len(AIs) - 1
    AIs_total[ai_index] += 1
    if AIs_stat[ai_index] < 0:
        AIs_stat[ai_index] = 0
    for i in range(len(AIs_stat)):
        if i != ai_index:
            AIs_stat[i] += 1
    ai_print_results()


def get_random_ai_index():
    total = sum(AIs_stat)
    v = random.randint(0, total)
    print v
    sofar = 0
    for i in range(len(AIs_stat) - 1):
        if v <= sofar + AIs_stat[i + 1]:
            return i
        sofar += AIs_stat[i]
    return len(AIs_stat) - 1


def get_ai(ai_index):
    return AIs[ai_index]

AIs = []
AIs_wins = []
AIs_total = []
AIs_stat = []
AIs_names = []

ALPHA = 100


def add_ai(ip, port, name):
    ai = SocketLayer(ip, port)
    ai.send({"type": "ping"})
    print ai.pump()
    AIs.append(ai)
    AIs_names.append(name)
    AIs_stat.append(ALPHA)
    AIs_wins.append(0)
    AIs_total.append(0)


# add_ai("127.0.0.1", 33333, "yunxing_rule_player")
# add_ai("127.0.0.1", 8889, "dumb player")
# add_ai("10.144.3.173", 33333, "weiwei")
add_ai("10.144.3.174", 33333, "guoxing")



if __name__ == "__main__":
    loop(sample_bot, "cuda.contest", 9999)
