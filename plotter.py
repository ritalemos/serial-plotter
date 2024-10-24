import numpy as np
import pandas as pd
import pyqtgraph as pg
import argparse
import os
import random
import serial
import sys
from collections.abc import Callable
from functools import partial
from PyQt5.QtWidgets import QApplication
from PyQt5 import QtCore

app = QApplication([])
win = pg.GraphicsLayoutWidget(show=False, title="Plotter Serial SC")
win.showFullScreen()

# Plot combinado dos dados
plot_combined = win.addPlot(title="Temperatura A e B", col=0, row=0)
plot_combined.setLabel('bottom', "Tempo decorrido (s)")
plot_combined.setLabel('left', "Temperatura (°C)")
plot_combined.showGrid(x=True, y=True, alpha=0.5)
curve_a_combined = plot_combined.plot(pen="c", name="Temperatura A")
curve_b_combined = plot_combined.plot(pen="g", name="Temperatura B")

# Plot individual dos dados
plot_a = win.addPlot(title="Temperatura A", col=1, row=0)
plot_a.setLabel('bottom', "Tempo decorrido (s)")
plot_a.setLabel('left', "Temperatura (°C)")
plot_a.showGrid(x=True, y=True, alpha=0.5)
curve_a = plot_a.plot(pen="c")

plot_b = win.addPlot(title="Temperatura B", col=1, row=1)
plot_a.setLabel('bottom', "Tempo decorrido (s)")
plot_a.setLabel('left', "Temperatura (°C)")
plot_b.showGrid(x=True, y=True, alpha=0.5)
curve_b = plot_b.plot(pen="g")


plot_c = win.addPlot(title="Duty", col=0, row=1)
plot_c.setLabel('bottom', "Tempo decorrido (s)")
plot_c.setLabel('left', "Duty Cycle (%)")
plot_c.showGrid(x=True, y=True, alpha=0.5)
curve_c = plot_c.plot(pen="r")


temp_a_data = np.array([])
temp_b_data = np.array([])
duty_data = np.array([])
time_data = []

plot_views = ["C", "IC", "A", "B"]
current_mode = -1


def toggle_plot_view():
    global current_mode

    current_mode = (current_mode + 1) % len(plot_views)
    match plot_views[current_mode]:
        case "C":
            plot_combined.show()
            plot_a.hide()
            plot_b.hide()
            plot_c.show()
        case "IC":
            plot_combined.hide()
            plot_a.show()
            plot_b.show()
            plot_c.hide()
        case "A":
            plot_combined.hide()
            plot_a.show()
            plot_b.hide()
            plot_c.hide()
        case "B":
            plot_combined.hide()
            plot_a.hide()
            plot_b.show()
            plot_c.hide()


last_t = random.randint(20, 45) + random.random()


def get_data_dummy():
    global last_t

    t1 = last_t + (random.random() - random.random())
    t2 = last_t + (random.random() - random.random())
    last_t = (t1 + t2) / 2
    data = f"> {t1:.2f};{t2:.2f}"
    return data


def get_data_serial(ser):
    data = ser.readline().decode("utf-8").strip()
    return data


def update_plots(get_data: Callable, log_f_path: str):
    global temp_a_data, temp_b_data, duty_data, time_data

    data = get_data()

    if data.startswith("> "):
        temp_a, temp_b, duty = [float(t) for t in data[2:].split(";")]

        timestamp = pd.Timestamp.now()

        temp_a_data = np.append(temp_a_data, temp_a)
        temp_b_data = np.append(temp_b_data, temp_b)
        duty_data = np.append(duty_data, duty)

        time_data.append(timestamp)
        plot_seconds = [(t - time_data[0]).total_seconds() for t in time_data]

        with open(log_f_path, "a") as f:
            f.write(f"{int(plot_seconds[-1] / 60):02d}:{plot_seconds[-1]:06.3f},{temp_a},{temp_b}\n")

        curve_a_combined.setData(plot_seconds, temp_a_data)
        curve_b_combined.setData(plot_seconds, temp_b_data)
        curve_a.setData(plot_seconds, temp_a_data)
        curve_b.setData(plot_seconds, temp_b_data)
        curve_c.setData(plot_seconds, duty_data)


def key_press_event(event):
    if event.key() == QtCore.Qt.Key_Space:
        toggle_plot_view()
    elif event.key() == QtCore.Qt.Key_Escape:
        sys.exit(0)


def arg_parse():
    parser = argparse.ArgumentParser(description="Plotter serial para sensores.")
    parser.add_argument(
        "port",
        type=str,
        help="Porta serial a ser plotada.")
    parser.add_argument(
        "baud",
        type=int,
        help="Baud rate da porta serial.")
    parser.add_argument(
        "--update-delay",
        "-u",
        metavar="<delay_ms>",
        type=int,
        default=100,
        help="Tempo entre atualizações do plot, em milissegundos."
    )
    parser.add_argument(
        "--output-log-path",
        "-o",
        metavar="<path/to/out>",
        type=str,
        default="./temp_logs/",
        help="Diretório de saída dos logs de gravação."
    )

    return parser.parse_args()


def main():
    args = arg_parse()
    port = args.port
    baud = args.baud
    update_delay = args.update_delay
    log_path = args.output_log_path

    dt = pd.Timestamp.now()
    df = pd.DataFrame(columns=["time", "temp_a", "temp_b"])

    if port != "sim":
        try:
            ser = serial.Serial(port, baud, timeout=1)
            get_data = partial(get_data_serial, ser)
        except serial.SerialException:
            print(f"Não foi possível abrir a porta serial {port}@{baud}")
            sys.exit(1)
    else:
        get_data = get_data_dummy

    try:
        os.mkdir(log_path)
    except FileExistsError:
        pass

    print(f"Salvando dados em {log_path}")
    log_file_path = log_path + f"log_{dt.year}-{dt.month}-{dt.day}-{dt.hour}-{dt.minute}-{dt.second}.csv"
    df.to_csv(log_file_path, index=False)

    timer = QtCore.QTimer()
    timer.timeout.connect(partial(update_plots, get_data, log_file_path))

    win.keyPressEvent = key_press_event
    toggle_plot_view()

    timer.start(update_delay)
    try:
        QApplication.instance().exec_()
    except KeyboardInterrupt:
        print("Exiting...")
        ser.close()
        sys.exit()


if __name__ == "__main__":
    main()
