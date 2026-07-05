import os
import sys
from cryptography.fernet import Fernet

try:
    import key
except ModuleNotFoundError:
    key = None

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


def get_runtime_root():
    if getattr(sys, 'frozen', False):
        executable_dir = os.path.dirname(sys.executable)
        internal_dir = os.path.join(executable_dir, '_internal')
        if os.path.isdir(internal_dir):
            return internal_dir
        meipass_dir = getattr(sys, '_MEIPASS', '')
        if meipass_dir and os.path.isdir(meipass_dir):
            return meipass_dir
        return executable_dir

    return os.path.dirname(os.path.abspath(__file__))

def decrypt(filename, key):
    # Расшифруем файл и записываем его
    f = Fernet(key)
    with open(filename, 'rb') as file:
        encrypted_data = file.read()
        
    decrypted_data = f.decrypt(encrypted_data)
    
    return decrypted_data.decode('utf-8')

if __name__ == '__main__':
    app = QApplication(sys.argv)
    runtime_root = get_runtime_root()
    os.chdir(runtime_root)
    main_path = os.path.join(runtime_root, 'data', 'main.py')
    
    # Create a namespace to hold our globals
    namespace = {
        'app': app,
        '__name__': '__main__',
        '__file__': main_path,
        **globals()
    }
    
    if os.path.exists(main_path):
        with open(main_path, 'r', encoding='utf-8') as f:
            exec(f.read(), namespace)
    else:
        if key is None:
            raise ModuleNotFoundError("Missing 'key' module required for encrypted runtime")
        exec(decrypt(os.path.join('data', 'sundpood-runtime.sr'), key.KEY), namespace)
    
    sys.exit(app.exec_())
