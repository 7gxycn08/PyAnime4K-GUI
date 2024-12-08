![pyanime4k](https://github.com/user-attachments/assets/c4ff1be9-b2d7-4643-9ec3-573db7ff0b80)

## PyAnime4K-GUI

PyAnime4K-GUI is a graphical user interface for upscaling video files using FFmpeg and [Anime4K](https://github.com/bloc97/Anime4K) custom shaders. It provides an easy way to manage video processing tasks with real-time progress updates and log outputs.


# Features

1. Batch Video Upscaling: Select multiple video files for upscaling.
2. Configurable Settings: Customize output dimensions, bitrate, codec, and shaders via a config file using a text editor.
3. Real-Time Progress: Monitor upscaling progress with a visual progress bar.
4. Log Viewer: View live progress in the GUI and ffmpeg stderr in output.txt file.
5. Cancel Operations: Cancel ongoing upscaling tasks at any time.
6. Output Folder Access: Quickly navigate to the output folder.


# Requirements
- Python 3.9+
- PySide6
- FFmpeg with Vulkan support
- Additional Python libraries:
  * tqdm
  * ffmpeg-progress-yield


# Installation

1. Clone this repository:
   ```
   git clone https://github.com/your-repo/PyAnime4K-GUI.git
   cd PyAnime4K-GUI
   ```
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Place the required ffmpeg.exe and ffprobe.exe in the `ffmpeg/` folder.
4. Ensure the `Resources/Config.ini` file contains your desired settings:
   ```
    [Settings]
    width = 3840
    height = 2160
    bit_rate = 10M
    preset = slow
    codec = hevc_amf
    shader = Anime4K_ModeA+A.glsl
   ```

# Usage

1. Run the application:
   ```
   python PyAnime4K.py
   ```
2. Use the GUI to:
   * Edit Configuration: Open the Config.ini file for adjustments.
   * Select Video Files: Choose videos to upscale.
   * Start Upscaling: Begin processing with the "Upscale" button.
   * Cancel Upscaling: Stop the current task with "Cancel."
   * Access Output Folder: Open the output directory to view results.
  

3. stderr Logs are saved in `output.txt` and progress updates will appear in the application window.


# Custom Shaders
[Click Here for Shader Details](https://github.com/bloc97/Anime4K/blob/master/md/GLSL_Instructions_Advanced.md#modes)
Shaders for upscaling are located in the `shaders/` directory. Modify or add your shaders as needed and reference It in `Resources/Config.ini` file.


# License

This project is licensed under the MIT License. See the LICENSE file for details.
