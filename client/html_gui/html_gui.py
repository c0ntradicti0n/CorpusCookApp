#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Coreference resolution server example.
A simple server serving the coreference system.
"""
from __future__ import unicode_literals
from __future__ import print_function

import json
from wsgiref.simple_server import make_server
import falcon

from human_in_loop_client.annotation_protocol import MakeProposals
from human_in_loop_client.client import AnnotationClient
from human_in_loop_client.paper_reader import paper_reader
from human_in_loop_client.upmarker import UpMarker


class AllResource(object):
    def __init__(self):
        self.me_as_client = AnnotationClient()
        self.upmarker = UpMarker()
        self.pr = paper_reader()

    def on_get(self, req, resp):
        self.response = {}

        text_param = req.get_param_as_list("text")
        print("text: ", text_param)

        if text_param is not None:

            self.me_as_client.commander(Command=MakeProposals, ProceedLocation=self.on_get_proceed, text=text_param)

    def on_get_proceed(self, proposals):
        self.upmarker.to_html(proposals)


        if doc._.has_coref:
            mentions = [{'start':    mention.start_char,
                         'end':      mention.end_char,
                         'text':     mention.text,
                         'resolved': cluster.main.text
                        }
                        for cluster in doc._.coref_clusters
                        for mention in cluster.mentions]
            clusters = list(list(span.text for span in cluster)
                            for cluster in doc._.coref_clusters)
            resolved = doc._.coref_resolved
            self.response['mentions'] = mentions
            self.response['clusters'] = clusters
            self.response['resolved'] = resolved

        resp.body = json.dumps(self.response)
        resp.content_type = 'application/json'
        resp.append_header('Access-Control-Allow-Origin', "*")
        resp.status = falcon.HTTP_200

if __name__ == '__main__':
    RESSOURCE = AllResource()
    APP = falcon.API()
    APP.add_route('/', RESSOURCE)
    HTTPD = make_server('0.0.0.0', 8000, APP)
    HTTPD.serve_forever()