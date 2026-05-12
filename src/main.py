"""
ALOE字幕提取软件
视频字幕提取工具 - Whisper 语音识别 + 翻译
"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import os
import sys

if getattr(sys, 'frozen', False):
    _app_dir = os.path.dirname(sys.executable)
    sys.path.insert(0, _app_dir)
else:
    _app_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, _app_dir)

from subtitle_downloader import find_ytdlp, get_video_title, download_audio, transcribe_audio
from translator import Translator
from exporter import export_docx_text


COLORS = {
    "bg": "#1a1a2e", "card_bg": "#16213e", "accent": "#0f3460",
    "highlight": "#e94560", "text": "#eee", "text_dim": "#888",
    "input_bg": "#0f3460", "btn": "#e94560", "btn_hover": "#ff6b81",
    "success": "#2ed573", "border": "#2a2a4a",
}


class ALOEApp:
    def __init__(self, root):
        self.root = root
        self.root.title("ALOE字幕提取软件")
        self.root.geometry("720x680")
        self.root.minsize(650, 600)
        self.root.configure(bg=COLORS["bg"])

        self.is_running = False
        self.ytdlp_path = find_ytdlp()
        self.output_dir = os.path.join(os.path.expanduser("~"), "Desktop", "YouTubeSubtitles")

        self.url_var = tk.StringVar()
        self.lang_var = tk.StringVar(value="bilingual")
        self.src_lang_var = tk.StringVar(value="auto")
        self.model_var = tk.StringVar(value="small")
        self.dir_var = tk.StringVar(value=self.output_dir)

        self._build_ui()
        self._check_ytdlp()

    def _build_ui(self):
        main = tk.Frame(self.root, bg=COLORS["bg"])
        main.pack(fill=tk.BOTH, expand=True, padx=20, pady=15)

        # 标题
        title_frame = tk.Frame(main, bg=COLORS["bg"])
        title_frame.pack(fill=tk.X, pady=(0, 15))
        tk.Label(title_frame, text="ALOE", font=("Consolas", 28, "bold"),
                 fg=COLORS["highlight"], bg=COLORS["bg"]).pack(side=tk.LEFT)
        tk.Label(title_frame, text="  字幕提取软件", font=("Microsoft YaHei UI", 16),
                 fg=COLORS["text"], bg=COLORS["bg"]).pack(side=tk.LEFT, padx=(5, 0), pady=(8, 0))

        # 输入区
        card1 = self._card(main)
        tk.Label(card1, text="视频链接", font=("Microsoft YaHei UI", 10, "bold"),
                 fg=COLORS["text"], bg=COLORS["card_bg"], anchor="w").pack(fill=tk.X, pady=(0, 6))
        url_row = tk.Frame(card1, bg=COLORS["card_bg"])
        url_row.pack(fill=tk.X)
        self.url_entry = tk.Entry(url_row, textvariable=self.url_var, font=("Consolas", 11),
                                  bg=COLORS["input_bg"], fg=COLORS["text"],
                                  insertbackground=COLORS["text"], relief=tk.FLAT, bd=8)
        self.url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=4)
        self._btn(url_row, "粘贴", self._paste_url, width=6).pack(side=tk.LEFT, padx=(8, 0))

        # 视频语言（识别语言）
        card_src = self._card(main)
        tk.Label(card_src, text="视频语言（语音识别）", font=("Microsoft YaHei UI", 10, "bold"),
                 fg=COLORS["text"], bg=COLORS["card_bg"], anchor="w").pack(fill=tk.X, pady=(0, 6))
        src_lang_frame = tk.Frame(card_src, bg=COLORS["card_bg"])
        src_lang_frame.pack(fill=tk.X)
        self.src_lang_options = [
            ("auto", "自动检测"),
            ("en", "英语"),
            ("zh", "中文"),
            ("ja", "日语"),
            ("ko", "韩语"),
            ("fr", "法语"),
            ("de", "德语"),
            ("es", "西班牙语"),
            ("ru", "俄语"),
            ("pt", "葡萄牙语"),
            ("ar", "阿拉伯语"),
            ("vi", "越南语"),
        ]
        src_lang_combo = ttk.Combobox(src_lang_frame, textvariable=self.src_lang_var,
                                       values=[f"{v} — {l}" for v, l in self.src_lang_options],
                                       state="readonly", font=("Microsoft YaHei UI", 10), width=25)
        src_lang_combo.set("auto — 自动检测")
        src_lang_combo.pack(side=tk.LEFT)

        # 识别精度
        model_frame = tk.Frame(card_src, bg=COLORS["card_bg"])
        model_frame.pack(fill=tk.X, pady=(8, 0))
        tk.Label(model_frame, text="识别精度：", font=("Microsoft YaHei UI", 9),
                 fg=COLORS["text_dim"], bg=COLORS["card_bg"]).pack(side=tk.LEFT)
        self.model_options = [
            ("tiny", "极速（精度低）"),
            ("base", "快速"),
            ("small", "均衡（推荐）"),
            ("medium", "高精度（较慢）"),
            ("large-v3", "最高精度（很慢）"),
        ]
        model_combo = ttk.Combobox(model_frame, textvariable=self.model_var,
                                    values=[f"{v} — {l}" for v, l in self.model_options],
                                    state="readonly", font=("Microsoft YaHei UI", 9), width=22)
        model_combo.set("small — 均衡（推荐）")
        model_combo.pack(side=tk.LEFT, padx=(8, 0))

        # 输出语言选择
        card2 = self._card(main)
        tk.Label(card2, text="输出语言", font=("Microsoft YaHei UI", 10, "bold"),
                 fg=COLORS["text"], bg=COLORS["card_bg"], anchor="w").pack(fill=tk.X, pady=(0, 8))
        lang_frame = tk.Frame(card2, bg=COLORS["card_bg"])
        lang_frame.pack(fill=tk.X)
        for val, label in [("en", "仅原文"), ("zh", "仅中文翻译"), ("bilingual", "双语（原文+中文）")]:
            rb = tk.Radiobutton(lang_frame, text=label, variable=self.lang_var, value=val,
                                font=("Microsoft YaHei UI", 10), fg=COLORS["text"],
                                bg=COLORS["card_bg"], selectcolor=COLORS["accent"],
                                activebackground=COLORS["card_bg"], activeforeground=COLORS["text"])
            rb.pack(side=tk.LEFT, padx=(0, 20))

        # 输出目录
        card4 = self._card(main)
        tk.Label(card4, text="保存位置", font=("Microsoft YaHei UI", 10, "bold"),
                 fg=COLORS["text"], bg=COLORS["card_bg"], anchor="w").pack(fill=tk.X, pady=(0, 6))
        dir_row = tk.Frame(card4, bg=COLORS["card_bg"])
        dir_row.pack(fill=tk.X)
        self.dir_entry = tk.Entry(dir_row, textvariable=self.dir_var, font=("Consolas", 10),
                                  bg=COLORS["input_bg"], fg=COLORS["text"],
                                  insertbackground=COLORS["text"], relief=tk.FLAT, bd=6)
        self.dir_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=3)
        self._btn(dir_row, "浏览", self._browse_dir, width=6).pack(side=tk.LEFT, padx=(8, 0))

        # 操作按钮
        btn_frame = tk.Frame(main, bg=COLORS["bg"])
        btn_frame.pack(fill=tk.X, pady=(10, 5))
        self.start_btn = tk.Button(btn_frame, text="▶  开始提取",
                                   font=("Microsoft YaHei UI", 13, "bold"),
                                   bg=COLORS["btn"], fg="white", relief=tk.FLAT, bd=0,
                                   activebackground=COLORS["btn_hover"], activeforeground="white",
                                   cursor="hand2", command=self._start_extraction, padx=30, pady=8)
        self.start_btn.pack(side=tk.LEFT)
        self.status_label = tk.Label(btn_frame, text="就绪", font=("Microsoft YaHei UI", 9),
                                     fg=COLORS["text_dim"], bg=COLORS["bg"])
        self.status_label.pack(side=tk.LEFT, padx=(15, 0))

        # 进度条
        self.progress = ttk.Progressbar(main, mode='indeterminate', length=300)
        self.progress.pack(fill=tk.X, pady=(5, 10))
        style = ttk.Style()
        style.configure("TProgressbar", troughcolor=COLORS["card_bg"], background=COLORS["highlight"])

        # 日志
        log_frame = tk.Frame(main, bg=COLORS["bg"])
        log_frame.pack(fill=tk.BOTH, expand=True)
        tk.Label(log_frame, text="运行日志", font=("Microsoft YaHei UI", 9, "bold"),
                 fg=COLORS["text_dim"], bg=COLORS["bg"], anchor="w").pack(fill=tk.X, pady=(0, 4))
        self.log_text = tk.Text(log_frame, font=("Consolas", 9), bg=COLORS["card_bg"],
                                fg=COLORS["text"], relief=tk.FLAT, bd=8, height=10,
                                insertbackground=COLORS["text"], wrap=tk.WORD, state=tk.DISABLED)
        scrollbar = tk.Scrollbar(log_frame, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.pack(fill=tk.BOTH, expand=True)

    def _card(self, parent):
        frame = tk.Frame(parent, bg=COLORS["card_bg"], bd=0, highlightthickness=1,
                         highlightbackground=COLORS["border"])
        frame.pack(fill=tk.X, pady=(0, 10))
        inner = tk.Frame(frame, bg=COLORS["card_bg"])
        inner.pack(fill=tk.X, padx=15, pady=12)
        return inner

    def _btn(self, parent, text, command, width=8):
        return tk.Button(parent, text=text, command=command, font=("Microsoft YaHei UI", 9),
                         bg=COLORS["accent"], fg=COLORS["text"], relief=tk.FLAT, bd=0,
                         activebackground=COLORS["highlight"], activeforeground="white",
                         cursor="hand2", width=width)

    def _paste_url(self):
        try:
            clip = self.root.clipboard_get()
            if clip:
                self.url_var.set(clip.strip())
        except tk.TclError:
            pass

    def _browse_dir(self):
        path = filedialog.askdirectory(title="选择保存位置")
        if path:
            self.dir_var.set(path)

    def _check_ytdlp(self):
        if not self.ytdlp_path:
            self._log("警告: 未找到 yt-dlp.exe，请将 yt-dlp.exe 放到软件同目录下")
            self.status_label.config(text="yt-dlp 未找到", fg=COLORS["highlight"])
        else:
            self._log(f"yt-dlp 路径: {self.ytdlp_path}")

    def _log(self, msg):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, msg + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def _set_status(self, text, color=None):
        self.status_label.config(text=text, fg=color or COLORS["text_dim"])

    def _validate(self):
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("提示", "请输入视频链接")
            return False
        if not self.ytdlp_path:
            messagebox.showerror("错误", "未找到 yt-dlp.exe，请将 yt-dlp.exe 放到软件同目录下")
            return False
        return True

    def _start_extraction(self):
        if self.is_running:
            return
        if not self._validate():
            return
        self.is_running = True
        self.start_btn.config(state=tk.DISABLED, text="处理中...")
        self.progress.start(10)
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete("1.0", tk.END)
        self.log_text.config(state=tk.DISABLED)
        thread = threading.Thread(target=self._extraction_worker, daemon=True)
        thread.start()

    def _extraction_worker(self):
        try:
            url = self.url_var.get().strip()
            lang = self.lang_var.get()
            output_dir = self.dir_var.get()

            # 解析源语言
            src_lang_raw = self.src_lang_var.get()
            src_lang = src_lang_raw.split(" — ")[0] if " — " in src_lang_raw else src_lang_raw
            whisper_lang = None if src_lang == "auto" else src_lang

            # 解析模型大小
            model_raw = self.model_var.get()
            model_size = model_raw.split(" — ")[0] if " — " in model_raw else model_raw

            def log(msg):
                self.root.after(0, self._log, msg)
            def status(msg):
                self.root.after(0, self._set_status, msg)

            log("=" * 50)
            log("ALOE字幕提取软件 - 开始处理")
            log("=" * 50)

            # 1. 获取视频标题
            status("正在获取视频信息...")
            title = get_video_title(self.ytdlp_path, url)
            log(f"视频标题: {title}")

            safe_title = title
            # 替换所有 Windows 文件名不允许的字符
            for ch in '<>:"/\\|?*#~!@%^&()[]{}+=':
                safe_title = safe_title.replace(ch, '_')
            # 清理连续空格和末尾省略号
            import re as _re
            safe_title = _re.sub(r'\s+', ' ', safe_title).strip()
            safe_title = safe_title.rstrip('.')
            # 限制长度，避免路径过长
            if len(safe_title) > 80:
                safe_title = safe_title[:80].rstrip()
            if not safe_title:
                safe_title = "untitled"

            # 2. 下载音频 + Whisper 语音识别
            status("正在下载音频...")
            log("正在下载音频...")
            audio_path = download_audio(self.ytdlp_path, url, output_dir, title)
            if not audio_path:
                self.root.after(0, lambda: messagebox.showerror("失败", "音频下载失败，请检查链接"))
                return

            log(f"音频下载完成: {os.path.basename(audio_path)}")
            status("正在语音识别...")

            def whisper_callback(msg):
                log(msg)
                status(msg)

            en_entries, full_english = transcribe_audio(audio_path, callback=whisper_callback, language=whisper_lang, model_size=model_size)

            if not en_entries:
                self.root.after(0, lambda: messagebox.showerror("失败", "语音识别失败"))
                return

            log(f"语音识别完成: {len(en_entries)} 条, {len(full_english)} 字符")
            log(f"文本样本: {full_english[:100]}...")

            # 3. 根据语言选择导出
            all_generated = []

            lang_name = dict(self.src_lang_options).get(src_lang, src_lang)

            if lang == "en":
                log(f"导出{lang_name}文档...")
                status(f"导出{lang_name}文档...")
                path = os.path.join(output_dir, f"{safe_title}_原文.docx")
                export_docx_text(full_english, path, title=safe_title, subtitle_type=f"{lang_name}原文")
                all_generated.append(path)
                log(f"已生成: {path}")

            elif lang == "zh":
                log("正在翻译为中文...")
                status("正在翻译...")
                translator = Translator(source_lang=src_lang)
                def tr_callback(cur, total, msg):
                    status(msg)
                zh_text = translator.translate_text(full_english, callback=tr_callback)
                log(f"翻译完成: {len(zh_text)} 字符")

                status("导出中文文档...")
                path = os.path.join(output_dir, f"{safe_title}_中文.docx")
                export_docx_text(zh_text, path, title=safe_title, subtitle_type="中文翻译")
                all_generated.append(path)
                log(f"已生成: {path}")

            elif lang == "bilingual":
                log("正在翻译为中文...")
                status("正在翻译...")
                translator = Translator(source_lang=src_lang)
                def tr_callback(cur, total, msg):
                    status(msg)
                zh_text = translator.translate_text(full_english, callback=tr_callback)
                log(f"翻译完成: {len(zh_text)} 字符")

                # 导出原文文档
                status(f"导出{lang_name}文档...")
                en_path = os.path.join(output_dir, f"{safe_title}_原文.docx")
                export_docx_text(full_english, en_path, title=safe_title, subtitle_type=f"{lang_name}原文")
                all_generated.append(en_path)
                log(f"已生成: {en_path}")

                # 导出中文文档
                status("导出中文文档...")
                zh_path = os.path.join(output_dir, f"{safe_title}_中文.docx")
                export_docx_text(zh_text, zh_path, title=safe_title, subtitle_type="中文翻译")
                all_generated.append(zh_path)
                log(f"已生成: {zh_path}")

            # 清理临时音频文件
            try:
                if audio_path and os.path.isfile(audio_path):
                    os.remove(audio_path)
                    log("已清理临时文件")
            except Exception:
                pass

            # 完成
            log("")
            log("=" * 50)
            log(f"完成! 共生成 {len(all_generated)} 个文件:")
            for f in all_generated:
                log(f"  → {f}")
            log("=" * 50)

            def show_done():
                self.is_running = False
                self.start_btn.config(state=tk.NORMAL, text="▶  开始提取")
                self.progress.stop()
                self._set_status(f"完成! 共生成 {len(all_generated)} 个文件", COLORS["success"])
                if messagebox.askyesno("完成", f"共生成 {len(all_generated)} 个文件\n是否打开输出目录?"):
                    if os.name == "nt":
                        os.startfile(output_dir)
                    else:
                        import subprocess
                        subprocess.Popen(["open", output_dir])
            self.root.after(0, show_done)

        except Exception as e:
            self.root.after(0, self._log, f"错误: {str(e)}")
            def show_err():
                self.is_running = False
                self.start_btn.config(state=tk.NORMAL, text="▶  开始提取")
                self.progress.stop()
                self._set_status("出错", COLORS["highlight"])
                messagebox.showerror("错误", str(e))
            self.root.after(0, show_err)


def main():
    root = tk.Tk()
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

    app = ALOEApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
