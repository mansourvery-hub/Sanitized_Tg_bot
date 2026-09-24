# SheerID 自動認證 Telegram 機器人

![Stars](https://img.shields.io/github/stars/PastKing/tgbot-verify?style=social)
![Forks](https://img.shields.io/github/forks/PastKing/tgbot-verify?style=social)
![Issues](https://img.shields.io/github/issues/PastKing/tgbot-verify)
![License](https://img.shields.io/github/license/PastKing/tgbot-verify)

> 🤖 自動完成 SheerID 學生/教師認證的 Telegram 機器人
>
> 基於 [@auto_sheerid_bot](https://t.me/auto_sheerid_bot) GGBond 的舊版程式碼改進

[English](README_EN.md) | [简体中文](README.md) | 繁體中文

---

## 📋 專案簡介

基於 Python 的 Telegram 機器人，自動完成多個平台的 SheerID 學生/教師身分認證。機器人自動產生身分資訊、建立認證文件並提交到 SheerID 平台，大幅簡化認證流程。

### 🎯 支援的認證服務

| 指令 | 服務 | 類型 | 狀態 |
|------|------|------|------|
| `/verify` | Gemini One Pro | 教師認證 | ✅ 完整 |
| `/verify2` | ChatGPT Teacher K12 | 教師認證 | ✅ 完整 |
| `/verify3` | Spotify Student | 學生認證 | ✅ 完整 |
| `/verify4` | Bolt.new Teacher | 教師認證 | ✅ 完整 |
| `/verify5` | YouTube Premium Student | 學生認證 | ⚠️ 開發中 |

> **⚠️ 使用前必讀**：各模組的 `programId` 可能定期更新，使用前請檢查並更新對應模組的 `config.py` 設定，詳見下方「設定說明」章節。

### ✨ 核心功能

- 🚀 **自動化流程**：一鍵完成資訊產生、文件建立、認證提交
- 🎨 **智慧產生**：自動產生學生證/教師證 PNG 圖片
- 💰 **積分系統**：簽到、邀請、卡密兌換等多種獲取方式
- 🔐 **安全可靠**：MySQL 資料庫，支援環境變數設定
- ⚡ **並行控制**：智慧管理並行請求，確保穩定性
- 👥 **管理功能**：完善的使用者管理和積分管理系統

---

## 🛠️ 技術堆疊

- **語言**：Python 3.14+
- **Bot 框架**：python-telegram-bot 20.0+
- **資料庫**：MySQL 5.7+
- **瀏覽器自動化**：Playwright
- **HTTP 客戶端**：httpx
- **圖像處理**：Pillow, reportlab, xhtml2pdf
- **環境管理**：python-dotenv

---

## 🚀 快速開始

### 1. 複製專案

```bash
git clone https://github.com/mansourvery-hub/Sanitized_Tg_bot.git
cd Sanitized_Tg_bot
```

### 2. 安裝依賴

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.lock.txt
playwright install chromium
```

### 3. 設定環境變數

複製 `env.example` 為 `.env` 並填寫設定：

```env
BOT_TOKEN=your_bot_token_here
CHANNEL_USERNAME=your_channel
CHANNEL_URL=https://t.me/your_channel
ADMIN_USER_ID=your_admin_id

MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=tgbot_verify
```

### 4. 啟動機器人

```bash
python bot.py
```

---

## 🐳 Docker 部署

```bash
cp env.example .env
nano .env
docker-compose up -d
docker-compose logs -f
```

手動建置：

```bash
docker build -t tgbot-verify .
docker run -d --name tgbot-verify --env-file .env -v $(pwd)/logs:/app/logs tgbot-verify
```

---

## 🏫 支援的院校 & SheerID 組織

本倉庫透過 `sheerid_schools.py` 維護權威院校目錄（SheerID 生產組織 ID），並透過 `generation.py` / `render_service.py` 提供確定性檔案與文件產生。

| 院校 ID | 院校名稱 | 國家/地區 | 網域 | SheerID ID | 別名範例 |
|---------|----------|-----------|------|------------|----------|
| `psu` | Penn State University | US | `psu.edu` | `2565` | `psu`, `penn_state` |
| `ucla` | Univ. of California, Los Angeles | US | `ucla.edu` | `285` | `ucla`, `285` |
| `nyu` | New York University | US | `nyu.edu` | `2678` | `nyu`, `2678` |
| `umich` | University of Michigan | US | `umich.edu` | `2027` | `umich`, `michigan` |
| `ut_austin` | Univ. of Texas at Austin | US | `utexas.edu` | `3895` | `ut_austin`, `ut`, `3895` |
| `up_diliman` | University of the Philippines Diliman | PH | `up.edu.ph` | `355870` | `up_diliman`, `upd`, `355870` |
| `usp` | Universidade de São Paulo | BR | `usp.br` | `10042652` | `usp`, `sao_paulo` |
| `universiti_malaya` | Universiti Malaya | MY | `um.edu.my` | `355254` | `universiti_malaya`, `um`, `malaya` |
| `makerere` | Makerere University | UG | `mak.ac.ug` | `662864` | `makerere`, `mak`, `662864` |
| `unilag` | University of Lagos | NG | `unilag.edu.ng` | `660895` | `unilag`, `lagos`, `660895` |
| `springfield_k12` | Springfield School District (K-12) | US | `springfieldsd.org` | — | `k12`, `springfield` |
| `nittany_tech` | Nittany Technical College | US | `nittanytech.edu` | — | `nittany_tech` |

> 國際院校均採用 SheerID 生產環境真實組織 ID（經 `orgsearch.sheerid.net` 校驗），並配備本地化姓名池、學號格式、學期日曆與文件模板。

國際文件模板（`generation.py` → `DocumentKind.SCHEDULE` / `REGISTRAR_LETTER`）：
- **UP Diliman** — Form 5 / CRS 註冊表（Class Code、Units、OUR 抬頭）
- **USP** — Atestado de Matrícula / Sistema Janus（Número USP、Disciplinas Matriculadas、數位認證）
- **Universiti Malaya** — Surat Pengesahan Pelajar / MAYA Portal（雙語抬頭、Matric No.）
- **Makerere** — Letter of Enrollment / ACMIS（Academic Registrar 簽章）
- **UNILAG** — Letter of Student Enrollment（Matriculation Number、Faculty/Level 資訊）

---

## 🛠️ 統一本地身分與文件產生工具 CLI (`app.py` / `generation.py`)

零網路依賴的本地確定性產生引擎，聚合 `one/` `k12/` `spotify/` `youtube/` `Boltnew/` 邏輯於單一入口。

### 互動式精靈

```bash
./venv/bin/python app.py
./venv/bin/python app.py --target 1 --seed 42
```

### 常用子指令

```bash
./venv/bin/python app.py list
./venv/bin/python app.py identity --institution up_diliman --seed 42 --json
./venv/bin/python app.py document --institution usp --seed 42 --kind schedule --json
./venv/bin/python app.py render --institution makerere --seed 42 --format pdf --output output/
./venv/bin/python app.py fixture --institution unilag --seed 12345
./venv/bin/python app.py batch --count 10 --institution universiti_malaya
./venv/bin/python app.py validate output/
./venv/bin/python app.py visual-regression
./venv/bin/python app.py visual-regression --update-baselines
```

- `--institution` 支援院校 ID、數字 SheerID ID 與別名（見上表），由 `render_service.PayloadTransformer` 統一歸一。
- `--seed` 保證跨運行確定性。
- SheerID 信箱透過 `sheerid_schools.generate_institutional_student_email()` 按院校網域產生。
- 視覺回歸基線位於 `tests/visual_baselines/`（含 `up_diliman_form5.png` 等 12 份金標），清單見 `manifest.json`。

---

## 📖 使用說明

### 使用者指令

```
/start              # 開始使用（註冊）
/about              # 瞭解機器人功能
/balance            # 查看積分餘額
/qd                 # 每日簽到（+1 積分）
/invite             # 產生邀請連結（+2 積分/人）
/use <卡密>         # 使用卡密兌換積分
/verify <連結>      # Gemini One Pro 認證
/verify2 <連結>     # ChatGPT Teacher K12 認證
/verify3 <連結>     # Spotify Student 認證
/verify4 <連結>     # Bolt.new Teacher 認證
/verify5 <連結>     # YouTube Premium Student 認證
/help               # 查看幫助資訊
```

### 管理員指令

```
/addbalance <使用者ID> <積分>               # 增加使用者積分
/block <使用者ID>                           # 封鎖使用者
/white <使用者ID>                           # 取消封鎖
/blacklist                                  # 查看黑名單
/genkey <卡密> <積分> [次數] [天數]         # 產生卡密
/listkeys                                   # 查看卡密列表
/broadcast <文字>                           # 群發通知
```

### 使用流程

1. 造訪對應服務的認證頁面，開始認證流程
2. 複製瀏覽器網址列中包含 `verificationId` 的完整 URL
3. 傳送給機器人：`/verify3 https://services.sheerid.com/verify/xxx/?verificationId=yyy`
4. 等待機器人自動處理，審核通常在幾分鐘內完成

---

## 📁 專案結構

```
tgbot-verify/
├── app.py                  # 統一 CLI 入口與互動精靈
├── generation.py           # 確定性身分/文件/渲染引擎（12 院校 × 5 文件類型）
├── render_service.py       # JSON 驅動的機構化渲染服務與別名解析
├── sheerid_schools.py      # SheerID 權威院校目錄與信箱解析
├── visual_regression.py    # 視覺回歸引擎與基線管理
├── bot.py                  # 機器人主程式
├── config.py               # 全域設定
├── database_mysql.py       # MySQL 資料庫管理
├── env.example             # 環境變數範本
├── requirements.txt        # Python 依賴
├── Dockerfile              # Docker 設定
├── docker-compose.yml      # Docker Compose 設定
├── handlers/               # 指令處理器
│   ├── user_commands.py
│   ├── admin_commands.py
│   └── verify_commands.py
├── one/                    # Gemini One Pro 模組
├── k12/                    # ChatGPT K12 模組
├── spotify/                # Spotify Student 模組
├── youtube/                # YouTube Premium 模組
├── Boltnew/                # Bolt.new 模組
├── tests/
│   ├── test_generation.py
│   ├── test_sheerid_schools.py
│   ├── test_render_service.py
│   ├── test_visual_regression.py
│   └── visual_baselines/   # 12 份金標 PNG + manifest.json
└── utils/                  # 工具函式
    ├── messages.py
    ├── concurrency.py
    └── checks.py
```

---

## ⚙️ 設定說明

### 環境變數

| 變數名稱 | 必填 | 說明 |
|----------|------|------|
| `BOT_TOKEN` | ✅ | Telegram Bot Token |
| `ADMIN_USER_ID` | ✅ | 管理員 Telegram ID |
| `MYSQL_HOST` | ✅ | MySQL 主機位址 |
| `MYSQL_USER` | ✅ | MySQL 使用者名稱 |
| `MYSQL_PASSWORD` | ✅ | MySQL 密碼 |
| `MYSQL_DATABASE` | ✅ | 資料庫名稱 |
| `CHANNEL_USERNAME` | ❌ | 頻道使用者名稱（預設 pk_oa）|
| `CHANNEL_URL` | ❌ | 頻道連結 |
| `MYSQL_PORT` | ❌ | MySQL 連接埠（預設 3306）|

### 更新 programId

如果認證持續失敗，通常是 `programId` 已過期。更新步驟：

1. 造訪對應服務認證頁面，開啟瀏覽器開發者工具（F12）→ 網路標籤
2. 開始認證流程，尋找 `https://services.sheerid.com/rest/v2/verification/` 請求
3. 從請求中擷取 `programId`，更新對應模組的 `config.py` 檔案

需要更新的檔案：`one/config.py` | `k12/config.py` | `spotify/config.py` | `youtube/config.py` | `Boltnew/config.py`

### 積分設定（config.py）

```python
VERIFY_COST = 1        # 驗證消耗積分
CHECKIN_REWARD = 1     # 簽到獎勵
INVITE_REWARD = 2      # 邀請獎勵
REGISTER_REWARD = 1    # 註冊獎勵
```

---

## 🤝 聯繫與合作

- 📢 **Telegram 頻道**：[@pk_oa](https://t.me/pk_oa)
- 📧 **電子郵件**：pastking69@gmail.com
- 🐛 **問題回饋**：[GitHub Issues](https://github.com/PastKing/tgbot-verify/issues)

歡迎合作與交流，有意向請透過以上方式聯繫。

---

## 🛠️ 二次開發

歡迎基於本專案進行二次開發，請遵守以下規則：

- 保留原儲存庫位址及作者資訊
- 遵循 MIT 開源協議，二次開發專案須同樣開源
- 個人使用免費；商業使用請自行最佳化並承擔相應責任

---

## 📜 開源協議

本專案採用 [MIT License](LICENSE) 開源協議。

---

## 🙏 致謝

- 感謝 [@auto_sheerid_bot](https://t.me/auto_sheerid_bot) GGBond 提供的舊版程式碼基礎
- 感謝所有為本專案做出貢獻的開發者

---

## 📊 專案統計

[![Star History Chart](https://api.star-history.com/svg?repos=PastKing/tgbot-verify&type=Date)](https://star-history.com/#PastKing/tgbot-verify&Date)

---

<p align="center">
  <strong>⭐ 如果這個專案對你有幫助，請給個 Star 支持一下！</strong>
</p>

<p align="center">
  Made with ❤️ by <a href="https://github.com/PastKing">PastKing</a>
</p>
