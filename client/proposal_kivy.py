from kivy.app import App
from kivy.properties import ListProperty, StringProperty, NumericProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.recycleview import RecycleView

#from human_in_loop_client.multislider import SliderX


class ProposalRecycleViewRow(BoxLayout):
    tokens = ListProperty()
    annotation = ListProperty()
    text = StringProperty()
    id = NumericProperty()
    no = NumericProperty()
    app = App.get_running_app()


class ProposalSliderX(SliderX):
    def __init__(self, **kwargs):
        super(SliderX, self).__init__(**kwargs)

    def on_change(self, index, delete_add=None):
        self.get_root_window().children[0].change_proposal_neighbors(self.mirror_index(index), self.mirror_values, delete_add=delete_add)


class ProposalView(RecycleView):
    pass