from kivymd.app import MDApp
from kivy.core.window import Window
from kivy.uix.screenmanager import ScreenManager, Screen
from kivymd.uix.button import MDIconButton
from kivymd.uix.floatlayout import MDFloatLayout
from kivymd.uix.label import MDLabel
from kivy.storage.jsonstore import JsonStore
from kivy.utils import get_color_from_hex
from kivy.clock import Clock
import threading
import requests
import json
import time
import os
import speech_recognition as sr

# ১. উইন্ডো কনফিগারেশন
from kivy.config import Config
Config.set('graphics', 'resizable', False)
Config.set('graphics', 'width', '360')
Config.set('graphics', 'height', '740')
Window.size = (360, 740)

FIREBASE_URL = "https://geminiremote-default-rtdb.firebaseio.com"

# --- স্ক্রিন ১: মেইন রিমোট কন্ট্রোল ---
class RemoteScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.app = MDApp.get_running_app()
        self.layout = MDFloatLayout(md_bg_color=(0, 0, 0, 1))
        
        # --- Top Status Bar ---
        self.status_light = MDIconButton(
            icon="circle", theme_icon_color="Custom", icon_color=(1, 0, 0, 1),
            pos_hint={"top": 0.99, "x": 0.02}, icon_size="15sp"
        )
        self.id_lbl = MDLabel(
            text=f"ID: Initializing...", halign="left", font_style="Caption",
            theme_text_color="Custom", text_color=(0, 1, 0.5, 1),
            pos_hint={"top": 0.99, "x": 0.12}, size_hint=(None, None), height="48dp", width="150dp"
        )
        self.login_btn = MDIconButton(
            icon="account-circle", pos_hint={"top": 0.99, "right": 0.88},
            on_release=lambda x: self.app.open_login()
        )
        self.settings_btn = MDIconButton(
            icon="cog", pos_hint={"top": 0.99, "right": 0.98},
            on_release=lambda x: self.app.open_editor()
        )

        # --- Bottom Voice Bar ---
        self.mic_btn = MDIconButton(
            icon="microphone", icon_size="40sp", pos_hint={"center_x": 0.5, "center_y": 0.1},
            md_bg_color=(0.15, 0.15, 0.15, 1), on_release=self.app.start_voice_search
        )
        self.voice_status = MDLabel(
            text="Tap Mic to Search", halign="center", font_style="Caption",
            theme_text_color="Hint", pos_hint={"center_y": 0.05}
        )

        self.layout.add_widget(self.status_light)
        self.layout.add_widget(self.id_lbl)
        self.layout.add_widget(self.login_btn)
        self.layout.add_widget(self.settings_btn)
        self.layout.add_widget(self.mic_btn)
        self.layout.add_widget(self.voice_status)
        self.add_widget(self.layout)

# --- স্ক্রিন ২: লগইন স্ক্রিন (placeholder) ---
class LoginScreen(Screen):
    def on_enter(self):
        layout = MDFloatLayout(md_bg_color=(0.1, 0.1, 0.1, 1))
        layout.add_widget(MDLabel(text="Login System (Integrated)", halign="center", theme_text_color="Primary"))
        back_btn = MDIconButton(icon="arrow-left", pos_hint={"top": 0.98, "x": 0.02}, on_release=self.go_back)
        layout.add_widget(back_btn)
        self.add_widget(layout)

    def go_back(self, *args):
        self.manager.current = 'remote'

# --- স্ক্রিন ৩: এডিটর স্ক্রিন (placeholder) ---
class EditScreen(Screen):
    def on_enter(self):
        layout = MDFloatLayout(md_bg_color=(0.1, 0.1, 0.1, 1))
        layout.add_widget(MDLabel(text="Layout Editor (Integrated)", halign="center", theme_text_color="Primary"))
        back_btn = MDIconButton(icon="arrow-left", pos_hint={"top": 0.98, "x": 0.02}, on_release=self.go_back)
        layout.add_widget(back_btn)
        self.add_widget(layout)

    def go_back(self, *args):
        self.manager.current = 'remote'

# --- মেইন অ্যাপ্লিকেশন ক্লাস ---
class MainRemote(MDApp):
    def build(self):
        self.theme_cls.theme_style = "Dark"
        self.layout_store = JsonStore('remote_layout.json')
        self.user_store = JsonStore('user_config.json')

        if self.user_store.exists('user'):
            self.my_user_id = self.user_store.get('user')['user_id']
        else:
            self.my_user_id = "Guest_User"

        # Screen Manager Setup
        self.sm = ScreenManager()
        self.remote_screen = RemoteScreen(name='remote')
        self.sm.add_widget(self.remote_screen)
        self.sm.add_widget(LoginScreen(name='login'))
        self.sm.add_widget(EditScreen(name='edit'))

        # মেইন স্ক্রিনের আইডি আপডেট
        self.remote_screen.id_lbl.text = f"ID: {self.my_user_id}"

        self.load_ui()
        Clock.schedule_interval(self.check_connection, 5)
        return self.sm

    def load_ui(self):
        root_layout = self.remote_screen.layout
        fixed = [self.remote_screen.status_light, self.remote_screen.id_lbl, 
                 self.remote_screen.settings_btn, self.remote_screen.login_btn, 
                 self.remote_screen.mic_btn, self.remote_screen.voice_status]
        
        for widget in list(root_layout.children):
            if widget not in fixed:
                root_layout.remove_widget(widget)

        for key in self.layout_store.keys():
            data = self.layout_store.get(key)
            bx, by = data['pos']
            scale = float(data.get('size', 1.0))
            container = MDFloatLayout(size_hint=(None, None), size=(80*scale, 100*scale), pos=(bx-5, by-20))
            btn = MDIconButton(
                icon=data['icon'], icon_size=f"{30*scale}sp", theme_icon_color="Custom",
                icon_color=get_color_from_hex(data['color']),
                md_bg_color=get_color_from_hex(data.get('bg', '#333333')),
                pos_hint={"center_x": .5, "top": 1},
                on_release=lambda x, b_id=key: self.send_btn_cmd(x, b_id)
            )
            lbl = MDLabel(text=data['name'], halign="center", theme_text_color="Custom", text_color=(1, 1, 1, 1),
                          size_hint=(1, None), height="20dp", pos_hint={"center_x": .5, "y": 0}, font_style="Caption")
            container.add_widget(btn)
            container.add_widget(lbl)
            root_layout.add_widget(container)

    def send_btn_cmd(self, instance, b_id):
        data = self.layout_store.get(b_id)
        cmd = data['action']
        instance.md_bg_color = (1, 1, 1, 0.4)
        Clock.schedule_once(lambda dt: setattr(instance, 'md_bg_color', get_color_from_hex(data.get('bg', '#333333'))), 0.2)
        self.push_to_firebase(cmd)

    def start_voice_search(self, *args):
        self.remote_screen.mic_btn.md_bg_color = (0.8, 0, 0, 1)
        self.remote_screen.voice_status.text = "Listening..."
        threading.Thread(target=self._voice_logic, daemon=True).start()

    def _voice_logic(self):
        r = sr.Recognizer()
        try:
            with sr.Microphone() as source:
                r.adjust_for_ambient_noise(source, duration=0.5)
                audio = r.listen(source, timeout=5)
                text = r.recognize_google(audio, language="en-US")
                self.push_to_firebase(f"SEARCH:{text}")
                Clock.schedule_once(lambda dt: self._reset_mic(f"Searching: {text}"), 0)
        except Exception:
            Clock.schedule_once(lambda dt: self._reset_mic("Mic Error!"), 0)

    def _reset_mic(self, msg):
        self.remote_screen.mic_btn.md_bg_color = (0.15, 0.15, 0.15, 1)
        self.remote_screen.voice_status.text = msg

    def push_to_firebase(self, cmd):
        path = f"{FIREBASE_URL}/users/{self.my_user_id}/remote_control.json"
        payload = {"command": cmd, "timestamp": int(time.time() * 1000)}
        threading.Thread(target=lambda: requests.patch(path, data=json.dumps(payload), timeout=5), daemon=True).start()

    def check_connection(self, *args):
        def _check():
            try:
                r = requests.get(f"{FIREBASE_URL}/.json", timeout=3)
                color = (0, 1, 0, 1) if r.status_code == 200 else (1, 0, 0, 1)
                self.remote_screen.status_light.icon_color = color
            except:
                self.remote_screen.status_light.icon_color = (1, 0, 0, 1)
        threading.Thread(target=_check, daemon=True).start()

    def open_login(self):
        self.root.current = 'login'

    def open_editor(self):
        self.root.current = 'edit'

if __name__ == "__main__":
    MainRemote().run()
