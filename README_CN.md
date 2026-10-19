# P(DOOM) — Blender 复刻版音乐视频

**用 Blender 5.2 真实建模、打光、摄像机与 EEVEE 渲染的 2:36 音乐视频。**

这是对 [mexicat/pdoom-video](https://github.com/mexicat/pdoom-video)（TypeScript + three.js 的程序化 WebGL
音乐视频）的一次独立重建。全片 **22 个 plate、4702 帧、1920×1080 / 30 fps**，逐词歌词同步与剪辑点来自原作
的歌词/节拍数据。

[![License: MIT](https://img.shields.io/badge/license-MIT-EEE9DF.svg)](LICENSE)
[![Blender](https://img.shields.io/badge/Blender-5.2-FF4D12.svg)](https://www.blender.org/)

![poster](docs/poster.jpg)

## 观看

- **[完整成片 1080p（含原曲）](https://github.com/WGcx2006/pdoom-blender/releases/latest)** — GitHub Release，约 172 MB
- **[31 秒无声片段](docs/highlight.mp4)**
- **[60 帧全片缩略图](docs/contact-sheet.jpg)**、**[转场边界检查图](docs/cut-boundary-sheet.jpg)**

歌曲与歌词的版权归原作者；Release 中的成片是非商业演示，详见 [NOTICE.md](NOTICE.md)。

## 规格

| | |
|---|---|
| 时长 | 156.73 s（2:36.73） |
| 帧数 | 4702 @ 30 fps |
| 分辨率 | 1920 × 1080 |
| 渲染 | Blender 5.2 / EEVEE，motion blur，Bloom/Halation/色散 |
| 后期 | ffmpeg：4/255 胶片颗粒 + PI/7 暗角，AAC 192 kbps |
| 代码 | 17 个 Python 场景模块 → 22 个 plate |

## 做了什么

- 把原作的 treatment 重新 stage 成真实 3D：图书馆、触手群、纸夹晶格、变压器堆栈、笔记本房间、
  倾斜桌面、剧场、纸张方程卡，以及大量真实字体排版。
- 确定性的 Blender 渲染管线：每个 plate 都是歌曲时间的纯函数；逐词高亮直接由
  `data.line()` 的 word start/end 驱动，节拍来自 132 BPM 网格。
- 把 WebGL 的 ink/bone/信号橙、雕刻线、Swiss 排版翻译成 Blender 的 emission 材质、曲线、
  面积光与合成器。

## 与原创的差距

- 30 fps（原版 60 fps），极快甩镜头的运动模糊更明显。
- 原版雕刻是 raymarched shader；这里是真实 3D 几何 + 平面 object-space hatching。
- 少数 plate 仍偏暖/偏密（paperclips、fuse 图表、spacetime 涡流、shoggoth 的灰调）。
- 结尾回到开场是意象级循环，不是逐像素一致。

## 快速开始

环境：**Blender 5.2**、**ffmpeg/ffprobe**、**Python 3.10+**、Pillow。

    git clone https://github.com/WGcx2006/pdoom-blender.git
    cd pdoom-blender
    python -m pip install -r requirements.txt

    # 拉取原作的数据、字体与歌曲（不随本仓库分发）
    python scripts/fetch_source.py
    python scripts/check_env.py

    # 单个 plate 的静帧
    blender -b --factory-startup --python blender/build.py -- open --stills 1,80,170

    # 全片渲染 + 拼接
    python tools/render_all.py --workers 3
    python tools/assemble.py

    # 审片
    python tools/qa.py
    python tools/cuts.py

Blender/ffmpeg 不在 PATH 时：

    BLENDER="/path/to/blender" python tools/render_all.py --workers 3

## 仓库结构

    blender/
      pdoom/core.py       # 调色板、字体排版、曲线、摄像机、合成器、关键帧
      pdoom/data.py       # 时间线、歌词/节拍/音频数据
      pdoom/motifs.py     # 火花、面具、HUD、P(doom) 仪表
      scenes/*.py         # 17 个模块 → 22 个 plate
      build.py            # 构建单个场景，可选静帧
      STYLE.md            # 场景作者的视觉规范
    tools/                # 并行渲染、拼接、QA、缩略图、转场检查
    scripts/              # 拉取原作、环境检查、CI 卫生检查
    docs/                 # 剧照、海报、无声片段、分镜表、审查记录
    .github/workflows/    # 语法 + 仓库卫生 CI

22 个 plate 的时间窗与做法见 [docs/SCENES.md](docs/SCENES.md)，管线细节见
[docs/PIPELINE.md](docs/PIPELINE.md) 与 [blender/STYLE.md](blender/STYLE.md)。

## 审查过程

七个 sub-agent 分头做场景，我负责统一工具链、open、四个 hook、最终剪辑与所有审片。每个 plate
先出 6–20 张全分辨率静帧，我逐张检查字是否出画、是否重叠、调色板、黑帧、歌词可读性、构图；不合格
就打回重做。典型修改包括：loss 的整片橙褐地形、shoggoth 的灰管/缺面具、spacetime 的扭曲歌词与
棕色 bug、ilya 的橙色平板、paperclips 的青铜珠宝感、outro 的透底读数/残留卡片。完整记录见
[docs/REVIEW.md](docs/REVIEW.md)。

## 许可

- 代码、Blender 场景、渲染与文档：MIT，2026 WGcx2006 与贡献者。
- 原作 [mexicat/pdoom-video](https://github.com/mexicat/pdoom-video)：MIT。
- 歌曲/歌词、字体、原作素材：归各自作者/许可（OFL 等），**不包含在本仓库**；用
  `scripts/fetch_source.py` 在本地获取。详见 [NOTICE.md](NOTICE.md)。

本仓库不包含音频、对齐歌词数据或字体文件；Release 中的成片仅用于演示。
