# Pi 技术文库 · 本地运行

这个主压缩包已包含 Pi 1.04 和 Pi Durable 两本完整网站。只下载并解压主包即可运行，不需要下载原图包，也不需要 Python。

## 启动

1. 安装 Node.js LTS（最低 20.19，推荐 22 或 24）。
2. 克隆本仓库（或解压发布压缩包），在含 `package.json` 的文件夹中打开终端。
3. 依次运行：

```sh
npm ci --ignore-scripts
npm run build
npm run preview
```

然后在同一台电脑的浏览器打开 http://localhost:4173 。停止时在终端按 Ctrl+C。

编辑开发模式：

```sh
npm run dev
```

打开终端打印的本地地址，通常是 http://localhost:5173 。不要把源文件直接拖进浏览器。

## 本次新增

- Pi Durable：10 章、7 节参考资料及完整开篇，共 53 个阅读/参考小节
- 64 个代码块、94 张可调整列宽的正文表格
- 66 幅原生 SVG 交互图，保留可放大的组合封面原图；67 张原图均可对照
- 图中可点击节点、用方向键切换；“读取图中文字”提供可选择和复制的原始标签
- 手机宽度下使用“书籍目录”，宽图和宽表在各自区域内横向滚动
- Pi 1.04 的正文和原有图片保持不变

## 已处理的格式问题

修复冗余粗体分隔符、中文标点邻接导致粗体标记外露、表格类型联合符号误分列、空引用尾行；依据 PDF 恢复 4 个缺失的提示标签，并对应原书呈现警告、规则和来源。没有改写示例代码或猜测技术结论。

原书图表与正文存在一处 JSONL 查询耗时 `0.45 / 0.44 μs` 差异，两处原值均保留并记录。原始 PDF 使用轮廓字体，因此保留其字形，同时提供可复制文字。少量斜线纹理由 SVG 线条重建；组合封面保留原图。

## 原图与校验

`pi-durable-originals-1.zip` 和 `pi-durable-originals-2.zip` 仅供后续编辑/原始资料复核。将其中 `sources/` 合并到主项目根目录即可；它们不影响日常运行。Pi 1.04 的原始 PNG 仍使用之前提供的两份原图包。

`npm run check:assets` 使用 Node 校验所有 129 张运行时 WebP。

完整源码复核需 Python 和对应原图包：`npm run check:book`、`npm run check:durable`。普通启动不调用这些 Python 检查。

## 原文来源

两本手册的原始 PDF 由作者公开发布，本仓库只提供中文翻译：

- **Pi Technical Manual** — <https://x.com/calebfahlgren/status/2107199330926899652>
- **Pi Durable Technical Manual** — <https://x.com/lucataco/status/2107230736403013653>

原 PDF 不随本仓库分发。翻译内容版权归原作者所有，此处仅作学习交流。

## 验证范围

已进行完整文字/代码/表格/原图校验、独立复核、桌面与 390 CSS 像素窄屏浏览器检查，以及全新解压后的安装、构建、预览和开发启动测试。窄屏验证是云端 Chromium 中的响应式视口，并非实机手机；未在真实 Windows 机器上运行，但正常启动链路只依赖跨平台 Node.js。

站点通过 GitHub Actions 自动部署到 GitHub Pages：<https://caizongyuan.github.io/pi-lessons/> 。详细证据见 `QA.md`。

## 许可

本仓库的构建脚本、站点代码与排版实现遵循 [MIT](LICENSE)；原手册内容版权归原作者所有。
