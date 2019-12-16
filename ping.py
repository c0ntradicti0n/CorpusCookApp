from typing import List

from twisted.internet import reactor

from client.annotation_client import AnnotationClient
from client.annotation_protocol import *
logging.getLogger().setLevel(logging.INFO)

I_as_client = AnnotationClient()

def waiter():
    x = yield
    yield x

back = waiter();
back.__next__()

bla = 123

def forward_proceed(done=''):
    global bla
    print("client callback approached")
    print("waiting now")
    bla = "c"
    print("going")
    reactor.stop()




I_as_client.commander(ProceedLocation=forward_proceed, Command=Ping, text="hallo!")
print (bla)

print(back.send(123));

reactor.run()
print("after reactor run")

