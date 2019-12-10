import glob
from time import time
from typing import List

from flask import request
from flask import Flask

from client import bio_annotation
import shell_commander
from client.annotation_client import AnnotationClient
from client.annotation_protocol import *

app = Flask(__name__)
logging.getLogger().setLevel(logging.INFO)

import json
import config
from config import htmls

I_as_client = AnnotationClient()

@app.route("/paths",  methods=['GET', 'POST'])
def html_paths():
    ''' available files '''

    logging.info("get html paths")
    paths = list(glob.iglob(htmls + '/*.html', recursive=config.recursive))
    return str(paths)

@app.route("/html",  methods=['GET', 'POST'])
def give_html():
    ''' give file '''
    if request.method == 'GET':
        path = request.args['path']
        logging.info("give file " + path)
        try:
            with open( path, 'r+') as f:
                return f.read().encode();
        except FileNotFoundError:
            logging.info("give file " + path)
            return ""
    logging.info("no file path given")
    return ""

@app.route("/docload", methods=["POST"])
def upload():
    uploaded_bytes = request.data
    filename = request.args['filename']
    with open(htmls + filename, 'wb') as f:
        f.write(uploaded_bytes)
    logging.info('file uploaded to folder')
    try:
        path = htmls + filename
        import subprocess
        cmd = """python ./client/paper_reader.py "{path}""""".format(path=path)
        logging.warning('calling command: ' + cmd)
        subprocess.Popen(cmd, shell=True)
    except Exception:
        logging.error("Calling annotation software caused an error, but I will ignore")

    return ""

from client.upmarker import UpMarker
upmarker = UpMarker(_generator="tml")

@app.route("/markup", methods=["POST"])
def markup():
    markedup = '???'
    if request.method == 'POST':
        spans = request.json['spans']
        spans = [list(d.values()) for d in spans]
        text =  request.json['text']
        tokens = text.split()
        annotated_sample = bio_annotation.BIO_Annotation.spans2annotation(tokens=tokens, paired_spans=spans)
        markedup = upmarker.markup_annotation(annotated_sample)
    else:
        logging.error("not a post request")

    return markedup

from twisted.internet.defer import inlineCallbacks


@inlineCallbacks
@app.route("/predict", methods=["POST"])
def predictmarkup():
    spans = []
    if request.method == 'POST':
        text =  request.json['text']
        print ('text', text)

        ret = shell_commander.call_os(MakePrediction, text=text)
        spans = list(bio_annotation.BIO_Annotation.annotation2nested_spans(ret['annotation']))

        spans = [{an[0]:  {
             'kind': an[0],
             'start': float(an[1][0]),
             'end':   float(an[1][1]),
             'able':  True,
             'no': int(set_no)
            } for an in an_set} for set_no, an_set in enumerate (spans)]
    else:
        logging.error("not a post request")

    return json.dumps(spans)


@app.route("/ping/")
def ping():
    class Timer(object):
        def __init__(self, description):
            self.description = description

        def __enter__(self):
            self.start =    time()

        def __exit__(self, type, value, traceback):
            self.end = time()
            print(f"{self.description}: {self.end - self.start}")

    with Timer("ping"):
        ret = shell_commander.call_os(Ping, text='yes')
    return ret


if __name__ == '__main__':
    app.run(port=5000, debug=True)

