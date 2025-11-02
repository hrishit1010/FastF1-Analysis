import os
import sys
import shutil
import threading
import pandas as pd
from random import randint
from PyQt5 import QtGui, QtCore
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QProgressBar, QMessageBox, QComboBox
)

# Create necessary directories
CWD = os.getcwd()
for folder in ['cache', 'plot']:
    os.makedirs(os.path.join(CWD, folder), exist_ok=True)

# Import custom script for telemetry plotting
import script

# Load datasets
events_df = pd.read_csv(r"C:\Users\hrish\Downloads\formula1-telemetry-tool-main\formula1-telemetry-tool-main\data\events.csv")
drivers_df = pd.read_csv(r"C:\Users\hrish\Downloads\formula1-telemetry-tool-main\formula1-telemetry-tool-main\data\drivers.csv")
laps_df = pd.read_csv(r"C:\Users\hrish\Downloads\formula1-telemetry-tool-main\formula1-telemetry-tool-main\data\laps.csv")
placeholder_path = r"C:\Users\hrish\Downloads\formula1-telemetry-tool-main\formula1-telemetry-tool-main\img\placeholder.png"

# Dropdown options
year_options = ['Select Year'] + events_df.columns[1:].tolist()
session_types = ['Race', 'Qualifying', 'FP1', 'FP2', 'FP3']
analysis_options = ['Lap Time', 'Fastest Lap', 'Fastest Sectors', 'Full Telemetry']

# Stylesheet
AppStyle = """
#RedProgressBar {
    min-height: 14px;
    max-height: 14px;
    border-radius: 3px;
    border: 1px solid #FFFFFF;
    background-color: #1C1C1C;
}
#RedProgressBar::chunk {
    background-color: #FF1E00;
    border-radius: 3px;
}

QWidget {
    background-color: #0F0F0F;
    color: #FFFFFF;
    font-family: 'Segoe UI', sans-serif;
    font-size: 10.5pt;
}

QLabel {
    font-weight: bold;
    color: #E0E0E0;
}

QPushButton {
    background-color: #DC0000;
    color: white;
    padding: 6px 12px;
    border: none;
    border-radius: 4px;
    font-weight: bold;
}

QPushButton:hover {
    background-color: #FF1E00;
}

QComboBox {
    padding: 1px;
    background-color: #1F1F1F;
    color: white;
    border: 1px solid #444;
    border-radius: 3px;
}
"""


class RedProgressBar(QProgressBar):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setValue(0)
        if self.minimum() != self.maximum():
            self.timer = QtCore.QTimer(self, timeout=self.update_progress)
            self.timer.start(randint(1, 3) * 1000)

    def update_progress(self):
        if self.value() >= 100:
            self.timer.stop()
            self.timer.deleteLater()
            return
        self.setValue(self.value() + 1)


class F1TelemetryApp(QWidget):
    def __init__(self):
        super().__init__()
        self.build_ui()

    def build_ui(self):
        self.setFixedSize(1200,600)
        self.setWindowTitle("F1 Race Insights - Telemetry Analyzer")
        self.setWindowIcon(QtGui.QIcon(r"C:\Users\hrish\Downloads\formula1-telemetry-tool-main\formula1-telemetry-tool-main\img\f1.png"))

        # Layouts
        main_layout = QHBoxLayout()
        controls_layout = QVBoxLayout()

        # UI Components
        self.year_selector = QComboBox()
        self.venue_selector = QComboBox()
        self.session_selector = QComboBox()
        self.primary_driver = QComboBox()
        self.secondary_driver = QComboBox()
        self.analysis_mode = QComboBox()
        self.lap_selector = QComboBox()
        self.lap_selector.hide()

        self.run_btn = QPushButton('▶ START ANALYSIS')
        self.save_btn = QPushButton('💾 EXPORT IMAGE')
        self.save_btn.hide()

        self.plot_view = QLabel()
        self.plot_view.setPixmap(QPixmap(placeholder_path).scaledToWidth(670, QtCore.Qt.SmoothTransformation))

        self.progress = RedProgressBar(self, minimum=0, maximum=0, textVisible=False, objectName="RedProgressBar")
        self.progress.hide()

        # Add items to dropdowns
        self.year_selector.addItems(year_options)
        self.session_selector.addItems(session_types)
        self.analysis_mode.addItems(analysis_options)

        for combo in [self.venue_selector, self.primary_driver, self.secondary_driver]:
            combo.addItem("Select")

        # Labels
        controls_layout.addWidget(QLabel("SELECT SEASON"))
        controls_layout.addWidget(self.year_selector)
        controls_layout.addWidget(QLabel("GRAND PRIX VENUE"))
        controls_layout.addWidget(self.venue_selector)
        controls_layout.addWidget(QLabel("SESSION TYPE"))
        controls_layout.addWidget(self.session_selector)
        controls_layout.addWidget(QLabel("DRIVER ONE"))
        controls_layout.addWidget(self.primary_driver)
        controls_layout.addWidget(QLabel("DRIVER TWO"))
        controls_layout.addWidget(self.secondary_driver)
        controls_layout.addWidget(QLabel("ANALYSIS MODE"))
        controls_layout.addWidget(self.analysis_mode)
        controls_layout.addWidget(self.lap_selector)
        controls_layout.addWidget(self.progress)
        controls_layout.addWidget(self.run_btn)
        controls_layout.addWidget(self.save_btn)
        controls_layout.addStretch()

        main_layout.addLayout(controls_layout)
        main_layout.addWidget(self.plot_view)

        self.setLayout(main_layout)

        # Signals
        self.year_selector.currentTextChanged.connect(self.update_dropdowns)
        self.venue_selector.currentTextChanged.connect(self.update_lap_selector)
        self.analysis_mode.currentTextChanged.connect(self.toggle_lap_visibility)
        self.run_btn.clicked.connect(self.run_analysis_thread)
        self.save_btn.clicked.connect(self.save_plot)

    def current_input(self):
        return [
            self.year_selector.currentText(),
            self.venue_selector.currentText(),
            self.session_selector.currentText(),
            self.primary_driver.currentText(),
            self.secondary_driver.currentText(),
            self.analysis_mode.currentText(),
            self.lap_selector.currentText()
        ]

    def update_dropdowns(self):
        selected_year = self.year_selector.currentText()
        if selected_year != 'Select Year':
            self.venue_selector.clear()
            self.primary_driver.clear()
            self.secondary_driver.clear()

            self.venue_selector.addItems(events_df[selected_year].dropna().tolist())
            self.primary_driver.addItems(drivers_df[selected_year].dropna().tolist())
            self.secondary_driver.addItems(drivers_df[selected_year].dropna().tolist())

    def update_lap_selector(self):
        self.lap_selector.clear()
        selected_race = self.venue_selector.currentText()
        if selected_race != 'Select':
            try:
                total_laps = laps_df.loc[laps_df.event == selected_race, 'laps'].values[0]
                self.lap_selector.addItems(['Select Lap'] + [str(i) for i in range(1, total_laps + 1)])
            except IndexError:
                self.lap_selector.addItem("No Laps Found")

    def toggle_lap_visibility(self):
        if self.analysis_mode.currentText() == 'Fastest Sectors':
            self.lap_selector.show()
        else:
            self.lap_selector.hide()

    def display_plot(self, path):
        self.plot_view.setPixmap(QPixmap(path).scaledToWidth(640, QtCore.Qt.SmoothTransformation))

    def run_analysis_thread(self):
        thread = threading.Thread(target=self.run_analysis)
        thread.start()

    def run_analysis(self):
        input_data = self.current_input()
        if input_data[0] == 'Select Year':
            self.run_btn.setText("⚠ Select Valid Year")
            return
        self.run_btn.setText("Running...")
        self.save_btn.hide()
        self.progress.show()
        script.get_race_data(input_data)
        self.plot_path = os.path.join(r'C:\Users\hrish\Downloads\formula1-telemetry-tool-main\formula1-telemetry-tool-main\plot')
        self.display_plot(self.plot_path)
        self.run_btn.setText("▶ RUN NEW ANALYSIS")
        self.progress.hide()
        self.save_btn.show()

    def save_plot(self):
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        shutil.copy(self.plot_path, desktop)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyleSheet(AppStyle)
    f1_app = F1TelemetryApp()
    f1_app.show()
    sys.exit(app.exec_())
