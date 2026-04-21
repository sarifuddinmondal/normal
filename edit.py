from kivymd.app import MDApp
from kivy.core.window import Window
from kivymd.uix.button import MDIconButton, MDRaisedButton, MDFillRoundFlatButton
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.floatlayout import MDFloatLayout
from kivymd.uix.textfield import MDTextField
from kivymd.uix.label import MDLabel
from kivy.uix.scrollview import ScrollView
from kivy.uix.behaviors import DragBehavior
from kivy.storage.jsonstore import JsonStore
from kivy.utils import get_color_from_hex
from kivy.graphics import Color, RoundedRectangle, Line
from kivy.clock import Clock
import subprocess
import os
import time
import threading

# উইন্ডো সাইজ এবং ক্র্যাশ প্রোটেকশন
Window.size = (1100, 700)
Window.minimum_width, Window.minimum_height = 1000, 600

class DraggableBtn(DragBehavior, MDFloatLayout):
    def __init__(self, btn_id, text, action, icon, color, bg, size, pos=(100, 100), **kwargs):
        super().__init__(**kwargs)
        self.btn_id, self.action = btn_id, action
        self.size_hint = (None, None)
        self.scale_val = float(size)
        self.size = (65 * self.scale_val, 65 * self.scale_val)
        self.pos = pos
        self.color_hex, self.bg_hex = color, bg
        self.selected = False

        self.btn = MDIconButton(
            icon=icon, icon_size=f"{28 * self.scale_val}sp",
            theme_icon_color="Custom", icon_color=get_color_from_hex(color),
            md_bg_color=get_color_from_hex(bg), pos_hint={"center_x": .5, "center_y": .5}
        )
        self.add_widget(self.btn)
        self.lbl = MDLabel(text=text, halign="center", font_style="Caption", 
                           theme_text_color="Custom", text_color=(1, 1, 1, 1),
                           pos_hint={"center_x": .5, "center_y": -.35})
        self.add_widget(self.lbl)

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            MDApp.get_running_app().select_button(self)
            self.drag_rectangle = [self.x, self.y, self.width, self.height]
        return super().on_touch_down(touch)

    def update_ui(self):
        self.canvas.after.clear()
        if self.selected:
            with self.canvas.after:
                Color(0, 0.8, 1, 1) 
                Line(rounded_rectangle=(self.x-5, self.y-5, self.width+10, self.height+10, 12), width=1.5)

class RemoteEditor(MDApp):
    def build(self):
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "Cyan"
        self.store = JsonStore('remote_layout.json')
        self.selected_btn = None
        
        self.root = MDFloatLayout(md_bg_color=(0.05, 0.05, 0.05, 1))

        # লেআউট ক্যালকুলেশন
        self.mobile_x, self.mobile_y = 60, 40
        self.fw, self.fh = 340, 680

        self.frame_body = MDFloatLayout(size_hint=(None, None), size=(self.fw + 30, self.fh + 30), pos=(self.mobile_x - 15, self.mobile_y - 15))
        with self.frame_body.canvas.before:
            Color(0.15, 0.15, 0.15, 1)
            RoundedRectangle(pos=self.frame_body.pos, size=self.frame_body.size, radius=[40,])
        
        self.work_area = MDFloatLayout(size_hint=(None, None), size=(self.fw, self.fh), pos=(self.mobile_x, self.mobile_y), md_bg_color=(0, 0, 0, 1))
        with self.work_area.canvas.before:
            Color(0, 0, 0, 1)
            RoundedRectangle(pos=self.work_area.pos, size=self.work_area.size, radius=[30,])

        self.root.add_widget(self.frame_body)
        self.root.add_widget(self.work_area)

        # সাইডবার সেটআপ
        self.setup_sidebar()
        
        Window.bind(on_key_down=self.on_key_press)
        Clock.schedule_once(lambda dt: self.load_data(), 0.5)
        return self.root

    def setup_sidebar(self):
        scroll = ScrollView(size_hint=(None, 1), width="360dp", pos_hint={"right": 1})
        self.sidebar = MDBoxLayout(orientation='vertical', size_hint_y=None, padding=[15, 10], spacing=8, md_bg_color=(0.08, 0.08, 0.1, 1))
        self.sidebar.bind(minimum_height=self.sidebar.setter('height'))
        
        self.sidebar.add_widget(MDLabel(text="AI REMOTE DESIGNER", font_style="Button", halign="center", bold=True, size_hint_y=None, height="40dp"))
        
        self.chat_input = MDTextField(hint_text="Ask AI...", mode="rectangle")
        self.sidebar.add_widget(self.chat_input)
        self.sidebar.add_widget(MDFillRoundFlatButton(text="SEND TO AI", icon="robot", on_release=self.send_to_ai, size_hint_x=1))
        
        # এরর ফিক্স: md_bg_color সরিয়ে দেওয়া হয়েছে
        self.ai_response_box = MDLabel(
            text="AI Ready...", theme_text_color="Custom", text_color=(0, 1, 1, 1),
            font_style="Caption", halign="center", size_hint_y=None, height="80dp"
        )
        self.sidebar.add_widget(self.ai_response_box)

        # বাটন এডিটর অংশ
        self.sidebar.add_widget(MDLabel(text="PROPERTIES", font_style="Caption", size_hint_y=None, height="20dp"))
        self.prop_name = MDTextField(hint_text="Label", mode="rectangle")
        self.prop_action = MDTextField(hint_text="Action", mode="rectangle")
        self.prop_icon = MDTextField(hint_text="Icon Name", mode="rectangle")
        self.prop_color = MDTextField(hint_text="Icon Hex", mode="rectangle")
        self.prop_bg = MDTextField(hint_text="BG Hex", mode="rectangle")
        
        for w in [self.prop_name, self.prop_action, self.prop_icon, self.prop_color, self.prop_bg]:
            self.sidebar.add_widget(w)

        self.sidebar.add_widget(MDFillRoundFlatButton(text="APPLY", icon="check", on_release=self.apply_properties, size_hint_x=1))
        self.sidebar.add_widget(MDFillRoundFlatButton(text="ADD NEW", icon="plus", on_release=self.add_new_btn, size_hint_x=1, md_bg_color=(0.1, 0.5, 0.8, 1)))
        self.sidebar.add_widget(MDFillRoundFlatButton(text="GENERATE 0-9", icon="numeric", on_release=self.add_full_numpad, size_hint_x=1, md_bg_color=(0.4, 0.2, 0.7, 1)))
        self.sidebar.add_widget(MDFillRoundFlatButton(text="DELETE", icon="trash-can", on_release=self.delete_btn, size_hint_x=1, md_bg_color=(0.7, 0.1, 0.1, 1)))
        self.sidebar.add_widget(MDRaisedButton(text="SAVE & RUN", icon="content-save", on_release=self.save_all, size_hint_x=1, md_bg_color=(0, 0.5, 0.2, 1)))

        scroll.add_widget(self.sidebar)
        self.root.add_widget(scroll)

    def send_to_ai(self, *args):
        if self.chat_input.text:
            self.ai_response_box.text = f"AI: Processing '{self.chat_input.text}'"
            self.chat_input.text = ""

    def add_full_numpad(self, *args):
        nums = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0"]
        sx, sy = 50, 220
        count = 0
        for n in nums:
            b_id = f"num_{n}_{int(time.time()*1000)}"
            btn = DraggableBtn(b_id, n, f"KEY_{n}", f"numeric-{n}", "#00FFFF", "#222222", "0.85", 
                              pos=(self.mobile_x + sx + (count * 75), self.mobile_y + sy))
            self.work_area.add_widget(btn)
            count += 1
            if count > 2: count = 0; sy -= 75

    def select_button(self, btn):
        if self.selected_btn: self.selected_btn.selected = False; self.selected_btn.update_ui()
        self.selected_btn = btn
        btn.selected = True; btn.update_ui()
        self.prop_name.text, self.prop_action.text = btn.lbl.text, btn.action
        self.prop_icon.text, self.prop_color.text, self.prop_bg.text = btn.btn.icon, btn.color_hex, btn.bg_hex

    def apply_properties(self, *args):
        if not self.selected_btn: return
        b = self.selected_btn
        b.lbl.text, b.action, b.btn.icon = self.prop_name.text, self.prop_action.text, self.prop_icon.text
        b.color_hex, b.bg_hex = self.prop_color.text, self.prop_bg.text
        b.btn.icon_color, b.btn.md_bg_color = get_color_from_hex(b.color_hex), get_color_from_hex(b.bg_hex)

    def on_key_press(self, window, key, scancode, codepoint, modifiers):
        if key == 115 and 'ctrl' in modifiers: self.save_all(); return True
        if not self.selected_btn: return
        if key == 273: self.selected_btn.y += 4
        elif key == 274: self.selected_btn.y -= 4
        elif key == 276: self.selected_btn.x -= 4
        elif key == 275: self.selected_btn.x += 4
        self.selected_btn.update_ui()

    def add_new_btn(self, *args):
        b_id = f"btn_{int(time.time() * 1000)}"
        btn = DraggableBtn(b_id, "New", "NONE", "circle", "#FFFFFF", "#333333", "1.0", pos=(self.mobile_x + 120, self.mobile_y + 400))
        self.work_area.add_widget(btn); self.select_button(btn)

    def delete_btn(self, *args):
        if self.selected_btn: self.work_area.remove_widget(self.selected_btn); self.selected_btn = None

    def save_all(self, *args):
        self.store.clear()
        for child in self.work_area.children:
            if isinstance(child, DraggableBtn):
                self.store.put(child.btn_id, name=child.lbl.text, action=child.action, icon=child.btn.icon, color=child.color_hex, bg=child.bg_hex, pos=(float(child.x - self.mobile_x), float(child.y - self.mobile_y)), size=child.scale_val)
        threading.Thread(target=self.run_main).start()

    def run_main(self):
        time.sleep(0.2); py = 'python' if os.name == 'nt' else 'python3'
        subprocess.Popen([py, 'main.py']); self.stop()

    def load_data(self):
        for b_id in self.store.keys():
            d = self.store.get(b_id)
            btn = DraggableBtn(b_id, d['name'], d['action'], d['icon'], d['color'], d['bg'], d['size'], (d['pos'][0] + self.mobile_x, d['pos'][1] + self.mobile_y))
            self.work_area.add_widget(btn)

if __name__ == "__main__":
    RemoteEditor().run()
