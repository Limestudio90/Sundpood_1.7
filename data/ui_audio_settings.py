from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_AudioSettings(object):
    def setupUi(self, AudioSettings):
        AudioSettings.setObjectName("AudioSettings")
        AudioSettings.resize(400, 200)
        AudioSettings.setMinimumSize(QtCore.QSize(400, 200))
        AudioSettings.setMaximumSize(QtCore.QSize(400, 200))
        
        self.background = QtWidgets.QWidget(AudioSettings)
        self.background.setGeometry(QtCore.QRect(0, 0, 400, 200))
        self.background.setObjectName("background")
        
        self.inputLabel = QtWidgets.QLabel(self.background)
        self.inputLabel.setGeometry(QtCore.QRect(20, 50, 90, 30))
        self.inputLabel.setText("Input Device:")
        
        self.outputLabel = QtWidgets.QLabel(self.background)
        self.outputLabel.setGeometry(QtCore.QRect(20, 90, 90, 30))
        self.outputLabel.setText("Output Device:")
        
        self.inputCombo = QtWidgets.QComboBox(self.background)
        self.inputCombo.setGeometry(QtCore.QRect(120, 50, 260, 30))
        
        self.outputCombo = QtWidgets.QComboBox(self.background)
        self.outputCombo.setGeometry(QtCore.QRect(120, 90, 260, 30))
        
        self.refreshBtn = QtWidgets.QPushButton(self.background)
        self.refreshBtn.setGeometry(QtCore.QRect(20, 140, 360, 30))
        self.refreshBtn.setText("Refresh Devices")
        
        self.titleLabel = QtWidgets.QLabel(self.background)
        self.titleLabel.setGeometry(QtCore.QRect(0, 10, 400, 30))
        self.titleLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.titleLabel.setText("Audio Device Settings")