import os
import sys
from cryptography.fernet import Fernet
import key

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

def decrypt(filename, key):
    # Расшифруем файл и записываем его
    f = Fernet(key)
    with open(filename, 'rb') as file:
        encrypted_data = file.read()
        
    decrypted_data = f.decrypt(encrypted_data)
    
    return decrypted_data.decode('utf-8')

if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    # Create a namespace to hold our globals
    namespace = {
        'app': app,
        '__name__': '__main__',
        **globals()
    }
    
    if os.path.exists(os.path.join('data', 'main.py')):
        with open(os.path.join('data', 'main.py'), 'r', encoding='utf-8') as f:
            exec(f.read(), namespace)
    else:
        exec(decrypt(os.path.join('data', 'sundpood-runtime.sr'), key.KEY), namespace)
    
    sys.exit(app.exec_())
