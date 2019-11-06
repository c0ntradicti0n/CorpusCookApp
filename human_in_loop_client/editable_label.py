import kivy
from kivy.input.providers.mtdev import MTDMotionEvent
from regex import regex

kivy.require('1.10.1')

from kivy.uix.floatlayout import FloatLayout
from kivy.uix.textinput import TextInput
from kivy.uix.label import Label
from kivy.base import runTouchApp
from kivy.properties import BooleanProperty, ObjectProperty, Clock


#https://github.com/kivy/kivy/wiki/Editable-Label
class EditableLabel(Label):

    edit = BooleanProperty(False)

    textinput = ObjectProperty(None, allownone=True)


    def on_touch_down(self, touch):
        if isinstance(touch, MTDMotionEvent):
            return super(EditableLabel, self).on_touch_down(touch)
        if self.collide_point(*touch.pos) and not self.edit:
            self.edit = True
        return super(EditableLabel, self).on_touch_down(touch)

    unformat_bbcode = r"""(~~~|\[[^\[\]]+\])"""

    def on_edit(self, instance, value):
        if not value:
            if self.textinput:
                self.remove_widget(self.textinput)
            return
        unformatted_text = regex.sub(self.unformat_bbcode, "", self.text)
        self.textinput = t = TextInput(
                text=unformatted_text, size_hint=(None, None),
                font_size=self.font_size, font_name=self.font_name,
                pos=self.pos, size=self.size, multiline=False)
        self.bind(pos=t.setter('pos'), size=t.setter('size'))
        self.add_widget(self.textinput)
        t.bind(on_text_validate=self.on_text_validate, focus=self.on_text_focus)
        #Clock.schedule_once(lambda dt: self.textinput.cancel_selection())

    selection_made = ObjectProperty()

    def on_text_validate(self, instance):
        #self.text = instance.text

        self.selection_made(instance)
        self.edit = False

    def _on_selection_made(self, instance):
        print (instance.text)

    def on_text_focus(self, instance, focus):
        if focus is False:
            self.text = instance.text
            self.edit = False

if __name__ == '__main__':

    root = FloatLayout()

    lbl = 'Press here and then try to edit (type a character), but text gets shortened suddenly.'
    label = EditableLabel(text=lbl, size_hint_y=None, height=50, pos_hint={'top': 1})
    root.add_widget(label)

    runTouchApp(root)