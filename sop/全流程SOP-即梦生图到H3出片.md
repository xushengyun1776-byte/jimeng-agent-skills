# 全流程 SOP：即梦生图 → 本地 MiniMax H3 出视频

> ## ⛔ 铁律（2026-10-03 用户明令，最高优先级）
> **绝不允许由 Agent 重启 / taskkill / 重新拉起 Edge 来"恢复"即梦网页。**
> 重启后拿到的是**没有登录态**的浏览器实例（登录态并不随 `--user-data-dir` 复用成功），
> 一切接管操作必须基于**用户自己手动打开并已登录**的那个浏览器。
> - 9222 连不上 ≠ 可以重启浏览器。正确动作：**停下来，请用户自己打开并确认已登录**，
>   或请用户按下方命令自行启动；Agent 只能等，不能代劳杀进程。
> - 下文第 0 步的启动命令只是给用户的参考，不是 Agent 的执行授权。

> 状态：**已跑通并验证**（2026-09-30 02:11）
> 实测成片：`ai_comic_pipeline/output/beach_girl_dog.mp4`
> h264 / 576×1024 / 124帧 / 25fps / 4.96秒 / 1.44MB，**提交到出片 76 秒，零 API 费用**

---

## 零、一句话原理

**即梦负责"长什么样"，本地 H3 负责"怎么动"。**

- 即梦网页端（Seedream 5.0 Pro）出**关键帧**——审美和构图的活儿。
- 把关键帧当**首帧**喂给本机 ComfyUI 的 MiniMax H3，出**5 秒动态镜头**——RTX 5090 本地跑，不烧积分。

H3 是图生视频（I2V）模型，**人物身份、服装、场景全部只从首帧继承**。
所以首帧选对，这一段就成了一半。

---

## 一、分工（这样最快）

| 谁 | 干什么 | 为什么 |
|---|---|---|
| **你（人类）** | 即梦网页端写提示词、出图、挑图、**点下载** | 审美判断是你的强项；网页点下载是唯一稳的落盘方式 |
| **我（Agent）** | 取图 → 验内容 → 投 H3 → 审三帧 → 交付 | 批量、参数、踩坑这些重复劳动我扛 |

关键：**你不需要把图拖给谁，也不用告诉我路径**——点完下载，图自动落在
`<下载目录>/`，我自己去取。

---

## 二、第 0 步：把环境拉起来

每次开工前先确认三件事都活着：

```bash
curl -s --noproxy '*' http://127.0.0.1:8188/system_stats   # ComfyUI（H3 生视频）
curl -s --noproxy '*' http://127.0.0.1:11434/api/tags      # Ollama（VL 审核）
curl -s --noproxy '*' http://127.0.0.1:9222/json/list      # Edge CDP（即梦接管）
```

### ComfyUI 没起来（开机后默认关的）

```bash
cd F:/ComfyUI-2025.9 && F:/ComfyUI-2025.9/python/python.exe -s \
  F:/ComfyUI-2025.9/ComfyUI/main.py --listen 127.0.0.1 --port 8188
```

启动时先抓 188 条 ComfyRegistry 数据，**约 5–8 分钟才监听端口**，后台跑别干等。

### Edge 没开调试端口（9222 连不上）

**⛔ 先看顶部铁律：Agent 不得自行重启浏览器（重启=无登录态）。以下步骤仅供用户手动执行，或由用户明确说"你来启动"时才可由 Agent 执行。**

必须先删单例锁，否则会静默失败（直接挂到已有 Edge 进程上，没有调试端口）：

```bash
export MSYS_NO_PATHCONV=1
rm -f "<用户目录>/AppData/Local/Microsoft/Edge/User Data/SingletonLock" \
      "<用户目录>/AppData/Local/Microsoft/Edge/User Data/SingletonCookie" \
      "<用户目录>/AppData/Local/Microsoft/Edge/User Data/SingletonSocket"
"/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe" \
  --remote-debugging-port=9222 --remote-allow-origins=* \
  --user-data-dir="<用户目录>/AppData/Local/Microsoft/Edge/User Data" \
  "https://jimeng.jianying.com/ai-tool/home/"
```

> 用 `--user-data-dir` 指向**默认配置目录**，登录态和 Cookie 都在，
> 打开即梦直接是已登录状态（右上角能看到积分余额）。

验证成功：页面列表里出现 `即梦AI - 一站式AI创作平台`，body 里能读到「积分」「你好，今天想要创作什么?」。

---

## 三、五步 SOP（照着做就行）

### 第 1 步：即梦出图 + 点下载 ★关键

1. 打开即梦网页 → 创作页（`ai-tool/generate?type=image`）
2. 底部面板切成**「图片生成」**（默认是 Agent 模式，要点下拉切）
3. 参数条确认：`Seedream 5.0 Pro | 9:16 | 2K | 4张`
4. 输入框写提示词 → 点圆形 ↑ 发送钮
5. 等生成完（4 张一组出现在结果网格）

6. **★ 点小图上的「向下箭头」图标 = 下载键**
   （就在每张结果小图的角上，鼠标移上去会显示"下载"）
7. 图直接进 **`<下载目录>/`**，命名格式：
   ```
   jimeng-2026-09-30-2685-电影感写实摄影。一位二十多岁的美丽东方女性，长发被海风吹起，....png
   ```
   即 `jimeng-<日期>-<4位随机>-<提示词前若干字>.png`

> **★ 血泪教训：这一步不要让我用 CDP 去抓。**
> 之前我花了很多轮在"用 CDP 打开查看器 → fetch 高清图 → 翻页"这条路上，
> 失败了不止一次（抓到的是 UI 缩略图 / 查看器定位失败）。
> **手点下载键是最稳、最快的方式**，抓图那一整环可以彻底删掉。

### 第 2 步：我取图 + 验内容

```bash
# 取今天最新下载的即梦图
python - <<'EOF'
import glob, os, shutil
srcs = glob.glob("<下载目录>/jimeng-<今天日期>-*.png")
srcs.sort(key=os.path.getmtime)
shutil.copy(srcs[-1], "output/首帧.png")
EOF
```

**★ 必须用 qwen3-vl 描述一遍内容，不许靠猜。**

> 反面教材：我曾用「平均色调偏暖 = 夕阳海滩」来判断，
> 结果那张图其实是**咖啡馆门口一个背绿包的男青年**（暖光一样是暖色）。
> 视频都生成完了才发现首帧是错的，白跑一轮。

```python
# 让 qwen3-vl:30b 描述，确认场景/人物/物件/画幅
prompt = "详细描述这张图：场景在哪、人物（性别年龄衣着）、有没有动物、光线、竖版还是横版"
```

### 第 3 步：检查比例（不做会全片变形）

```python
im.size  # 必须 宽/高 == 目标画布比例
```

- 目标 9:16 竖版 → 比例必须 = **0.5625**
- 合法档位：**576×1024 / 864×1536 / 1152×2048**（都要是 32 的倍数）
- 本次 `beach_hd.png` 是 1440×2560，正好 0.5625 → **cover-crop 无损**
- 比例不符的图必须先裁，否则 H3 会**纯拉伸**首帧（源码 `crop="disabled"`），
  整段人物被压扁，且是每个采样步都在放大这个形变

> `videogen.py` 内置 `_cover_crop()` 会自动裁，但裁之前先确认比例能省很多事。

### 第 4 步：投 H3 出视频

```bash
export PATH="<工作区>/.workbuddy/binaries/PortableGit/versions/1.2.0/usr/bin:/c/Windows/System32:/c/Windows:$PATH"
cd ai_comic_pipeline
unset HTTP_PROXY HTTPS_PROXY http_proxy https_proxy ALL_PROXY all_proxy
export no_proxy="*"

python agents/videogen.py \
  --image output/首帧.png \
  --prompt "电影感写实摄影。<主体+动作>。镜头缓慢向右平移并轻微推进，<光线风格>。" \
  --workflow workflows/h3_i2v.json \
  --out output/成片.mp4
```

默认参数（已验证）：576×1024 / 124帧 / 4步 / cfg 1.0 / uni_pc / simple。
出片落在 `F:/ComfyUI-2025.9/ComfyUI/output/H3_test/`，脚本会打印文件名。

**提示词写法**：主体与场景 → 动作顺序 → 相机运动 → 光线风格。
主体动作和镜头动作要分开写，别互相矛盾。

### 第 5 步：审三帧，可用才交付

```bash
ffmpeg -i 成片.mp4 -frames:v 1 -y f1.png              # 首帧
ffmpeg -i 成片.mp4 -vf "select=eq(n\,60)" -frames:v 1 -y mid.png   # 中间帧
ffmpeg -sseof -0.1 -i 成片.mp4 -frames:v 1 -y last.png             # 末帧
```

三张一起喂 qwen3-vl，问：主体是否一致 / 有无崩坏变形 / 动作是否自然。

本次审核结果：**主体一致、无崩坏、动作自然 → 可用**。

---

## 四、H3 铁律（ComfyUI 0.37，全是我撞出来的）

完整版见 `skills/minimax-h3-local-pipeline/SKILL.md` 第九节，这里列最要命的：

| # | 铁律 | 违反后果 |
|---|---|---|
| 1 | `/prompt` 只收**图格式** `{"class_type","inputs"}` | 旧列表格式**一律 500**，且错误体只有一句话，无 traceback |
| 2 | 连线第二项是**整数槽位** `["9",0]` | 写 `["9","IMAGE"]` 报 `tuple indices must be integers` |
| 3 | `VAEDecode`(IMAGE) 和 `SaveVideo`(VIDEO) 之间**必须插 `CreateVideo`** | `SaveVideo required VIDEO, got IMAGE` |
| 4 | 文本编码器必须是 **`qwen3vl_32b_minimax_h3_nvfp4_awq`** | 用 Qwen-Image 的 8B 报 `697x4096 and 5120x5376` |
| 5 | 首帧**直接 copy 进 `ComfyUI/input/`**，别走 `/upload/image` | 该接口本机返 400 |

另外：
- **帧数必须落在 17k+5 网格**：124 / 141 / 158 / 175 / 192 / 209；**单段 ≤ 209 帧**
- 超过 8 秒的镜头 → 拆子段，用**首尾帧双锁**（`MiniMaxH3ImageToVideo` 同时有
  `first_frame` 和 `last_frame`）串起来
- 首帧里**没有脸，摇上去的脸就是随机的**
- 切模型族前必须 `/free`，否则必卡死

---

## 五、出问题怎么查

| 现象 | 查什么 |
|---|---|
| `/prompt` 返回 500 | 99% 是图格式写错（第 1 条）。**别用空图验证接口**——空图反而正常返 400 |
| 返回 400 带 `node_errors` | 读 `node_errors`，它会明确告诉你哪个节点要什么类型 |
| 报 `mat1 and mat2 shapes` | 文本编码器选错了（第 4 条） |
| 卡住不动 | 看功耗：GPU 100% + **功耗 <200W** = 已死，只能重启；>500W 是在算，等着 |
| `HostBuffer.read_file_slice failed` | 上一个任务崩了留下毒，`POST /free {"unload_models":true}` 解毒 |

拿完整错误信息（urllib 会吞掉错误体）：

```python
except urllib.error.HTTPError as e:
    print(e.code, e.read().decode())   # ← 一定要读 body
```

---

## 六、实测数据（本机 RTX 5090 32GB）

| 项目 | 数值 |
|---|---|
| 576×1024 / 124帧 / 4步 | **73~76 秒/镜** |
| 成片规格 | h264, 576×1024, 124帧, 25fps, 4.96秒, ~1.5MB |
| 显存占用 | 采样期接近贴顶（31.8/32.6 GB），正常 |

**下一步想提画质**：用 Z-Image Base（50步/CFG3.5）出首帧，比 Turbo 档细节多一倍
（详见 H3 技能第八节）。首帧质量直接决定成片上限。

---

## 七、备份目录最新内容

```
agent操作备份/
├── README.md                          # 方法总览
├── 全流程SOP-即梦生图到H3出片.md       # ← 本文件
├── jimeng-web-automation/SKILL.md     # 即梦网页接管（含下载键说明）
├── skills/minimax-h3-local-pipeline/  # H3 本地出片（含 0.37 协议第九节）
└── ai_comic_pipeline/
    ├── workflows/h3_i2v.json          # ★ 已验证可跑的 H3 I2V 工作流
    ├── agents/videogen.py             # ★ 提交脚本
    ├── output/beach_girl_dog.mp4      # 成片样例
    └── output/beach_hd.png            # 首帧样例（1440×2560）
```
