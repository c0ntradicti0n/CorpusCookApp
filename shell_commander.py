_start = "!§$%&/()=?"
_end = "?=(/&%$§"
import subprocess

def substring(whole, sub1, sub2):
    try:
        return whole[whole.index(sub1) + len(sub1): whole.index(sub2)]
    except ValueError:
        logging.error("problems annotating, CorpusCook did not sent dilimited result.")

def call_os (command, **args) :
    cmd = """python shell_commander.py "{command}"  '{args}'  """.format(command=command.__name__, args=json.dumps(args))
    logging.info('calling command: ' + cmd)
    result = subprocess.check_output(cmd, shell=True).decode("utf-8")
    return free_result(result)

def print_return_result(arg):
    print("RETURN" + _start + json.dumps(arg) + _end)
def free_result(result):
    result = substring(result, _start, _end)
    logging.info(result)
    try:
        return json.loads(result)
    except TypeError:
        return {}

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
    class SmartFormatter(argparse.HelpFormatter):

        def _split_lines(self, text, width):
            # this is the RawTextHelpFormatter._split_lines
            if text.startswith('R|'):
                return text[2:].splitlines()
            return argparse.HelpFormatter._split_lines(self, text, width)

    parser = ArgumentParser(description='Call corpuscook commands inside flask. Twisted and flask can deadlock each other. ', formatter_class=SmartFormatter)
    parser.add_argument('command', type=str, help='R|command from the protocol: \n'
                                                  + pprint.pformat(client.annotation_protocol.__commands__,  width=20, indent=1))
    parser.add_argument('arguments', type=str, help='arguments for the command as json (see commandd description)')
    args = parser.parse_args()

    logging.getLogger().setLevel(logging.INFO)

    I_as_client = AnnotationClient()

    def forward_proceed(**kwargs):
        print ("RETURN" + _start+json.dumps(kwargs)+_end)
        reactor.stop()

    logging.warning(f"CALLING {str(eval(args.command))}")
    I_as_client.commander(ProceedLocation=forward_proceed, Command=eval(args.command), **json.loads(args.arguments))
    reactor.run()

if __name__ == "__main__":
    main()


