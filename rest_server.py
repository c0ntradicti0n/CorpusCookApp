from datetime import datetime
from time import time
import os
import signal
import subprocess

from scispacy.abbreviation import AbbreviationDetector

from client import bio_annotation
import shell_commander
from client.annotation_client import RequestAnnotation
from client.annotation_protocol import *

from flask import request
from flask import Flask

from helpers.os_tools import get_filename_from_path
from helpers.str_tools import remove_ugly_chars

app = Flask(__name__)
logging.getLogger().setLevel(logging.INFO)

import json
import config

request_annotation = RequestAnnotation()

import spacy
nlp = spacy.load("en_core_sci_sm")
abbreviation_pipe = AbbreviationDetector(nlp)
nlp.add_pipe(abbreviation_pipe)


def arg_parse():
    args = json.loads(request.data.decode('utf-8'))
    return args


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
    spot, spans = arg_parse()
    shell_commander.call_os(ZeroAnnotation, text=spot['text'], which=which)


def save_sample (request, which=None, zero_before=None, zero_after=None, zero_text=False):
    args = arg_parse()
    tokens = args['spot']['text'].split()
    annotated_sample = bio_annotation.BIO_Annotation.spans2annotation(tokens=tokens, paired_spans=args['spans'])
    _zero_before, _zero_after = before_after_prepare(args['spot'])
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


@app.route("/annotate_certain_json_in_doc_folder", methods=["POST"])
def annotate_json_in_doc_folder():
    filename = request.json['filename']
    path = filename

    with open(path, 'r+') as f:
        data = json.load(f)
    indexed_words = {
        index: word
        for index, word in data['indexed_words'].items()}

    proposals = request_annotation.schedule(command="MakeProposalsIndexed",
                    indexed=indexed_words,
                    text_name=path.replace("/", ""))

    upmarker_css = UpMarker(_generator="css")
    css = upmarker_css.markup_proposal_list(proposals, _indexed_words=indexed_words)
    filename = remove_ugly_chars(get_filename_from_path(path))

    css_path = config.apache_css_dir + filename + ".css"

    with open(css_path, 'w', encoding="utf8") as f:
        f.write(css)

    logging.info(f"css written to {css_path}")
    return None


from client.upmarker import UpMarker
upmarker_html = UpMarker(_generator="tml")


@app.route("/markup", methods=["POST"])
def markup():
    args = arg_parse()
    tokens, spans = args['data']
    spans = [annotation_span for annotation_span in spans]
    annotated_sample = bio_annotation.BIO_Annotation.spans2annotation(tokens=tokens, paired_spans=spans)
    markedup = upmarker_html.markup_annotation(annotated_sample, start_level=1).replace('"',"'")
    return markedup


@app.route("/predict", methods=["POST"])
def predict():
    args = arg_parse()
    if not args['spot']['text']:
        logging.warning("empty call")
        ret = []
    else:
        request = request_annotation.schedule(command="MakePrediction", text=args['spot']['text'])

    spans = list(bio_annotation.BIO_Annotation.annotation2nested_spans(request['annotation']))

    spans = [[
        {
         'kind': an[0],
         'start': float(an[1][0]),
         'end':   float(an[1][1]),
         'able':  True,
         'no': int(set_no),
         '_i': int(_i)
        } for _i, an in enumerate (an_set)] for set_no, an_set in enumerate (spans)]

    return json.dumps(spans)

@app.route("/tokenize", methods=["POST"])
def tokenize():
    args = arg_parse()
    doc = nlp(args['spot']['text'])
    tokens = [token.text for token in doc]
    return json.dumps(tokens)

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


@app.route("/annotation_around", methods=["POST"])
def annotation_around():
    rets = []
    if request.method == 'POST':
        rets = save_sample (request, which='first')
    else:
        logging.error("not a post request")
    return json.dumps(rets)

##---------------------------------


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
        cmd = "cp {cc_corpus_path}/*.conll3 {dist_corpus_path}/".format(
            cc_corpus_path=config.cc_corpus_collection_path,
            dist_corpus_path=config.dist_corpus_path)
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

        subfolder = str(datetime.now()).replace(" ", "_")
        cmd = "mkdir {cc_corpus_collection_path}/{subfolder}; " \
              "cp {cc_corpus_working_path}/*.conll3 {cc_corpus_collection_path}/{subfolder}/ ".format(
            cc_corpus_collection_path=config.cc_corpus_collection_path,
            cc_corpus_working_path=config.cc_corpus_working_path,
            dist_corpus_path=config.dist_corpus_path,
            subfolder=subfolder)
        logging.debug(str(os.system(cmd)))

        cmd = "export PYTHONPATH=$PYTHONPATH:{mixer_working_dir}; bash {corpuscook_venv} && python {mixer} {cc_corpus_path}".format(
            mixer_working_dir=config.mixer_working_dir,
            corpuscook_venv=config.corpuscook_venv,
            mixer=config.mixer_path,
            cc_corpus_path=config.cc_corpus_collection_path)
        logging.info("mixing corpus commits to test/train/valid connl3s\n" + cmd)
        subprocess.Popen(cmd, cwd=config.mixer_working_dir, shell=True, preexec_fn=os.setsid)

        return json.dumps(rets)
    return []

#---------------------------------------


train_process = []
@app.route("/start_training", methods=['GET'])
def start_training():
    global train_process
    ''' give file '''
    if request.method == 'GET':
        which = request.args['which']
        logging.info("give log " + which)
        rets = []
        cmd = "bash {train_venv_python} && " \
              "python {train_script} {allennlp_config} > {train_log}".format(
            train_venv_python = config.train_venv_python,
            train_script=config.train_script,
            train_path=config.train_path,
            train_log=config.train_log,
            allennlp_config=config.allennlp_config)


        logging.info("start training process, lasts 1h to 3days \n" + cmd)

        proc = subprocess.Popen(cmd, cwd=os.path.realpath(config.train_path), shell=True, preexec_fn=os.setsid)
        train_process.append(proc)
        logging.info("PID of subprocess is: " + str(os.getpgid(proc.pid)))
    return json.dumps(rets)

@app.route("/stop_training", methods=['GET'])
def stop_training():
    global train_process
    print ("killing", train_process)

    ''' give file '''
    if request.method == 'GET':

        for proc in train_process:
            logging.info("killing {p}".format(p=str(proc)))
            if train_process:
                os.killpg(os.getpgid(proc.pid), signal.SIGTERM)

    train_process = []

    rets = []
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

#---------------------------------------

@app.route("/get_corpus_content",  methods=['GET'])
def get_corpus_content():
    ''' give file '''
    if request.method == 'GET':
         content = autocorpus.contains()
         return upmarker.upmark(content)
    return ""


if __name__ == '__main__':
    app.debug = True
    app.run(port=config.app_port, debug=True, use_reloader=False)

