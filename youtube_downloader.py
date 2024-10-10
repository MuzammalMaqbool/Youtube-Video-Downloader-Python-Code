import os
import threading
import tkinter as tk
from tkinter import messagebox, filedialog, scrolledtext
import shutil
import yt_dlp

# ------------------------------ Helper Functions ------------------------------ #

def is_ffmpeg_installed():
    """Check if FFmpeg is installed and accessible."""
    return shutil.which("ffmpeg") is not None

def sanitize_filename(name):
    """Sanitize the filename by removing or replacing invalid characters."""
    invalid_chars = r'<>:"/\|?*'
    for char in invalid_chars:
        name = name.replace(char, "_")
    return name

def get_video_info(url):
    """Fetch video information using yt-dlp."""
    ydl_opts = {
        'format': 'bestvideo+bestaudio/best',
        'quiet': True,
        'no_warnings': True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        return info

def download_video_with_ydl(url, output_path, format, resolution, progress_callback=None):
    """Download video using yt-dlp with progress callback."""
    ydl_opts = {
        'format': 'bestaudio' if format == 'MP3' else f'bestvideo[height={resolution}]+bestaudio/best',
        'outtmpl': os.path.join(output_path, '%(title)s.%(ext)s'),
        'merge_output_format': 'mp4' if format == 'MP4' else None,
        'progress_hooks': [progress_callback] if progress_callback else [],
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

# ------------------------------ GUI Application ------------------------------ #

class YouTubeDownloaderApp:
    def __init__(self, master):
        self.master = master
        master.title("YouTube Video Downloader")
        master.geometry("600x500")
        master.resizable(False, False)

        # Initialize variables
        self.video_info = None
        self.selected_format = tk.StringVar(value="MP4")
        self.selected_resolution = tk.StringVar(value="144p")

        # URL Input
        self.url_label = tk.Label(master, text="YouTube URL:")
        self.url_label.pack(pady=(10, 0))
        self.url_entry = tk.Entry(master, width=70)
        self.url_entry.pack(pady=5)

        # Save Path Selection
        self.path_frame = tk.Frame(master)
        self.path_frame.pack(pady=5)
        self.path_label = tk.Label(self.path_frame, text="Save Path:")
        self.path_label.pack(side=tk.LEFT)
        self.path_entry = tk.Entry(self.path_frame, width=50)
        self.path_entry.pack(side=tk.LEFT, padx=5)
        self.browse_button = tk.Button(self.path_frame, text="Browse", command=self.browse_path)
        self.browse_button.pack(side=tk.LEFT)

        # Format Selection
        self.format_label = tk.Label(master, text="Select Format:")
        self.format_label.pack(pady=(10, 0))
        self.format_menu = tk.OptionMenu(master, self.selected_format, "MP3", "MP4")
        self.format_menu.pack(pady=5)

        # Resolution Selection (MP4 only)
        self.resolution_label = tk.Label(master, text="Select Resolution (MP4 only):")
        self.resolution_label.pack(pady=(10, 0))
        self.resolution_menu = tk.OptionMenu(master, self.selected_resolution, "144p", "256p", "360p", "1080p")
        self.resolution_menu.pack(pady=5)

        # Fetch Info Button
        self.fetch_button = tk.Button(master, text="Fetch Video Info", command=self.fetch_info)
        self.fetch_button.pack(pady=10)

        # Video Information Display
        self.info_text = scrolledtext.ScrolledText(master, width=70, height=15, state='disabled')
        self.info_text.pack(pady=5)

        # Download Button
        self.download_button = tk.Button(master, text="Download Video", command=self.download_video, state='disabled')
        self.download_button.pack(pady=10)

        # Progress Bar (Optional)
        self.progress = tk.StringVar()
        self.progress_label = tk.Label(master, textvariable=self.progress)
        self.progress_label.pack(pady=5)

    def browse_path(self):
        """Open a dialog to select the save directory."""
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            self.path_entry.delete(0, tk.END)
            self.path_entry.insert(0, folder_selected)

    def fetch_info(self):
        """Fetch video information in a separate thread."""
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showerror("Input Error", "Please enter a YouTube URL.")
            return

        save_path = self.path_entry.get().strip()
        if not save_path:
            messagebox.showerror("Input Error", "Please select a save path.")
            return

        # Disable buttons to prevent multiple clicks
        self.fetch_button.config(state='disabled')
        self.download_button.config(state='disabled')
        self.info_text.config(state='normal')
        self.info_text.delete('1.0', tk.END)
        self.info_text.insert(tk.END, "Fetching video information...\n")
        self.info_text.config(state='disabled')

        threading.Thread(target=self._fetch_info_thread, args=(url,)).start()

    def _fetch_info_thread(self, url):
        """Threaded function to fetch video information."""
        try:
            info = get_video_info(url)
            self.video_info = info
            sanitized_title = sanitize_filename(info.get('title', 'Unknown Title'))

            # Extract required information
            title = info.get('title', 'Unknown Title')
            duration = info.get('duration', 'Unknown')
            view_count = info.get('view_count', 'Unknown')
            formats = info.get('formats', [])

            # Find highest resolution
            best_video = None
            for f in formats:
                if f.get('vcodec') != 'none':
                    if not best_video or f.get('height', 0) > best_video.get('height', 0):
                        best_video = f
            highest_resolution = best_video.get('height', 'Unknown') if best_video else 'Unknown'

            # Update the info display in the main thread
            info_message = (
                f"Title: {title}\n"
                f"Duration: {duration} seconds\n"
                f"View Count: {view_count}\n"
                f"Highest Available Resolution: {highest_resolution}p\n"
            )

            self.info_text.config(state='normal')
            self.info_text.delete('1.0', tk.END)
            self.info_text.insert(tk.END, info_message)
            self.info_text.config(state='disabled')

            # Enable download button
            self.download_button.config(state='normal')

        except yt_dlp.utils.DownloadError as de:
            self.show_error(f"Download error: {de}")
        except Exception as e:
            self.show_error(f"An unexpected error occurred: {str(e)}")
        finally:
            self.fetch_button.config(state='normal')

    def download_video(self):
        """Initiate the video download process."""
        if not self.video_info:
            messagebox.showerror("Error", "No video information available.")
            return

        url = self.url_entry.get().strip()
        save_path = self.path_entry.get().strip()
        format = self.selected_format.get()
        resolution = self.selected_resolution.get()

        if not is_ffmpeg_installed():
            messagebox.showerror("FFmpeg Not Found", "FFmpeg is not installed or not found in system PATH.\n"
                                                    "Please install FFmpeg to enable merging of video and audio streams.\n"
                                                    "Visit https://ffmpeg.org/download.html for installation instructions.")
            return

        # Confirm download
        confirm = messagebox.askyesno("Confirm Download", "Do you want to download this video?")
        if not confirm:
            return

        # Disable buttons during download
        self.download_button.config(state='disabled')
        self.fetch_button.config(state='disabled')
        self.progress.set("Starting download...")

        threading.Thread(target=self._download_video_thread, args=(url, save_path, format, resolution)).start()

    def _download_video_thread(self, url, save_path, format, resolution):
        """Threaded function to download the video."""
        try:
            download_video_with_ydl(url, save_path, format, resolution, self.update_progress)
            self.progress.set("Download completed successfully!")
            messagebox.showinfo("Success", "Download completed successfully!")
        except yt_dlp.utils.DownloadError as de:
            self.show_error(f"Download error: {de}")
        except Exception as e:
            self.show_error(f"An unexpected error occurred: {str(e)}")
        finally:
            self.download_button.config(state='normal')
            self.fetch_button.config(state='normal')

    def update_progress(self, d):
        """Update the progress label based on yt-dlp's progress hooks."""
        if d['status'] == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate')
            downloaded = d.get('downloaded_bytes', 0)
            if total:
                percent = (downloaded / total) * 100
                self.progress.set(f"Downloading... {percent:.2f}%")
        elif d['status'] == 'finished':
            self.progress.set("Download completed!")

    def show_error(self, message):
        """Show error message in the GUI."""
        messagebox.showerror("Error", message)

# ------------------------------ Main Execution ------------------------------ #

if __name__ == "__main__":
    root = tk.Tk()
    app = YouTubeDownloaderApp(root)
    root.mainloop()
