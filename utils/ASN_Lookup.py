__author__ = 'rudolf'

from lxml import html
import requests
import json
import subprocess

def reverseIP(address):
    temp = address.split(".")
    convertedAddress = str(temp[3]) +'.' + str(temp[2]) + '.' + str(temp[1]) +'.' + str(temp[0])
    return convertedAddress

def main():
    IP_reversed = reverseIP("78.92.184.61")
    querycmd1 = IP_reversed + '.origin.asn.cymru.com'
    response1 = subprocess.Popen(['dig', '-t', 'TXT', querycmd1, '+short'], stdout=subprocess.PIPE).communicate()[0]
    #response1List = response1.split('|')
    #ASN = response1List[0].strip('" ')
    print response1


if __name__ == "__main__":
    main()