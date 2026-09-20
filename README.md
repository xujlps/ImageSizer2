# ImageSizer

一个开源的 Windows 图片尺寸 + 文件大小压缩小工具。

## 功能

- JPG / JPEG / PNG / WebP / BMP / TIFF
- 拖拽添加图片
- 设置最大宽度（px）
- 设置最大高度（px）
- 设置最大文件大小（KB）
- 自动按比例缩小
- 自动二分搜索 JPEG 质量，在满足文件大小限制的前提下尽量保留画质
- 支持批量处理
- 输出 JPEG，便于严格控制文件大小
- MIT License

## 使用源码

需要 Python 3.10+：

```bash
pip install -r requirements.txt
python ImageSizer.py
```

## 打包成 Windows EXE

双击：

```text
build_windows.bat
```

完成后：

```text
dist\ImageSizer.exe
```

就是单文件 Windows 程序，可以直接复制到其他电脑使用。

## 示例

输入：

- 最大宽度：1920
- 最大高度：1920
- 最大文件大小：500 KB

例如原图：

`6000×4000 / 8 MB`

程序会先缩小到不超过：

`1920×1920`

实际比例可能得到：

`1920×1280`

然后自动调整 JPEG 质量，直到文件大小不超过：

`500 KB`

## 注意

为了可靠地实现“最大 KB”限制，输出统一为 JPEG。
带透明背景的 PNG 会以白色背景输出。

MIT License


### 拖拽功能说明
Windows 单文件版本使用 `tkinterdnd2`，GitHub Actions 会通过 `--collect-all tkinterdnd2` 将拖拽运行组件一并打包进 EXE。
