import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk
import os
import subprocess
import tempfile
import shutil
import threading

class AudioMerger:
    def __init__(self):
        self.root = tk.Tk()
       # self.root.configure(bg="#7CA0BA")   # or any colour you want
        self.root.title("Ses Dosyası Birleştirici")
        self.root.geometry("500x550")
        self.root.resizable(False, False)

        self.paths = [None] * 3
        self.labels = []

        tk.Label(self.root,
                 text="Ses Dosyası Birleştirici",
                 font=("Arial", 16, "bold")).pack(pady=15)

        # File selectors
        for i in range(3):
            frame = tk.Frame(self.root)
            frame.pack(pady=8, fill="x", padx=40)

            btn = tk.Button(frame,
                            text=f"Audio {i+1}",
                            width=20, height=2,
                            command=lambda x=i: self.browse(x))
            btn.pack(side="left")

            lbl = tk.Label(frame,
                           text="seçili dosya yok",
                           anchor="w", width=30)
            lbl.pack(side="left", padx=15)

            self.labels.append(lbl)

        # LUFS selector
        self.lufs_var = tk.StringVar(value="-16")

        frame_lufs = tk.Frame(self.root)
        frame_lufs.pack(pady=10)

        tk.Label(frame_lufs, text="Hedef LUFS:").pack(side="left", padx=5)
        tk.OptionMenu(frame_lufs, self.lufs_var, "-18", "-16", "-14").pack(side="left")

        # Merge button (threaded)
        tk.Button(self.root,
                  text="BİRLEŞTİR (mp3)",
                  font=("Arial", 12, "bold"),
                  bg="#4CAF50", fg="white",
                  height=2,
                  command=self.start_merge_thread).pack(pady=15)

        # Reset button
        tk.Button(self.root,
                  text="temizle",
                  font=("Arial", 10),
                  bg="#f44336",
                  fg="white",
                  height=1,
                  command=self.reset).pack(pady=5)

        # Progress bar
        self.progress = ttk.Progressbar(self.root, mode="indeterminate", length=300)
        self.progress.pack(pady=10)

        # Info box
        info_box = tk.Text(self.root, height=4, width=60, bg="#f0f0f0")
        info_box.pack(side="bottom", pady=10)
        info_box.insert("end",
                        "Ses Dosyası Birleştirici v0.2\n"
                        "© 2026 Ersin Öztürk— Tüm hakları saklıdır.\n"
                        "FFmpeg tabanlı ses işleme.\n"
                        "100 ms crossfade + LUFS normalizasyonu ")
        info_box.config(state="disabled")

        self.root.mainloop()

    def start_merge_thread(self):
        thread = threading.Thread(target=self.merge)
        thread.start()
        self.progress.start(10)

    def browse(self, index):
        file = filedialog.askopenfilename(
            title=f"Ses dosyası seç {index+1}",
            filetypes=[("Audio Files", "*.mp3 *.wav *.ogg *.flac *.m4a")]
        )
        if file:
            self.paths[index] = file
            name = os.path.basename(file)
            self.labels[index].config(
                text=name[:35] + "..." if len(name) > 35 else name
            )

    def reset(self):
        self.paths = [None] * 3
        for lbl in self.labels:
            lbl.config(text="Seçili dosya yok")

    def process_file(self, input_path, output_path):
        lufs = self.lufs_var.get()

        cmd = [
            "ffmpeg",
            "-y",
            "-i", input_path,
            "-af",
            f"loudnorm=I={lufs}:LRA=11:TP=-1,alimiter=limit=-1dB",
            "-vn",
            "-c:a", "pcm_s16le",
            output_path
        ]

        subprocess.run(cmd, check=True,
                       stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL)


    def merge(self):
        try:
            valid_paths = [p for p in self.paths if p]

            if len(valid_paths) < 2:
                self.progress.stop()
                messagebox.showerror("HATA !", "En az 2 ses dosyası seç!")
                return

            output_path = filedialog.asksaveasfilename(
                defaultextension=".mp3",
                filetypes=[("MP3 files", "*.mp3")],
                title="Kaydet"
            )

            if not output_path:
                self.progress.stop()
                return

            temp_dir = tempfile.mkdtemp()
            processed_files = []

            # Step 1: Normalize each file to WAV
            for i, path in enumerate(valid_paths):
                temp_out = os.path.join(temp_dir, f"processed_{i}.wav")
                self.process_file(path, temp_out)
                processed_files.append(temp_out)

            # Step 2: Build crossfade filter
            inputs = []
            filter_graph = ""

            for i, p in enumerate(processed_files):
                inputs += ["-i", p]
                filter_graph += f"[{i}:a]anull[a{i}];"

            last_label = "[a0]"
            for i in range(len(processed_files) - 1):
                left = last_label
                right = f"[a{i+1}]"
                out = f"[x{i+1}]"
                filter_graph += f"{left}{right}acrossfade=d=0.1:c1=tri:c2=tri{out};"
                last_label = out

            filter_graph += f"{last_label}anull[out];"

            cmd = [
                "ffmpeg", "-y",
                *inputs,
                "-filter_complex", filter_graph,
                "-map", "[out]",
                "-b:a", "192k",
                output_path
            ]

            subprocess.run(cmd, check=True,
                       stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL)


            shutil.rmtree(temp_dir)

            self.progress.stop()
            messagebox.showinfo("İşlem Tamam!", f"Kaydedildi:\n{output_path}")

        except Exception as e:
            self.progress.stop()
            messagebox.showerror("HATA", str(e))


if __name__ == "__main__":
    AudioMerger()