# Canvas_Downloader
![Open Source](https://img.shields.io/badge/Open_Source-brightgreen?style=flat-square)
![Educational](https://img.shields.io/badge/Educational-blue?style=flat-square)
![Canvas LMS](https://img.shields.io/badge/Canvas_LMS-red?style=flat-square&logo=canvas)
![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue?style=flat-square&logo=python&logoColor=white)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square)
![CLI Tool](https://img.shields.io/badge/CLI-Tool-green?style=flat-square&logo=windowsterminal)

A fast, safe, and customizable tool to download course content from Canvas (Instructure).

**Features:**
- **Safe:** Strictly read-only. Never modifies, deletes, or uploads any data.
- **Cross-Platform:** Works on macOS, Windows, and Linux.
- **Optimized:** Uses parallel downloading and smart rate-limiting to be fast without getting blocked.
- **Complete:** Can download Files, Modules, Pages, and Assignments (including attached solutions/descriptions).
- **Flexible:** download everything in structured folders, or flatten it; ignore specific files; pick specific courses.

**Why?**
- I was tired of downloading course content manually
- I wanted to have a backup of my courses
- I wanted to be able to access my courses offline
- I want to feed the downloaded content into a LLM
- I want to turn my courses into a searchable database
- I want to turn my courses into a quiz or practice test
---

## ⚡ Quick Start

### Option 1: Install via Pip (Recommended)
This is the easiest way to use the tool.
```bash
pip install canvas_downloader
```
Then run it anywhere:
```bash
canvas-downloader --help
```

### Option 2: Run from Source
1. **Clone the repo:**
   ```bash
   git clone https://github.com/jamubc/Canvas_Downloader.git
   cd Canvas_Downloader
   ```
2. **Install dependencies:**
   ```bash
   uv pip install -r requirements.txt
   # OR
   pip install -r requirements.txt
   ```
3. **Run:**
   ```bash
   python downloader.py --help
   ```

### Basic Usage
```bash
canvas-downloader \
    --api-token YOUR_API_TOKEN \
    --course-id YOUR_COURSE_ID \
    --output-dir ./my_course_download \
    --canvas-url https://canvas.instructure.com
```
*(Replace `YOUR_API_TOKEN`, `YOUR_COURSE_ID` with real values. Use your school's URL for `--canvas-url`)*

*For more information see [Canvas API Documentation](https://canvas.instructure.com/doc/api/courses.html)*

---

## 🛠 Flags

You can customize the download by adding these flags to the command above:

| Flag | Description |
| :--- | :--- |
| `--include-assignments` | **Recommended.** Downloads assignment instructions and attached files (solutions, starter code, etc.) into an `Assignments/` folder. |
| `--include-submissions` | Download your own submissions (e.g. uploaded files, graded PDFs) into `Assignments/{Name}/Submissions/`. |
| `--no-structure` | Flattens all files into a single directory instead of organizing them by Module/Week. |
| `--ignore-pattern "*.ext"` | Skips files matching the pattern. Can be used multiple times. <br> *Example:* `--ignore-pattern "*.zip" --ignore-pattern "*.m"` |
| `--no-optimize` | Disables parallel downloading and smart rate-limiting. Use this if you encounter errors or want a strictly sequential, slower download. |
| `--force` | Force redownload of all files, ignoring any existing files (bypassing sync logic). |
| `--canvas-url URL` | Base URL of your Canvas instance. Defaults to `https://canvas.instructure.com`. <br> *Example:* `https://canvas.ubc.ca` |

### Example Usage:
```bash
uv run python downloader.py \
    --api-token <TOKEN> \
    --course-id 123456 \
    --output-dir ./Fall2024_Backup \
    --canvas-url https://canvas.ubc.ca \
    --include-assignments \
    --ignore-pattern "*.mp4" 
```

---

## 🔄 Re-running
To download new content later, just run the same command again. The script is safe to run multiple times; it will overwrite existing files with the latest versions from Canvas.

## 🙋 Common Questions (FAQ)

**Q: How do I download all my Canvas course contents at once?**
A: This tool is built exactly for that. It iterates through your entire course (Modules, Files, Assignments, Pages) and saves everything to your local computer in one go.

**Q: Can I backup my Canvas courses before I lose access?**
A: Yes! Use this tool at the end of the semester to create a permanent, offline archive of your materials (PDFs, PPTXs, Videos, etc).

**Q: Does this download videos and quiz content?**
A: It downloads files and assignment descriptions. Video support and specific quiz capture are currently being worked on (see Upcoming Features).

## Issues with usage?
*Im happy to help, please open an issue on GitHub.*

## Upcoming Features
-  Downloading Video files (currently unhandled)
- AI [Embedding](https://www.ibm.com/think/topics/embedding)
- Plug in usage for '[canvas-mcp-tool](https://github.com/jamubc/canvas-mcp-tool)' (please reach out if you are interested in testing it!)
- [Repomix](https://github.com/yamadashy/repomix) integration

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
