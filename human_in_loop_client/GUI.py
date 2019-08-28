from helpers.color_logger import *
from collections import Counter
from time import sleep
from collections import OrderedDict as OD

import kivy

from helpers.nested_dict_tools import flatten
from human_in_loop_client.bio_annotation import BIO_Annotation

kivy.require('1.9.0')
from kivy.config import Config
Config.set('graphics', 'width', '2000')
Config.set('graphics', 'height', '1500')
Config.write()
from kivy.core.window import Window
Window.clearcolor = (1, 1, 1, 1)

from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.slider import Slider
from kivy.properties import StringProperty, NumericProperty, BooleanProperty, ListProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.recycleview import RecycleView

from human_in_loop_client.upmarker import UpMarker
from human_in_loop_client.client import AnnotationClient
from human_in_loop_client.annotation_protocol import *


class Annotation_Screen(Screen):
    pass

class Manipulation_Screen(Screen):
    pass


class Proposal_Screen(Screen):
    pass


class Sample_Screen(Screen):
    pass

class ProposalRecycleViewRow(BoxLayout):
    id = StringProperty()
    annotation = ListProperty()
    text = StringProperty()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.main = self.get_root()

    def get_root(self):
        return self.get_root_window().children[0]


class ManipulationRecycleViewRow(BoxLayout):
    id = StringProperty()
    kind = StringProperty()
    start = NumericProperty()
    end = NumericProperty()
    length = NumericProperty()
    able = BooleanProperty()

class AnnotationManipulationRow(BoxLayout):
    kind = StringProperty()

    def more_annotation_of(self, kind):
        self.get_root_window().children[0].more_annotation_of(kind)

    def less_annotation_of(self, kind):
        self.get_root_window().children[0].less_annotation_of(kind)





class SliderView(RecycleView):
    pass

class AnnotationManipulationView(RecycleView):
    pass

class ProposalView(RecycleView):
    pass


class SpanSlider(Slider):
    def on_touch_up(self, touch):
        root = self.get_root_window().children[0]
        boxes = list(self.parent.parent.children)
        new_data = [SpanSlider.collect_data_from_box(b) for b in boxes]
        root.update_from_data(new_data)

    def collect_data_from_box(b):
        return OD({
            'able': b.ids.active_or_not.active,
            'kind': b.kind,
            'start': int(b.ids.start.value),
            'end': int(b.ids.end.value),
            'length': int(b.ids.end.max),
            'id': 'hach'
        })

class RootWidget(ScreenManager):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.me_as_client = AnnotationClient()
        self.upmarker = UpMarker()
        self.textstore = None

        self.current = "Proposal_Screen"

        #self.next_page()

    def next_page(self):
        self.me_as_client.commander(ProceedLocation=self.sampler_proceed, Command=DeliverPage)

    def sampler_add_selection(self):
        text = self.ids.sampl.ids.html_sample.selection_text.replace('\n', ' ').replace('  ', ' ')
        if not text:
            logging.error('Text must be selected')
            return None
        logging.info("Adding sample to library")
        self.me_as_client.commander(Command=SaveSample, text=text)
        self.current = "Sample_Screen"

    def zero_annotation_selection(self):
        text = self.ids.sampl.ids.html_sample.selection_text.replace('\n', ' ').replace('  ', ' ')
        if not text:
            logging.error('Text must be selected')
            return None
        logging.info("Adding zero sample to library")
        self.me_as_client.commander(Command=ZeroAnnotation, text=text)

    def sampler_proceed(self, text=''):
        self.ids.sampl.ids.html_sample.text = text
        self.me_as_client.commander(Command=MakeProposals, ProceedLocation=self.proposaler_proceed, text=text)
        self.current = "Sample_Screen"

    def proposaler_proceed(self, proposals=''):
        print (proposals)
        self.ids.proposals.ids.proposalview.data = \
            [OD(p) for p in proposals if all(k in ['annotation', 'text'] for k in p.keys())]

    def go_annotating(self):
        self.take_next()
        sleep(0.2)
        self.current = "Annotation_Screen"

    def ok(self):
        self.me_as_client.commander(Command=SaveAnnotation, annotation=self.final_version)
        logging.info("Added to corpus")
        self.take_next()
        self.current = "Annotation_Screen"

    def complicated_sample(self):
        self.complicated(" ".join([word for word, _ in self.final_version]))
        self.take_next()
        self.current = "Annotation_Screen"

    def complicated_selection(self):
        self.complicated(self.ids.sampl.ids.html_sample.selection_text)
        self.current = "Sample_Screen"

    def complicated(self, text):
        self.me_as_client.commander(Command=SaveComplicated, text=text)
        with open("./complicated.txt", 'a+') as f:
            f.writelines([text])

    def shit(self):
        self.take_next()
        self.current = "Annotation_Screen"

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
        markedup_sentence = self.upmarker.markup(self.annotated_sample)
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
        self.me_as_client.commander(ProceedLocation=self.got_sample, Command=DeliverSample)

    def got_sample(self, text=''):
        self.sentence = text
        print(text)
        if self.sentence == None:
            logging.info('Thank you for working!')
            App.get_running_app().stop()
            return None

        self.me_as_client.commander(ProceedLocation=self.take_next_rest, Command=MakePrediction, text=text)

    def take_next_rest(self, annotation=''):
        print (annotation)
        self.annotated_sample = annotation
        self.final_version = self.annotated_sample
        self.update_sliders_from_spans()
        self.display_sample()

Builder.load_file("./human_in_loop_client/HumanInLoop.kv")

class MainApp(App):
    def build(self):
        return RootWidget()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


if __name__ == "__main__":
    MainApp().run()