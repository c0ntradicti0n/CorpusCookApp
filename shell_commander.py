_start = "!§$%&/()=?"
_end = "?=(/&%$§"

import subprocess

def substring(whole, sub1, sub2):
    print (whole)
    print (whole.index(sub1))
    return whole[whole.index(sub1) + len(sub1) : whole.index(sub2)]
def call_os (command, **args) :
    cmd = """python shell_commander.py "{command}" "{args}" """.format(command=command.__name__, args=str(args))
    logging.info('calling command: ' + cmd)
    result = subprocess.check_output(cmd, shell=True).decode("utf-8")
    return eval(substring(result, _start, _end))

import argparse
import pprint

from twisted.protocols import amp
import client
from argparse import ArgumentParser
from typing import List

from twisted.internet import reactor
from client.annotation_client import AnnotationClient
from client.annotation_protocol import *


def main():
    print ("hallo")
    class SmartFormatter(argparse.HelpFormatter):

        def _split_lines(self, text, width):
            # this is the RawTextHelpFormatter._split_lines
            if text.startswith('R|'):
                return text[2:].splitlines()
            return argparse.HelpFormatter._split_lines(self, text, width)

    parser = ArgumentParser(description='Analyse txt, pdf etc. text files for utterances of differences. ', formatter_class=SmartFormatter)
    parser.add_argument('command', type=str, help='R|command from the protocol: \n'
                                                  + pprint.pformat(client.annotation_protocol.__commands__,  width=20, indent=1))

    parser.add_argument('arguments', type=str, help='arguments for the command as json (see commandd description)')

    args = parser.parse_args()


    logging.getLogger().setLevel(logging.INFO)

    I_as_client = AnnotationClient()

    def forward_proceed(**kwargs):

        print ("RETURN" + _start+str(kwargs)+_end)
        reactor.stop()

    I_as_client.commander(ProceedLocation=forward_proceed, Command=eval(args.command), **eval(args.arguments))
    reactor.run()

if __name__ == "__main__":
    main()


