from kivy.clock import Clock
from kivy.core.window import Window
from kivy.input.providers.mtdev import MTDMotionEvent
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.slider import Slider
from more_itertools import pairwise

from helpers.color_logger import *


__all__ = ('SliderX',)

from kivy.properties import AliasProperty, ListProperty


from kivy.lang import Builder

Builder.load_string('''
<CursorLabel>:
    text: ""
    color: 0.9294117647058824, 0.7176470588235294, 0.2901960784313726, 1
    font_size: dp(40)
    
<CursorImage>
    Label:
        id: anzeige
        color: 0.9294117647058824, 0.7176470588235294, 0.2901960784313726, 1
        font_size: dp(40)
''')

class CursorImage(Image):

    def __init__(self, **kwargs):
        super(CursorImage, self).__init__(**kwargs)

class CursorLabel(Label):

    def __init__(self, **kwargs):
        super(CursorLabel, self).__init__(**kwargs)


class SliderX(Slider):
    """Class for creating a Sliderx widget.

    Check module documentation for more details.
    """

    def __init__(self, **kwargs):
        super(Slider, self).__init__(**kwargs)

    crtl = False

    def __len__(self):
        return len(self.values)

    standard_len = None
    mirror = True

    def assert_standard_len(self):
        if self.standard_len and len(self)!=self.standard_len:
            logging.warning('len of slider changed unexpectedly from %d to %d!' % (self.standard_len, len(self)) )
        if len(self.values) != len(set(self.values)):
            logging.warning('values have repetitions: %s' % (str(self.values)) )

        self.standard_len = len(self)

    touched_down = -1

    values = ListProperty([0,2,3,4,5])


    def return_cursors (self):
        self.assert_standard_len()
        return self.children

    def make_cursors(self):
        self.assert_standard_len()

        self.clear_widgets()

        for index, v in enumerate(self.values):
            img = CursorImage()
            img.pos = self.get_single_pos(index)
            img.source=self.cursor_image
            #img.ids.anzeige.text = str(img.pos)
            #print ("image positions", img.pos)
            self.add_widget(img)

        for index, (first, second) in enumerate(pairwise(self.values)):
            label = CursorLabel()
            pos1 = self.get_single_pos(index)
            pos2 = self.get_single_pos(index+1)
            label.pos = [sum(p)/2 for p in  zip(pos1, pos2)]
            label.text = str(index) if not self.mirror else str (self.mirror_index(index))
            self.add_widget(label)

    images = AliasProperty(make_cursors, return_cursors,
                                     bind=('values', 'min', 'max'),
                                     cache=True)

    def __init__(self, **kwargs):
        super(SliderX, self).__init__(**kwargs)

    def mirror(self):
        self.assert_standard_len()
        return sorted(self.max - v for v in self.values)
    def remirror(self, mirror_values):
        self.assert_standard_len()
        self.values = sorted([self.max - v for v in mirror_values])
        return True
    mirror_values = AliasProperty(mirror, remirror,
                                     bind=('values', 'max'))
    def mirror_index(self, mi):
        self.assert_standard_len()
        return len(self.values) -1 - mi

    def calc_pos (self, normal_value):
        print ('xy', self.x, self.y)
        print ('cxy', self.center_x, self.center_y)
        print ('wh', self.width, self.height)

        if self.orientation == 'horizontal':
            pos = (self.x + (normal_value) * self.width*0.95 - self.cursor_width/2,
                    self.center_y - 1.5 * self.cursor_height)
        else:
            pos = (self.center_x - 1.5 * self.cursor_width,
                    self.y  + (normal_value) * self.height*0.95 - self.cursor_height/2)
        #print (pos)
        return pos


    def update_pos(self):
        norm_values = self.get_norm_values()
        return [self.calc_pos(nv) for nv in norm_values]

    def get_single_pos(self, index):
        norm_values = self.get_norm_values()
        return self.calc_pos(norm_values[index])

    def on_min(self, *largs):
        self.assert_standard_len()
        self.values = [self.min if v < self.min else v for v in self.values]

    def on_max(self, *largs):
        self.assert_standard_len()
        self.values = [self.max if v > self.max else v for v in self.values]

    def get_norm_values(self):
        self.assert_standard_len()
        vmin = self.min
        d = self.max - vmin
        if 0==d:
            d = 1
        return [(v - vmin) / float(d) for v in self.values]

    def get_nearest_index_val(self, values,  v, left_only=False, variance=1):
        self.assert_standard_len()

        if left_only:
            for i, val in enumerate(values):
                d = val - v
                if d>0:
                    return i-1
            else:
                return i

        return min(enumerate(abs(val-v) for val in values  ), key=lambda t: t[1])[0]

    def set_norm_values(self, raw_value_s):
        self.assert_standard_len()
        vmin = self.min
        vmax = self.max
        step = self.step
        if isinstance(raw_value_s, (int, float)):
            new_value = min(raw_value_s * (vmax - vmin) + vmin, vmax)
            index = self.get_nearest_index_val(self.values, new_value)
            self.values[index] = round(new_value)
            self.on_change(index)
            return True
        elif isinstance(raw_value_s, list):
            self.values = [round(min(v, vmax)) for v in raw_value_s]
            return True
        else:
            raise NotImplementedError

    values_normalized = AliasProperty(get_norm_values, set_norm_values,
                                     bind=('values', 'min', 'max'),
                                     cache=True)

    def get_values_pos(self):
        self.assert_standard_len()
        padding = self.padding
        x = self.x - self.cursor_width
        y = self.y - self.cursor_height
        nval = self.values_normalized
        if isinstance(nval, int):
            raise ValueError("MultiSlider has to have list values")
        if self.orientation == 'horizontal':
            return [(x + padding + nv * (self.width - padding), y) for nv in nval]
        else:
            return [(x, y + padding + nv * (self.height - padding)) for nv in nval]

    def set_values_pos(self, pos):
        self.assert_standard_len()
        if not isinstance(pos, list):
            padding = self.padding
            x = min(self.right - padding, max(pos[0], self.x + padding))
            y = min(self.top - padding, max(pos[1], self.y + padding))
            if self.orientation == 'horizontal':
                self.values_normalized = (x - self.x - padding) / float(self.width - padding)
            else:
                self.values_normalized = (y - self.y - padding) / float(self.height - padding)

    values_pos = AliasProperty(get_values_pos, set_values_pos,
                              bind=('pos', 'size', 'min', 'max', 'padding',
                                    'values_normalized', 'orientation'),
                              cache=True)

    last_click = None
    def _on_keyboard_down(instance, keyboard, keycode, text, modifiers):
        if len(modifiers) > 0 and modifiers[0] == 'ctrl' :
            SliderX.crtl = True
    def _on_keyboard_up( keycode, text, modifiers):
        SliderX.crtl = False

    def on_touch_down(self, touch):
        if isinstance(touch, MTDMotionEvent):
            return True

        self.assert_standard_len()
        if self.disabled or not self.collide_point(*touch.pos):
            return True
        self.touched_down = touch.pos
        self.values = [min(self.max, v) for v in self.values]
        positions = [v[0] for v in self.values_pos] if self.orientation == 'horizontal' else [v[1] for v in
                                                                                              self.values_pos]
        index = self.get_nearest_index_val(positions,
                                           touch.pos[0] if self.orientation == 'horizontal' else touch.pos[1],
                                           left_only=True, variance = 0.05)
        if index == None:
            return True

        if 'right' in touch.button:
            self.standard_len -= 1
            self.values.remove(self.values[index])
            self.on_change(index-1, delete_add=-1)
        if 'left' in touch.button:
            # values_pos setter acts 'polmorphically'. so if this list is set to a single value, it looks for the nearest one
            if not SliderX.crtl:
                self.values_pos = touch.pos
            else:
                print ("INSERTING!!!")
                val = self.values[index]-1 if not self.mirror_values else self.values[index]+1
                self.values.insert(index, val)
                self.on_change(index, delete_add=1)
        self.last_click = touch.pos
        return True

Window.bind(on_key_down=SliderX._on_keyboard_down)
Window.bind(on_key_up=SliderX._on_keyboard_up)


if __name__ == '__main__':
    from kivy.app import App
    s = Slider(padding=35)
    s.value = 0
    x = SliderX()
    x.step = 1
    x.max = 20
    x.min = 0
    x.orientation='vertical'
    x.values = [0, 5,15, 20]

    class SliderxApp(App):
        def build(self):
            return x

    SliderxApp().run()

