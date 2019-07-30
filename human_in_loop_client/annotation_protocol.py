from twisted.protocols import amp
from twisted.protocols.amp import Argument

import json
class JSON(Argument):
    """ Transfrom json to byte string and retransform it back """
    def toString(self, inObject):
        return json.dumps(inObject, ensure_ascii=False).encode('utf-8')

    def fromString(self, inString):
        return json.loads(inString.decode('utf-8'))


class DeliverPage(amp.Command):
    arguments = []
    response = [(b'text', amp.Unicode())]


class MakePrediction(amp.Command):
    arguments = [(b'text', amp.Unicode())]
    response = [(b'annotation', JSON())]


class DeliverSample(amp.Command):
    arguments = []
    response = [(b'text', amp.Unicode())]


class SaveAnnotation(amp.Command):
    arguments = [(b'annotation', JSON())]
    response =  [(b'done', amp.Unicode())]


class SaveComplicated(amp.Command):
    arguments = [(b'text', amp.Unicode())]
    response =  [(b'done', amp.Unicode())]


class SaveSample(amp.Command):
    arguments = [(b'text', amp.Unicode())]
    response =  [(b'done', amp.Unicode())]
