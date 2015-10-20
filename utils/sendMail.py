#!/usr/bin/python

__author__ = 'Rudolf Horvath'

import requests

msg = """Szia Rudolf!

Ez egy python scriptbol inditott uzenet.

Udv,
Python script"""


sub = "Teszt uzenet"
you = "rudolf.official@gmail.com"
me =  "limiere@sendgrid.net"

path = "https://api.sendgrid.com/api/mail.send.json"
token = "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"

header = {"Authorization": "Bearer "+token}
req = {"to": me,
        "subject": sub,
        "text": msg,
        "from": me
        }
result = requests.post(path, req, headers=header)

print result.content