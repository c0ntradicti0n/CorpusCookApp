from collections import OrderedDict as OD

from kivy.properties import StringProperty, NumericProperty, BooleanProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.recycleview import RecycleView
from kivy.uix.slider import Slider


class ManipulationRecycleViewRow(BoxLayout):
    id = StringProperty()
    kind = StringProperty()
    start = NumericProperty()
    end = NumericProperty()
    length = NumericProperty(30)
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