import os
import sys
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QPushButton, QTextEdit, QFileDialog,
                               QMainWindow)
from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QIcon, QTextCursor, QTextBlockFormat, Qt
from ffmpeg_progress_yield import FfmpegProgress
from tqdm import tqdm
import subprocess
import configparser


class MainWindow(QMainWindow):
    output_signal = Signal(str)
    progress_signal = Signal()
    success_signal = Signal()
    error_signal = Signal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("PyAnime4K-GUI v1.1")
        self.setWindowIcon(QIcon('Resources/anime.ico'))
        self.setGeometry(100, 100, 1000, 650)
        self.selected_files = None
        self.std_thread = QThread()
        self.encode_thread = QThread()
        self.pass_param_thread = QThread()
        self.current_file = None
        self.process = None
        self.cancel_encode = False
        self.progress_msg = None
        self.error_msg = None
        self.output_dir = None
        self.error_signal.connect(self.err_msg_handler)
        self.progress_signal.connect(self.update_progress)

        # Create a central widget
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        # Layout setup
        layout = QVBoxLayout(central_widget)

        # Create a QTextEdit widget for logs
        self.log_widget = QTextEdit(self)
        self.log_widget.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self.log_widget.setReadOnly(True)

        # Add the log widget to the layout
        layout.addWidget(self.log_widget)

        # Create buttons
        self.edit_button = QPushButton("Edit Config File")
        self.select_button = QPushButton("Select Video Files")
        self.output_button = QPushButton("Open Output Folder")
        self.upscale_button = QPushButton("Upscale")
        self.cancel_button = QPushButton("Cancel")

        # Add buttons to the layout
        layout.addWidget(self.edit_button)
        layout.addWidget(self.select_button)
        layout.addWidget(self.output_button)
        layout.addWidget(self.upscale_button)
        layout.addWidget(self.cancel_button)

        self.pass_param_thread.run = self.pass_param
        # Connect button clicks to log messages
        self.edit_button.clicked.connect(self.open_config)
        self.select_button.clicked.connect(self.open_file_dialog)
        self.output_button.clicked.connect(self.open_output_folder)
        self.upscale_button.clicked.connect(self.thread_check)
        self.cancel_button.clicked.connect(self.cancel_operation)
        open("output.txt", "w").close()
        self.append_ascii_art()


    def thread_check(self):
        if self.pass_param_thread.isRunning():
            return
        else:
            self.pass_param_thread.start()

    def open_config(self): # noqa
        os.startfile(f"{os.getcwd()}/Resources/Config.ini")

    def open_output_folder(self): # noqa
        if self.output_dir:
            os.startfile(f"{self.output_dir}")

    def cancel_operation(self):
        self.cancel_encode = True

    def log_message(self, message):
        self.log_widget.append(message)

    def open_file_dialog(self):
        file_paths, _ = QFileDialog.getOpenFileNames(self, "Select Files", "", "Text Files (*.mkv)")
        if file_paths:
            self.log_widget.clear()
            self.selected_files = file_paths
            for file in self.selected_files:
                self.log_widget.append(f"[Added] - {file}")
        output_path = QFileDialog.getExistingDirectory(None, "Select Output Directory")
        if output_path:
            self.output_dir = output_path

    def update_progress(self):
        # noinspection SpellCheckingInspection
        self.log_widget.append(f"[Upscaling] - {os.path.basename(self.current_file)} - {self.progress_msg}")

    def err_msg_handler(self):
        with open("output.txt", "a") as file:
            file.write(self.error_msg + "\n")
        # noinspection SpellCheckingInspection
        self.log_widget.append(f"Upscaling Finished Check Output.txt for Details.")

    def start_encoding(self, process):
        # noinspection SpellCheckingInspection
        with tqdm(total=100, position=1, desc="Progress") as pbar:
            # noinspection SpellCheckingInspection
            for progress in process.run_command_with_progress(popen_kwargs={"creationflags" :
                                                                                subprocess.CREATE_NO_WINDOW}):
                if self.cancel_encode:
                    process.quit()
                    # noinspection SpellCheckingInspection
                    self.log_widget.append("Upscaling Canceled.")
                    break
                pbar.update(progress - pbar.n)
                # noinspection SpellCheckingInspection
                tqdm_line = pbar.format_meter(
                    n=pbar.n,
                    total=pbar.total,
                    elapsed=pbar.format_dict['elapsed'],
                    ncols=80,
                )
                self.progress_msg = tqdm_line
                self.progress_signal.emit()
        self.error_msg = str(process.stderr)
        self.error_signal.emit()

    def pass_param(self):
        self.cancel_encode = False
        config = configparser.ConfigParser()
        config.read('Resources/Config.ini')
        width = config['Settings']['width']
        height = config['Settings']['height']
        bit_rate = config['Settings']['bit_rate']
        preset = config['Settings']['preset']
        codec = config['Settings']['codec']
        shader = config['Settings']['shader']
        for file in self.selected_files:
            # noinspection SpellCheckingInspection
            command = [
                "ffmpeg/ffmpeg.exe",
                "-progress", "pipe:1",
                "-hide_banner", "-y", "-hwaccel_device", "opencl",
                "-i", f"{file}",
                "-init_hw_device", "vulkan",
                "-vf", f"format=yuv420p,hwupload,"
                f"libplacebo=w={width}:h={height}:upscaler=ewa_lanczos:custom_shader_path=shaders/{shader},"
                "format=yuv420p",
                "-map", "0", "-c:a", "copy", "-c:d", "copy",
                "-b:v", f"{bit_rate}", "-maxrate", "20M", "-bufsize", "40M",
                "-c:v", f"{codec}", "-preset", f"{preset}",
                f"{self.output_dir}\\{os.path.basename(file).strip('.mkv')}-upscaled.mkv"
            ]
            if self.cancel_encode:
                break
            self.current_file = file
            process = FfmpegProgress(command)
            self.cancel_encode = False
            self.encode_thread.run = lambda: self.start_encoding(process)
            self.encode_thread.start()
            self.encode_thread.wait()

    def append_ascii_art(self):
        ascii_art = """
  ⠀⢀⣀⣀⣤⣤⣤⣤⣶⣶⣶⣶⣿⡿⡫⢶⠏⡃⣥⣩⢵⣶⣾⣿⣿⣿⣿⣿⣷⣿⣬⣿⣒⣪⢨⣻⠿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠏⠜⠩⣔⠪⣑⣶⣾⣿⣿⣿⣿⣿⣿⣟⣻⣿⣿⣿⣿⡯⣟⠳⣭⣻⢦⣛⢿⣿⠟⠛⠛⠛⠛⠛⠛⠛⠛
⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⢟⠱⣢⣵⣯⠔⡫⢖⣿⣿⣿⣿⣿⣿⣿⣺⡿⣿⣿⣿⣿⣿⣯⣓⢿⡿⣑⢝⡲⣕⠝⢿⣷⣦⣤⣀⡀⠀⠀⠀
⣿⣿⣿⣿⣿⣿⣿⣿⢟⢕⣵⣿⡛⢿⣿⣿⣎⠵⣿⣿⣿⣿⣿⠿⠿⠿⢯⣿⣿⣿⣿⣿⣿⣿⢿⣙⢮⣑⢮⣿⣦⢣⡻⣿⣿⣿⣿⣿⣶⣤
⣿⣿⣿⣿⣿⡿⠋⢔⣥⣿⣿⣿⣿⣄⠀⠉⠉⠉⠉⠉⠁⠀⠀⠀⠀⠀⠀⠀⠈⠉⠛⢿⣿⢏⡳⣭⣳⣾⣿⣿⣿⣷⢕⢎⢿⣿⣿⣿⣿⣿
⣿⣿⣿⣿⡿⡡⣱⢛⢿⣿⣿⣿⣿⡿⠃⠀⠀⠀⠀⠀⢌⣆⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠳⣬⣾⣿⣿⣿⡟⡙⢌⢦⢨⣃⢿⣿⣿⣿⣿
⣿⣿⣿⣿⢡⠱⠣⡡⠩⠻⠿⠋⠁⠀⠀⠀⠀⠀⠀⠀⣾⣿⣧⡀⠀⠀⠀⢦⡂⠀⠀⠀⠀⠀⠈⠛⢿⣿⠡⡱⣘⣬⣶⣶⣏⣎⣿⣿⣿⣿
⣿⣿⣿⡇⠢⣷⣷⣷⣱⢠⡀⠀⠀⠀⠀⠀⠀⣀⠀⢸⣿⣿⣿⣿⣦⡀⠀⠘⡇⡄⡀⠐⠀⠀⠀⠀⠈⠻⣷⣷⣿⣿⣿⣿⣿⡞⢸⣿⣿⣿
⣿⣿⡟⡈⢂⢹⣿⣿⣿⣿⣿⠇⠀⠀⠀⠀⠀⣾⠀⣿⣿⣿⣿⣿⣿⣿⣦⣀⠱⣎⡀⠘⠄⠀⠀⠀⠀⠀⠈⢙⡋⠇⠏⣿⣿⡇⣻⣿⣿⣿
⣿⣿⡧⣼⣿⣿⣿⣿⣿⠟⠁⠀⠀⠀⠀⠀⢸⣛⣓⣛⠛⠛⢿⣿⣿⣿⣫⠅⠉⣍⣥⠚⢷⠀⠀⠀⠀⠀⠹⢻⢿⡏⠏⡏⡟⣷⢱⡿⠿⠿
⣿⣿⡇⣿⣿⣿⠻⠿⣅⣀⣀⡀⠀⠀⠀⡄⣿⠋⣡⣴⣦⢈⢿⡎⣿⣿⣶⡇⣾⠋⠙⣷⠸⡆⠀⢀⢄⠀⠀⠈⣩⣓⣥⣥⣃⣿⢨⣤⣤⣤
⡛⠛⠃⢻⣿⣿⣄⣤⣧⣿⣿⠟⠀⠀⠀⢡⡅⢹⣏⣀⣹⡇⢸⣏⢹⣿⣿⣖⡻⠷⠾⢟⣲⢰⠀⠑⢸⠀⣶⣿⣿⣿⣿⣿⣿⣿⢀⠀⠀⠀
⣿⣿⣿⡎⣟⢻⠹⡉⢏⠻⡜⢁⣠⠀⠢⠸⣷⣜⣿⣿⣫⣼⣼⣛⣘⣧⣿⣿⣿⣭⣨⣥⣶⠸⢦⡀⡄⠀⠈⢟⢿⢿⣿⣿⣿⢣⣿⣿⣿⣿
⣿⣿⣿⣿⡘⢦⣢⣹⣮⣶⣷⣿⣿⢀⠕⢁⢻⣿⣿⠿⢛⣫⣭⣵⣶⣶⣶⣿⣿⣿⣶⢀⡏⠦⡠⠜⢰⢆⡤⣵⣕⣵⣾⢛⢡⣿⣿⣿⣿⣿
⣿⣿⣿⣿⣿⣌⢻⣿⣿⣿⣿⡿⡟⢇⠱⣅⠈⢿⣦⡸⡿⠿⣛⣫⣭⣽⣶⣶⣶⠶⣢⣾⠏⠂⠠⢄⢸⣭⡪⢊⡿⢋⣴⣿⣾⣿⣿⣿⣿⣿
⣿⣿⣿⣿⣿⠋⢄⣍⠻⣿⡃⢝⡪⣵⢟⡢⢀⡬⡛⢿⣦⣽⣛⣛⣛⣛⣛⣯⣵⡾⠟⠁⠀⡀⢮⡑⣘⠿⠓⠥⣶⣿⣿⡿⣻⣿⣿⣿⣿⣿
⣿⣿⣿⡿⠇⢢⣿⣿⣿⣶⣝⣛⠿⢬⣕⣲⣟⣁⡄⡀⠈⣉⡛⠛⠿⠿⠟⢫⣉⣤⣾⠠⠰⢟⣩⣥⣶⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
⣿⣿⡿⠁⣱⣿⣿⣿⣿⣿⣿⣿⠃⠀⠀⠉⠉⠛⠛⠓⠂⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⢰⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
⣿⡿⠑⣼⣿⣿⣿⣿⣿⣿⣿⣿⠀⠀⠀⠀⠀⠀⠀⠀⠀⢿⣿⣿⣿⣿⣿⣿⡿⣋⣿⡈⢹⣿⣿⣿⠉⠉⠉⠉⠉⠙⠛⠛⠛⠛⠋⠛⠛⠉
⣿⣇⣾⣿⣿⣿⣿⣿⣿⣿⣿⣿⠀⠀⠀⠀⠀⣠⠰⠚⣼⣷⣭⡻⠿⡿⢿⣫⣾⣿⢸⣧⠀⠒⡘⠿⠀⠀⠀⠀⠀⠀⠀⠀⠀⣷⣿⣿⣷⣶
⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡿⠇⠀⠴⠂⡾⠁⣠⣾⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⢸⣿⣷⠄⢾⠀⣳⣄⡀⠦⠤⠤⠤⢤⣰⣿⣿⣿⣿⣿
⣿⣿⣿⣿⣿⠟⣩⣴⣶⣾⣿⣿⣿⣾⡄⢸⡇⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡿⣸⡿⢡⡶⠃⣸⣿⣿⣿⣿⣿⣿⣿⣿⣶⣬⡙⢿⣿⣿
⣿⣿⣿⠟⣡⣾⣿⣿⢿⣿⣿⣿⣿⣿⣷⡈⣇⢛⣛⣻⠿⢿⣿⣿⣿⠿⢟⣛⣭⡥⢁⣴⣏⣡⣶⣿⣿⣿⢻⣿⣿⣿⣿⣿⠛⣿⣿⣎⠻⣿
⣿⣿⠁⣺⡟⠿⡿⠛⠈⣿⣽⣿⣿⡟⠻⣿⠇⣿⣿⣿⣿⣶⣿⣟⣥⣾⣿⣿⣿⢰⣿⣿⣿⣿⣿⣿⣟⣓⡄⠸⣿⣿⡿⠫⠀⢸⣿⣿⣥⠹
⣿⠣⡪⠏⠀⠀⠨⠀⡀⢿⣿⣿⡿⢰⠇⡽⣸⣿⣿⣿⣿⠟⠡⣿⣿⣿⣿⣿⣿⢸⣿⣿⣿⣿⢿⣿⣿⢻⠀⠠⠙⠛⠁⠀⠀⠺⣿⠛⢛⣸
⣅⠍⠀⠀⠀⠀⠘⠀⢠⣺⣿⣿⣿⣦⣾⢃⡹⠟⠿⠟⣡⠆⣆⠛⢿⡿⣿⢟⡁⣼⣿⣿⠿⢽⠯⡠⠀⠈⠀⠀⠀⠀⠁⠀⠁⠀⠉⠠⠨⢿
⠃⠀⠀⠀⠀⠀⠀⢀⣨⡸⣛⣿⣿⣿⡟⣴⠋⢊⣷⣾⡟⢀⣿⢸⠢⠶⣴⣿⡇⣿⣿⣿⣷⣆⣑⢱⡀⠀⠂⠀⠀⠀⠀⡄⠀⠆⠀⠀⣴⣿
        """
        cursor = self.log_widget.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)

        block_format = QTextBlockFormat()
        block_format.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cursor.insertBlock(block_format)
        cursor.insertText(ascii_art)
        self.log_widget.setTextCursor(cursor)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet("""
            QTextEdit {
                background-color: #2b2d30;
                border: none;
            }
            QPushButton {
                background-color: #2b2d30;
            }
            QPushButton:hover {
                border-style: inset;
                border-width: 2px;
                background-color: #61646e;
            }
        """)
    window = MainWindow()
    window.show()
    app.exec()
