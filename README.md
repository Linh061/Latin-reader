# Latin Reader

[English](#english) | [中文](#中文)

---

## English

A web-based Latin reading tool powered by [Whitaker's Words](https://github.com/mk270/whitakers-words). Read Project Gutenberg Latin texts or upload PDFs, click any word to see its grammatical analysis and dictionary definition.

### Features

- **Interactive Reader** — Project Gutenberg Latin books in a parchment-style interface. Click any word to analyze.
- **PDF Reader** — Upload PDFs of Latin texts; Kraken OCR with automatic word analysis. Page-by-page image + text view.
- **Grammatical Analysis** — Part-of-speech, lemma, morphology, and translation for every word form.
- **Dictionary Lookup** — Full Whitaker's Words dictionary entries for every lemma.
- **English→Latin Reverse Lookup** — Search English words to find corresponding Latin vocabulary.
- **Inflection Tables** — Complete declension / conjugation tables for any identified lemma.
- **Full-Text Search** — Search across all books; results with context snippets and highlighted matches.
- **Vocabulary Book** — Save words to a personal vocabulary list for review.
- **Bookmarks** — Bookmark pages for quick navigation.
- **Dark Academia UI** — Parchment-toned background, serif typography, ornamental details.

### Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3, Flask |
| Frontend | React, TypeScript, Vite |
| Latin Engine | [Whitaker's Words](https://github.com/mk270/whitakers-words) (Ada, compiled to SQLite) |
| OCR | Kraken (CLI) |
| Book Source | [Project Gutenberg](https://www.gutenberg.org/) |

### Quick Start

#### Prerequisites

- Python 3.8+
- Node.js 18+
- npm 9+
- [Kraken](https://github.com/mittagessen/kraken) CLI installed (`pip install kraken`)

#### 1. Set up the backend

```bash
cd backend
pip install -r requirements.txt
python3 app.py
```

The server starts at `http://127.0.0.1:5000`. It pre-loads the Latin lemmatizer and dictionary on startup.

#### 2. (Optional) Rebuild the frontend

```bash
cd frontend
npm install
npx vite build
```

Then restart the Flask server.

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check |
| `/api/books` | GET | List available books |
| `/api/books/<id>?page=&per_page=` | GET | Book content with optional pagination |
| `/api/analyze` | POST | Full analysis: parse + dictionary lookup |
| `/api/parse` | POST | Lemmatize a word form |
| `/api/dict` | POST | Look up a dictionary entry |
| `/api/reverse` | POST | English→Latin reverse lookup |
| `/api/fuzzy` | POST | Fuzzy Latin word search |
| `/api/inflect` | POST | Generate inflection table for a lemma |
| `/api/search?q=` | GET | Full-text search across books |
| `/api/ocr` | POST | Recognize Latin text from an uploaded image |
| `/api/ocr/analyze` | POST | Recognize + word-by-word analysis |
| `/api/pdf/upload` | POST | Upload a PDF for OCR reading |
| `/api/pdf/bookshelf` | GET | List uploaded PDFs with cover thumbnails |
| `/api/pdf/<id>/page/<n>` | GET | Get rendered page image + text |
| `/api/pdf/<id>/page/<n>/ocr` | GET | Poll OCR text for a page |
| `/api/pdf/<id>/page/<n>/text` | PUT | Save user-edited text |
| `/api/pdf/<id>/analyze/<n>` | POST | Analyze a word on a PDF page |
| `/api/pdf/<id>` | DELETE | Delete a PDF and its cache |
| `/api/vocab` | GET/POST | List / add vocabulary entries |
| `/api/vocab/<lemma>` | DELETE | Remove a vocabulary entry |

### Project Structure

```
Latin-reader/
├── backend/
│   ├── app.py                 # Flask application
│   ├── requirements.txt
│   ├── books/
│   │   ├── __init__.py        # PG HTML parser, book cache, search
│   │   └── data/              # PG HTML source files
│   ├── cache/                 # Cached book JSON + Whitaker's Words DB
│   ├── data/                  # Whitaker's Words dictionary data
│   ├── engine/
│   │   ├── lemmatizer.py      # Latin lemmatization
│   │   ├── dictionary.py      # Dictionary lookup + reverse lookup
│   │   ├── inflection.py      # Inflection table generation
│   │   ├── ocr.py             # Kraken OCR text recognition
│   │   └── pdf_ocr.py         # PDF upload, rendering, OCR pipeline
│   └── pdf_books/             # Uploaded PDFs + OCR cache (gitignored)
├── frontend/
│   ├── src/
│   │   ├── App.tsx            # Root component (route-based)
│   │   ├── main.tsx           # Entry point
│   │   ├── pages/             # Route pages (Home, Reader, OCR, PDFReader)
│   │   └── types/latin.ts     # TypeScript type definitions
│   └── dist/                  # Built static files (served by Flask)
└── .gitignore
```

### How It Works

1. **Book import:** `books/__init__.py` parses Project Gutenberg HTML files into chapters and paragraphs. Cached as JSON.
2. **Analysis:** Click a word → `/api/analyze` → lemmatize → dictionary lookup.
3. **Reverse Lookup:** Type an English word → `/api/reverse` → finds Latin words whose definitions contain the English term.
4. **Inflection:** Click "Declina …" → `/api/inflect` → full declension/conjugation table.
5. **PDF OCR:** Upload PDF → render page image → Kraken OCR in background → poll for text → click any word to analyze.
6. **Search:** `/api/search` does case-insensitive substring match across all cached book paragraphs.

### Adding Books

1. Download a Latin text from Project Gutenberg in "HTML" format.
2. Place the `.html` file in `backend/books/data/`.
3. Add a new entry to `BOOKS_CONFIG` in `backend/books/__init__.py`.
4. Restart the server.

### Credits

- [Whitaker's Words](https://github.com/mk270/whitakers-words) — the engine behind all Latin analysis, ported from the original Ada code by William Whitaker.
- [Project Gutenberg](https://www.gutenberg.org/) — source of the Latin texts.
- [Kraken](https://github.com/mittagessen/kraken) — OCR engine for Latin text recognition.

---

## 中文

一个基于 Web 的拉丁语阅读工具，由 [Whitaker's Words](https://github.com/mk270/whitakers-words) 驱动。支持阅读 Project Gutenberg 拉丁语文本或上传 PDF，点击任意单词即可查看其语法分析和词典释义。

### 功能特性

- **交互式阅读器** — 羊皮纸风格的 Project Gutenberg 拉丁语书籍界面。点击任意单词即可分析。
- **PDF 阅读器** — 上传拉丁语 PDF 文件；Kraken OCR 自动识别并支持逐词分析。页面图像 + 文本对照视图。
- **语法分析** — 每个单词形式的词性、词干、形态和翻译。
- **词典查询** — 每个词干的完整 Whitaker's Words 词典条目。
- **英拉反查** — 输入英文单词搜索对应的拉丁语词汇。
- **变位/变格表** — 任何已识别词干的完整变位/变格表。
- **全文搜索** — 跨所有书籍搜索；结果包含上下文片段和高亮匹配。
- **生词本** — 将单词保存到个人生词列表以便复习。
- **书签** — 为页面添加书签以便快速导航。
- **暗色学院风 UI** — 羊皮纸色调背景、衬线字体、装饰细节。

### 技术栈

| 层 | 技术 |
|-------|-----------|
| 后端 | Python 3, Flask |
| 前端 | React, TypeScript, Vite |
| 拉丁语引擎 | [Whitaker's Words](https://github.com/mk270/whitakers-words) (Ada, 编译为 SQLite) |
| OCR | Kraken (CLI) |
| 书籍来源 | [Project Gutenberg](https://www.gutenberg.org/) |

### 快速开始

#### 环境要求

- Python 3.8+
- Node.js 18+
- npm 9+
- [Kraken](https://github.com/mittagessen/kraken) CLI (`pip install kraken`)

#### 1. 启动后端

```bash
cd backend
pip install -r requirements.txt
python3 app.py
```

服务器启动在 `http://127.0.0.1:5000`。启动时会预加载拉丁语词形分析器和词典。

#### 2. （可选）重新构建前端

```bash
cd frontend
npm install
npx vite build
```

然后重启 Flask 服务器。

### API 接口

| 接口 | 方法 | 说明 |
|----------|--------|-------------|
| `/api/health` | GET | 健康检查 |
| `/api/books` | GET | 列出可用书籍 |
| `/api/books/<id>?page=&per_page=` | GET | 获取书籍内容（支持分页） |
| `/api/analyze` | POST | 完整分析：解析 + 词典查询 |
| `/api/parse` | POST | 词形还原 |
| `/api/dict` | POST | 查询词典条目 |
| `/api/reverse` | POST | 英拉反查 |
| `/api/fuzzy` | POST | 拉丁语模糊搜索 |
| `/api/inflect` | POST | 生成词干变位/变格表 |
| `/api/search?q=` | GET | 跨书籍全文搜索 |
| `/api/ocr` | POST | 识别上传图片中的拉丁语文本 |
| `/api/ocr/analyze` | POST | 识别 + 逐词分析 |
| `/api/pdf/upload` | POST | 上传 PDF 进行 OCR 阅读 |
| `/api/pdf/bookshelf` | GET | 列出已上传的 PDF 及封面缩略图 |
| `/api/pdf/<id>/page/<n>` | GET | 获取渲染的页面图像 + 文本 |
| `/api/pdf/<id>/page/<n>/ocr` | GET | 轮询获取页面的 OCR 文本 |
| `/api/pdf/<id>/page/<n>/text` | PUT | 保存用户编辑的文本 |
| `/api/pdf/<id>/analyze/<n>` | POST | 分析 PDF 页面上的单词 |
| `/api/pdf/<id>` | DELETE | 删除 PDF 及其缓存 |
| `/api/vocab` | GET/POST | 列出 / 添加生词 |
| `/api/vocab/<lemma>` | DELETE | 删除生词 |

### 项目结构

```
Latin-reader/
├── backend/
│   ├── app.py                 # Flask 应用
│   ├── requirements.txt
│   ├── books/
│   │   ├── __init__.py        # PG HTML 解析器、书籍缓存、搜索
│   │   └── data/              # PG HTML 源文件
│   ├── cache/                 # 缓存的书籍 JSON + Whitaker's Words 数据库
│   ├── data/                  # Whitaker's Words 词典数据
│   ├── engine/
│   │   ├── lemmatizer.py      # 拉丁语词形还原
│   │   ├── dictionary.py      # 词典查询 + 英拉反查
│   │   ├── inflection.py      # 变位/变格表生成
│   │   ├── ocr.py             # Kraken OCR 文本识别
│   │   └── pdf_ocr.py         # PDF 上传、渲染、OCR 流水线
│   └── pdf_books/             # 上传的 PDF + OCR 缓存（git 忽略）
├── frontend/
│   ├── src/
│   │   ├── App.tsx            # 根组件（基于路由）
│   │   ├── main.tsx           # 入口点
│   │   ├── pages/             # 路由页面（首页、阅读器、OCR、PDF阅读器）
│   │   └── types/latin.ts     # TypeScript 类型定义
│   └── dist/                  # 构建的静态文件（由 Flask 提供）
└── .gitignore
```

### 工作原理

1. **书籍导入：** `books/__init__.py` 将 Project Gutenberg HTML 文件解析为章节和段落。缓存为 JSON。
2. **分析：** 点击单词 → `/api/analyze` → 词形还原 → 词典查询。
3. **英拉反查：** 输入英文单词 → `/api/reverse` → 查找释义中包含该英文词的拉丁语词汇。
4. **变位/变格：** 点击"Declina …" → `/api/inflect` → 完整的变位/变格表。
5. **PDF OCR：** 上传 PDF → 渲染页面图像 → Kraken OCR 后台运行 → 轮询获取文本 → 点击任意单词分析。
6. **搜索：** `/api/search` 在所有缓存的书籍段落中进行不区分大小写的子串匹配。

### 添加书籍

1. 从 Project Gutenberg 下载拉丁语文本的 "HTML" 格式。
2. 将 `.html` 文件放入 `backend/books/data/`。
3. 在 `backend/books/__init__.py` 的 `BOOKS_CONFIG` 中添加新条目。
4. 重启服务器。

### 致谢

- [Whitaker's Words](https://github.com/mk270/whitakers-words) — 所有拉丁语分析背后的引擎，由 William Whitaker 的原始 Ada 代码移植而来。
- [Project Gutenberg](https://www.gutenberg.org/) — 拉丁语文本来源。
- [Kraken](https://github.com/mittagessen/kraken) — 拉丁语文本识别的 OCR 引擎。
