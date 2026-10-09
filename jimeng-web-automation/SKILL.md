# 即梦网页自动化生图 (CDP 接管)

通过 Chrome DevTools Protocol 接管已登录即梦的 Edge 浏览器，用「真实鼠标/键盘事件 + DOM 定位」自动完成：填提示词 → 点生成 → 轮询结果 → 下载高清成图。适用于 AI 漫剧/短剧流水线中的即梦生图 Agent。

## 前置条件（一次性）

> ## ⛔ 铁律（2026-10-03 用户明令，最高优先级）
> **Agent 绝不重启 / taskkill / Stop-Process 用户的 Edge 来"恢复"即梦网页。**
> 重启拿到的是**没有登录态**的实例（用户亲测：登录态不会如预期随 user-data-dir 复用）。
> 接管必须基于**用户自己手动打开并已登录**的浏览器。
> 9222 连不上时的正确动作 = 停下来，请用户自己打开并确认已登录，Agent 只能等，不能代劳杀进程。
> 下面的启动命令仅供**用户本人**参考执行。

1. Edge 必须带调试参数启动（保留原用户目录，登录态不丢；**由用户手动执行**）：
   ```
   msedge.exe --remote-debugging-port=9222 --remote-allow-origins=* --user-data-dir="<用户目录>\AppData\Local\Microsoft\Edge\User Data" https://jimeng.jianying.com/ai-tool/home/
   ```
   - 在 WorkBuddy 中必须用 Bash 工具的 `run_in_background: true` 启动；`nohup`/`Start-Process` 都不行（进程会随调用结束被回收或静默失败）。
   - 启动前若 Edge 残留，先 `cmd.exe /c "taskkill /IM msedge.exe /F"`（Git Bash 里 `/IM` 会被路径转换，需 `export MSYS_NO_PATHCONV=1`）。
2. Python 需 `websocket-client`。

## 关键坑（全部踩过）

| 坑 | 症状 | 解法 |
|---|---|---|
| 本地 HTTP 代理劫持 localhost | curl/WS 连 9222 得 502 | 连接前清空 `HTTP_PROXY/HTTPS_PROXY` 等环境变量 |
| Git Bash `/tmp` 路径 Python 读不到 | 从日志取 UUID 失败回退到过期 UUID → 404 | **不要用浏览器级 UUID**，直接用 `/json/list` 的页面级 WebSocket |
| 页面级端点免 UUID | — | `ws://127.0.0.1:9222/devtools/page/<ID>`，从 `http://127.0.0.1:9222/json/list` 拿 |
| React SPA 输入 | JS 改 input.value 不触发框架状态 | 用 `Input.insertText`（受信任 IME 式插入）+ `Input.dispatchMouseEvent` 真实点击 |
| 即梦图片防盗链 | 去掉 URL `~tplv-*` 参数直接 fetch → 403 | 必须带签名 URL 在页面内 fetch（查看器主图是高清带签名版） |
| 后台任务 stdout 缓冲 | 长轮询脚本后台跑看不到输出 | 用 `python -u` 或直接等 task-notification |

## 核心工具

`ai_comic_pipeline/jm.py`（工作区内）：
- `python jm.py shot <path>` 截图 / `boxes` 列元素坐标 / `click <x> <y>` 真实点击 / `insert <文本>` 输入 / `press Enter|ArrowRight` 按键 / `eval <js>` 执行 JS
- Python 内 `from jm import JM` 复用类。

## 完整生图流程

1. **定位输入框**：contenteditable div，placeholder 含「上传参考图、输入文字或 主体」；用 `boxes()` 按 tag/ce/尺寸过滤。
2. **点输入框 → `Input.insertText`** 注入提示词（即梦六要素格式：主体/场景/光线/构图/画风/避免）。
3. **点生成**：圆形主按钮 class `lv-btn-shape-circular`（lv-btn-primary）；点击后页面跳创作记录页。
4. **轮询结果**：页面 img 中 `dreamina-sign.byteimg.com` 的出现即完成（进度百分比在记录块 innerText）。
5. **★ 下载高清图 —— 首选「点下载键」，不要走 CDP 抓图**：

   **结果小图上有个「向下箭头」图标，那就是下载键**，鼠标移上去显示"下载"。
   点它，浏览器直接把图存进 **`<下载目录>/`**，命名格式：

   ```
   jimeng-2026-09-30-2685-电影感写实摄影。一位二十多岁的美丽东方女性，长发被海风吹起，....png
   └─ jimeng-<日期>-<4位随机>-<提示词前若干字>.png
   ```

   取图只需一行 glob：

   ```python
   glob.glob("<下载目录>/jimeng-<今天日期>-*.png")  # 按 mtime 排序取最新
   ```

   实测下载下来是 **1440×2560（2.6~3.3 MB）高清原图**，比 CDP 抓的还干净。

   **★ 为什么不用 CDP 抓**：之前按下面 (a)(b)(c) 那套「开查看器 → 页面内 fetch →
   ArrowRight 翻页」实现过，失败过多次（抓到 UI 缩略图 / 查看器覆盖层定位失败 /
   大图找不到）。**这条路维护成本高、成功率低，已废弃。**
   （原实现保留在 `ai_comic_pipeline/step3_download.py`，仅作参考。）

   <details><summary>废弃的 CDP 抓图法（存档，不建议用）</summary>

   a. 结果网格里点第一张图（render >140px 的 img）打开详情查看器；
   b. 查看器主图 render>300px，naturalWidth≈1728（2K·3:4），页面内 `fetch(src)` → FileReader → base64（带签名不 403）；
   c. 派发 ArrowRight 键盘事件翻页 1→4，重复下载。

   </details>

6. 成图落地：手点下载键 → `<下载目录>/jimeng-*.png`；
   （旧路径产物为 `output/jm_shot1_hd_1..4.png`）。

### 取到图之后必做：用 VL 验内容，不要靠猜

**反面教材**：曾以「平均 RGB 偏暖 → 判定是夕阳海滩」来挑首帧，
结果那张图其实是**咖啡馆门口背绿包的男青年**（室内暖光同样偏暖）。
视频生成完才发现，白跑一整轮。

**凡是挑首帧，一律先让 `qwen3-vl:30b` 描述一遍**，确认场景/人物/物件/画幅再投 H3。

## 流水线集成要点

- 每次调用独立建 JM 连接（连接便宜，页面级 WS 无状态依赖）。
- 坐标会随窗口尺寸变化，永远用 `getBoundingClientRect` 现算，不要存死坐标。
- 生图参数（比例/分辨率/张数）在输入框下方的参数条按钮里（`3:4 2K 4`），需先真实点击展开再选。
- 模型切换：参数条上模型名（如 `Seedream 5.0 Pro`）点开下拉，再点选项文本。
