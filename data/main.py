#\ SundPood version 2.0.1 /#

import os
import sys
import json
import re
import shutil
from time import time
import numpy as np
import pygame as pg
import sounddevice as sd
from pynput.keyboard import Listener
from cryptography.fernet import Fernet
from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtCore import QFile, QTextStream
from PyQt5.QtWidgets import QApplication, QFileDialog
from data import ui_preferences
from data import ui_hotkeys
from data import ui_sundpood
from data import ui_overlay
from data import keys
import themes

try:
    import key
except ModuleNotFoundError:
    key = None


###! UI !###
class OverlayUi(QtWidgets.QMainWindow, ui_overlay.Ui_MainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowStaysOnTopHint)
        self.setGeometry(QtCore.QRect(0, 0, 360, 56))
        self.setupUi(self)

    def keyPressEvent(self, e):
        if e.key() == QtCore.Qt.Key_F1:
            self.hide()
            win.show()

class PreferencesUi(QtWidgets.QMainWindow, ui_preferences.Ui_MainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
        self.setupUi(self)

    def mousePressEvent(self, event):
        self.offset = event.pos()

    def mouseMoveEvent(self, event):
        x = event.globalX()
        y = event.globalY()
        x_w = self.offset.x()
        y_w = self.offset.y()
        self.move(x-x_w, y-y_w)
    
    def closeEvent(self, event):
        save()

class HotkeysUi(QtWidgets.QMainWindow, ui_hotkeys.Ui_MainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
        self.setupUi(self)

    def mousePressEvent(self, event):
        self.offset = event.pos()

    def mouseMoveEvent(self, event):
        x = event.globalX()
        y = event.globalY()
        x_w = self.offset.x()
        y_w = self.offset.y()
        self.move(x-x_w, y-y_w)

class MainUi(QtWidgets.QMainWindow, ui_sundpood.Ui_MainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
        self.setupUi(self)
        self.volume_slider.valueChanged[int].connect(change_volume)

    def mousePressEvent(self, event):
        self.offset = event.pos()

    def mouseMoveEvent(self, event):
        try:
            x = event.globalX()
            y = event.globalY()
            x_w = self.offset.x()
            y_w = self.offset.y()
            self.move(x-x_w, y-y_w)
        except AttributeError:
            pass
    
    def keyPressEvent(self, e):
        if e.key() == QtCore.Qt.Key_F1:
            pref.close()
            self.hide()
            over.show()

    def closeEvent(self, event):
        save()
        stop_microphone_passthrough()
        if os.path.exists('.play'):
            os.remove('.play')
        hotk.close()
        pref.close()


###! JSON !###
def jsonread(file):
    '''
    Чтение JSON файла file
    file - имя JSON файла, может содержать полный или относительный путь
    '''
    with open(file, "r", encoding='utf-8') as read_file:
        data = json.load(read_file)
    return data

def jsonwrite(file, data):
    '''
    Запись в JSON файл file данные data
    file - имя JSON файла, может содержать полный или относительный путь
    data - данные, может быть словарем/списком/кортежем/строкой/числом
    '''
    with open(file, 'w', encoding='utf-8') as write_file:
        write_file.write(json.dumps(data))


###! FUNCTIONS !###
def toggle_stylesheet(path):
    """Apply the selected theme to all windows"""
    try:
        theme_path = os.path.join('themes', path)
        if os.path.exists(theme_path):
            with open(theme_path, 'r', encoding='utf-8') as file:
                stylesheet = file.read()
                win.setStyleSheet(stylesheet)
                pref.setStyleSheet(stylesheet)
                hotk.setStyleSheet(stylesheet)
                over.setStyleSheet(stylesheet)
                
                # Save theme selection
                config_data = jsonread(config)
                config_data['Theme'] = path
                jsonwrite(config, config_data)
    except Exception as e:
        print(f"Theme loading error: {e}")

if __name__ == '__main__':
    app_ready_for_save = False
    mic_passthrough_stream = None
    mic_passthrough_volume = 1.0
    PREFERRED_INPUT_KEYWORDS = [
        'microfono',
        'microphone',
        'mic',
        'insta360',
    ]
    PREFERRED_OUTPUT_KEYWORDS = [
        'virtual audio cable',
        'line 1',
        'line 2',
        'line 3',
        'cable input',
        'voicemeeter input',
    ]
    HOSTAPI_PREFERENCE = [
        'Windows WASAPI',
        'Windows DirectSound',
        'MME',
        'Windows WDM-KS',
    ]
    DEFAULT_AUDIO_SETTINGS = {
        'input': '',
        'output': '',
        'mic_passthrough_enabled': True,
        'mic_volume': 100,
    }

    def get_audio_settings():
        if not os.path.exists(config):
            return DEFAULT_AUDIO_SETTINGS.copy()

        try:
            config_data = jsonread(config)
        except (json.JSONDecodeError, KeyError, TypeError):
            return DEFAULT_AUDIO_SETTINGS.copy()
        saved_audio = config_data.get('audio_devices', {})
        audio_settings = DEFAULT_AUDIO_SETTINGS.copy()
        audio_settings.update(saved_audio)
        return audio_settings

    def find_input_device(preferred_name=''):
        '''
        Возвращает имя устройства ввода звука.
        Сначала пытается найти сохраненное устройство, затем предпочитает
        физический микрофон, после этого использует первый доступный input.
        '''
        devices = list(sd.query_devices())
        input_devices = [device for device in devices if device['max_input_channels'] > 0]
        preferred_name = (preferred_name or '').strip().lower()

        if preferred_name:
            for device in input_devices:
                if preferred_name == device['name'].strip().lower():
                    return device['name']

        for keyword in PREFERRED_INPUT_KEYWORDS:
            for device in input_devices:
                device_name = device['name'].lower()
                if keyword in device_name and 'cable output' not in device_name and 'loopback' not in device_name:
                    return device['name']

        for device in input_devices:
            device_name = device['name'].lower()
            if 'cable output' not in device_name and 'loopback' not in device_name and 'sound mapper' not in device_name:
                return device['name']

        if input_devices:
            return input_devices[0]['name']

        return ''

    def find_output_device(preferred_name=''):
        '''
        Возвращает имя устройства вывода звука.
        Сначала пытается найти сохраненное устройство, затем предпочитает
        Virtual Audio Cable, после этого использует первый доступный output.
        '''
        devices = list(sd.query_devices())
        output_devices = [device for device in devices if device['max_output_channels'] > 0]
        preferred_name = (preferred_name or '').strip().lower()

        if preferred_name:
            for device in output_devices:
                if preferred_name == device['name'].strip().lower():
                    return device['name']

        for keyword in PREFERRED_OUTPUT_KEYWORDS:
            for device in output_devices:
                if keyword in device['name'].lower():
                    return device['name']

        if output_devices:
            return output_devices[0]['name']

        msg = QtWidgets.QMessageBox()
        msg.setIcon(QtWidgets.QMessageBox.Critical)
        msg.setText("No output audio device found")
        msg.setInformativeText(
            "Install or enable an output device such as Virtual Audio Cable, "
            "then restart SundPood."
        )
        msg.setWindowTitle('Error')
        msg.exec_()
        sys.exit(1)

    def normalize_device_name(name):
        normalized = (name or '').strip().lower()
        normalized = re.sub(r'\s+', ' ', normalized)
        normalized = normalized.replace('(', '').replace(')', '')
        normalized = normalized.replace('-', ' ')
        return normalized

    def get_hostapi_name(hostapi_index):
        try:
            return sd.query_hostapis(hostapi_index)['name']
        except Exception:
            return ''

    def get_hostapi_priority(hostapi_index):
        hostapi_name = get_hostapi_name(hostapi_index)
        try:
            return HOSTAPI_PREFERENCE.index(hostapi_name)
        except ValueError:
            return len(HOSTAPI_PREFERENCE)

    def get_pygame_output_name(output_name):
        if not output_name:
            return ''

        try:
            import pygame._sdl2.audio as sdl2_audio
            pg.init()
            pygame_outputs = list(sdl2_audio.get_audio_device_names(False))
        except Exception:
            return output_name

        normalized_target = normalize_device_name(output_name)

        for pygame_name in pygame_outputs:
            if pygame_name == output_name:
                return pygame_name

        for pygame_name in pygame_outputs:
            normalized_pygame = normalize_device_name(pygame_name)
            if normalized_target in normalized_pygame or normalized_pygame in normalized_target:
                return pygame_name

        return output_name

    def init_pygame_mixer(output_name=''):
        requested_name = (output_name or '').strip()
        candidate_names = []

        if requested_name:
            candidate_names.append(get_pygame_output_name(requested_name))
            candidate_names.append(requested_name)

        unique_candidates = []
        for candidate in candidate_names:
            candidate = (candidate or '').strip()
            if candidate and candidate not in unique_candidates:
                unique_candidates.append(candidate)

        pg.mixer.quit()
        pg.mixer.pre_init(44100, -16, 2, 2048)

        errors = []
        for candidate in unique_candidates:
            try:
                pg.mixer.init(devicename=candidate)
                return candidate
            except Exception as exc:
                errors.append(f"{candidate}: {exc}")
                pg.mixer.quit()
                pg.mixer.pre_init(44100, -16, 2, 2048)

        try:
            pg.mixer.init()
            return ''
        except Exception as exc:
            errors.append(f"default device: {exc}")
            raise RuntimeError('\n'.join(errors))

    def get_files(dir_, config):
        '''
        Сбор всех аудифайлов
        dir_ - Путь к папке со звуками
        config - Имя файла настроек
        '''
        msg = QtWidgets.QMessageBox()       # Окно ошибки (Не найдены файлы в папке 'sound')
        msg.setIcon(QtWidgets.QMessageBox.Critical)
        msg.setText("You don't have any sounds in 'sound' folder")
        msg.setInformativeText('download sound in .wav / .mp3 / .m4a format')
        msg.setWindowTitle('Error')
        supported_extensions = {'.mp3', '.m4a', '.wav', '.ogg'}
    
        if os.path.exists(dir_):
            if len(os.listdir(dir_)) == 0:
                msg.exec_()
    
            sounds = []                     # Все аудио файлы
            sounds_list = [f'{dir_}\\']       # Начальная категория
    
            for i in sorted(os.listdir(dir_)):
                full_path = os.path.join(dir_, i)
                if os.path.isfile(full_path):
                    if os.path.splitext(i)[1].lower() in supported_extensions:
                        sounds_list.append(i)
                elif os.path.isdir(full_path):
                    sounds_list_cat = [full_path]
                    for root, _, files in os.walk(full_path):
                        for file_name in sorted(files):
                            if os.path.splitext(file_name)[1].lower() not in supported_extensions:
                                continue
                            file_path = os.path.join(root, file_name)
                            relative_path = os.path.relpath(file_path, full_path)
                            sounds_list_cat.append(relative_path)
                    sounds.append(sounds_list_cat)
            sounds.append(sounds_list)
    
            if os.path.exists(config):
                config_data = jsonread(config)
                hotkeys = config_data['hotkeys']
                theme = config_data['Theme']
                KEYS_CMD = config_data['KEYS_CMD']
                audio_devices = get_audio_settings()
                sounds_list = { 'hotkeys':hotkeys, 
                                'sounds':sounds,
                                'Theme':theme,
                                'audio_devices': audio_devices,
                                'KEYS_CMD':KEYS_CMD}
            else:
                sounds_list = { 'hotkeys':{}, 
                                'sounds':sounds,
                                'Theme':'None',
                                'audio_devices': DEFAULT_AUDIO_SETTINGS.copy(),
                                'KEYS_CMD':{
                                'select_move_up'    :' ',# вверх
                                'select_move_down'  :' ',# вниз
                                'select_move_left'  :' ',# влево
                                'select_move_right' :' ',# вправо
                                'play_sound'        :' ',# Играть
                                'stop_sound'        :' ',# Остановить
                                }}
    
            jsonwrite(config, sounds_list)
        else:
            sounds_list = { 'hotkeys':{}, 
                            'sounds':'',
                            'Theme':'None',
                            'audio_devices': DEFAULT_AUDIO_SETTINGS.copy(),
                            'KEYS_CMD':{
                                'select_move_up'    :' ',# вверх
                                'select_move_down'  :' ',# вниз
                                'select_move_left'  :' ',# влево
                                'select_move_right' :' ',# вправо
                                'play_sound'        :' ',# Играть
                                'stop_sound'        :' ',# Остановить
                                }}
            jsonwrite(config, sounds_list)
            os.mkdir(dir_)
            msg.exec_()

    def rebuild_hotkey_list():
        hotk.hotkeyList.clear()
        for category in sound_get_dict['sounds']:
            for item in category[1:]:
                sound_path = os.path.join(category[0], item)
                if sound_path in hotkeys.values():
                    hotk.hotkeyList.addItem(f'{find_key(hotkeys, sound_path)}\t: {sound_path}')

    def rebuild_category_list():
        current_category = win.catList.currentItem().text() if win.catList.currentItem() else ''
        win.catList.clear()

        for category in menu:
            label = category[0].replace('sound', '')
            win.catList.addItem(label)

        if win.catList.count() == 0:
            win.soundList.clear()
            win.select_label.setText('')
            return

        target_category = current_category if current_category else win.catList.item(0).text()
        matching_items = win.catList.findItems(target_category, QtCore.Qt.MatchExactly)
        if matching_items:
            win.catList.setCurrentItem(matching_items[0])
            cat_select(matching_items[0].text())
        else:
            win.catList.setCurrentRow(0)
            cat_select(win.catList.item(0).text())

    def refresh_sound_library(show_message=False):
        global sound_get_dict
        global hotkeys
        global theme
        global menu
        global select

        get_files(dir_, config)
        sound_get_dict = jsonread(config)
        hotkeys = sound_get_dict['hotkeys']
        theme = sound_get_dict['Theme']
        menu = sound_get_dict['sounds']
        select = [0, 0]

        rebuild_category_list()
        rebuild_hotkey_list()

        if menu and len(menu[0]) > 1:
            over.label.setText(menu[0][1])
            win.select_label.setText(menu[0][1])
        else:
            over.label.setText('')
            win.select_label.setText('')

        if show_message:
            msg = QtWidgets.QMessageBox()
            msg.setIcon(QtWidgets.QMessageBox.Information)
            msg.setText("Library refreshed")
            msg.setInformativeText("The sound library has been reloaded from the 'sound' folder.")
            msg.setWindowTitle('Library')
            msg.exec_()

    def import_sound_folder():
        source_dir = QFileDialog.getExistingDirectory(
            win,
            'Select folder to import',
            os.getcwd()
        )
        if not source_dir:
            return

        destination_root = os.path.join(dir_, os.path.basename(os.path.normpath(source_dir)))
        os.makedirs(destination_root, exist_ok=True)
        supported_extensions = {'.mp3', '.m4a', '.wav', '.ogg'}
        imported_count = 0

        for root, _, files in os.walk(source_dir):
            relative_root = os.path.relpath(root, source_dir)
            destination_dir = destination_root if relative_root == '.' else os.path.join(destination_root, relative_root)
            os.makedirs(destination_dir, exist_ok=True)

            for file_name in files:
                if os.path.splitext(file_name)[1].lower() not in supported_extensions:
                    continue
                source_file = os.path.join(root, file_name)
                destination_file = os.path.join(destination_dir, file_name)
                shutil.copy2(source_file, destination_file)
                imported_count += 1

        refresh_sound_library()

        msg = QtWidgets.QMessageBox()
        msg.setIcon(QtWidgets.QMessageBox.Information)
        msg.setText("Folder imported")
        msg.setInformativeText(f"Imported {imported_count} audio file(s) into '{destination_root}'.")
        msg.setWindowTitle('Library')
        msg.exec_()

    def change_volume(value):
        pg.mixer.music.set_volume(value/100)

    def stop_sound():
        pg.mixer.music.stop()

    def set_microphone_volume(value):
        global mic_passthrough_volume
        mic_passthrough_volume = max(0.0, float(value) / 100.0)

        if hasattr(pref, 'micVolumeValue'):
            pref.micVolumeValue.setText(f"{int(value)}%")
        if hasattr(pref, 'micVolumeSlider'):
            pref.micVolumeSlider.setEnabled(pref.micPassthroughCheck.isChecked())

        if app_ready_for_save:
            save()

    def stop_microphone_passthrough():
        global mic_passthrough_stream
        if mic_passthrough_stream is not None:
            try:
                mic_passthrough_stream.stop()
                mic_passthrough_stream.close()
            except Exception:
                pass
            mic_passthrough_stream = None

    def get_device_candidates(device_name, wants_input):
        if not device_name:
            return []

        candidates = []
        for index, device in enumerate(sd.query_devices()):
            if wants_input and device['max_input_channels'] <= 0:
                continue
            if not wants_input and device['max_output_channels'] <= 0:
                continue
            if device['name'] == device_name:
                candidates.append((index, device))

        if candidates:
            return candidates

        lowered_name = device_name.lower()
        for index, device in enumerate(sd.query_devices()):
            if wants_input and device['max_input_channels'] <= 0:
                continue
            if not wants_input and device['max_output_channels'] <= 0:
                continue
            if lowered_name in device['name'].lower() or device['name'].lower() in lowered_name:
                candidates.append((index, device))

        channel_key = 'max_input_channels' if wants_input else 'max_output_channels'
        candidates.sort(
            key=lambda item: (
                get_hostapi_priority(item[1]['hostapi']),
                int(item[1].get(channel_key, 0) or 0),
                item[0],
            )
        )

        return candidates

    def get_duplex_device_pairs(input_name, output_name):
        input_candidates = get_device_candidates(input_name, True)
        output_candidates = get_device_candidates(output_name, False)

        if not input_candidates or not output_candidates:
            return []

        ranked_pairs = []

        selected_input_idx = pref.inputDeviceCombo.currentData() if hasattr(pref, 'inputDeviceCombo') else None
        selected_output_idx = pref.outputDeviceCombo.currentData() if hasattr(pref, 'outputDeviceCombo') else None

        for input_idx, input_device in input_candidates:
            for output_idx, output_device in output_candidates:
                same_hostapi = input_device['hostapi'] == output_device['hostapi']
                ranked_pairs.append((
                    (
                        0 if (input_idx == selected_input_idx and output_idx == selected_output_idx and same_hostapi) else 1,
                        0 if same_hostapi else 1,
                        get_hostapi_priority(input_device['hostapi']),
                        abs(
                            int(input_device.get('default_samplerate', 44100) or 44100) -
                            int(output_device.get('default_samplerate', 44100) or 44100)
                        ),
                        int(output_device.get('max_output_channels', 0) or 0),
                        int(input_device.get('max_input_channels', 0) or 0),
                    ),
                    (input_idx, output_idx, input_device, output_device)
                ))

        ranked_pairs.sort(key=lambda item: item[0])
        return [pair for _, pair in ranked_pairs]

    def start_microphone_passthrough(input_idx=None, output_idx=None):
        global mic_passthrough_stream

        stop_microphone_passthrough()

        if input_idx is None or output_idx is None:
            return

        input_name = pref.inputDeviceCombo.currentText() if hasattr(pref, 'inputDeviceCombo') else ''
        output_name = pref.outputDeviceCombo.currentText() if hasattr(pref, 'outputDeviceCombo') else ''
        device_pairs = get_duplex_device_pairs(input_name, output_name)

        if not device_pairs:
            device_pairs = [(input_idx, output_idx, sd.query_devices(input_idx), sd.query_devices(output_idx))]

        last_error = None
        for candidate_input_idx, candidate_output_idx, input_device, output_device in device_pairs:
            input_channels = max(1, min(int(input_device['max_input_channels']), 2))
            output_channels = max(1, min(int(output_device['max_output_channels']), 2))
            stream_channels = min(input_channels, output_channels)

            if stream_channels <= 0:
                continue

            sample_rates = []
            for rate in (
                int(output_device.get('default_samplerate', 44100) or 44100),
                int(input_device.get('default_samplerate', 44100) or 44100),
                48000,
                44100,
            ):
                if rate not in sample_rates:
                    sample_rates.append(rate)

            for samplerate in sample_rates:
                try:
                    sd.check_input_settings(
                        device=candidate_input_idx,
                        samplerate=samplerate,
                        channels=stream_channels,
                        dtype='float32',
                    )
                    sd.check_output_settings(
                        device=candidate_output_idx,
                        samplerate=samplerate,
                        channels=stream_channels,
                        dtype='float32',
                    )

                    def microphone_callback(indata, outdata, frames, time_info, status):
                        if status:
                            print(status)

                        outdata.fill(0)
                        routed_audio = indata[:, :stream_channels]
                        routed_audio = np.clip(routed_audio * mic_passthrough_volume, -1.0, 1.0)

                        if outdata.shape[1] == routed_audio.shape[1]:
                            outdata[:] = routed_audio
                        elif outdata.shape[1] > routed_audio.shape[1]:
                            outdata[:, :routed_audio.shape[1]] = routed_audio
                            if routed_audio.shape[1] == 1:
                                outdata[:, 1:] = np.repeat(routed_audio, outdata.shape[1] - 1, axis=1)
                        else:
                            outdata[:] = routed_audio[:, :outdata.shape[1]]

                    mic_passthrough_stream = sd.Stream(
                        device=(candidate_input_idx, candidate_output_idx),
                        samplerate=samplerate,
                        channels=(stream_channels, stream_channels),
                        dtype='float32',
                        callback=microphone_callback,
                        blocksize=0,
                        latency='high',
                    )
                    mic_passthrough_stream.start()

                    if hasattr(pref, 'inputDeviceCombo'):
                        input_combo_index = pref.inputDeviceCombo.findText(input_device['name'])
                        if input_combo_index >= 0:
                            input_blocker = QtCore.QSignalBlocker(pref.inputDeviceCombo)
                            pref.inputDeviceCombo.setCurrentIndex(input_combo_index)
                            del input_blocker
                    if hasattr(pref, 'outputDeviceCombo'):
                        output_combo_index = pref.outputDeviceCombo.findText(output_device['name'])
                        if output_combo_index >= 0:
                            output_blocker = QtCore.QSignalBlocker(pref.outputDeviceCombo)
                            pref.outputDeviceCombo.setCurrentIndex(output_combo_index)
                            del output_blocker
                    return
                except Exception as e:
                    last_error = e
                    mic_passthrough_stream = None

        if last_error is not None:
            raise last_error

    def play_sound(*argv):
        if False in argv:
            try:
                sound = os.path.join(win.soundList.item(0).text(),
                        win.soundList.currentItem().text())
            except AttributeError:
                return False
        else:
            sound = argv[0]
        try:
            pg.mixer.music.load(sound)
            pg.mixer.music.play()
            pg.event.wait()
        except RuntimeError:
            pass

    def cat_select(cat):
        win.soundList.clear()
        for i in menu:
            if 'sound' + cat == i[0]:
                win.soundList.addItems(i)

    def hotkey_remap():
        '''
        Переназначение хоткея
        btn - индекс кнопки хоткея в списке HOTKEYS
        '''
        def check(key):
            key = str(key).replace("'",'')
            try:
                sound = os.path.join(win.soundList.item(0).text(),
                            win.soundList.currentItem().text())
            except AttributeError:
                win.hkset.setEnabled(True)
                return False
    
            if key not in keys.forbidden:
                hotkeys.update({key:sound})
            elif key == 'Key.backspace':
                del hotkeys[find_key(hotkeys, sound)]
    
            save()
            rebuild_hotkey_list()
    
            win.hkset.setEnabled(True)
            return False
    
        win.hkset.setEnabled(False)
    
        hotkey_remap_Listener = Listener(
            on_release=check)
        hotkey_remap_Listener.start()

    def hotkey_delete():
        key = hotk.hotkeyList.currentItem().text().split(':')[0].replace('\t', '')
        hotkeys.pop(key)
    
        save()
        rebuild_hotkey_list()

    def pref_remap(btn, func_):
        '''
        Переназначение клавиши в окно Preference
        btn - PyQt5 кнопка
        func_ - строковое значени функции из словаря KEYS_CMD
        '''
        def check(key):
            '''
            Проверка кнопки btn на не участие 
                в списке запрещенных клавиш keys.forbidden
                если это клавиша 'Key.backspace' то стираем значение
            key - pynput код клавиши
            '''
            key = str(key).replace("'",'')
            if key not in keys.forbidden:
                KEYS_CMD.update({find_key(COMMAND_DICT, func_) : key})
                btn.setText(keys.dict_[key])
            elif key == 'Key.backspace':
                KEYS_CMD.update({find_key(COMMAND_DICT, func_) : ' '})
                btn.setText(' ')
            for i in PREF_BTN:
                i.setEnabled(True)
            save()
            return False
    
        for i in PREF_BTN:
            i.setEnabled(False)
    
        hotkey_remap_Listener = Listener(
            on_release=check)
        hotkey_remap_Listener.start()

    def find_key(dict, val):
        '''
        Поиск ключа в словаре dict по значению val
        dict - словарь
        val - значение
        '''
        return next((key for key, value in dict.items() if value == val), None)

    def check_update():
        if key is None:
            return VERSION

        def decrypt(filename, key):
            f = Fernet(key)
            with open(filename, 'rb') as file:
                encrypted_data = file.read()
    
            decrypted_data = f.decrypt(encrypted_data)
    
            return decrypted_data.decode('utf-8')
    
        file_ = decrypt(os.path.join('data', 'sundpood-runtime.sr') , key.KEY)
        version = ''
        for i in file_:
            if i != '/':
                version += i
            else:
                break
        print(VERSION)
        return version.split(' ')[3]

    def save():
        '''
        Сохранение настроек оверлея и глобальных хоткеев
        '''
        if not app_ready_for_save:
            return

        sounds = jsonread(config)['sounds']# Все аудиофайлы
        
        KEYS_JSON = {}                      # Настроенные клавиши
        for i in KEYS_CMD.keys():
            KEYS_JSON.setdefault(COMMAND_DICT[i], KEYS_CMD[i])
    
        try:
            theme = pref.themesList.currentItem().text()
        except AttributeError:
            theme = jsonread(config)['Theme']

        audio_devices = get_audio_settings()

        if hasattr(pref, 'inputDeviceCombo') and pref.inputDeviceCombo.count() > 0:
            audio_devices['input'] = pref.inputDeviceCombo.currentText()
        if hasattr(pref, 'outputDeviceCombo') and pref.outputDeviceCombo.count() > 0:
            audio_devices['output'] = pref.outputDeviceCombo.currentText()
        if hasattr(pref, 'micPassthroughCheck'):
            audio_devices['mic_passthrough_enabled'] = pref.micPassthroughCheck.isChecked()
        if hasattr(pref, 'micVolumeSlider'):
            audio_devices['mic_volume'] = pref.micVolumeSlider.value()

        sounds_list = {
            'sounds':sounds,
            'hotkeys':hotkeys,
            'Theme':theme,
            'audio_devices': audio_devices,
            'KEYS_CMD':KEYS_JSON
        }
        jsonwrite(config, sounds_list)

    ###! CONTROL !###
    def select_move(mode):
        '''
        Перемешение по оверлейному меню
        mode - кортеж из двух цифр 
            (смещение по категории, смещение по списку)
        '''
        select[0] += mode[0]    # Категории
        select[1] += mode[1]    # Файлы в категории
        if select[0] > len(menu)-1 or select[0] < -len(menu)+1:
            select[0] = 0
        if select[1] > len(menu[select[0]])-1 or select[1] < -len(menu[select[0]])+1:
            select[1] = 0
        if mode[0] != 0:
            select[1] = 0
        over.label.setText(menu[select[0]][select[1]])
        win.select_label.setText(menu[select[0]][select[1]])
    
    def key_check(key):
        key = str(key).replace("'",'')  # Преобразование кода в строку
        key_n = ''                      # Переведенное значение клавиши
        try:
            key_n = keys.dict_[key]
        except KeyError:
            pass
        if key in hotkeys.keys():
            play_sound(hotkeys[key])
        elif key in KEYS_CMD.values():
            find_key(KEYS_CMD, key)()

    def populate_audio_devices():
        """Populate audio device selection comboboxes"""
        input_devices = []
        output_devices = []
        
        for i, device in enumerate(sd.query_devices()):
            if device['max_input_channels'] > 0:
                input_devices.append((i, device['name']))
            if device['max_output_channels'] > 0:
                output_devices.append((i, device['name']))

        input_devices.sort(
            key=lambda item: (
                get_hostapi_priority(sd.query_devices(item[0])['hostapi']),
                normalize_device_name(item[1]),
                item[0],
            )
        )
        output_devices.sort(
            key=lambda item: (
                get_hostapi_priority(sd.query_devices(item[0])['hostapi']),
                normalize_device_name(item[1]),
                item[0],
            )
        )
        
        input_blocker = QtCore.QSignalBlocker(pref.inputDeviceCombo)
        output_blocker = QtCore.QSignalBlocker(pref.outputDeviceCombo)
        mic_toggle_blocker = QtCore.QSignalBlocker(pref.micPassthroughCheck)
        mic_volume_blocker = QtCore.QSignalBlocker(pref.micVolumeSlider)

        pref.inputDeviceCombo.clear()
        pref.outputDeviceCombo.clear()
        
        for idx, name in input_devices:
            pref.inputDeviceCombo.addItem(name, idx)
        for idx, name in output_devices:
            pref.outputDeviceCombo.addItem(name, idx)

        saved_devices = get_audio_settings()
        saved_input = saved_devices.get('input', '')
        saved_output = saved_devices.get('output', '')

        if saved_input:
            input_index = pref.inputDeviceCombo.findText(saved_input)
            if input_index >= 0:
                pref.inputDeviceCombo.setCurrentIndex(input_index)
            else:
                normalized_saved_input = normalize_device_name(saved_input)
                for combo_index in range(pref.inputDeviceCombo.count()):
                    if normalize_device_name(pref.inputDeviceCombo.itemText(combo_index)) == normalized_saved_input:
                        pref.inputDeviceCombo.setCurrentIndex(combo_index)
                        break
        elif pref.inputDeviceCombo.count() > 0:
            preferred_input = find_input_device()
            input_index = pref.inputDeviceCombo.findText(preferred_input)
            if input_index >= 0:
                pref.inputDeviceCombo.setCurrentIndex(input_index)

        if saved_output:
            output_index = pref.outputDeviceCombo.findText(saved_output)
            if output_index >= 0:
                pref.outputDeviceCombo.setCurrentIndex(output_index)
            else:
                normalized_saved_output = normalize_device_name(saved_output)
                for combo_index in range(pref.outputDeviceCombo.count()):
                    if normalize_device_name(pref.outputDeviceCombo.itemText(combo_index)) == normalized_saved_output:
                        pref.outputDeviceCombo.setCurrentIndex(combo_index)
                        break
        elif pref.outputDeviceCombo.count() > 0:
            preferred_output = find_output_device()
            output_index = pref.outputDeviceCombo.findText(preferred_output)
            if output_index >= 0:
                pref.outputDeviceCombo.setCurrentIndex(output_index)

        pref.micPassthroughCheck.setChecked(saved_devices.get('mic_passthrough_enabled', True))
        pref.micVolumeSlider.setValue(int(saved_devices.get('mic_volume', 100)))
        pref.micVolumeSlider.setEnabled(pref.micPassthroughCheck.isChecked())
        pref.micVolumeValue.setText(f"{pref.micVolumeSlider.value()}%")
        set_microphone_volume(pref.micVolumeSlider.value())

        del input_blocker
        del output_blocker
        del mic_toggle_blocker
        del mic_volume_blocker
        apply_audio_device_preferences()

    def apply_audio_device_preferences():
        input_idx = pref.inputDeviceCombo.currentData()
        output_idx = pref.outputDeviceCombo.currentData()
        output_name = pref.outputDeviceCombo.currentText()
        mic_passthrough_enabled = pref.micPassthroughCheck.isChecked()

        try:
            if input_idx is not None and output_idx is not None:
                sd.default.device = (input_idx, output_idx)
            elif output_idx is not None:
                current_input = sd.default.device[0] if isinstance(sd.default.device, (list, tuple)) else None
                sd.default.device = (current_input, output_idx)

            init_pygame_mixer(output_name)

            if mic_passthrough_enabled:
                start_microphone_passthrough(input_idx, output_idx)
            else:
                stop_microphone_passthrough()
            if app_ready_for_save:
                save()
        except Exception as e:
            stop_microphone_passthrough()
            msg = QtWidgets.QMessageBox()
            msg.setIcon(QtWidgets.QMessageBox.Critical)
            msg.setText("Failed to apply audio routing")
            msg.setInformativeText(str(e))
            msg.setWindowTitle('Error')
            msg.exec_()
    
    # Add imports at the top
    from data import ui_audio_settings
    
    # Add new class for audio settings
    class AudioSettingsWindow(QtWidgets.QMainWindow, ui_audio_settings.Ui_AudioSettings):
        def __init__(self, parent=None):
            super().__init__(parent)
            self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
            self.setupUi(self)
            self.refresh_devices()
            
            # Connect buttons
            self.refreshBtn.clicked.connect(self.refresh_devices)
            self.inputCombo.currentIndexChanged.connect(self.apply_changes)
            self.outputCombo.currentIndexChanged.connect(self.apply_changes)
        
        def refresh_devices(self):
            self.inputCombo.clear()
            self.outputCombo.clear()
            
            devices = sd.query_devices()
            for i, dev in enumerate(devices):
                if dev['max_input_channels'] > 0:
                    self.inputCombo.addItem(dev['name'], i)
                if dev['max_output_channels'] > 0:
                    self.outputCombo.addItem(dev['name'], i)
        
        def apply_changes(self):
            try:
                input_idx = self.inputCombo.currentData()
                output_idx = self.outputCombo.currentData()
                
                if input_idx is not None:
                    sd.default.device[0] = input_idx
                if output_idx is not None:
                    sd.default.device[1] = output_idx
                    init_pygame_mixer(self.outputCombo.currentText())
                
                # Save settings
                config_data = jsonread(config)
                if 'audio_devices' not in config_data:
                    config_data['audio_devices'] = {}
                config_data['audio_devices'].update({
                    'input': self.inputCombo.currentText(),
                    'output': self.outputCombo.currentText()
                })
                jsonwrite(config, config_data)
                
            except Exception as e:
                msg = QtWidgets.QMessageBox()
                msg.setIcon(QtWidgets.QMessageBox.Critical)
                msg.setText("Failed to change audio device")
                msg.setInformativeText(str(e))
                msg.setWindowTitle('Error')
    
    # In the main initialization section:
    if __name__ == '__main__':
        def main():
            key_check_Listener = Listener(
                on_release=key_check)
            key_check_Listener.start()
        
            win.exit_button.clicked.connect(win.close)
            win.min_button.clicked.connect(win.showMinimized)
            pref.exit_button.clicked.connect(pref.close)
            pref.min_button.clicked.connect(pref.showMinimized)
            hotk.exit_button.clicked.connect(hotk.close)
            hotk.min_button.clicked.connect(hotk.showMinimized)
        
            win.hkset.clicked.connect(hotkey_remap)
            win.pref_button.clicked.connect(pref.show)
            win.hotkeys_button.clicked.connect(hotk.show)
            win.catList.currentTextChanged.connect(cat_select)
            win.stop_button.clicked.connect(stop_sound)
            win.play_button.clicked.connect(play_sound)
            win.refresh_library_button.clicked.connect(lambda: refresh_sound_library(show_message=True))
            win.import_folder_button.clicked.connect(import_sound_folder)
        
            pref.play_sound.clicked.connect(
                lambda: pref_remap(pref.play_sound, 'play_sound'))
            pref.stop_sound.clicked.connect(
                lambda: pref_remap(pref.stop_sound, 'stop_sound'))
            pref.select_move_up.clicked.connect(
                lambda: pref_remap(pref.select_move_up, 'select_move_up'))
            pref.select_move_down.clicked.connect(
                lambda: pref_remap(pref.select_move_down, 'select_move_down'))
            pref.select_move_left.clicked.connect(
                lambda: pref_remap(pref.select_move_left, 'select_move_left'))
            pref.select_move_right.clicked.connect(
                lambda: pref_remap(pref.select_move_right, 'select_move_right'))
            pref.themesList.currentTextChanged.connect(toggle_stylesheet)
            pref.refreshDevicesBtn.clicked.connect(populate_audio_devices)
            pref.inputDeviceCombo.currentIndexChanged.connect(apply_audio_device_preferences)
            pref.outputDeviceCombo.currentIndexChanged.connect(apply_audio_device_preferences)
            pref.micPassthroughCheck.stateChanged.connect(apply_audio_device_preferences)
            pref.micPassthroughCheck.stateChanged.connect(
                lambda _state: pref.micVolumeSlider.setEnabled(pref.micPassthroughCheck.isChecked()))
            pref.micVolumeSlider.valueChanged.connect(set_microphone_volume)
            # Theme initialization
            if os.path.exists('themes'):
                theme_files = [f for f in os.listdir('themes') if f.endswith('.qss')]
                if theme_files:
                    pref.themesList.clear()
                    pref.themesList.addItems(theme_files)
                    
                    # Set current theme if exists
                    current_theme = sound_get_dict.get('Theme', 'None')
                    if current_theme != 'None' and current_theme in theme_files:
                        index = theme_files.index(current_theme)
                        pref.themesList.setCurrentRow(index)
                        toggle_stylesheet(current_theme)
            
            # Make sure theme changes are properly connected
            pref.themesList.itemClicked.connect(lambda item: toggle_stylesheet(item.text()))
            # Remove this line:
            # pref.update_button.clicked.connect(check_update)
        
            hotk.delete_button.clicked.connect(hotkey_delete)
        
            win.show()
        
        
        if __name__ == '__main__':
            ### Глобальные переменные ###
            VERSION = "2.0.1"
            dir_ = 'sound'
            config = 'settings.json'
        
            # Add directory checks
            required_dirs = ['sound', 'themes', 'data']
            for dir_name in required_dirs:
                if not os.path.exists(dir_name):
                    os.makedirs(dir_name)
                    
            if not os.path.exists('settings.json'):
                get_files(dir_, config)
                
            # Continue with existing initialization
            app = QApplication([])
            over = OverlayUi()
            pref = PreferencesUi()
            hotk = HotkeysUi()
            win = MainUi()
        
            PREF_BTN = [                        # Список кнопок настроек клавиш в pref
                pref.select_move_up,
                pref.select_move_down,
                pref.select_move_left,
                pref.select_move_right,
                pref.play_sound,
                pref.stop_sound,]
            
            ### Поиск устроства ввода ###
            try:
                startup_config = get_audio_settings()
                saved_output = startup_config.get('output', '')
                init_pygame_mixer(find_output_device(saved_output))
            except Exception as e:
                msg = QtWidgets.QMessageBox()
                msg.setIcon(QtWidgets.QMessageBox.Critical)
                msg.setText("Audio device initialization failed")
                msg.setInformativeText(str(e))
                msg.setWindowTitle('Error')
                msg.exec_()
                sys.exit(1)
            
            ### Глобальные переменные ###
            VERSION = "2.0.1"
            dir_ = 'sound'
            config = 'settings.json'
            get_files(dir_, config)             # Сбор всех аудиофайлов
            sound_get_dict = jsonread(config)   # Загрузка данных
            hotkeys = sound_get_dict['hotkeys'] # Загрузка словаря хоткеев
            theme = sound_get_dict['Theme']     # Загрузка темы
            menu = sound_get_dict['sounds']     # Загрузка оверлейного меню
            select = [0, 0]                     # Установка курсора оверлея в нулевую позицию
        
            if theme != 'None':
                toggle_stylesheet(theme)
            pref.themesList.addItems(os.listdir('themes'))
            populate_audio_devices()
            rebuild_category_list()
            rebuild_hotkey_list()
        
        
            COMMAND_DICT = {                    # Словарь функций к строковому значению
                    lambda: select_move((0, -1)):'select_move_up',      # вверх
                    lambda: select_move((0, 1)) :'select_move_down',    # вниз
                    lambda: select_move((-1, 0)):'select_move_left',    # влево
                    lambda: select_move((1, 0)) :'select_move_right',   # вправо
                    lambda: play_sound(os.path.join(menu[select[0]][0], 
                        menu[select[0]][select[1]])):'play_sound',      # Играть
                    stop_sound                   :'stop_sound',          # Остановить
            }
            KEYS_JSON = sound_get_dict['KEYS_CMD']# Загрузка настроенных клавиш
            KEYS_CMD = COMMAND_DICT.copy()      # Настроенные клавиши
        
            ### Установка настроенных клавиш ###
            for i in KEYS_CMD.keys():           
                KEYS_CMD.update({i:KEYS_JSON[COMMAND_DICT[i]]})
            KEYS_JSON = None
        
            combo = 0
            for i in KEYS_CMD.values():
                PREF_BTN[combo].setText(keys.dict_[i])
                combo += 1

            app_ready_for_save = True
        
            main()
        
            sys.exit(app.exec())
