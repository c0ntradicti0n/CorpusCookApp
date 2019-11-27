import glob
import logging
from flask import request
from flask import Flask, jsonify, make_response
import requests
import os
import simplejson as json

app = Flask(__name__)
logging.getLogger().setLevel(logging.INFO)


import config
from config import htmls


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
        cmd = "python ./client/paper_reader.py '{path}'".format(path=path)
        logging.warning('calling command: ' + cmd)
        subprocess.Popen(cmd, shell=True)
    except Exception:
        logging.error("Calling annotation software caused an error, but I will ignore")

    return ""

if __name__ == '__main__':
    app.run(port=5000, debug=True)