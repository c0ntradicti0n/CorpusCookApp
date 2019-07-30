from typing import Callable, Optional

from helpers.color_logger import *
import pprint


from twisted.internet.protocol import ClientCreator
from twisted.protocols import amp

from kivy.support import install_twisted_reactor

install_twisted_reactor()
from twisted.internet import reactor, protocol

from human_in_loop_client.annotation_protocol import *

import json


def dummy_response(done=''):
    pass

class AnnotationClient:
    def __init__(self, log_everything=True):
        """ Client for not spreading client-server-commands throughout your App.

        Call in your `app`, where the twisted reactor is installed inside kivy with

        from kivy.support import install_twisted_reactor

        something like:

        >>> self.me_as_client = AnnotationClient()

        and then you can call commands from the commands instantiations in `human_in_loop_client/annotation_protocol.py`
        like this:

        >>> self.me_as_client.commander(fun ,MakePrediction, text="I love you. You love me.")

        """
        self.log_everything = log_everything
        self.connection = ClientCreator(reactor, amp.AMP).connectTCP("localhost", 5180)



    def commander(self,
                  ProceedLocation: Optional[Callable] = dummy_response,
                  Command: amp.Command = None,
                  **kwargs):
        """ Its like a bind function between some Server Command and a action on client side.
        You call it like this:

        >>> self.me_as_client.commander(fun ,MakePrediction, text="I love you. You love me.")

        The Command is an amp.Command, defined somewhere as:

        ```
        class MakePrediction(amp.Command):
            arguments = [(b'text', amp.Unicode())]
            response = [(b'prediction', amp.Unicode())]
        ```

        The results of the actions defined for the commands of the protocol are mapped to the `fun` Callable
        as keyword arguments, so if MakePrediction returns some AMP-box with a `prediction` key, the
        fetching `fun` should be defined in the manner of:

        ```
        def fun(prediction=None):
            do0815()
        ```

        :param ProceedLocation: Callable with keyword arguments, that answer to the Commands `response` keywords
        :param Command: AMP-Command inheritant, that defines some command for the server
        :param kwargs: arguments for the Command, mapping to the arguments of the commands

        """
        if not Command:
            raise ValueError('`Command` must be given')

        def error(reason):
            logging.error("Something went wrong")
            logging.error(str(reason))
            reactor.stop()

        def seampless_apply(result):
            if self.log_everything:
                logging.warning(pprint.pformat(result))
            ProceedLocation(**result)
            return result

        def callback(result):
            logging.warning(str(Command))
            for k, warg in kwargs.items():
                logging.warning(k)
                logging.warning(warg)

            result.callRemote(Command, **kwargs).addCallback(seampless_apply).addErrback(error)
            return result

        self.connection.addCallback(callback)

