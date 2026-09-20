# -*- coding: utf-8 -*-
"""
ImageSizer - Windows 图片尺寸/文件大小压缩工具
License: MIT
"""

import io
import os
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path

from PIL import Image, ImageOps

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
except ImportError:
    DND_FILES = None
    TkinterDnD = None


SUPPORTED = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}


def fit_size(w, h, max_w, max_h):
    scale = min(max_w / w, max_h / h, 1.0)
    return max(1, round(w * scale)), max(1, round(h * scale))


def encode_jpeg(img, quality):
    # JPEG 不支持透明通道；白色背景通常比黑色背景更符合照片压缩场景。
    if img.mode in ("RGBA", "LA"):
        bg = Image.new("RGB", img.size, "white")
        bg.paste(img, mask=img.getchannel("A"))
        img = bg
    elif img.mode != "RGB":
        img = img.convert("RGB")

    bio = io.BytesIO()
    img.save(
        bio,
        format="JPEG",
        quality=quality,
        optimize=True,
        progressive=True,
        subsampling="4:2:0",
    )
    return bio.getvalue()


def compress_image(src, dst, max_w, max_h, max_kb):
    with Image.open(src) as original:
        img = ImageOps.exif_transpose(original)
        w, h = fit_size(img.width, img.height, max_w, max_h)
        if (w, h) != img.size:
            img = img.resize((w, h), Image.Resampling.LANCZOS)

        target = max_kb * 1024

        # 先以高质量尝试；如果本身就满足，则仍输出标准化 JPEG。
        data = encode_jpeg(img, 95)
        if len(data) <= target:
            quality = 95
        else:
            # 二分寻找“尽可能高”的 JPEG 质量，同时满足大小限制。
            lo, hi = 20, 94
            best = None
            best_q = None
            while lo <= hi:
                q = (lo + hi) // 2
                candidate = encode_jpeg(img, q)
                if len(candidate) <= target:
                    best = candidate
                    best_q = q
                    lo = q + 1
                else:
                    hi = q - 1

            if best is None:
                # 极端小目标：降尺寸继续寻找，而不是无限降低质量。
                while img.width > 320 and img.height > 320:
                    nw, nh = max(1, round(img.width * 0.9)), max(1, round(img.height * 0.9))
                    img = img.resize((nw, nh), Image.Resampling.LANCZOS)
                    candidate = encode_jpeg(img, 20)
                    if len(candidate) <= target:
                        best = candidate
                        best_q = 20
                        break

            if best is None:
                raise ValueError("目标文件大小过小，无法生成满足要求的图片。请提高目标 KB。")
            data = best
            quality = best_q

        Path(dst).write_bytes(data)
        return img.size, quality, len(data)


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("ImageSizer - 图片尺寸与文件大小压缩工具")
        self.root.geometry("720x560")
        self.root.minsize(650, 500)
        self.files = []

        self.max_w = tk.StringVar(value="1920")
        self.max_h = tk.StringVar(value="1920")
        self.max_kb = tk.StringVar(value="500")
        self.out_dir = tk.StringVar()
        self.status = tk.StringVar(value="等待添加图片")
        self.progress = tk.DoubleVar(value=0)

        self.build_ui()

        # tkinterdnd2 must be registered on the actual widget receiving the drop.
        # Use a dedicated Text widget as the drop target and bind both drop and drag-over
        # events so the single-file PyInstaller build behaves consistently on Windows.
        if TkinterDnD and DND_FILES:
            self.drop.drop_target_register(DND_FILES)
            self.drop.dnd_bind("<<Drop>>", self.on_drop)
            self.drop.dnd_bind("<<DragEnter>>", lambda e: "copy")

    def build_ui(self):
        style = ttk.Style()
        try:
            style.theme_use("vista")
        except Exception:
            pass

        frm = ttk.Frame(self.root, padding=16)
        frm.pack(fill="both", expand=True)

        ttk.Label(frm, text="ImageSizer", font=("Segoe UI", 20, "bold")).pack(anchor="w")
        ttk.Label(
            frm,
            text="拖入图片 → 设置最大尺寸和文件大小 → 一键压缩",
            foreground="#666666",
        ).pack(anchor="w", pady=(2, 12))

        settings = ttk.LabelFrame(frm, text="输出限制", padding=12)
        settings.pack(fill="x")

        ttk.Label(settings, text="最大宽度（px）").grid(row=0, column=0, sticky="w")
        ttk.Entry(settings, textvariable=self.max_w, width=12).grid(row=0, column=1, padx=(8, 20))
        ttk.Label(settings, text="最大高度（px）").grid(row=0, column=2, sticky="w")
        ttk.Entry(settings, textvariable=self.max_h, width=12).grid(row=0, column=3, padx=(8, 20))
        ttk.Label(settings, text="最大文件大小（KB）").grid(row=0, column=4, sticky="w")
        ttk.Entry(settings, textvariable=self.max_kb, width=12).grid(row=0, column=5, padx=8)

        self.drop = tk.Text(frm, height=12, relief="groove", borderwidth=1, font=("Segoe UI", 10))
        self.drop.pack(fill="both", expand=True, pady=14)
        self.drop.insert("1.0", "把 JPG / PNG / WebP / BMP / TIFF 图片拖到这里\n\n"
                         "也可以点击下面的“选择图片”按钮。")
        self.drop.configure(state="disabled")

        buttons = ttk.Frame(frm)
        buttons.pack(fill="x")
        ttk.Button(buttons, text="选择图片", command=self.choose_files).pack(side="left")
        ttk.Button(buttons, text="清空", command=self.clear_files).pack(side="left", padx=8)
        ttk.Button(buttons, text="开始压缩", command=self.start).pack(side="right")

        out = ttk.Frame(frm)
        out.pack(fill="x", pady=(12, 0))
        ttk.Label(out, text="输出目录：").pack(side="left")
        ttk.Entry(out, textvariable=self.out_dir).pack(side="left", fill="x", expand=True, padx=6)
        ttk.Button(out, text="浏览", command=self.choose_dir).pack(side="right")

        ttk.Progressbar(frm, variable=self.progress, maximum=100).pack(fill="x", pady=(12, 4))
        ttk.Label(frm, textvariable=self.status).pack(anchor="w")

        if not (TkinterDnD and DND_FILES):
            self.status.set("当前版本未加载拖拽组件；请使用“选择图片”。")

    def choose_files(self):
        files = filedialog.askopenfilenames(
            title="选择图片",
            filetypes=[
                ("图片", "*.jpg *.jpeg *.png *.webp *.bmp *.tif *.tiff"),
                ("所有文件", "*.*"),
            ],
        )
        self.add_files(files)

    def on_drop(self, event):
        files = self.root.tk.splitlist(event.data)
        self.add_files(files)

    def add_files(self, files):
        added = 0
        for f in files:
            p = Path(f)
            if p.is_file() and p.suffix.lower() in SUPPORTED and str(p) not in self.files:
                self.files.append(str(p))
                added += 1

        self.drop.configure(state="normal")
        self.drop.delete("1.0", "end")
        if self.files:
            self.drop.insert("1.0", f"已添加 {len(self.files)} 张图片\n\n")
            for i, f in enumerate(self.files, 1):
                self.drop.insert("end", f"{i}. {Path(f).name}\n")
        else:
            self.drop.insert("1.0", "请拖入图片或点击“选择图片”。")
        self.drop.configure(state="disabled")
        self.status.set(f"已添加 {len(self.files)} 张图片" if added else "没有新增图片")

    def clear_files(self):
        self.files.clear()
        self.drop.configure(state="normal")
        self.drop.delete("1.0", "end")
        self.drop.insert("1.0", "把 JPG / PNG / WebP / BMP / TIFF 图片拖到这里\n\n"
                         "也可以点击下面的“选择图片”按钮。")
        self.drop.configure(state="disabled")
        self.progress.set(0)
        self.status.set("等待添加图片")

    def choose_dir(self):
        d = filedialog.askdirectory(title="选择输出目录")
        if d:
            self.out_dir.set(d)

    def start(self):
        if not self.files:
            messagebox.showwarning("提示", "请先添加图片。")
            return
        try:
            mw, mh, kb = int(self.max_w.get()), int(self.max_h.get()), int(self.max_kb.get())
            if mw < 1 or mh < 1 or kb < 1:
                raise ValueError
        except ValueError:
            messagebox.showerror("参数错误", "最大宽度、最大高度、最大文件大小必须是正整数。")
            return

        out = Path(self.out_dir.get()) if self.out_dir.get() else Path(self.files[0]).parent / "ImageSizer_Output"
        out.mkdir(parents=True, exist_ok=True)

        threading.Thread(target=self.worker, args=(mw, mh, kb, out), daemon=True).start()

    def worker(self, mw, mh, kb, out):
        ok = 0
        errors = []
        total = len(self.files)

        for i, src in enumerate(self.files, 1):
            try:
                name = Path(src).stem + "_compressed.jpg"
                dst = out / name
                size, quality, bytes_written = compress_image(src, dst, mw, mh, kb)
                ok += 1
                self.root.after(
                    0,
                    lambda i=i, size=size, q=quality, b=bytes_written:
                    self.status.set(f"{i}/{total}：{size[0]}×{size[1]}，质量 {q}，{b/1024:.1f} KB"),
                )
            except Exception as e:
                errors.append(f"{Path(src).name}: {e}")

            self.root.after(0, lambda i=i: self.progress.set(i / total * 100))

        msg = f"完成：{ok}/{total} 张\n输出目录：{out}"
        if errors:
            msg += "\n\n失败文件：\n" + "\n".join(errors[:10])

        self.root.after(0, lambda: messagebox.showinfo("处理完成", msg))
        self.root.after(0, lambda: self.status.set(f"完成：{ok}/{total} 张"))


if __name__ == "__main__":
    if TkinterDnD:
        root = TkinterDnD.Tk()
    else:
        root = tk.Tk()
    App(root)
    root.mainloop()
