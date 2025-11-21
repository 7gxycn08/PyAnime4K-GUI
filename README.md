
<img width="1017" height="765" alt="2 2" src="https://github.com/user-attachments/assets/dbcef93a-2efa-4581-9cd2-f6a3db23c698" />


## PyAnime4K-GUI

PyAnime4K-GUI is a graphical user interface for hardware accelerated upscaling of video files using FFmpeg and [Anime4K](https://github.com/bloc97/Anime4K) custom shaders. It provides an easy way to save [Anime4K](https://github.com/bloc97/Anime4K) upscaled videos to disk with real-time progress updates and log outputs and preconfigured output settings.


# Features

1. Batch Video Upscaling: Select multiple video files for upscaling which will be saved to disk.
2. Configurable Settings: Customize output `dimensions`, `bitrate`, `codec`, and `shaders` etc... directly from GUI.
3. Real-Time Progress: Monitor upscaling progress with a visual progress bar.
4. Log Viewer: View live progress and errors in the GUI.
5. Cancel Operations: Cancel ongoing upscaling tasks at any time.
6. Output Folder Access: Quickly navigate to the output folder.
7. Multiple Subtitle Stream Copy: Includes all subtitle streams from input file.
8. Upscale hdr/dolby vision input videos while maintaining all their metadata required for playback.
9. Compare Two Videos Side-by-Side: Video compare function that display quality changes in real-time.
10. Supports Hardware acceleration for AMD `hevc_amf` and Nvidia `hevc_nvenc`.


# Requirements
- Python 3.9+
- PySide6
- Opencv-Python
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
4. Ensure the required settings are set properly for your hardware settings. You can configure them directly from the GUI.:
   ```
    Codec:
    For Nvidia GPU's use hevc_nvenc
    For AMD GPU's use hevc_amf
   ```

# Usage

1. Run the application:
   ```
   python PyAnime4K.py
   ```
2. Use the GUI to:
   * Set Configuration: Configure output video settings.
   * Select Video Files: Choose videos to upscale.
   * Start Upscaling: Begin processing with the "Upscale" button.
   * Cancel Upscaling: Stop the current task with "Cancel."
   * Access Output Folder: Open the output directory to view results.
  

3. ffmpeg upscaling summary are saved in `output.txt` and progress updates will appear in the application window.


# Custom Shaders
[Click Here for Shader Details](https://github.com/bloc97/Anime4K/blob/master/md/GLSL_Instructions_Advanced.md#modes)
Shaders for upscaling are located in the `shaders/` directory. Modify or add your shaders as needed and reference It in `Resources/Config.ini` file.

You can use your own custom shader combinations example:


`Anime4K-R+DTD+U+R+DTD+U.glsl` This combination takes 10 minutes to 2-pass upscale an episode to 4K on a `RX 7900xtx` gpu.
```
# Included shaders:
Anime4K_Restore_CNN_UL.glsl
Anime4K_Upscale_DTD_x2.glsl            # Pass-1
Anime4K_Upscale_CNN_x2_UL.glsl
Anime4K_AutoDownscalePre_x2.glsl
Anime4K_AutoDownscalePre_x4.glsl
Anime4K_Restore_CNN_UL.glsl
Anime4K_Upscale_DTD_x2.glsl            # Pass-2
Anime4K_Upscale_CNN_x2_UL.glsl
```


# License

This project is licensed under the MIT License. See the LICENSE file for details.
