from kivymd.app import MDApp
from kivy.core.window import Window
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
import subprocess
import os
import speech_recognition as sr # Voice Library

# ১. উইন্ডো কনফিগারেশন
from kivy.config import Config
Config.set('graphics', 'resizable', False)
Config.set('graphics', 'width', '360')
Config.set('graphics', 'height', '740')

Window.size = (360, 740)
FIREBASE_URL = "https://geminiremote-default-rtdb.firebaseio.com"

class MainRemote(MDApp):
    def build(self):
        self.theme_cls.theme_style = "Dark"
        self.layout_store = JsonStore('remote_layout.json')
        self.user_store = JsonStore('user_config.json')
        
        # Unique User ID (Mobile Number) load
        if self.user_store.exists('user'):
            self.my_user_id = self.user_store.get('user')['user_id']
        else:
            self.my_user_id = "Guest_User"
        
        self.root = MDFloatLayout(md_bg_color=(0, 0, 0, 1))
        
        # --- Top Status Bar ---
        self.status_light = MDIconButton(
            icon="circle", theme_icon_color="Custom", icon_color=(1, 0, 0, 1),
            pos_hint={"top": 0.99, "x": 0.02}, icon_size="15sp"
        )
        
        self.id_lbl = MDLabel(
            text=f"ID: {self.my_user_id}", halign="left", font_style="Caption",
            theme_text_color="Custom", text_color=(0, 1, 0.5, 1),
            pos_hint={"top": 0.99, "x": 0.12}, size_hint=(None, None), height="48dp", width="150dp"
        )

        self.login_btn = MDIconButton(
            icon="account-circle", pos_hint={"top": 0.99, "right": 0.88},
            on_release=self.open_login
        )
        
        self.settings_btn = MDIconButton(
            icon="cog", pos_hint={"top": 0.99, "right": 0.98},
            on_release=self.open_editor
        )
        
        # --- Bottom Voice Bar ---
        self.mic_btn = MDIconButton(
            icon="microphone", icon_size="40sp",
            pos_hint={"center_x": 0.5, "center_y": 0.1},
            md_bg_color=(0.15, 0.15, 0.15, 1),
            on_release=self.start_voice_search
        )
        
        self.voice_status = MDLabel(
            text="Tap Mic to Search", halign="center", font_style="Caption",
            theme_text_color="Hint", pos_hint={"center_y": 0.05}
        )

        self.root.add_widget(self.status_light)
        self.root.add_widget(self.id_lbl)
        self.root.add_widget(self.login_btn)
        self.root.add_widget(self.settings_btn)
        self.root.add_widget(self.mic_btn)
        self.root.add_widget(self.voice_status)

        # বাটনগুলো লোড করা
        self.load_ui()
        Clock.schedule_interval(self.check_connection, 5)
        
        return self.root

    def load_ui(self):
        """Layout file theke button load kora"""
        fixed = [self.status_light, self.id_lbl, self.settings_btn, self.login_btn, self.mic_btn, self.voice_status]
        for widget in list(self.root.children):
            if widget not in fixed:
                self.root.remove_widget(widget)

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
            
            lbl = MDLabel(text=data['name'], halign="center", theme_text_color="Custom",
                          text_color=(1, 1, 1, 1), size_hint=(1, None), height="20dp",
                          pos_hint={"center_x": .5, "y": 0}, font_style="Caption")
            
            container.add_widget(btn)
            container.add_widget(lbl)
            self.root.add_widget(container)

    def send_btn_cmd(self, instance, b_id):
        data = self.layout_store.get(b_id)
        cmd = data['action']
        instance.md_bg_color = (1, 1, 1, 0.4)
        Clock.schedule_once(lambda dt: setattr(instance, 'md_bg_color', get_color_from_hex(data.get('bg', '#333333'))), 0.2)
        self.push_to_firebase(cmd)

    def start_voice_search(self, *args):
        self.mic_btn.md_bg_color = (0.8, 0, 0, 1)
        self.voice_status.text = "Listening..."
        threading.Thread(target=self._voice_logic, daemon=True).start()

    def _voice_logic(self):
        r = sr.Recognizer()
        try:
            with sr.Microphone() as source:
                r.adjust_for_ambient_noise(source, duration=0.5)
                audio = r.listen(source, timeout=5)
                # Bangla search chaile: language="bn-BD"
                text = r.recognize_google(audio, language="en-US")
                self.push_to_firebase(f"SEARCH:{text}")
                Clock.schedule_once(lambda dt: self._reset_mic(f"Searching: {text}"), 0)
        except Exception as e:
            Clock.schedule_once(lambda dt: self._reset_mic("Mic Error!"), 0)

    def _reset_mic(self, msg):
        self.mic_btn.md_bg_color = (0.15, 0.15, 0.15, 1)
        self.voice_status.text = msg

    def push_to_firebase(self, cmd):
        path = f"{FIREBASE_URL}/users/{self.my_user_id}/remote_control.json"
        payload = {"command": cmd, "timestamp": int(time.time() * 1000)}
        threading.Thread(target=lambda: requests.patch(path, data=json.dumps(payload), timeout=5), daemon=True).start()

    def check_connection(self, *args):
        def _check():
            try:
                r = requests.get(f"{FIREBASE_URL}/.json", timeout=3)
                self.status_light.icon_color = (0, 1, 0, 1) if r.status_code == 200 else (1, 0, 0, 1)
            except: self.status_light.icon_color = (1, 0, 0, 1)
        threading.Thread(target=_check, daemon=True).start()

    def open_login(self, *args):
        subprocess.Popen(['python', 'login.py'] if os.name == 'nt' else ['python3', 'login.py'])
        self.stop()

    def open_editor(self, *args):
        subprocess.Popen(['python', 'edit.py'] if os.name == 'nt' else ['python3', 'edit.py'])
        self.stop()

if __name__ == "__main__":
    MainRemote().run()
