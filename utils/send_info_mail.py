#!/usr/bin/env python
import requests
import subprocess
import traceback

print "python script started"

to_mail = "rudolf.official@gmail.com"
from_mail =  "python-limiere@sendgrid.net"

sub = "Openshift cartridge started"

try:
    #print "calling 'ps aux'"
    msg = subprocess.check_output(["ps", "aux"])
    #print "Call ended"
except subprocess.CalledProcessError as e:
    #print "Error at calling ps aux (CalledProcessError): ", e.output
    msg = e.output
except Exception:
    #print "Error at calling ps aux (Uncaught error): ", traceback.format_exc()
    msg = traceback.format_exc()

#print "message: ", msg

path = "https://api.sendgrid.com/api/mail.send.json"
token = "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"

msg = msg.replace("\n", "<br>")
msg = msg.replace("\t", "&nbsp;&nbsp;&nbsp;&nbsp;")
header = {"Authorization": "Bearer "+token}
req = {"to": to_mail,
        "subject": sub,
        "html": msg,
        "from": from_mail
        }

feedback = requests.post(path, req, headers=header)
print "Status info e-mail send: ", ("Succeed" if "success" in feedback.content else "Failed")
__author__ = 'Rudolf'
