import json
import os
import sys
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTextEdit, QFileDialog,
                               QMainWindow, QMessageBox, QComboBox, QLabel, QLineEdit, QFrame)
from PySide6.QtCore import QThread, Signal, QSharedMemory
from PySide6.QtGui import QIcon, QTextCursor, QTextBlockFormat, Qt, QAction, QIntValidator
from ffmpeg_progress_yield import FfmpegProgress
from tqdm import tqdm
import subprocess
import cv2
import psutil
from pathlib import Path


class MainWindow(QMainWindow):
    output_signal = Signal(str)
    progress_signal = Signal(str)
    error_box_signal = Signal(str)
    f_probe_signal = Signal(str)
    finished_signal = Signal(str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("PyAnime4K-GUI v2.6")
        self.setWindowIcon(QIcon('Resources/anime.ico'))
        self.setGeometry(100, 100, 1000, 650)
        self.selected_files = None
        self.std_thread = QThread()
        self.encode_thread = QThread()
        self.pass_param_thread = QThread()
        self.compare_thread = QThread()
        self.progress_thread = QThread()
        self.reading_thread = QThread()
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
        self.f_probe_msg = None
        self.finished_msg = None
        self.progress_signal.connect(self.update_progress)
        self.error_box_signal.connect(self.error_box)
        self.f_probe_signal.connect(self.send_f_probe_msg)
        self.finished_signal.connect(self.send_finished_msg)

        # Create a central widget
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        self.menu_bar = self.menuBar()
        self.file_menu = self.menu_bar.addMenu('File')
        self.about_in_menu_bar = QAction(QIcon(r"Resources\about.ico"), 'About', self)
        self.about_in_menu_bar.triggered.connect(self.about_page)
        self.exit_from_menu_bar = QAction(QIcon(r"Resources\exit.ico"), 'Exit Application', self)
        self.exit_from_menu_bar.triggered.connect(self.close)
        self.file_menu.addActions([self.about_in_menu_bar, self.exit_from_menu_bar])

        # Layout setup
        text_edit_layout = QVBoxLayout(central_widget)
        buttons_layout = QVBoxLayout()
        text_and_combo_layout = QHBoxLayout()
        combo_column_container = QWidget()
        combo_column_layout = QVBoxLayout(combo_column_container)

        # Create a QTextEdit widget for logs
        self.log_widget = QTextEdit(self)
        self.log_widget.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self.log_widget.setFrameShape(QFrame.Shape.NoFrame)
        self.log_widget.setFrameShadow(QFrame.Shadow.Plain)
        self.log_widget.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.log_widget.setReadOnly(True)
        self.width_combo = QLineEdit(self)
        self.width_combo.setText("3840")

        self.height_combo = QLineEdit(self)
        self.height_combo.setText("2160")

        self.bit_combo = QLineEdit(self)
        self.bit_combo.setText("10M")

        self.max_combo = QLineEdit(self)
        self.max_combo.setText("20M")
        self.buffer_combo = QLineEdit(self)
        self.buffer_combo.setText("40M")
        self.set_line_edit_frames()

        self.codec_combo = QComboBox(self)
        self.codec_combo.setEditable(False)
        # noinspection SpellCheckingInspection
        self.codec_combo.addItems(["hevc_amf (AMD)", "hevc_nvenc (Nvidia)", "h264_amf (AMD)",
                                   "h264_nvenc (Nvidia)", "av1_amf (AMD)", "av1_nvenc (Nvidia)",
                                   "libx265 (CPU)", "libx264 (CPU)", "libaom-av1 (CPU)"])
        self.shader_combo = QComboBox(self)
        self.shader_combo.setWindowTitle("Shader")
        # noinspection SpellCheckingInspection
        self.shader_combo.addItems(["Anime4K_ModeA.glsl",
                                    "Anime4K_ModeA+A+UL.glsl",
                                    "Anime4k_ModeB.glsl",
                                    "Anime4K_ModeB+B.glsl",
                                    "Anime4K_ModeC.glsl",
                                    "Anime4K_ModeC+A.glsl",
                                    "Anime4k-ModeA-UL.glsl",
                                    "Anime4K_ModeA+FSR.glsl",
                                    "FSRCNNX_x2_16-0-4-1.glsl"
                                    ])
        self.hdr_combo = QComboBox(self)
        self.hdr_combo.addItems(["off", "on"])
        # Add the log widget to the layout
        combo_column_layout.addWidget(QLabel("📏Video Width:"))
        combo_column_layout.addWidget(self.width_combo)
        combo_column_layout.addWidget(QLabel("📐Video Height:"))
        combo_column_layout.addWidget(self.height_combo)
        combo_column_layout.addWidget(QLabel("📶Bitrate:"))
        combo_column_layout.addWidget(self.bit_combo)
        combo_column_layout.addWidget(QLabel("🌟Max Bitrate:"))
        combo_column_layout.addWidget(self.max_combo)
        combo_column_layout.addWidget(QLabel("💽Buffer Size:"))
        combo_column_layout.addWidget(self.buffer_combo)
        combo_column_layout.addWidget(QLabel("🎛️Codec:"))
        combo_column_layout.addWidget(self.codec_combo)
        combo_column_layout.addWidget(QLabel("💡Shader:"))
        combo_column_layout.addWidget(self.shader_combo)
        combo_column_layout.addWidget(QLabel("🌅HDR:"))
        combo_column_layout.addWidget(self.hdr_combo)

        text_and_combo_layout.addWidget(self.log_widget, 1)
        text_and_combo_layout.addWidget(combo_column_container, 0)

        text_edit_layout.addLayout(text_and_combo_layout)

        # Create buttons
        self.compare_button = QPushButton("🎬Compare Videos")
        self.select_button = QPushButton("📁Select Video Files")
        self.output_button = QPushButton("📤Open Output Folder")
        self.upscale_button = QPushButton("🟢Upscale")
        self.cancel_button = QPushButton("🛑Cancel")

        # Add buttons to the layout
        buttons_layout.addWidget(self.compare_button)
        buttons_layout.addWidget(self.select_button)
        buttons_layout.addWidget(self.output_button)
        buttons_layout.addWidget(self.upscale_button)
        buttons_layout.addWidget(self.cancel_button)
        text_edit_layout.addLayout(buttons_layout)

        self.pass_param_thread.run = self.pass_param
        # Connect button clicks to log messages
        self.compare_button.clicked.connect(self.compare_selection)
        self.select_button.clicked.connect(self.open_file_dialog)
        self.output_button.clicked.connect(self.open_output_folder)
        self.upscale_button.clicked.connect(self.thread_check)
        self.cancel_button.clicked.connect(self.cancel_operation)
        open("output.txt", "w").close()
        self.append_ascii_art()

    def set_line_edit_frames(self):
        line_edits = [self.width_combo,
                      self.height_combo,
                      self.max_combo,
                      self.bit_combo,
                      self.buffer_combo]
        for edit in line_edits:
            edit.setFrame(False)
            if edit == line_edits[0] or edit == line_edits[1]:
                edit.setMaxLength(4)
                edit.setValidator(QIntValidator(0, 9999))
            else:
                edit.setMaxLength(3)


    # noinspection PyMethodMayBeStatic
    def about_page(self):
        subprocess.Popen("start https://github.com/7gxycn08/PyAnime4K-GUI",
                         shell=True, creationflags=subprocess.CREATE_NEW_CONSOLE)

    def send_f_probe_msg(self, received_msg):
        self.log_widget.append(f"[Upscaling] - {os.path.basename(self.current_file)} - {received_msg}")

    def send_finished_msg(self, received_msg):
        self.log_widget.append(f"[Upscaling] - {os.path.basename(self.current_file)} - {received_msg}")

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

    def closeEvent(self, event):
        if self.exit_confirm_box() == QMessageBox.StandardButton.Yes:
            self.cancel_encode = True
            self.encode_thread.wait()
            try:
                self.stop_ffmpeg()
                event.accept()
            except Exception as e:
                self.error_box_signal.emit(e)
                event.accept()
            event.accept()
        else:
            event.ignore()

    def exit_confirm_box(self):
        exit_message_box = QMessageBox(self)
        exit_message_box.setIcon(QMessageBox.Icon.Question)
        exit_message_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        exit_message_box.setWindowTitle("PyAnime4K-GUI")
        exit_message_box.setWindowIcon(QIcon(r"Resources\anime.ico"))
        exit_message_box.setFixedSize(400, 200)
        exit_message_box.setText(f"Do you want to exit PyAnime4K-GUI?")
        screen = app.primaryScreen()
        screen_geometry = screen.availableGeometry()
        x = (screen_geometry.width() - exit_message_box.width()) // 2
        y = (screen_geometry.height() - exit_message_box.height()) // 2
        exit_message_box.move(x, y)
        result = exit_message_box.exec()
        return result

    def open_output_folder(self):  # noqa
        if self.output_dir:
            subprocess.run(["xdg-open", str(self.output_dir)])

    def cancel_operation(self):
        self.cancel_encode = True
        self.stop_ffmpeg()
        # noinspection SpellCheckingInspection
        self.log_widget.append("Upscaling Canceled.")

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

    def update_progress(self, received_msg):
        # noinspection SpellCheckingInspection
        self.log_widget.append(f"[Upscaling] - {os.path.basename(self.current_file)} - {received_msg}")

    def is_ffmpeg_running(self):
        return any(
            p.info["name"] and p.info["name"].lower().startswith("ffmpeg")
            for p in psutil.process_iter(["name"])
        )

    def stop_ffmpeg(self):
        if self.is_ffmpeg_running():
            # noinspection SpellCheckingInspection
            subprocess.run(["pkill", "-9", "-x", "ffmpeg"])

    def start_encoding(self, process):
        # noinspection PyBroadException
        try:
            # noinspection SpellCheckingInspection
            self.f_probe_msg = "Calculating Video Duration With FFprobe..."
            self.f_probe_signal.emit(self.f_probe_msg)
            # noinspection SpellCheckingInspection
            ff_probe = Path(__file__).parent / "ffmpeg" / "ffprobe"
            probe_process = subprocess.Popen(
                [
                    str(ff_probe),
                    "-v", "error",
                    "-select_streams", "v:0",
                    "-show_entries", "format=duration",
                    "-of", "json",
                    self.current_file
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            stdout, stderr = probe_process.communicate()
            try:
                data = json.loads(stdout)
                duration = float(data["format"]["duration"])
            except (KeyError, ValueError, json.JSONDecodeError):
                duration = None
            self.progress_msg = f"Video Duration is {duration} Seconds."
            self.progress_signal.emit(self.progress_msg)

            p_bar = tqdm(total=100, position=1, desc="Progress")
            # noinspection SpellCheckingInspection
            for progress in process.run_command_with_progress(duration_override=duration):
                if self.cancel_encode:
                    return
                p_bar.update(progress - p_bar.n)
                # noinspection SpellCheckingInspection
                tqdm_line = p_bar.format_meter(
                    n=p_bar.n,
                    total=p_bar.total,
                    elapsed=p_bar.format_dict['elapsed'],
                    ncols=80,
                )
                self.progress_msg = tqdm_line
                self.progress_signal.emit(self.progress_msg)
                p_bar.refresh()
                if progress == 100:
                    self.finished_msg = "Upscaling Finished Successfully."
                    self.finished_signal.emit(self.finished_msg)
            p_bar.close()

        except Exception as e:
            if self.cancel_encode:
                return
            self.exception_msg = e
            self.cancel_encode = True
            self.error_msg = str(process.stderr)
            self.error_box_signal.emit(self.error_msg)
            self.stop_ffmpeg()

    # noinspection PyMethodMayBeStatic
    # noinspection SpellCheckingInspection
    def get_codec(self, selected_codec):
        codecs = (
            "hevc_amf",
            "hevc_nvenc",
            "h264_amf",
            "h264_nvenc",
            "av1_amf",
            "av1_nvenc",
            "libaom-av1",
            "libx265",
        )

        for codec in codecs:
            if codec in selected_codec:
                return codec

        return "libx264"

    def pass_param(self):
        if self.cancel_encode:
            return

        width = self.width_combo.text()
        height = self.height_combo.text()
        bit_rate = self.bit_combo.text()
        max_bitrate = self.max_combo.text()
        buffer_size = self.buffer_combo.text()
        selected_codec = self.codec_combo.currentText()
        codec = self.get_codec(selected_codec)
        shader = self.shader_combo.currentText()
        hdr = self.hdr_combo.currentText()
        if not self.selected_files:
            return

        for file in self.selected_files:
            sys.stdout.flush()
            sys.stderr.flush()
            if hdr == "on":
                # noinspection SpellCheckingInspection
                ff_mpeg = Path(__file__).parent / "ffmpeg" / "ffmpeg"
                output = Path(self.output_dir) / f"{Path(file).stem}-upscaled.mkv"
                shader_path = Path(__file__).parent / "shaders" / shader

                command = [
                    str(ff_mpeg),
                    "-loglevel", "info",
                    "-i", str(file),
                    "-map", "0:v",
                    "-map", "0:s?",
                    "-map", "0:a",
                    "-vf", (
                        f"format=p010le,"
                        f"libplacebo=w={width}:h={height}:upscaler=ewa_lanczos:"
                        f"custom_shader_path={shader_path}"
                    ),
                    "-c:s", "copy",
                    "-c:a", "copy",
                    "-c:d", "copy",
                    "-b:v", str(bit_rate),
                    "-maxrate", str(max_bitrate),
                    "-bufsize", str(buffer_size),
                    "-c:v", str(codec),
                    "-map_metadata", "0",
                    str(output)
                ]
            else:
                # noinspection SpellCheckingInspection
                ff_mpeg = Path(__file__).parent / "ffmpeg" / "ffmpeg"
                output = Path(self.output_dir) / f"{Path(file).stem}-upscaled.mkv"
                shader_path = Path(__file__).parent / "shaders" / shader

                command = [
                    str(ff_mpeg),
                    "-loglevel", "info",
                    "-i", str(file),
                    "-map", "0:v",
                    "-map", "0:s?",
                    "-map", "0:a?",
                    "-init_hw_device", "vulkan",
                    "-vf",
                    (
                        f"format=yuv420p,hwupload,"
                        f"libplacebo=w={width}:h={height}:upscaler=ewa_lanczos:"
                        f"custom_shader_path={shader_path}"
                    ),
                    "-c:s", "copy",
                    "-c:a", "copy",
                    "-c:d", "copy",
                    "-b:v", str(bit_rate),
                    "-maxrate", str(max_bitrate),
                    "-bufsize", str(buffer_size),
                    "-c:v", str(codec),
                    str(output),
                ]

            if self.cancel_encode:
                break
            self.current_file = file
            process = FfmpegProgress(command)
            self.cancel_encode = False
            if self.encode_thread.isRunning():
                self.encode_thread.wait()
            self.encode_thread.run = lambda: self.start_encoding(process)
            self.encode_thread.start()
            self.encode_thread.wait()

    def error_box(self, received_msg):
        with open("output.txt", "a") as file:
            file.write(str(received_msg) + "\n")
        with open("output.txt", 'r', encoding='utf-8') as read_file:
            text = read_file.read()
        self.log_widget.append(text)
        warning_message_box = QMessageBox(self)
        warning_message_box.setIcon(QMessageBox.Icon.Critical)
        warning_message_box.setWindowTitle("PyAnime4K-GUI Error")
        warning_message_box.setWindowIcon(QIcon(r"Resources\anime.ico"))
        warning_message_box.setFixedSize(400, 200)
        warning_message_box.setText(f"Unexpected Error Occurred.")
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

            width = int(self.width_combo.text())
            height = int(self.height_combo.text())
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
            self.error_box_signal.emit(e)

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
    if app.styleHints().colorScheme() == Qt.ColorScheme.Dark:
        with open(r"Resources/dark_theme_utf8.qss", "r") as f:
            app.setStyleSheet(f.read())
    else:
        with open(r"Resources/light_theme_utf8.qss", "r") as f:
            app.setStyleSheet(f.read())
    shared_mem = QSharedMemory("PyAnime4K")
    if not shared_mem.create(1):
        # Already running
        msg = QMessageBox()
        msg.setWindowTitle("PyAnime4K-GUI Error")
        msg.setWindowIcon(QIcon(r"Resources\anime.ico"))
        msg.setText("Another instance is already running.")
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.exec()
        sys.exit(0)
    window = MainWindow()
    window.show()
    app.exec()
