import glob
import urllib
from datetime import datetime
from time import time, sleep
import os
import signal
import subprocess

from bs4 import BeautifulSoup
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
#sys.stdout = LogFile('stdout')
#sys.stderr = LogFile('stderr')


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



@app.route("/save_text", methods=["POST"])
def save_text():
    filename = request.json['filename']
    path = htmls + filename + '.json'
    with open(path, 'w') as f:
        json.dump(request.json, f)
    cmd = f"""python {config.paper_reader} "{path}"  """
    logging.info('calling paper reader: ' + cmd)
    result = subprocess.check_output(cmd, shell=True).decode("utf-8")
    answer = shell_commander.free_result(result)
    return answer


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
            markedup = upmarker.markup_annotation(annotated_sample, start_level=1).replace('"',"'")
            logging.info (markedup)
        except Exception as e:
            raise #markedup = "Could not be annotated +" + str(e)
    else:
        logging.error("not a post request")

    return markedup



@app.route("/predict", methods=["POST"])
def predictmarkup():
    spans = []
    if request.method == 'POST':
        spot, spans = arg_parse(request)
        if not spot['text']:
            logging.warning("empty call")
            ret = []
        else:
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


#Prepare training
#Execution of scripts,
#kill training script
#connect annotations
#throw annotations into HAL



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

@app.route("/science_map", methods=['GET'])
def science_map():
    ''' give file '''
    if request.method == 'GET':
        which = request.args['which']
        logging.info("give log " + which)
        rets = []

        cmd = "cp {cc_corpus_collection_path}/*.conll3 {science_map_corpus_path} ".format(
            cc_corpus_collection_path=config.cc_corpus_collection_path,
            science_map_corpus_path=config.science_map_corpus_path
            )
        logging.debug(str(os.system(cmd)))

        cmd = "export PYTHONPATH=$PYTHONPATH:{science_map_working_dir}; bash {science_map_venv} && python {science_map} {science_map_corpus_path} ".format(
            science_map_working_dir=config.science_map_working_dir,
            science_map_venv=config.science_map_venv,
            science_map=config.science_map,
            science_map_corpus_path = config.science_map_corpus_path
        )
        logging.info("doing sciencemapping" + cmd)
        subprocess.Popen(cmd, cwd=config.science_map_working_dir, shell=True, preexec_fn=os.setsid)

        return json.dumps(rets)
    return []

@app.route("/science_coords", methods=['GET'])
def science_coords():
    ''' give file '''
    if request.method == 'GET':
        which = request.args['which']
        logging.info("give log " + which)
        rets = []


        cmd = "export PYTHONPATH=$PYTHONPATH:{ampligraph_working_dir}; bash {ampligraph_venv} && python {ampligraph} {ampligraph_csv} ".format(
            ampligraph_working_dir=config.ampligraph_working_dir,
            ampligraph_venv=config.ampligraph_venv,
            ampligraph=config.ampligraph,
            ampligraph_csv = config.science_map_csv

        )
        logging.info("mapping graph to coordinates " + cmd)
        subprocess.Popen(cmd, cwd=config.ampligraph_working_dir, shell=True, preexec_fn=os.setsid)

        return json.dumps(rets)
    return []


@app.route("/science_video", methods=['GET'])
def science_video():
    ''' give file '''
    if request.method == 'GET':
        which = request.args['which']
        logging.info("give log " + which)
        rets = []

        cmd = "ls; xvfb-run -a java -jar {hal} -all {all_coordinates} -c {colors} -p {path} -d 100 -m 100000 -v 1.7354  -h blub".format(
            all_coordinates=config.all_coordinates,
            colors=config.ke_colors,
            path=config.ke_path,
            hal=config.hal
        )
        logging.info(f"making video of journey {cmd} in dir {config.video_dir}")
        p = subprocess.Popen(cmd, cwd=config.video_dir, shell=True)
        (output, err) = p.communicate()

        cmd = "ffmpeg -y -i record.mp4 -acodec libfaac -ab 96k -vcodec libx264 -crf 28 -vf scale=700:700  record_compressed.mp4  ;" + \
              f"cp ./record_compressed.mp4 {config.apache_dir}"
        
        logging.info("compressing video\n" + cmd)
        subprocess.Popen(cmd, cwd=config.video_dir, shell=True)

        logging.info ("video finished")


        #cmd = "ffmpeg -y -i record.mp4 record_compressed.ogg "
        #logging.info("compressing video\n" + cmd)
        #subprocess.Popen(cmd, cwd=config.video_dir, shell=True, preexec_fn=os.setsid)

        return json.dumps(rets)
    return []


if __name__ == '__main__':
    import logging, logging.config, yaml

    logging.config.dictConfig(yaml.load(open('logging.conf')))
    logfile = logging.getLogger('file')
    logconsole = logging.getLogger('console')
    logfile.debug("Debug FILE")
    logconsole.debug("Debug CONSOLE")

    app.run(port=5000, debug=True)

