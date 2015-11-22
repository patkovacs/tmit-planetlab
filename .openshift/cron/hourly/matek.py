#!/usr/bin/env python
import os
import requests
import re

regexp = r'\n<tr>\n.*>(TS48JK)<\/td>\n.*>(.*)<\/td>\n.*>(.*)<\/td>\n.*>(.*)<\/td>\n.*>(.*)<\/td>\n.*>(.*)<\/td>\n.*>(.*)<\/td>\n.*>(.*)<\/td>\n.*>(.*)<\/td>\n.*>(.*)<\/td>\n.*>(.*)<\/td>\n<\/tr>\n'
url_path = "http://www.math.bme.hu/~mogy/oktatas/villamosMSC_2015osz/VillamosMSC_Sztoch_eredmenyek_2015osz.html"
sub = "Matek pontok"

stdout = ""


def main():
    global msg

    if 'OPENSHIFT_REPO_DIR' in os.environ:
        file_name = os.environ['OPENSHIFT_REPO_DIR']+".openshift/cron/matek"
    else:
        file_name = "matek"

    RE_POINTS = re.compile(regexp)

    webpage = requests.get(url_path).text

    match = RE_POINTS.search(webpage)

    header = ["Neptun", "HF1", "HF2", "HF3", "HF4", "HF5",
              "Gyakvez", "ZH1/1", "ZH1/2", "ZH1/3", "ZH1_sum"]

    if match is None:
        log("No match!")
    else:
        log("Matek pontok:")
        for i in range(len(header)):
            log("\t"+header[i]+": "+match.group(i+1))


    with open(file_name, "r") as f:
        prev = f.read()

    if prev != stdout:
        send_mail(stdout, sub)
        print "Sending mail"

    with open(file_name, "w") as f:
        f.write(stdout)


def log(msg):
    global stdout
    stdout += msg + "\n"
    print msg


def send_mail(msg, sub):
    to_mail = "rudolf.official@gmail.com"
    from_mail = "python-limiere@sendgrid.net"
    path = "https://api.sendgrid.com/api/mail.send.json"
    token = "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"

    msg = msg.replace("\n", "<br>")
    msg = msg.replace(" ", "&nbsp;")
    msg = msg.replace("\t", "&nbsp;&nbsp;&nbsp;&nbsp;")

    header = {"Authorization": "Bearer "+token}
    req = {"to": to_mail,
           "subject": sub,
           "html": msg,
           "from": from_mail
           }

    feedback = requests.post(path, req, headers=header)
    #log("Status info e-mail send: %s"% ("Succeed" if "success" in feedback.content else "Failed"))
    return "success" in feedback.content


if __name__ == '__main__':
    main()
