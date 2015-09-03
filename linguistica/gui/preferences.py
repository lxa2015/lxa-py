# Definition of MainWindow_Preferences for the Linguistica 5 GUI
# Jackson Lee, 2015

import json
from pathlib import Path

from PyQt5.QtWidgets import (QDialog, QWidget,
                             QHBoxLayout, QVBoxLayout,
                             QLabel, QPushButton,
                             QTabWidget, QDoubleSpinBox, QLineEdit)

class MainWindow_Preferences():

    def filePreferencesDialog(self):
        return
        # complete revamp of this function needed, J Lee 2015/8/10

        preferencesDialog = QDialog()
        preferencesDialog.resize(640, 480)
        preferencesDialog.setWindowTitle('Preferences')

        # tab for Lxa text-->signatures parameters
        lxaTab = QWidget()

        language, corpus, datafolder = self.loadConfig()

        self.para_language = QLineEdit()
        self.para_language.setText(language)
        self.para_corpus = QLineEdit()
        self.para_corpus.setText(corpus)
        self.para_datafolder = QLineEdit()
        self.para_datafolder.setText(datafolder)

        self.para_MinimumStemLength = QDoubleSpinBox()
        self.para_MinimumStemLength.setValue(4)
        self.para_MaximumAffixLength = QDoubleSpinBox()
        self.para_MaximumAffixLength.setValue(3)
        self.para_MinimumNumberofSigUses = QDoubleSpinBox()
        self.para_MinimumNumberofSigUses.setValue(50)

        lxaTabLayout = QVBoxLayout()
        lxaTabLayout.addWidget(QLabel("language"))
        lxaTabLayout.addWidget(self.para_language)
        lxaTabLayout.addWidget(QLabel("corpus filename"))
        lxaTabLayout.addWidget(self.para_corpus)
        lxaTabLayout.addWidget(QLabel("datafolder"))
        lxaTabLayout.addWidget(self.para_datafolder)
        lxaTabLayout.addWidget(self.para_MinimumStemLength)
        lxaTabLayout.addWidget(self.para_MaximumAffixLength)
        lxaTabLayout.addWidget(self.para_MinimumNumberofSigUses)

        lxaTab.setLayout(lxaTabLayout)

        # overall layout
        tabWidget = QTabWidget()
        tabWidget.addTab(lxaTab, "test")

        saveButton = QPushButton("Save")
        saveButton.clicked.connect(self.updatePreferences)

        runButton = QPushButton("Run")
        runButton.clicked.connect(self.runLxa)

        overallLayout = QVBoxLayout()
        overallLayout.addWidget(tabWidget)
        overallLayout.addWidget(saveButton)
        overallLayout.addWidget(runButton)

        preferencesDialog.setLayout(overallLayout)
        preferencesDialog.exec_()


    def updatePreferences(self):
        # complete revamp of this function needed, J Lee 2015/8/10

        self.language = self.para_language.text()
        self.corpus = self.para_corpus.text()
        self.datafolder = self.para_datafolder.text()

        self.MinimumStemLength = self.para_MinimumStemLength.value()
        self.MaximumAffixLength = self.para_MaximumAffixLength.value()
        self.MinimumNumberofSigUses = self.para_MinimumNumberofSigUses.value()

        config_path = Path(self.configfilename)

        config = {'language': self.language,
                  'corpus': self.corpus,
                  'datafolder': self.datafolder}

        with config_path.open('w') as config_file:
            json.dump(config, config_file)



