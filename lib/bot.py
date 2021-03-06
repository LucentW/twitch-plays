from ircbot import Irc
from game import Game
from misc import pp, pbot, pbutton
from control import Control

import time
import threading
import Queue

import operator

import web as web

exitFlag = 0

class Bot:

    def __init__(self, config):
        self.config = config
        self.game = Game()
        self.queue = Queue.Queue(0)
        pp("Initiating Irc Thread")
        self.c1 = Control(1, "Controller-1", self.config, self.queue, Irc.from_config(self.config, self.queue).start)
        self.c1.daemon = True
        self.c1.start()
        pp("Initiating Tornado Thread")
        self.c2 = Control(2, "Controller-2", self.config, self.queue, web.run)
        self.c2.daemon = True
        self.c2.start()

    def to_web(self, msg):
        web.send(msg)

    def run(self):
        pp("Starting Monitoring Loop")
        last_start = time.time()
        mode = False
        if self.config["anarchy-democracy"]["enabled"]:
            vote_size = self.config["anarchy-democracy"]["size"]
            vote_state = int(round(vote_size / 2))
        if self.config["polling"]["enabled"] or self.config["anarchy-democracy"]["enabled"]:
            polling = time.time()
            tick = self.config["polling"]["time"]
            poll = {"a":0, "b":0, "up":0, "down":0, "left":0, "right":0, "start":0, "select":0}
        while not exitFlag:
            if self.config["polling"]["enabled"] or mode and time.time() > (polling + tick):
                polling = time.time()
                turn = max(poll.iteritems(), key=operator.itemgetter(1))[0]
                if poll[turn] != 0:
                    self.to_web({"endpoll": {"winner": turn}})
                    self.game.push_button(turn)
                poll = dict.fromkeys(poll, 0)
                self.to_web({"polling": {"poll": 0}})

            if not self.queue.empty():
                job = self.queue.get()
                button = job["msg"]
                user = job["user"].capitalize()
                print (pbutton(user, button))
                if self.config["anarchy-democracy"]["show"]:
                    self.to_web({"button": {"user":user, "button":button, "formated": pbutton(user, button)}})
                elif button != "anarchy" and button != "democracy":
                    self.to_web({"button": {"user":user, "button":button, "formated": pbutton(user, button)}})                    
                if self.config['start_throttle']['enabled'] and button == 'start':   
                    if time.time() - last_start < self.config['start_throttle']['time']:
                        continue
                    last_start = time.time()
                if self.config["anarchy-democracy"]["enabled"]:
                    if button == "anarchy" and vote_state != 0:
                        vote_state -= 1
                        if mode and vote_state < vote_size * 0.50:
                            mode = False
                            print "Set mode to anarchy."
                    if button == "democracy" and vote_state < vote_size:
                        vote_state += 1
                        if not mode and vote_state > vote_size * 0.80:
                            mode = True
                            print "Set mode to democracy." 
                    self.to_web({"anarchy_democracy": {"mode": mode, "size": vote_size, "state": vote_state}})
                    if button == "anarchy" or button == "democracy":
                        continue
                if self.config["polling"]["enabled"] or mode:
                    poll[button] += 1
                    poll_sorted = dict((k, v) for k, v in poll.items() if v > 0)
                    poll_sorted = sorted(poll_sorted.iteritems(), key=lambda x:x[1], reverse=True)[:6] 
                    self.to_web({"polling": {"poll": poll_sorted}})
                else:
                    self.game.push_button(button)
