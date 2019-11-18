import base64
import logging
import zlib
import json

from twisted.protocols import amp
from twisted.protocols.amp import Argument

class JSON(Argument):
    """ Transfrom json to byte string and retransform it back """
    def toString(self, inObject):
        return json.dumps(inObject, ensure_ascii=False).encode('utf-8')

    def fromString(self, inString):
        return json.loads(inString.decode('utf-8'))

class JSONB64COMPRESS(Argument):
    """ Transfrom json to byte string and retransform it back """
    def toString(self, inObject):
        encoded = base64.b64encode(
            zlib.compress(
                str(json.dumps(inObject)).encode('ascii')
            )
        )
        l_before = len(json.dumps(inObject).encode('ascii'))
        l_after = len(base64.b64encode(zlib.compress(json.dumps(inObject).encode('ascii'))).decode('utf-8'))
        logging.info('compression: %dkB to %dkB, means to %2.1f%% of the original' % (l_before/1000, l_after/1000, 100/(l_before/l_after)))
        return encoded

    def fromString(self, inString):
        decoded = json.loads(zlib.decompress(base64.b64decode(inString)))
        l_before = len(inString)
        l_after = len(str(decoded))
        logging.info('compression: %dkB to %dkB, means to %2.1f%% of the original' % (l_before/1000, l_after/1000, 100/(l_before/l_after)))

        return decoded

class DeliverPage(amp.Command):
    arguments = []
    response = [(b'text', amp.Unicode())]


class DeliverSample(amp.Command):
    arguments = []
    response = [(b'text', amp.Unicode())]


class ChangeProposals(amp.Command):
    arguments = [(b'cuts', JSONB64COMPRESS()), (b'indices', JSONB64COMPRESS()), (b'delete_add', JSONB64COMPRESS())]
    response = [(b'proposals', JSONB64COMPRESS()), (b'indices', JSONB64COMPRESS()),  (b'delete_add', JSONB64COMPRESS())]

class MakePrediction(amp.Command):
    arguments = [(b'text', amp.Unicode())]
    response = [(b'annotation', JSON())]

class MakeProposals(amp.Command):
    arguments = [(b'text', amp.Unicode())]
    response = [(b'proposals', JSONB64COMPRESS())]


class SaveAnnotation(amp.Command):
    arguments = [(b'annotation', JSON()), (b'which', amp.Unicode())]
    response =  [(b'done', amp.Unicode())]

class SaveComplicated(amp.Command):
    arguments = [(b'text', amp.Unicode())]
    response =  [(b'done', amp.Unicode())]

class SaveSample(amp.Command):
    arguments = [(b'text', amp.Unicode())]
    response =  [(b'done', amp.Unicode())]

class ZeroAnnotation(amp.Command):
    arguments = [(b'annotation', JSON()), (b'which', amp.Unicode())]
    response =  [(b'done', amp.Unicode())]




