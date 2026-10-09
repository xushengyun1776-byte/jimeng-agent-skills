# jimeng-agent-skills

即梦（jimeng.jianying.com）网页自动化的 Agent 技能集 —— 三个互补技能 + 一份全流程 SOP。

> 适用场景：AI 漫剧 / 短剧流水线中，用即梦网页出关键帧、出视频，再落地本地推理出片。
> 全部技能均已在真实环境实操验证（2026-09 ~ 2026-10）。

## 技能清单

| 名称 | 目录 | 一句话说明 | 标签 |
|---|---|---|---|
| **jimeng-web-automation** | `jimeng-web-automation/` | CDP 接管已登录 Edge，真实鼠标/键盘事件完成即梦**生图**：填提示词 → 点生成 → 轮询 → 点下载键取高清图 | `#cdp` `#生图` `#edge` |
| **jimeng-ref2video** | `jimeng-ref2video/` | **纯人手模拟**（不接管端口、不用官方 CLI）在即梦网页**上传参考图生成视频/图片**：原生文件对话框接管 + 准星法坐标标定 + 白圆发送键图像识别 | `#人手模拟` `#参考图生视频` `#pyautogui` |
| **全流程 SOP** | `sop/` | 即梦生图 → 本地 ComfyUI MiniMax H3 出视频的**五步出片 SOP**（含审核 Agent、零 API 费用） | `#sop` `#comfyui` `#h3` |

## 三个技能怎么配合

```
即梦网页（出关键帧 / 参考图生视频）
   │  jimeng-web-automation（CDP，快、批量）
   │  jimeng-ref2video（人手模拟，无 API 权限时的唯一入口）
   ▼
Downloads/ 高清图
   │  qwen3-vl 验内容（别靠像素猜）
   ▼
本地 ComfyUI MiniMax H3（I2V 出动态镜头，RTX 本地跑，零费用）
   │  见 sop/全流程SOP-即梦生图到H3出片.md
   ▼
成片 mp4
```

- **有 CDP 条件**（能带调试参数启动浏览器）→ 用 `jimeng-web-automation`，批量效率高。
- **不能接管端口 / 标准会员无 CLI 权限** → 用 `jimeng-ref2video`，纯人手模拟，与 UI 实现解耦。
- 两者产出的图都走同一套「验内容 → 投 H3 → 审三帧」流程（`sop/`）。

## 安装

把对应目录复制到你的 Agent 技能目录（如 `~/.workbuddy/skills/` 或 `~/.claude/skills/`），
或直接把本仓库 clone 后软链：

```bash
git clone https://github.com/<owner>/jimeng-agent-skills.git
ln -s jimeng-agent-skills/jimeng-ref2video ~/.workbuddy/skills/
```

依赖（jimeng-ref2video）：

```bash
pip install pyautogui pyperclip pywinauto pillow opencv-python numpy
```

## 核心方法论（本仓库最有价值的部分）

1. **原生文件对话框接管**：网页上传弹的是 Windows `#32770` 对话框，不在 DOM 里。
   解法 = 等它出现 → 文件名框 `Ctrl+A` → 剪贴板粘贴完整路径 → 回车。中文路径无障碍。
2. **准星自检法标定 UI 坐标**：视觉模型直接标坐标误差 ±40px；
   裁剪放大 5–6 倍 + 画十字准星二次确认 → 精度 ±5px。工具：`jimeng-ref2video/scripts/calibrate.py`。
3. **白圆发送键图像识别**：即梦发送键 = 白圆（激活）/ 灰圆（禁用）。
   亮度阈值 + 连通域 + 圆形度定位，"找不到白圆 = 不该点" 是天然安全联锁。
4. **前台窗口校验**：人手模拟会抢鼠标。点击前必须 `GetForegroundWindow() == 目标hwnd`，
   并检测用户空闲（`GetLastInputInfo`），用户活跃就暂停。

## 安全约定

- ⛔ 绝不重启 / taskkill 用户的浏览器（登录态不复用，重启即丢）。
- 密钥一律走环境变量，不入库（`calibrate.py` 读 `VLM_API_KEY`）。
- 截图证据已脱敏：移除含会员积分、本机目录名、未发表作品角色图的截图。

## License

MIT
