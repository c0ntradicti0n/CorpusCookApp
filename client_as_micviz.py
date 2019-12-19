import glob
from time import time, sleep
import os

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

import logging, sys

class LogFile(object):
    """File-like object to log text using the `logging` module."""

    def __init__(self, name=None):
        self.logger = logging.getLogger(name)

    def write(self, msg, level=logging.INFO):
        self.logger.log(level, msg)

    def flush(self):
        for handler in self.logger.handlers:
            handler.flush()

logging.basicConfig(level=logging.DEBUG, filename='mylog.log')

# Redirect stdout and stderr
sys.stdout = LogFile('stdout')
sys.stderr = LogFile('stderr')
print ('sdsdsdsdsdsds')


def arg_parse(request):
    args = json.loads(request.data.decode('utf-8'))  # request.json['spot']
    data = args['data']
    spot = args['spot']
    logging.info("\ndata = {data}\n spot= {spot}".format(data=str(data), spot=spot))
    return spot, data

def before_after_prepare (spot):
    # get some text to both sides and transform to zero annotations
    text_before = spot['before'].split()
    text_after = spot['after'].split()
    zero_before = [(word, 'O') for word in text_before]
    zero_after = [(word, 'O') for word in text_after]
    return zero_after, zero_before

def roll_windows(which, zero_before= [], final_version=[], zero_after = [], max_len=200 ):
    # roll in windows over annotation and save them all as samples
    whole_annotation = zero_before+final_version+zero_after
    for start in range(
            max(0,len(zero_before)+len(final_version)-max_len),
            len(zero_before) + 1):
        new_annotation = whole_annotation[start:start + max_len]
        logging.info ("creating annotation window from %d to %d with text %s" % (start, start + max_len, new_annotation))
        yield shell_commander.call_os(SaveAnnotation, annotation=new_annotation, which=which)

def save_zero_sample(request=None, which=None):
    spot, spans = arg_parse(request)
    shell_commander.call_os(ZeroAnnotation, text=spot['text'], which=which)

def save_sample (request, which=None, zero_before=None, zero_after=None, zero_text=False):
    spot, spans = arg_parse(request)
    tokens = spot['text'].split()
    annotated_sample = bio_annotation.BIO_Annotation.spans2annotation(tokens=tokens, paired_spans=spans)
    _zero_before, _zero_after = before_after_prepare(spot)
    if zero_before != None:
        _zero_before = zero_before
    if zero_after != None:
        _zero_after = zero_after
    if zero_text:
        annotated_sample = [(word, 'O') for word in tokens]
    rets = list(
        roll_windows(which=which,
                     zero_before=_zero_before,
                     zero_after=_zero_after,
                     final_version=annotated_sample,
                     max_len=config.max_len))
    return rets


@app.route("/paths",  methods=['GET', 'POST'])
def html_paths():
    ''' available files '''

    logging.info("get html paths")
    paths = list(glob.iglob(htmls + '/*.html', recursive=config.recursive))
    return json.dumps(paths)

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
        cmd = """python ./client/paper_reader.py "{path}" """.format(path=path)
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
        try:
            spot, spans = arg_parse(request)
            tokens = spot['text'].split()
            spans = [ an_set for an_set in spans]
            annotated_sample = bio_annotation.BIO_Annotation.spans2annotation(tokens=tokens, paired_spans=spans)
            markedup = upmarker.markup_annotation(annotated_sample).replace('"',"'")
        except Exception as e:
            markedup = "Could not be annotated +" + str(e)
    else:
        logging.error("not a post request")

    return markedup

@app.route("/predict", methods=["POST"])
def predictmarkup():
    spans = []
    if request.method == 'POST':
        spot, spans = arg_parse(request)
        ret = shell_commander.call_os(MakePrediction, text=spot['text'])
        spans = list(bio_annotation.BIO_Annotation.annotation2nested_spans(ret['annotation']))

        spans = [[
            {
             'kind': an[0],
             'start': float(an[1][0]),
             'end':   float(an[1][1]),
             'able':  True,
             'no': int(set_no),
             '_i': int(_i)

            } for _i, an in enumerate (an_set)] for set_no, an_set in enumerate (spans)]
    else:
        logging.error("not a post request")

    return json.dumps(spans)

@app.route("/textlen", methods=["POST"])
def textlen():
    if request.method == 'POST':
        spot, spans = arg_parse(request)
        ret = len(spot['text'].split())
    else:
        logging.error("not a post request")

    return json.dumps(ret)

@app.route("/ping/", methods=["POST", "GET"])
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

############################################################################################
##--------------------------------- FIRST Annotation commands
# Base model/corpus is named 'first' (primary, ground-one) from top/text-level.
# Nested model/corpus is named 'over' (overall)
# TODO: RENAME?


@app.route("/annotation_from_here", methods=["POST"])
def annotation_from_here():
    rets = []
    if request.method == 'POST':
        rets = save_sample (request, which='first', zero_before=[])
    else:
        logging.error("not a post request")
    return json.dumps(rets)

##---------------------------------


@app.route("/take_it_as_is", methods=["POST"])
def take_it_as_is():
    rets = []
    if request.method == 'POST':
        rets = save_sample(request, which='first', zero_before=[], zero_after=[])
    else:
        logging.error("not a post request")
    return json.dumps(rets)

##----------------------------


@app.route("/zero_annotation_selection_first_corpus", methods=["POST"])
def zero_annotation_selection_first_corpus():
    rets = []
    if request.method == 'POST':
        rets = save_zero_sample(request, which='first')
    else:
        logging.error("not a post request")
    return json.dumps(rets)

##--------------------------------- OVERALL Annotation commands

@app.route("/annotation_in_between", methods=["POST"])
def annotation_in_between():
    rets = []
    if request.method == 'POST':
        rets = save_sample(request, which='over', zero_before=[], zero_after=[])
    else:
        logging.error("not a post request")
    return json.dumps(rets)

#---------------------------------------


@app.route("/zero_annotation_selection_second_corpus", methods=["POST"])
def zero_annotation_selection_second_corpus():
    rets = []
    if request.method == 'POST':
        rets = save_zero_sample(request, which='over')
    else:
        logging.error("not a post request")
    return json.dumps(rets)

#---------------------------------------

@app.route("/migrate_corpus", methods=['GET'])
def migrate_corpus():
    ''' give file '''
    if request.method == 'GET':
        which = request.args['which']
        logging.info("give log " + which)
        rets = []
        cmd = "cp {cc_corpus_path}/*.conll3 {dist_corpus_path}/ ".format(cc_corpus_path=config.cc_corpus_path, dist_corpus_path=config.dist_corpus_path )
        logging.info("copying corpus from corpuscook to trainer by this command\n" + cmd)
        os.system(cmd)
    return json.dumps(rets)

#---------------------------------------

@app.route("/mix_corpus", methods=['GET'])
def mix_corpus():
    ''' give file '''
    if request.method == 'GET':
        which = request.args['which']
        logging.info("give log " + which)
        rets = []
        cmd = "python {mixer} {cc_corpus_path}".format(mixer=config.mixer_path, cc_corpus_path=config.cc_corpus_path)
        logging.info("mixing corpus commits to test/train/valid connl3s\n" + cmd)
        logging.debug(str(os.system(cmd)))
        return json.dumps(rets)
    return []

#---------------------------------------



@app.route("/start_training", methods=['GET'])
def start_training():
    ''' give file '''
    if request.method == 'GET':
        which = request.args['which']
        logging.info("give log " + which)
        rets = []
        cmd = "source {train_venv} ; cd {train_path}; export PYTHONPATH=.; python {train_script} {allennlp_config}".format(
            train_venv = config.train_venv,
            train_path = config.train_path,
            train_script=config.train_script,
            allennlp_config=config.allennlp_config)
        logging.info("start training process, lasts 1h to 3days \n" + cmd)
        import subprocess

        subprocess.call(cmd, shell=True)
    return json.dumps(rets)


#---------------------------------------

@app.route("/migrate_model", methods=['GET'])
def migrate_model():
    ''' give file '''
    if request.method == 'GET':
        which = request.args['which']
        logging.info("give log " + which)
        rets = []

        cmd = "cp {dist_model_path} {cc_model_path}/ ".format(dist_model_path=config.dist_model_path_first, cc_model_path=config.cc_model_path_first )
        logging.info("copying FIRST corpus from corpuscook to trainer by this command\n" + cmd)
        os.system(cmd)

        cmd = "cp {dist_model_path} {cc_model_path}/ ".format(dist_model_path=config.dist_model_path_over, cc_model_path=config.cc_model_path_over )
        logging.info("copying OVER corpus from corpuscook to trainer by this command\n" + cmd)
        os.system(cmd)

    return json.dumps(rets)
#---------------------------------------

def readlines_reverse(filename):
    with open(filename) as qfile:
        qfile.seek(0, os.SEEK_END)
        position = qfile.tell()
        line = ''
        while position >= 0:
            qfile.seek(position)
            next_char = qfile.read(1)
            if next_char == "\n":
                yield line[::-1]
                line = ''
            else:
                line += next_char
            position -= 1
        yield line[::-1]

#---------------------------------------

@app.route("/get_logs",  methods=['GET'])
def get_log():
    ''' give file '''
    if request.method == 'GET':
        which = request.args['which']
        logging.info("give log " + which)
        path = config.log_files[which]
        try:
            rev_lines = readlines_reverse(path)
            return "\n".join(list(rev_lines)).encode()
        except FileNotFoundError:
            logging.info("error with giving log " + path)
            return ""
    logging.info("no file path given")
    return ""

###########################################################################################

if __name__ == '__main__':
    import logging, logging.config, yaml

    logging.config.dictConfig(yaml.load(open('logging.conf')))
    logfile = logging.getLogger('file')
    logconsole = logging.getLogger('console')
    logfile.debug("Debug FILE")
    logconsole.debug("Debug CONSOLE")

    app.run(port=5000, debug=True)

