from pprint import pprint
from typing import List

from helpers.color_logger import *
from collections import Counter, OrderedDict
from time import sleep
from collections import OrderedDict as OD

import kivy

from helpers.nested_dict_tools import flatten
from human_in_loop_client.bio_annotation import BIO_Annotation
from human_in_loop_client.paper_reader import paper_reader

kivy.require('1.9.0')
from kivy.config import Config
Config.set('graphics', 'width', '1000')
Config.set('graphics', 'height', '1000')
#Config.set('input', 'mouse', 'mouse,multitouch_on_demand')
Config.write()
from kivy.core.window import Window
Window.clearcolor = (1, 1, 1, 1)

from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.slider import Slider
#from human_in_loop_client.multislider import SliderX

from kivy.properties import StringProperty, NumericProperty, BooleanProperty, ListProperty, ObservableList
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.recycleview import RecycleView

from human_in_loop_client.upmarker import UpMarker
from human_in_loop_client.client import AnnotationClient
from human_in_loop_client.annotation_protocol import *
from human_in_loop_client.screens_kivy import *
from human_in_loop_client.manipulation_kivy import *
#from human_in_loop_client.proposal_kivy import *
from human_in_loop_client.editable_label import  EditableLabel

class RootWidget(ScreenManager):
    final_version = []
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.me_as_client = AnnotationClient()
        self.upmarker = UpMarker()
        self.pr = paper_reader()
        self.textstore = None

        self.current = "MultiMedia_Screen"

        self.load_something()

        # extra-text window width of annotations to be made
        self.l = 200

        self.landing_screen = "MultiMedia_Screen"
        #self.landing()

        #self.next_page()


    def landing(self):
        self.current = self.landing_screen

    def next_page(self):
        self.me_as_client.commander(ProceedLocation=self.sampler_proceed, Command=DeliverPage)

    def load_mm(self):
        self.current = "MultiMedia_Screen"

    def load_something(self):
        adress = self.ids.multim.ids.address.text
        self.pr.load_text(adress)
        text = self.pr.analyse()
        self.me_as_client.commander(Command=MakeProposals, ProceedLocation=self.get_analysed, text=text)

    def get_analysed(self, proposals:List=[]):
        self.current = "MultiMedia_Screen"

        self.ids.multim.ids.editor.text = \
            self.upmarker.markup_proposal_list(proposals)

    def analyse_paper(self):
        text = self.ids.multim.ids.editor.text
        self.me_as_client.commander(Command=MakeProposals, ProceedLocation=self.proposaler_proceed, text=text)


    def sampler_add_selection(self, input_field):
        # extract selected text and selection information
        full_text = input_field.text
        selected_text =  input_field.selection_text
        selected_text = selected_text.replace('\n', ' ').replace('  ', ' ')
        sel_start = min(input_field.selection_from, input_field.selection_to)
        sel_to = max(input_field.selection_from, input_field.selection_to)

        if not selected_text:
            logging.error('Text must be selected')
            return None

        # get some text to both sides and transform to zero annotations
        self.text_before = full_text[:sel_start].split()[-self.l:]
        self.text_after = full_text[sel_to:].split()[:self.l]
        self.zero_before = [(word, 'O') for word in self.text_before]
        self.zero_after = [(word, 'O') for word in self.text_after]

        # get prediction and let the human annotate it
        self.me_as_client.commander(Command=MakePrediction, ProceedLocation=self.window_sample_proceed, text=selected_text)
        self.user_action = 'rolling'
        self.current = "Manipulation_Screen"

    def window_sample_proceed(self, annotation =[]):
        # update the manipulation screen after making a prediction
        self.annotated_sample = annotation
        self.final_version = self.annotated_sample
        self.update_sliders_from_spans()
        self.display_sample()

    def roll_windows(self, which):
        # roll in windows over annotation and save them all as samples
        whole_annotation = self.zero_before+self.final_version+self.zero_after
        for start in range(
                max(0,len(self.zero_before)+len(self.final_version)-self.l),
                len(self.zero_before) + 1):
            new_annotation = whole_annotation[start:start + self.l]
            logging.info ("creating annotation window from %d to %d with text %s" % (start, start + self.l, new_annotation))
            self.me_as_client.commander(Command=SaveAnnotation, annotation=new_annotation, which=which)
            sleep(0.5)
        self.landing()

    def zero_annotation_selection(self, proposal=None, which=None):
        if not which:
            raise ValueError("Which corpus/model save to?")
        if proposal:
            text=proposal.text
            self.update_from_proposal(proposal)
        else:
            text = self.ids.sampl.ids.html_sample.selection_text.replace('\n', ' ').replace('  ', ' ')

        if not text:
            logging.error('Text must be selected')
            return None

        logging.info("Adding zero sample to library")
        self.me_as_client.commander(Command=ZeroAnnotation, text=text, which=which)

    def sampler_proceed(self, text=''):
        self.ids.sample.ids.html_sample.text = text
        self.me_as_client.commander(Command=MakeProposals, ProceedLocation=self.proposaler_proceed, text=text)

        self.landing()

    def proposaler_proceed(self, proposals=''):
        proposal_cuts = [d['start'] for d in proposals]
        self.ids.proposals.ids.splitter.max = max(proposal_cuts)
        self.ids.proposals.ids.splitter.mirror_values = proposal_cuts

        proposal_data = [OD(p) for p in proposals]
        self.ids.proposals.ids.proposalview.data = self.sort_proposals(proposal_data)
        self.current = "Proposal_Screen"

    def sort_proposals(self, proposal_data):
        for i, p in enumerate(proposal_data):
            p['no'] = i + 1
        return sorted(proposal_data, key=lambda p: p['start'])

    change_values_before = []
    def change_proposal_neighbors(self, index, values, delete_add=None):
        if index<=0:
            index = 1

        indices = [index-1, index, index+1]
        if index >= len(values)-1:
            return

        cuts = (values[index-1], values[index], values[index+1])
        self.change_values_before = cuts
        self.me_as_client.commander(Command=ChangeProposals, ProceedLocation=self.proceed_change_proposals, cuts=cuts, indices=indices, delete_add=delete_add)

    def proceed_change_proposals(self, proposals, indices, delete_add=None):
        all_proposals = sorted(self.ids.proposals.ids.proposalview.data, key=lambda p:p['cut'])
        if delete_add==1:
            all_proposals.insert(min(indices), None)
        all_proposals[min(indices):max(indices)] = proposals
        cuts = [p['cut'] for p in all_proposals]
        if delete_add == -1:
            zero__proposal_indices = [idx for idx, item in enumerate(cuts) if item in cuts[:idx]]
            for z in zero__proposal_indices:
                # When inserting don't delete!
                all_proposals.pop(z-1)
                cuts.pop(z-1)
        self.ids.proposals.ids.splitter.mirror_values = cuts
        self.ids.proposals.ids.proposalview.data = self.sort_proposals(all_proposals)
        if not (len(all_proposals)==len(cuts)):
            logging.error("number of spans does not fit to number of cuts")

    def go_annotating(self):
        self.take_next()
        sleep(0.2)
        self.current = "Annotation_Screen"

    def go_manipulating(self, proposal = None):
        if proposal:
            self.update_from_proposal(proposal)
        else:
            logging.error("there must be given a proposal!")
        self.current = "Manipulation_Screen"

    def update_from_proposal(self, proposal):
        proposal.done = True
        self.final_version = proposal.annotation
        self.annotated_sample = self.final_version
        self.display_sample()
        self.update_sliders_from_spans()
        self.delete(proposal)

    def delete(self, proposal):
        to_del = [d for d in self.ids.proposals.ids.proposalview.data if d['id'] == proposal.id][0]

        self.ids.proposals.ids.proposalview.data.remove(to_del)
        cuts = self.ids.proposals.ids.splitter.mirror_values
        try:
            cuts.remove(to_del['start'])
        except ValueError:
            logging.error('...')
        except KeyError:
            logging.error('cut not in cuts list, can\'t delete')

        self.ids.proposals.ids.splitter.mirror_values = cuts
        if not self.ids.proposals.ids.proposalview.data:
            self.sampler_proceed()

    def ok(self, proposal=None, which=None):
        if not which:
            ValueError("Which corpus save to?")
        if self.user_action == 'rolling':
            self.roll_windows(which="first")
            return
        if proposal:
            self.update_from_proposal(proposal)
        self.me_as_client.commander(Command=SaveAnnotation, annotation=self.final_version, which=which)
        logging.info("Added to corpus")
        if not proposal:
            self.take_next()
        self.landing()

    def annotation_from_here(self):
        if self.user_action == 'rolling':
            self.zero_before = []
            self.roll_windows(which="over")
            return

    def annotation_in_between(self):
        if self.user_action == 'rolling':
            self.zero_before = []
            self.zero_after = []
            self.roll_windows(which="over")
            return

    def complicated_sample(self, proposal=None):
        if proposal:
            self.update_from_proposal(proposal)
        self.complicated(" ".join([word for word, _ in self.final_version]))
        self.take_next()
        self.landing()

    def complicated_selection(self):
        self.complicated(self.ids.sampl.ids.html_sample.selection_text)
        self.landing()

    def complicated(self, text):
        self.me_as_client.commander(Command=SaveComplicated, text=text)
        with open("./complicated.txt", 'a+') as f:
            f.writelines([text])

    def shit(self):
        self.take_next()
        self.landing()

    def manipulate(self):
        self.update_sliders()
        self.update_manip_display()
        self.current = "Manipulation_Screen"

    def update_manip_display(self):
        self.display_sample()

    def adjust_slider_len(self, new_annotation):
        l = len(new_annotation)
        for sl in flatten(flatten(list(self.sliders.values()))):
            sl.range = (0, l)

    def display_sample(self):
        markedup_sentence = self.upmarker.markup_annotation(self.annotated_sample)
        self.ids.annot.ids.sample.text = markedup_sentence
        self.ids.manip.ids.sample.text = markedup_sentence
        self.ids.manip.ids.annotationmanipulationview.refresh_from_data()
        logging.warning(self.ids.manip.ids.annotationmanipulationview.data)


    def update_sliders_from_spans(self):
        paired_spans = list(BIO_Annotation.compute_structured_spans(self.final_version))
        length =  len(self.final_version)

        self.sliders = {}
        self.part_sliders = {}
        self.ids.manip.ids.spansliderview.data = []

        for g, spans in enumerate(paired_spans):
            self.ids.manip.ids.spansliderview.data.append(
                [
                    OD({
                        'kind': kind,
                        'id': str(g)+str(i),
                        'start':start,
                        'end': end,
                        'able':True,
                        'length':length,
                    })
                    for i, (kind, (start, end), annotation) in enumerate(spans)
                ])
        self.ids.manip.ids.spansliderview.data = flatten(self.ids.manip.ids.spansliderview.data)
        self.ids.manip.ids.spansliderview.refresh_from_data()

    def update_sliders(self):
        recent_data = list(self.ids.manip.ids.spansliderview.data_model.data)
        self.update_from_data(recent_data)

    def sort_data(self, data):
        return sorted(data, key=lambda x: x['start'])

    def update_from_data(self, data):
        logging.info(data)
        data = self.sort_data(data)
        self.ids.manip.ids.spansliderview.data = data
        self.ids.manip.ids.spansliderview.refresh_from_data()
        tokens = [t[0] for t in self.final_version]
        paired_spans = BIO_Annotation.pair_spans(data)
        new_annotation = BIO_Annotation.annotation_from_spans(tokens=tokens, paired_spans=paired_spans)
        self.final_version = new_annotation
        self.annotated_sample = new_annotation
        self.check_annotation(new_annotation)
        self.display_sample()

    def more_annotation_of(self, kind):
        length = len(self.final_version)
        self.ids.manip.ids.spansliderview.data.append(
            OD({
                'kind': kind,
                'id': kind,
                'start': length - 2,
                'end': length - 1,
                'able': True,
                'length': length,
            }))

    def less_annotation_of(self, kind):
        try:
            for annotation in self.ids.manip.ids.spansliderview.data[::-1]:
                if annotation['kind'] == kind:
                    data_was = self.ids.manip.ids.spansliderview.data
                    data_was.remove(annotation)
                    self.ids.manip.ids.spansliderview.data = data_was
                    self.ids.manip.ids.spansliderview.refresh_from_data()
                    break
        except ValueError:
            logging.warning('no %s annotation was in used annotations' % kind)

    def check_annotation(self, annotation):
        span_delims = [t[1][0] for t in annotation]
        logging.info(span_delims)
        count = Counter(span_delims)
        if not count['B'] == 2:
            logging.error('Annotation contains not at least the minimum number of annotations!!! %s' % str(count))

    def take_next(self):
        pass

    def got_sample(self, text=''):
        self.sentence = text
        print(text)
        if self.sentence == None:
            App.get_running_app().stop()
            return None

        self.me_as_client.commander(ProceedLocation=self.take_next_rest, Command=MakePrediction, text=text)

    def take_next_rest(self, annotation=''):
        self.annotated_sample = annotation
        self.final_version = self.annotated_sample
        self.update_sliders_from_spans()
        self.display_sample()

Builder.load_file("./human_in_loop_client/HumanInLoop.kv")

class MainApp(App):
    def build(self):
        self.title = "Corpus Cook Application"
        return RootWidget()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


if __name__ == "__main__":
    MainApp().run()