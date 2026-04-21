from kivymd.app import MDApp
from kivymd.uix.textfield import MDTextField
from kivymd.uix.button import MDRaisedButton, MDFillRoundFlatButton
from kivymd.uix.floatlayout import MDFloatLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.card import MDCard
from kivy.uix.screenmanager import Screen
from kivy.storage.jsonstore import JsonStore
from kivy.clock import Clock
import threading
import requests
import os

# Database checking
try:
    from database import DB_URL, GROQ_API_KEY
except ImportError:
    DB_URL = "https://geminiremote-default-rtdb.firebaseio.com"
    GROQ_API_KEY = ""

# --- লগইন স্ক্রিন ক্লাস (Android Compatible) ---
class LoginScreen(Screen):
    def on_enter(self):
        self.app = MDApp.get_running_app()
        self.user_store = JsonStore('user_config.json')
        self.clear_widgets() # স্ক্রিন রিফ্রেশ করার জন্য
        
        self.layout = MDFloatLayout(md_bg_color=(0, 0, 0, 1))
        
        # --- Title ---
        self.layout.add_widget(MDLabel(
            text="REMOTE SYSTEM", halign="center", font_style="H4",
            pos_hint={"center_y": 0.85}, theme_text_color="Primary"
        ))

        # --- Status Card ---
        self.status_card = MDCard(
            orientation='vertical', padding=15, size_hint=(0.85, 0.15),
            pos_hint={"center_x": 0.5, "center_y": 0.7},
            md_bg_color=(0.1, 0.1, 0.1, 1), radius=[15,]
        )
        self.fb_status_lbl = MDLabel(text="Firebase: Checking...", theme_text_color="Hint", font_style="Caption")
        self.groq_status_lbl = MDLabel(text="Groq AI: Checking...", theme_text_color="Hint", font_style="Caption")
        self.status_card.add_widget(self.fb_status_lbl)
        self.status_card.add_widget(self.groq_status_lbl)
        self.layout.add_widget(self.status_card)

        # --- Login / Profile Section ---
        if self.user_store.exists('user'):
            saved_phone = self.user_store.get('user')['user_id']
            self.layout.add_widget(MDLabel(
                text=f"Logged in as: {saved_phone}", halign="center",
                pos_hint={"center_y": 0.55}, theme_text_color="Secondary"
            ))
            
            start_btn = MDFillRoundFlatButton(
                text="OPEN REMOTE CONTROL", pos_hint={"center_x": 0.5, "center_y": 0.45},
                size_hint=(0.8, 0.08), on_release=self.go_to_remote
            )
            self.layout.add_widget(start_btn)
            
            switch_btn = MDRaisedButton(
                text="Logout / Switch Account", pos_hint={"center_x": 0.5, "center_y": 0.35},
                md_bg_color=(0.3, 0.3, 0.3, 1), on_release=self.clear_user
            )
            self.layout.add_widget(switch_btn)
        else:
            self.phone_input = MDTextField(
                hint_text="Enter Mobile Number", helper_text="Your Unique ID",
                pos_hint={"center_x": 0.5, "center_y": 0.5}, size_hint_x=0.8, input_filter="int"
            )
            self.layout.add_widget(self.phone_input)
            
            login_btn = MDRaisedButton(
                text="LOGIN & START", pos_hint={"center_x": 0.5, "center_y": 0.4},
                size_hint=(0.8, 0.08), on_release=self.save_and_start
            )
            self.layout.add_widget(login_btn)

        self.add_widget(self.layout)
        Clock.schedule_once(self.check_services, 1)

    def check_services(self, *args):
        threading.Thread(target=self._check_thread, daemon=True).start()

    def _check_thread(self):
        # Firebase Check
        try:
            fb_res = requests.get(f"{DB_URL}/.json", timeout=5)
            if fb_res.status_code == 200:
                self.fb_status_lbl.text = "Firebase: Connected ✅"
                self.fb_status_lbl.theme_text_color = "Custom"
                self.fb_status_lbl.text_color = (0, 1, 0, 1)
            else:
                self.fb_status_lbl.text = "Firebase: Error ❌"
        except:
            self.fb_status_lbl.text = "Firebase: Offline ❌"

        # Groq Check
        if GROQ_API_KEY:
            try:
                headers = {"Authorization": f"Bearer {GROQ_API_KEY}"}
                gr_res = requests.get("https://api.groq.com/openai/v1/models", headers=headers, timeout=5)
                if gr_res.status_code == 200:
                    self.groq_status_lbl.text = "Groq AI: Active ✅"
                    self.groq_status_lbl.theme_text_color = "Custom"
                    self.groq_status_lbl.text_color = (0, 1, 0.5, 1)
                else:
                    self.groq_status_lbl.text = "Groq AI: Key Error ❌"
            except:
                self.groq_status_lbl.text = "Groq AI: Connection Failed ❌"
        else:
            self.groq_status_lbl.text = "Groq AI: API Key Missing ❌"

    def save_and_start(self, *args):
        phone = self.phone_input.text
        if len(phone) >= 10:
            self.user_store.put('user', user_id=phone)
            # মেইন অ্যাপের আইডি আপডেট করা (যদি প্রয়োজন হয়)
            if hasattr(self.app, 'my_user_id'):
                self.app.my_user_id = phone
            self.go_to_remote()
        else:
            self.phone_input.error = True

    def clear_user(self, *args):
        self.user_store.delete('user')
        self.on_enter() # স্ক্রিন রিফ্রেশ

    def go_to_remote(self, *args):
        # অ্যান্ড্রয়েডে subprocess এর বদলে সরাসরি স্ক্রিন চেঞ্জ
        self.manager.current = 'remote'
