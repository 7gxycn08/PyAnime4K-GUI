import os
import sys
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QPushButton, QTextEdit, QFileDialog,
                               QMainWindow, QMessageBox)
from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QIcon, QTextCursor, QTextBlockFormat, Qt
from ffmpeg_progress_yield import FfmpegProgress
from tqdm.asyncio import tqdm
import subprocess
import configparser
import winsound
import cv2
import asyncio


class MainWindow(QMainWindow):
    output_signal = Signal(str)
    progress_signal = Signal()
    success_signal = Signal()
    error_signal = Signal()
    error_box_signal = Signal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("PyAnime4K-GUI v1.6")
        self.setWindowIcon(QIcon('Resources/anime.ico'))
        self.setGeometry(100, 100, 1000, 650)
        self.selected_files = None
        self.std_thread = QThread()
        self.encode_thread = QThread()
        self.pass_param_thread = QThread()
        self.compare_thread = QThread()
        self.progress_thread = QThread()
        self.ffmpeg_progress = None
        self.current_file = None
        self.process = None
        self.cancel_encode = False
        self.progress_msg = None
        self.error_msg = None
        self.output_dir = None
        self.exception_msg = None
        self.paused = False
        self.combined = None
        self.split_pos = None
        self.error_signal.connect(self.err_msg_handler)
        self.progress_signal.connect(self.update_progress)
        self.error_box_signal.connect(self.error_box)

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
        self.compare_button = QPushButton("Compare Videos")
        self.select_button = QPushButton("Select Video Files")
        self.output_button = QPushButton("Open Output Folder")
        self.upscale_button = QPushButton("Upscale")
        self.cancel_button = QPushButton("Cancel")

        # Add buttons to the layout
        layout.addWidget(self.edit_button)
        layout.addWidget(self.compare_button)
        layout.addWidget(self.select_button)
        layout.addWidget(self.output_button)
        layout.addWidget(self.upscale_button)
        layout.addWidget(self.cancel_button)

        self.pass_param_thread.run = self.pass_param
        # Connect button clicks to log messages
        self.compare_button.clicked.connect(self.compare_selection)
        self.edit_button.clicked.connect(self.open_config)
        self.select_button.clicked.connect(self.open_file_dialog)
        self.output_button.clicked.connect(self.open_output_folder)
        self.upscale_button.clicked.connect(self.thread_check)
        self.cancel_button.clicked.connect(self.cancel_operation)
        open("output.txt", "w").close()
        self.append_ascii_art()

    def compare_selection(self):
        first, _ = QFileDialog.getOpenFileName(self, "Select First Video", "", "Video File (*.mkv)")
        if first:
            second, _ = QFileDialog.getOpenFileName(self, "Select Second Video", "",
                                                    "Video File (*.mkv)")
            if first and second:
                self.compare_thread.run = lambda: self.compare_videos_side_by_side(first, second)
                self.compare_thread.start()

    def thread_check(self):
        self.cancel_encode = False
        if self.pass_param_thread.isRunning():
            return
        else:
            self.pass_param_thread.start()

    def open_config(self):  # noqa
        os.startfile(f"{os.getcwd()}/Resources/Config.ini")

    def open_output_folder(self):  # noqa
        if self.output_dir:
            os.startfile(f"{self.output_dir}")

    def cancel_operation(self):
        self.cancel_encode = True

    def log_message(self, message):
        self.log_widget.append(message)

    def open_file_dialog(self):
        file_paths, _ = QFileDialog.getOpenFileNames(self, "Select Files", "",
                                                     "Video Files (*.mkv *.mp4)")
        if file_paths:
            self.log_widget.clear()
            self.selected_files = file_paths
            for file in self.selected_files:
                self.log_widget.append(f"[Added] - {file}")

        else:
            self.log_widget.clear()
            self.log_widget.append(f"File selection canceled.")
            return

        output_path = QFileDialog.getExistingDirectory(None, "Select Output Directory")
        if output_path:
            self.output_dir = output_path
            self.activateWindow()

        else:
            self.selected_files = None
            self.log_widget.clear()
            self.log_widget.append(f"File selection canceled.")
            self.activateWindow()

    def update_progress(self):
        # noinspection SpellCheckingInspection
        self.log_widget.append(f"[Upscaling] - {os.path.basename(self.current_file)} - {self.progress_msg}")

    def err_msg_handler(self):
        with open("output.txt", "a") as file:
            file.write(self.error_msg + "\n")
        # noinspection SpellCheckingInspection
        self.log_widget.append(f"Upscaling Finished Check Output.txt for Details.")

    async def start_encoding(self, process):
        # noinspection PyBroadException
        try:
            # noinspection SpellCheckingInspection
            pbar = tqdm(total=100, position=1, desc="Progress")
            # noinspection SpellCheckingInspection
            async for progress in process.async_run_command_with_progress(popen_kwargs={"creationflags":
                                                                                    subprocess.CREATE_NO_WINDOW}):
                if self.cancel_encode:
                    await process.async_quit_gracefully()
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
                pbar.refresh()
            pbar.close()

        except Exception as e:
            self.exception_msg = e
            self.cancel_encode = True
            self.error_msg = str(process.stderr)
            self.error_box_signal.emit()
            try:
                # noinspection SpellCheckingInspection
                subprocess.call(
                    ["taskkill", "/F", "/IM", "ffmpeg.exe"],
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
            except:
                return

    async def start_encoding_entry(self, process):
        await self.start_encoding(process)


    def pass_param(self):
        if self.cancel_encode:
            return
        config = configparser.ConfigParser()
        config.read('Resources/Config.ini')
        width = config['Settings']['width']
        height = config['Settings']['height']
        bit_rate = config['Settings']['bit_rate']
        codec = config['Settings']['codec']
        shader = config['Settings']['shader']
        for file in self.selected_files:
            sys.stdout.flush()
            sys.stderr.flush()
            # noinspection SpellCheckingInspection
            command = [
                "ffmpeg/ffmpeg.exe",
                "-loglevel", "info",
                "-i", f"{file}",
                "-map", "0:v",
                "-map", "0:s",
                "-map", "0:a",
                "-init_hw_device", "vulkan",
                "-smart_access_video", "True",
                "-vf", f"format=yuv420p,hwupload,"
                       f"libplacebo=w={width}:h={height}:upscaler=ewa_lanczos:custom_shader_path=shaders/{shader}",
                "-c:s", "copy", "-c:a", "copy", "-c:d", "copy",
                "-b:v", f"{bit_rate}", "-maxrate", "20M", "-bufsize", "40M",
                "-c:v", f"{codec}",
                f"{self.output_dir}\\{os.path.basename(file).strip('.mkv')}-upscaled.mkv"
            ]
            if self.cancel_encode:
                break
            self.current_file = file
            process = FfmpegProgress(command)
            self.cancel_encode = False
            self.encode_thread.run = lambda: asyncio.run(self.start_encoding_entry(process))
            self.encode_thread.start()
            self.encode_thread.wait()

    def error_box(self):
        warning_message_box = QMessageBox(self)
        warning_message_box.setIcon(QMessageBox.Icon.Critical)
        warning_message_box.setWindowTitle("PyAnime4K-GUI Error")
        warning_message_box.setWindowIcon(QIcon(r"Resources\anime.ico"))
        warning_message_box.setFixedSize(400, 200)
        warning_message_box.setText(f"{self.exception_msg}")
        winsound.MessageBeep()
        screen = app.primaryScreen()
        screen_geometry = screen.availableGeometry()
        x = (screen_geometry.width() - warning_message_box.width()) // 2
        y = (screen_geometry.height() - warning_message_box.height()) // 2
        warning_message_box.move(x, y)
        warning_message_box.exec()

    def compare_videos_side_by_side(self, video1_path, video2_path):
        def update_split(val):
            self.split_pos = val
            if self.paused:
                update_frame()

        def update_frame():
            frame1_resized = cv2.resize(frame1, (width, height))
            frame2_resized = cv2.resize(frame2, (width, height))
            self.combined = frame1_resized.copy()
            self.combined[:, self.split_pos:] = frame2_resized[:, self.split_pos:]
            cv2.line(self.combined, (self.split_pos, 0), (self.split_pos, height), (0, 255, 0),
                     2)

        try:
            cap1 = cv2.VideoCapture(video1_path)
            cap2 = cv2.VideoCapture(video2_path)

            if not cap1.isOpened() or not cap2.isOpened():
                raise Exception

            config = configparser.ConfigParser()
            config.read('Resources/Config.ini')
            width = int(config['Settings']['width'])
            height = int(config['Settings']['height'])
            fps = 60

            window_name = "Video Comparison"
            self.split_pos = width // 2

            cv2.namedWindow(window_name)
            cv2.setNumThreads(os.cpu_count())
            cv2.createTrackbar("Split", window_name, self.split_pos, width, update_split)

            frame1, frame2 = None, None

            while True:
                if not self.paused:
                    ret1, frame1 = cap1.read()
                    ret2, frame2 = cap2.read()

                    if not ret1 or not ret2:
                        break

                    update_frame()

                cv2.imshow(window_name, self.combined)

                key = cv2.waitKey(int(1000 / fps)) & 0xFF
                if key == 27 or cv2.getWindowProperty(window_name,
                                                      cv2.WND_PROP_VISIBLE) < 1:  # Esc key or window closed
                    break
                elif key == ord(' '):  # Space key
                    self.paused = not self.paused

            cap1.release()
            cap2.release()
            cv2.destroyAllWindows()
        except Exception as e:
            self.exception_msg = e
            self.error_box_signal.emit()

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