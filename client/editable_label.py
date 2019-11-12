import kivy
from kivy.input.providers.mtdev import MTDMotionEvent
from regex import regex

kivy.require('1.10.1')

from kivy.uix.floatlayout import FloatLayout
from kivy.uix.textinput import TextInput
from kivy.uix.label import Label
from kivy.base import runTouchApp
from kivy.properties import BooleanProperty, ObjectProperty

class SelectableLabel(TextInput):
    def _key_down(self, key, repeat=False):
        displayed_str, internal_str, internal_action, scale = key

        # handle deletion
        if (self._selection and
                internal_action in (None, 'del', 'backspace', 'enter')):
            if internal_action != 'enter' or self.multiline:
                self.delete_selection()
        elif internal_action == 'del':
            # Move cursor one char to the right. If that was successful,
            # do a backspace (effectively deleting char right of cursor)
            cursor = self.cursor
            self.do_cursor_movement('cursor_right')
            if cursor != self.cursor:
                self.do_backspace(mode='del')
        elif internal_action == 'backspace':
            self.do_backspace()

        # handle action keys and text insertion
        if internal_action is None:
            self.insert_text(displayed_str)
        elif internal_action in ('shift', 'shift_L', 'shift_R'):
            if not self._selection:
                self._selection_from = self._selection_to = self.cursor_index()
                self._selection = True
            self._selection_finished = False
        elif internal_action == 'ctrl_L':
            self._ctrl_l = True
        elif internal_action == 'ctrl_R':
            self._ctrl_r = True
        elif internal_action == 'alt_L':
            self._alt_l = True
        elif internal_action == 'alt_R':
            self._alt_r = True
        elif internal_action.startswith('cursor_'):
            cc, cr = self.cursor
            self.do_cursor_movement(internal_action,
                                    self._ctrl_l or self._ctrl_r,
                                    self._alt_l or self._alt_r)
            if self._selection and not self._selection_finished:
                self._selection_to = self.cursor_index()
                self._update_selection()
            else:
                self.cancel_selection()
        elif internal_action == 'enter':
            self.dispatch('on_text_validate')
            if self.text_validate_unfocus:
                 self.focus = False
        elif internal_action == 'escape':
            self.focus = False
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
        self.textinput = t = SelectableLabel(
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
            # TODO insert inputs, but beware format
            #self.text = instance.text

            self.edit = False

if __name__ == '__main__':

    root = FloatLayout()

    lbl = 'Press here and then try to edit (type a character), but text gets shortened suddenly.'
    label = EditableLabel(text=lbl, size_hint_y=None, height=50, pos_hint={'top': 1})
    root.add_widget(label)

    runTouchApp(root)