import os
import sys
from cryptography.fernet import Fernet
import json

### Добавь здесь модули нужные твоей программе ###
import pygame
import sounddevice as sd
from pynput.keyboard import Listener
from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtCore import QFile, QTextStream
from PyQt5.QtWidgets import QApplication
from data import ui_preferences
from data import ui_hotkeys
from data import ui_sundpood
from data import ui_overlay
from data import keys
### ^^^                                    ^^^ ###

# Chiave di crittografia fissa - Questa è una chiave Fernet valida
KEY = b'8jtTR9QcD5GEfaWxJ-tZ8dQjQBMGgwq_w-jnYnUJMjM='

# Funzione di decrittazione
def decrypt(filename, key):
    # Расшифруем файл и записываем его
    f = Fernet(key)
    with open(filename, 'rb') as file:
        encrypted_data = file.read()
        
    decrypted_data = f.decrypt(encrypted_data)
    
    return decrypted_data.decode('utf-8')

# Funzioni JSON robuste per gestire file vuoti
def safe_jsonread(file):
    '''
    Safely read JSON file, handling empty files
    '''
    try:
        with open(file, "r", encoding='utf-8') as read_file:
            content = read_file.read().strip()
            if not content:  # Handle empty file
                return {}
            return json.loads(content)
    except (json.JSONDecodeError, FileNotFoundError):
        return {}

def safe_jsonwrite(file, data):
    '''
    Safely write to JSON file
    '''
    with open(file, 'w', encoding='utf-8') as write_file:
        write_file.write(json.dumps(data))

if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    # Create a namespace to hold our globals
    namespace = {
        'app': app,
        '__name__': '__main__',
        'safe_jsonread': safe_jsonread,
        'safe_jsonwrite': safe_jsonwrite,
        'KEY': KEY,  # Aggiungiamo la chiave al namespace
        **globals()
    }
    
    # Patch the jsonread and jsonwrite functions in the namespace
    # This is crucial - we're replacing the original functions with our safe versions
    namespace['jsonread'] = safe_jsonread
    namespace['jsonwrite'] = safe_jsonwrite
    
    # Check if settings.json exists and is valid, if not create it
    settings_file = 'settings.json'
    if not os.path.exists(settings_file) or os.path.getsize(settings_file) == 0:
        # Create default settings
        default_settings = {
            'sounds': [],
            'hotkeys': {},
            'Theme': 'None',
            'KEYS_CMD': {
                'select_move_up': ' ',
                'select_move_down': ' ',
                'select_move_left': ' ',
                'select_move_right': ' ',
                'play_sound': ' ',
                'stop_sound': ' '
            }
        }
        safe_jsonwrite(settings_file, default_settings)
    else:
        # Validate existing settings file
        try:
            # Try to read the file to ensure it's valid JSON
            test_read = safe_jsonread(settings_file)
            # If it's empty or invalid, recreate it
            if not test_read:
                default_settings = {
                    'sounds': [],
                    'hotkeys': {},
                    'Theme': 'None',
                    'KEYS_CMD': {
                        'select_move_up': ' ',
                        'select_move_down': ' ',
                        'select_move_left': ' ',
                        'select_move_right': ' ',
                        'play_sound': ' ',
                        'stop_sound': ' '
                    }
                }
                safe_jsonwrite(settings_file, default_settings)
        except Exception as e:
            print(f"Error validating settings file: {e}")
            # Recreate the settings file if there's an issue
            default_settings = {
                'sounds': [],
                'hotkeys': {},
                'Theme': 'None',
                'KEYS_CMD': {
                    'select_move_up': ' ',
                    'select_move_down': ' ',
                    'select_move_left': ' ',
                    'select_move_right': ' ',
                    'play_sound': ' ',
                    'stop_sound': ' '
                }
            }
            safe_jsonwrite(settings_file, default_settings)
    
    # Utilizziamo direttamente il file main.py
    if os.path.exists(os.path.join('data', 'main.py')):
        with open(os.path.join('data', 'main.py'), 'r', encoding='utf-8') as f:
            exec(f.read(), namespace)
    else:
        print("Errore: File main.py non trovato nella cartella data!")
        print("Assicurati che il file main.py sia presente nella cartella data.")
    
    sys.exit(app.exec_())
