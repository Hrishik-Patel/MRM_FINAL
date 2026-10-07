import sys
import math
import serial
import threading
import time

import numpy as np
import pyqtgraph as pg

from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QLabel,
    QComboBox,
    QWidget,
    QHBoxLayout
)
from PyQt6.QtCore import QTimer


PORT = "/dev/cu.usbserial-0001"
BAUDRATE = 115200

MAX_LIDAR_DISTANCE = 12000


# ============================================================
# LIDAR
# ============================================================

class RPLidarA1:

    def __init__(self):

        self.ser = None
        self.running = False

        self.lock = threading.Lock()

        self.scan = np.full(
            360,
            np.nan,
            dtype=float
        )

        self.points_received = 0

    def connect(self):

        self.ser = serial.Serial(
            PORT,
            BAUDRATE,
            bytesize=8,
            parity=serial.PARITY_NONE,
            stopbits=1,
            timeout=1
        )

        print("Connected:", PORT)

    def command(self, command):

        self.ser.write(
            bytes([0xA5, command])
        )

    def start(self):

        self.connect()

        print("Resetting LiDAR...")

        self.command(0x40)

        time.sleep(2)

        self.ser.reset_input_buffer()

        print("Starting scan...")

        self.command(0x20)

        self.running = True

        self.thread = threading.Thread(
            target=self.read_loop,
            daemon=True
        )

        self.thread.start()

    def read_loop(self):

        print("Reading LiDAR...")

        while self.running:

            try:

                data = self.ser.read(5)

                if len(data) != 5:
                    continue

                b0, b1, b2, b3, b4 = data

                # Validate packet
                start_flag = b0 & 0x01
                inverse_start = (b0 >> 1) & 0x01

                if start_flag == inverse_start:
                    continue

                quality = b0 >> 2

                if quality == 0:
                    continue

                # Angle
                angle_raw = (
                    (b1 >> 1)
                    | (b2 << 7)
                )

                angle = angle_raw / 64.0

                # Distance
                distance_raw = (
                    b3
                    | (b4 << 8)
                )

                distance = distance_raw / 4.0

                if distance <= 0:
                    continue

                if distance > MAX_LIDAR_DISTANCE:
                    continue

                index = int(angle) % 360

                with self.lock:

                    self.scan[index] = distance
                    self.points_received += 1

            except Exception as e:

                print("Read error:", e)

                break

    def get_scan(self):

        with self.lock:
            return self.scan.copy()

    def stop(self):

        self.running = False

        try:

            self.command(0x25)

            time.sleep(0.2)

            self.ser.close()

        except Exception:
            pass


# ============================================================
# GUI
# ============================================================

class LidarGUI(QMainWindow):

    def __init__(self, lidar):

        super().__init__()

        self.lidar = lidar

        self.setWindowTitle(
            "RPLIDAR A1M8 Live Scanner"
        )

        self.resize(1000, 800)

        # Current display scale
        self.scale = 5.0

        # ====================================================
        # MAIN WIDGET
        # ====================================================

        central = QWidget()

        self.setCentralWidget(
            central
        )

        layout = QHBoxLayout()

        central.setLayout(
            layout
        )

        # ====================================================
        # PLOT
        # ====================================================

        self.plot = pg.PlotWidget()

        self.plot.setBackground(
            "black"
        )

        self.plot.setAspectLocked(
            True
        )

        self.plot.showGrid(
            x=True,
            y=True,
            alpha=0.25
        )

        self.plot.setLabel(
            "bottom",
            "X",
            units="m"
        )

        self.plot.setLabel(
            "left",
            "Y",
            units="m"
        )

        layout.addWidget(
            self.plot
        )

        # ====================================================
        # SCALE CONTROL
        # ====================================================

        control = QWidget()

        control_layout = QHBoxLayout()

        control.setLayout(
            control_layout
        )

        self.scale_label = QLabel(
            "Scale:"
        )

        self.scale_dropdown = QComboBox()

        self.scale_dropdown.addItems([
            "1 m",
            "2 m",
            "3 m",
            "5 m",
            "7 m",
            "10 m",
            "12 m"
        ])

        self.scale_dropdown.setCurrentText(
            "5 m"
        )

        self.scale_dropdown.currentTextChanged.connect(
            self.change_scale
        )

        control_layout.addWidget(
            self.scale_label
        )

        control_layout.addWidget(
            self.scale_dropdown
        )

        control.setParent(
            self.plot
        )

        control.move(
            15,
            15
        )

        control.adjustSize()

        # ====================================================
        # STATUS
        # ====================================================

        self.status = QLabel(
            "Connecting..."
        )

        self.status.setStyleSheet(
            """
            QLabel {
                color: white;
                background-color: rgba(0,0,0,180);
                padding: 8px;
                font-size: 14px;
            }
            """
        )

        self.status.setParent(
            self.plot
        )

        self.status.move(
            15,
            60
        )

        # ====================================================
        # INITIAL SCALE
        # ====================================================

        self.set_scale(
            self.scale
        )

        # ====================================================
        # UPDATE TIMER
        # ====================================================

        self.timer = QTimer()

        self.timer.timeout.connect(
            self.update_plot
        )

        self.timer.start(
            30
        )

    # ========================================================
    # CHANGE SCALE
    # ========================================================

    def change_scale(self, value):

        value = value.replace(
            " m",
            ""
        )

        self.scale = float(
            value
        )

        self.set_scale(
            self.scale
        )

    # ========================================================
    # SET SCALE
    # ========================================================

    def set_scale(self, meters):

        mm = meters * 1000

        self.plot.setXRange(
            -mm,
            mm,
            padding=0
        )

        self.plot.setYRange(
            -mm,
            mm,
            padding=0
        )

    # ========================================================
    # UPDATE
    # ========================================================

    def update_plot(self):

        scan = self.lidar.get_scan()

        valid = ~np.isnan(scan)

        if not np.any(valid):

            self.status.setText(
                "Waiting for LiDAR data..."
            )

            return

        angles = np.arange(
            360
        )[valid]

        distances = scan[valid]

        theta = np.radians(
            angles
        )

        # Convert mm → m
        distances_m = distances / 1000.0

        x = (
            distances_m *
            np.cos(theta)
        )

        y = (
            distances_m *
            np.sin(theta)
        )

        self.scatter.setData(
            x=x,
            y=y
        )

        self.status.setText(
            f"Points: {len(x)}\n"
            f"Scale: {self.scale:.0f} m"
        )

    # ========================================================
    # CLOSE
    # ========================================================

    def closeEvent(self, event):

        self.lidar.stop()

        event.accept()


# ============================================================
# MAIN
# ============================================================

def main():

    app = QApplication(
        sys.argv
    )

    lidar = RPLidarA1()

    try:

        lidar.start()

    except Exception as e:

        print(
            "LiDAR error:",
            e
        )

        return

    window = LidarGUI(
        lidar
    )

    # Create scatter after plot exists
    window.scatter = pg.ScatterPlotItem(
        size=5,
        pen=None,
        brush=pg.mkBrush(
            0,
            255,
            0,
            220
        )
    )

    window.plot.addItem(
        window.scatter
    )

    # Center marker
    window.center = pg.ScatterPlotItem(
        x=[0],
        y=[0],
        size=12,
        pen=pg.mkPen("red"),
        brush=pg.mkBrush("red")
    )

    window.plot.addItem(
        window.center
    )

    window.show()

    sys.exit(
        app.exec()
    )


if __name__ == "__main__":
    main()