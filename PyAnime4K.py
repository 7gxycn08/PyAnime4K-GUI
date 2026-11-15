import json
import os
import sys
import pywinstyles
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTextEdit, QFileDialog,
                               QMainWindow, QMessageBox, QComboBox, QLabel, QLineEdit, QFrame, QProgressBar)
from PySide6.QtCore import QThread, Signal, QSharedMemory
from PySide6.QtGui import QIcon, Qt, QAction, QIntValidator
from ffmpeg_progress_yield import FfmpegProgress
from tqdm import tqdm
from pathlib import Path
import subprocess
import winsound
import cv2
import ctypes
import numpy as np



# =====================================================================
#  THEME — "Neon Anime" (self-contained, no external .qss required)
# =====================================================================
# noinspection SpellCheckingInspection
THEME_QSS = """
/* ---------- palette ---------- */
* { outline: none; }

QMainWindow, QDialog {
    background-color: #0a0a12;
    color: #e5e7eb;
}

QWidget {
    background-color: transparent;
    color: #e5e7eb;
    font-family: "Segoe UI", "Inter", sans-serif;
    font-size: 13px;
}

/* ---------- header ---------- */
QFrame#header {
    background-color: #0d0d18;
    border-bottom: 1px solid #26263a;
}
#app_title { color: #f5f3ff; font-size: 20px; font-weight: 700; letter-spacing: .5px; }
#version_badge {
    color: #0a0a12; background-color: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #a855f7, stop:1 #22d3ee);
    border-radius: 6px; padding: 2px 9px; font-size: 11px; font-weight: 700;
}
#header_sub { color: #6b7280; font-size: 12px; }

/* ---------- panels ---------- */
QFrame#settings_panel, QFrame#console_panel {
    background-color: #12121e;
    border: 1px solid #26263a;
    border-radius: 10px;
}

/* ---------- section cards ---------- */
QFrame#section_frame {
    background-color: #171725;
    border: 1px solid #2b2b44;
    border-radius: 8px;
}
#section_header { color: #c084fc; font-size: 11px; font-weight: 700; letter-spacing: 1.3px; }

/* ---------- log / console ---------- */
QTextEdit#log_widget {
    background-color: #0a0a12;
    border: none;
    color: #d1d5db;
    font-family: "Cascadia Code", "Consolas", "JetBrains Mono", monospace;
    font-size: 12px;
    selection-background-color: #7c3aed; selection-color: #ffffff;
}

/* log line colours */
span.log-added     { color: #22d3ee; }
span.log-upscale   { color: #c084fc; }
span.log-finished  { color: #34d399; font-weight: bold; }
span.log-error     { color: #f43f5e; }
span.log-info      { color: #6b7280; }

.welcome { padding: 10px 0; border-left: 3px solid #a855f7; margin: 4px 0; }
.w-title { color: #f5f3ff; font-size: 15px; font-weight: 700; }
.w-ver   { color: #22d3ee; font-size: 12px; font-weight: 600; }
.w-sub   { color: #9ca3af; font-size: 12px; }

/* ---------- inputs ---------- */
QLineEdit {
    background-color: #0a0a12; border: 1px solid #2b2b44; border-radius: 6px;
    padding: 6px 10px; color: #e5e7eb; font-size: 13px; min-height: 28px;
}
QLineEdit:hover  { border-color: #a855f7; }
QLineEdit:focus  { border-color: #22d3ee; background-color: #0d0d18; }

/* ---------- combo boxes ---------- */
QComboBox {
    background-color: #0a0a12; border: 1px solid #2b2b44; border-radius: 6px;
    padding: 5px 12px; color: #e5e7eb; font-size: 13px; min-height: 28px;
}
QComboBox:hover  { border-color: #a855f7; }
QComboBox:focus  { border-color: #22d3ee; }
QComboBox::drop-down { border: none; width: 24px; }
QComboBox QAbstractItemView {
    background-color: #171725; color: #e5e7eb; selection-background-color: #7c3aed;
    selection-color: #ffffff; border: 1px solid #2b2b44; border-radius: 4px;
}

/* ---------- labels ---------- */
QLabel#field_label { color: #9ca3af; font-size: 12px; font-weight: 600; }

/* ---------- buttons ---------- */
QPushButton {
    background-color: #171725; border: 1px solid #2b2b44; border-radius: 8px;
    padding: 9px 16px; color: #e5e7eb; font-size: 13px; font-weight: 600;
}
QPushButton:hover   { background-color: #20203a; border-color: #a855f7; }
QPushButton:pressed { background-color: #171725; }

QPushButton#btn_upscale {
    background-color: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #7c3aed, stop:1 #06b6d4);
    border: none; color: #ffffff; font-weight: 700; font-size: 14px; padding: 10px 28px;
}
QPushButton#btn_upscale:hover   { background-color: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #8b5cf6, stop:1 #22d3ee); }
QPushButton#btn_upscale:pressed { background-color: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #6d28d9, stop:1 #0891b2); }

QPushButton#btn_cancel {
    background-color: transparent; border: 1px solid #f43f5e; color: #fb7185;
}
QPushButton#btn_cancel:hover   { background-color: #f43f5e; color: #ffffff; }
QPushButton#btn_cancel:pressed { background-color: #be123c; }

/* ---------- progress bar ---------- */
QProgressBar {
    background-color: #0a0a12; border: 1px solid #2b2b44; border-radius: 6px;
    text-align: center; color: #e5e7eb; font-size: 11px; font-weight: 700; min-height: 22px;
}
QProgressBar::chunk {
    background-color: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #a855f7, stop:1 #22d3ee);
    border-radius: 5px;
}

/* ---------- menu bar ---------- */
QMenuBar { background-color: #0d0d18; color: #e5e7eb; border-bottom: 1px solid #26263a; }
QMenuBar::item:selected { background-color: #171725; }
QMenu { background-color: #12121e; color: #e5e7eb; border: 1px solid #2b2b44; border-radius: 6px; padding: 4px; }
QMenu::item { padding: 6px 24px 6px 12px; border-radius: 4px; }
QMenu::item:selected { background-color: #7c3aed; color: #ffffff; }

/* ---------- scrollbars ---------- */
QScrollBar:vertical   { background: #0a0a12; width: 8px; margin: 0; }
QScrollBar:horizontal { background: #0a0a12; height: 8px; margin: 0; }
QScrollBar::handle:vertical   { background: #2b2b44; border-radius: 4px; min-height: 30px; }
QScrollBar::handle:horizontal { background: #2b2b44; border-radius: 4px; min-width: 30px; }
QScrollBar::handle:hover { background: #3a3a5c; }
QScrollBar::add-line, QScrollBar::sub-line { height: 0; width: 0; }

/* ---------- tooltips / dialogs ---------- */
QToolTip { background-color: #171725; color: #e5e7eb; border: 1px solid #2b2b44; border-radius: 4px; padding: 4px 8px; }
QMessageBox { background-color: #12121e; }
QMessageBox QLabel { color: #f5f3ff; font-size: 13px; }
"""


class MainWindow(QMainWindow):
    output_signal = Signal(str)
    progress_signal = Signal(str)
    percent_signal = Signal(int)          # NEW — drives the QProgressBar
    error_box_signal = Signal(str)
    f_probe_signal = Signal(str)
    finished_signal = Signal(str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("PyAnime4K-GUI v2.7")
        self.setWindowIcon(QIcon('Resources/anime.ico'))
        self.setGeometry(100, 100, 1180, 720)

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
        self.percent_signal.connect(self.update_percent_bar)
        self.error_box_signal.connect(self.error_box)
        self.f_probe_signal.connect(self.send_f_probe_msg)
        self.finished_signal.connect(self.send_finished_msg)

        # ---------------- central widget ----------------
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # menu bar (kept for About / Exit)
        self.menu_bar = self.menuBar()
        self.file_menu = self.menu_bar.addMenu('File')
        self.about_in_menu_bar = QAction(QIcon(r"Resources\about.ico"), 'About', self)
        self.about_in_menu_bar.triggered.connect(self.about_page)
        self.exit_from_menu_bar = QAction(QIcon(r"Resources\exit.ico"), 'Exit Application', self)
        self.exit_from_menu_bar.triggered.connect(self.close)
        self.file_menu.addActions([self.about_in_menu_bar, self.exit_from_menu_bar])

        # ---------------- header ----------------
        header = QFrame()
        header.setObjectName("header")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(18, 12, 18, 12)
        icon_path = Path("Resources/anime.ico").resolve()
        title_label = QLabel(
            f'<table><tr valign="middle">'
            f'<td><img src="{icon_path.as_uri()}" width="24"/></td>'
            f'<td>&nbsp;&nbsp;PyAnime4K-GUI</td>'
            f'</tr></table>',
        )
        title_label.setObjectName("app_title")
        version_badge = QLabel("v2.7")
        version_badge.setObjectName("version_badge")
        sub_label = QLabel("Anime4k Upscaler")
        sub_label.setObjectName("header_sub")
        header_layout.addWidget(title_label)
        header_layout.addSpacing(10)
        header_layout.addWidget(version_badge)
        header_layout.addSpacing(12)
        header_layout.addWidget(sub_label)
        header_layout.addStretch(1)
        root_layout.addWidget(header)

        # ---------------- content row: settings | console ----------------
        content = QWidget()
        content_layout = QHBoxLayout(content)
        content_layout.setContentsMargins(14, 14, 14, 6)
        content_layout.setSpacing(12)

        # ---- settings sidebar ----
        settings_panel = QFrame()
        settings_panel.setObjectName("settings_panel")
        settings_panel.setFixedWidth(330)
        settings_layout = QVBoxLayout(settings_panel)
        settings_layout.setContentsMargins(14, 16, 14, 16)
        settings_layout.setSpacing(12)

        # Resolution section
        res_section = QFrame()
        res_section.setObjectName("section_frame")
        res_grid = QVBoxLayout(res_section)
        res_grid.setContentsMargins(14, 12, 14, 14)
        res_grid.addWidget(self._lbl("RESOLUTION", "section_header"))
        self.width_combo = QLineEdit(self);  self.width_combo.setText("3840")
        self.height_combo = QLineEdit(self); self.height_combo.setText("2160")
        res_grid.addWidget(self._lbl("Width", "field_label"))
        res_grid.addWidget(self.width_combo)
        res_grid.addWidget(self._lbl("Height", "field_label"))
        res_grid.addWidget(self.height_combo)
        settings_layout.addWidget(res_section)

        # Encoding section
        enc_section = QFrame()
        enc_section.setObjectName("section_frame")
        enc_grid = QVBoxLayout(enc_section)
        enc_grid.setContentsMargins(14, 12, 14, 14)
        enc_grid.addWidget(self._lbl("ENCODING", "section_header"))
        self.codec_combo = QComboBox(self); self.codec_combo.setEditable(False)
        # noinspection SpellCheckingInspection
        self.codec_combo.addItems(["hevc_amf (AMD)", "hevc_nvenc (Nvidia)", "h264_amf (AMD)",
                                   "h264_nvenc (Nvidia)", "av1_amf (AMD)", "av1_nvenc (Nvidia)",
                                   "libx265 (CPU)", "libx264 (CPU)", "libaom-av1 (CPU)"])
        self.bit_combo = QLineEdit(self);   self.bit_combo.setText("10M")
        self.max_combo = QLineEdit(self);   self.max_combo.setText("20M")
        self.buffer_combo = QLineEdit(self); self.buffer_combo.setText("40M")
        enc_grid.addWidget(self._lbl("Codec", "field_label"))
        enc_grid.addWidget(self.codec_combo)
        # bitrate / max / buffer in a compact 3-col grid
        br_row = QHBoxLayout()
        for lbl, edit in (("Bitrate", self.bit_combo), ("Max Rate", self.max_combo), ("Buffer", self.buffer_combo)):
            col = QVBoxLayout()
            col.setSpacing(2)
            col.addWidget(self._lbl(lbl, "field_label"))
            col.addWidget(edit)
            br_row.addLayout(col, 1)
        enc_grid.addLayout(br_row)
        settings_layout.addWidget(enc_section)

        # Upscaling section
        up_section = QFrame()
        up_section.setObjectName("section_frame")
        up_grid = QVBoxLayout(up_section)
        up_grid.setContentsMargins(14, 12, 14, 14)
        up_grid.addWidget(self._lbl("UPSCALING", "section_header"))
        self.shader_combo = QComboBox(self); self.shader_combo.setWindowTitle("Shader")
        # noinspection SpellCheckingInspection
        self.shader_combo.addItems(["Anime4K_ModeA.glsl",
                                    "Anime4K_ModeA+A+UL.glsl",
                                    "Anime4k_ModeB.glsl",
                                    "Anime4K_ModeB+B.glsl",
                                    "Anime4K_ModeC.glsl",
                                    "Anime4K_ModeC+A.glsl",
                                    "Anime4k-ModeA-UL.glsl",
                                    "Anime4K_ModeA+FSR.glsl",
                                    "FSRCNNX_x2_16-0-4-1.glsl"])
        self.hdr_combo = QComboBox(self)
        self.hdr_combo.addItems(["off", "on"])
        up_grid.addWidget(self._lbl("Shader", "field_label"))
        up_grid.addWidget(self.shader_combo)
        up_grid.addWidget(self._lbl("HDR", "field_label"))
        up_grid.addWidget(self.hdr_combo)
        settings_layout.addWidget(up_section)

        settings_layout.addStretch(1)
        content_layout.addWidget(settings_panel, 0)

        # ---- console panel ----
        console_panel = QFrame()
        console_panel.setObjectName("console_panel")
        console_layout = QVBoxLayout(console_panel)
        console_layout.setContentsMargins(12, 12, 12, 12)
        self.log_widget = QTextEdit(self)
        self.log_widget.setObjectName("log_widget")
        self.log_widget.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self.log_widget.setFrameShape(QFrame.Shape.NoFrame)
        self.log_widget.setFrameShadow(QFrame.Shadow.Plain)
        self.log_widget.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.log_widget.setReadOnly(True)
        console_layout.addWidget(self.log_widget)
        content_layout.addWidget(console_panel, 1)

        root_layout.addWidget(content, 1)

        # ---------------- action bar ----------------
        action_bar = QFrame()
        action_bar.setObjectName("action_bar")
        action_layout = QHBoxLayout(action_bar)
        action_layout.setContentsMargins(14, 6, 14, 6)
        action_layout.setSpacing(10)
        self.select_button = QPushButton("Select Files")
        self.select_button.setObjectName("btn_select")
        self.compare_button = QPushButton("Compare Videos")
        self.compare_button.setObjectName("btn_compare")
        self.output_button = QPushButton("Output Folder")
        self.output_button.setObjectName("btn_output")
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setObjectName("btn_cancel")
        self.upscale_button = QPushButton("Upscale")
        self.upscale_button.setObjectName("btn_upscale")
        action_layout.addWidget(self.select_button)
        action_layout.addWidget(self.compare_button)
        action_layout.addWidget(self.output_button)
        action_layout.addStretch(1)
        action_layout.addWidget(self.cancel_button)
        action_layout.addWidget(self.upscale_button)
        root_layout.addWidget(action_bar)

        # ---------------- progress bar ----------------
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("%p%")
        pb_wrap = QWidget()
        pb_layout = QVBoxLayout(pb_wrap)
        pb_layout.setContentsMargins(14, 0, 14, 12)
        pb_layout.addWidget(self.progress_bar)
        root_layout.addWidget(pb_wrap)

        # wire up threads + buttons (logic unchanged)
        self.pass_param_thread.run = self.pass_param
        self.compare_button.clicked.connect(self.compare_selection)
        self.select_button.clicked.connect(self.open_file_dialog)
        self.output_button.clicked.connect(self.open_output_folder)
        self.upscale_button.clicked.connect(self.thread_check)
        self.cancel_button.clicked.connect(self.cancel_operation)

        self.set_line_edit_frames()

        open("output.txt", "w").close()
        self.append_welcome()

    # ------------------------------------------------------------------
    # noinspection PyMethodMayBeStatic
    def _lbl(self, text: str, name: str | None = None) -> QLabel:
        l = QLabel(text)
        if name:
            l.setObjectName(name)
        return l

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

    # ------------------------------------------------------------------
    # logging helpers (HTML colour-coded)
    # noinspection PyMethodMayBeStatic
    def _esc(self, text):
        return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def log_tag(self, css_class, message):
        self.log_widget.append(f'<span class="{css_class}">{self._esc(message)}</span>')

    def update_percent_bar(self, value):
        self.progress_bar.setValue(int(value))

    # noinspection PyMethodMayBeStatic
    def about_page(self):
        subprocess.Popen("start https://github.com/7gxycn08/PyAnime4K-GUI",
                         shell=True, creationflags=subprocess.CREATE_NEW_CONSOLE)

    def send_f_probe_msg(self, received_msg):
        self.log_tag("log-upscale", f"[Upscaling] - {os.path.basename(self.current_file)} - {received_msg}")

    def send_finished_msg(self, received_msg):
        self.log_tag("log-finished", f"[Upscaling] - {os.path.basename(self.current_file)} - {received_msg}")

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
        winsound.MessageBeep()
        screen = app.primaryScreen()
        screen_geometry = screen.availableGeometry()
        x = (screen_geometry.width() - exit_message_box.width()) // 2
        y = (screen_geometry.height() - exit_message_box.height()) // 2
        exit_message_box.move(x, y)
        result = exit_message_box.exec()
        return result

    def open_output_folder(self):  # noqa
        if self.output_dir:
            os.startfile(f"{self.output_dir}")

    def cancel_operation(self):
        self.cancel_encode = True
        self.stop_ffmpeg()
        # noinspection SpellCheckingInspection
        self.log_tag("log-info", "Upscaling Canceled.")

    def log_message(self, message):
        self.log_widget.append(message)

    def open_file_dialog(self):
        file_paths, _ = QFileDialog.getOpenFileNames(self, "Select Files", "",
                                                     "Video Files (*.mkv *.mp4)")
        if file_paths:
            self.log_widget.clear()
            self.selected_files = file_paths
            for file in self.selected_files:
                self.log_tag("log-added", f"[Added] - {file}")

        else:
            self.log_widget.clear()
            self.log_tag("log-info", "File selection canceled.")
            return

        output_path = QFileDialog.getExistingDirectory(None, "Select Output Directory")
        if output_path:
            self.output_dir = output_path
            self.activateWindow()

        else:
            self.selected_files = None
            self.log_widget.clear()
            self.log_tag("log-info", "File selection canceled.")
            self.activateWindow()

    def update_progress(self, received_msg):
        # noinspection SpellCheckingInspection
        self.log_tag("log-upscale", f"[Upscaling] - {os.path.basename(self.current_file)} - {received_msg}")

    def is_ffmpeg_running(self):
        process_query_limited_information = 0x1000

        process_names = "ffmpeg.exe"
        try:
            processes = (ctypes.c_ulong * 2048)()  # noqa
            cb = ctypes.c_ulong(ctypes.sizeof(processes))
            # noinspection SpellCheckingInspection
            ps_api = ctypes.WinDLL('Psapi.dll')
            enum_processes = ps_api.EnumProcesses

            enum_processes(ctypes.byref(processes), cb, ctypes.byref(cb))
            process_count = cb.value // ctypes.sizeof(ctypes.c_ulong)

            for i in range(process_count):
                process_id = processes[i]
                kernel32 = ctypes.WinDLL('kernel32.dll')
                open_process = kernel32.OpenProcess

                process_handle = open_process(process_query_limited_information, False,
                                              process_id)

                if process_handle:
                    buffer_size = 260
                    buffer = ctypes.create_unicode_buffer(buffer_size)
                    query_full_process_image_name_w = kernel32.QueryFullProcessImageNameW
                    success = query_full_process_image_name_w(process_handle, 0, buffer,
                                                              ctypes.byref(
                                                                  ctypes.c_ulong(buffer_size)))
                    close_handle = kernel32.CloseHandle
                    close_handle(process_handle)

                    if success:
                        process_name_actual = os.path.basename(buffer.value)
                        if process_name_actual in process_names:
                            return True
            return False

        except Exception as e:
            self.error_box_signal.emit(e)
            return False

    def stop_ffmpeg(self):
        if self.is_ffmpeg_running():
            # noinspection SpellCheckingInspection
            subprocess.call(
                ["taskkill", "/F", "/IM", "ffmpeg.exe"],
                creationflags=subprocess.CREATE_NO_WINDOW
            )

    def start_encoding(self, process):
        # noinspection PyBroadException
        try:
            # noinspection SpellCheckingInspection
            self.f_probe_msg = "Calculating Video Duration With FFprobe..."
            self.f_probe_signal.emit(self.f_probe_msg)
            # noinspection SpellCheckingInspection
            probe_process = subprocess.Popen(
                [
                    "ffmpeg/ffprobe.exe",
                    "-v", "error",
                    "-select_streams", "v:0",
                    "-show_entries", "format=duration",
                    "-of", "json",
                    self.current_file
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW
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
            for progress in process.run_command_with_progress(popen_kwargs={"creationflags":
                                                                                subprocess.CREATE_NO_WINDOW},
                                                              duration_override=duration):
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
                self.percent_signal.emit(int(progress))          # NEW — progress bar
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
                command = [
                    "ffmpeg/ffmpeg.exe",
                    "-loglevel", "info",
                    "-i", f"{file}",
                    "-map", "0:v",
                    "-map", "0:s?",
                    "-map", "0:a",
                    "-vf", (
                        f"format=p010le,"
                        f"libplacebo=w={width}:h={height}:upscaler=ewa_lanczos:custom_shader_path=shaders/{shader}"
                    ),
                    "-c:s", "copy",
                    "-c:a", "copy",
                    "-c:d", "copy",
                    "-b:v", f"{bit_rate}",
                    "-maxrate", f"{max_bitrate}",
                    "-bufsize", f"{buffer_size}",
                    "-c:v", f"{codec}",
                    "-map_metadata", "0",
                    f"{self.output_dir}\\{os.path.basename(file).removesuffix('.mkv')
                    .removesuffix('.mp4')}-upscaled.mkv"
                ]
            else:
                # noinspection SpellCheckingInspection
                command = [
                    "ffmpeg/ffmpeg.exe",
                    "-loglevel", "info",
                    "-i", f"{file}",
                    "-map", "0:v",
                    "-map", "0:s?",
                    "-map", "0:a",
                    "-init_hw_device", "vulkan",
                    "-vf", f"format=yuv420p,"
                           f"libplacebo=w={width}:h={height}:upscaler=ewa_lanczos:custom_shader_path=shaders/{shader}",
                    "-c:s", "copy", "-c:a", "copy", "-c:d", "copy",
                    "-b:v", f"{bit_rate}", "-maxrate", f"{max_bitrate}", "-bufsize", f"{buffer_size}",
                    "-c:v", f"{codec}",
                    f"{self.output_dir}\\{os.path.basename(file).removesuffix(".mkv")
                    .removesuffix(".mp4")}-upscaled.mkv"
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
        self.log_widget.append(f'<span class="log-error">{self._esc(text)}</span>')
        warning_message_box = QMessageBox(self)
        warning_message_box.setIcon(QMessageBox.Icon.Critical)
        warning_message_box.setWindowTitle("PyAnime4K-GUI Error")
        warning_message_box.setWindowIcon(QIcon(r"Resources\anime.ico"))
        warning_message_box.setFixedSize(400, 200)
        warning_message_box.setText(f"Unexpected Error Occurred.")
        winsound.MessageBeep()
        screen = app.primaryScreen()
        screen_geometry = screen.availableGeometry()
        x = (screen_geometry.width() - warning_message_box.width()) // 2
        y = (screen_geometry.height() - warning_message_box.height()) // 2
        warning_message_box.move(x, y)
        warning_message_box.exec()

    def compare_videos_side_by_side(self, video1_path, video2_path):
        try:
            width = max(2, int(self.width_combo.text().strip()))
            height = max(2, int(self.height_combo.text().strip()))
            print(width)
            print(height)
        except ValueError:
            self.error_box_signal.emit(ValueError("Width/height must be integers."))
            return

        cap1 = cv2.VideoCapture(video1_path)
        cap2 = cv2.VideoCapture(video2_path)
        if not cap1.isOpened() or not cap2.isOpened():
            cap1.release()
            cap2.release()
            self.error_box_signal.emit(
                RuntimeError(f"Could not open video: {video1_path} / {video2_path}")
            )
            return

        fps = max(1, int(cap1.get(cv2.CAP_PROP_FPS) or 30))
        window_name = "Video Comparison"
        self.split_pos = width // 2

        # total frames (fallback for codecs that don't report it)
        total_frames = int(cap1.get(cv2.CAP_PROP_FRAME_COUNT))
        if total_frames <= 1:
            total_frames = 99_999

        buf1 = np.empty((height, width, 3), np.uint8)
        buf2 = np.empty((height, width, 3), np.uint8)
        combined = np.empty((height, width, 3), np.uint8)

        frame1 = frame2 = None
        current_frame = 0
        seeking = False  # re-entrance guard

        def update_frame():
            nonlocal frame1, frame2
            if frame1 is None or frame2 is None:
                return
            cv2.resize(frame1, (width, height), dst=buf1)
            cv2.resize(frame2, (width, height), dst=buf2)
            s = self.split_pos
            combined[:, :s] = buf1[:, :s]
            combined[:, s:] = buf2[:, s:]
            cv2.line(combined, (s, 0), (s, height), (0, 255, 0), 2)

        def on_split(val):
            self.split_pos = val
            if self.paused and not seeking:
                update_frame()

        def on_seek(val):
            nonlocal current_frame, seeking, frame1, frame2
            if seeking:
                return  # we're the ones updating the bar — ignore
            seeking = True
            cap1.set(cv2.CAP_PROP_POS_FRAMES, val)
            cap2.set(cv2.CAP_PROP_POS_FRAMES, val)
            current_frame = val
            ret_seek1, f1 = cap1.read()
            ret_seek2, f2 = cap2.read()
            if ret_seek1 and f1 is not None:
                frame1 = f1
            if ret_seek2 and f2 is not None:
                frame2 = f2
            update_frame()
            seeking = False

        cv2.namedWindow(window_name)
        cv2.createTrackbar("Split", window_name, self.split_pos, width, on_split)
        cv2.createTrackbar("Seek", window_name, 0, total_frames - 1, on_seek)

        try:
            while True:
                if not self.paused and not seeking:
                    ret1, frame1 = cap1.read()
                    ret2, frame2 = cap2.read()
                    if not ret1 or not ret2:
                        break
                    current_frame += 1
                    # move the Seek bar to follow playback (guard prevents loop)
                    seeking = True
                    cv2.setTrackbarPos("Seek", window_name,
                                       min(current_frame, total_frames - 1))
                    seeking = False
                    update_frame()

                cv2.imshow(window_name, combined)

                key = cv2.waitKey(int(1000 / fps)) & 0xFF
                visible = cv2.getWindowProperty(window_name, cv2.WND_PROP_VISIBLE)
                if key == 27 or visible < 1:
                    break
                elif key == ord(' '):
                    self.paused = not self.paused
                elif key in (ord('r'), 8):  # R or Backspace → rewind to start
                    on_seek(0)
                elif key == ord('.'):  # . → step forward one frame
                    if current_frame < total_frames - 1:
                        on_seek(current_frame + 1)
                elif key == ord(','):  # , → step back one frame
                    if current_frame > 0:
                        on_seek(current_frame - 1)
        finally:
            cap1.release()
            cap2.release()
            try:
                cv2.destroyWindow(window_name)
            except cv2.error:
                pass

    def append_welcome(self):
        self.log_widget.append(
            '<div class="welcome">'
            '<span class="w-title">PyAnime4K-GUI</span> '
            '<span class="w-ver">v2.7</span><br/>'
            '<span class="w-sub">Select video files, choose your settings, then hit Upscale.</span>'
            '</div>'
        )


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet(THEME_QSS)          # self-contained theme (no external .qss)
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
    # noinspection PyBroadException
    try:
        pywinstyles.apply_style(window, "mica")
        pywinstyles.change_border_color(window, color="#7c3aed")
    except Exception:
        pass
    window.show()
    app.exec()