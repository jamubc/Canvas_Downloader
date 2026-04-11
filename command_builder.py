import http.server
import socketserver
import webbrowser
import threading
import sys
import json
import subprocess
import os

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Canvas Downloader Command Builder</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background-color: #f7f9fc; color: #333; line-height: 1.6; margin: 0; padding: 2rem; display: flex; justify-content: center; }
        .container { background: white; padding: 2rem 3rem; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); max-width: 800px; width: 100%; }
        h1 { margin-top: 0; color: #1a202c; }
        .header-link { text-decoration: none; color: inherit; display: flex; align-items: center; gap: 0.75rem; border-bottom: 2px solid #edf2f7; padding-bottom: 1rem; margin-bottom: 1rem; }
        .header-link:hover h1 { color: #4299e1; }
        .form-group { margin-bottom: 1.5rem; }
        label { display: block; font-weight: bold; margin-bottom: 0.5rem; color: #4a5568; }
        input[type="text"], input[type="password"] { width: 100%; padding: 0.75rem; border: 1px solid #cbd5e0; border-radius: 4px; box-sizing: border-box; font-size: 1rem; }
        input[type="text"]:focus, input[type="password"]:focus { outline: none; border-color: #4299e1; box-shadow: 0 0 0 3px rgba(66, 153, 225, 0.2); }
        .checkbox-group { display: flex; align-items: center; margin-bottom: 0.5rem; }
        .checkbox-group input { margin-right: 0.75rem; width: 1.2rem; height: 1.2rem; }
        .help-text { font-size: 0.85rem; color: #718096; margin-top: 0.25rem; }
        .result-box { margin-top: 2rem; background: #2d3748; color: #fff; padding: 1.5rem; border-radius: 6px; position: relative; }
        code { font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; word-break: break-all; font-size: 0.95rem; }
        .copy-btn { position: absolute; top: 1rem; right: 1rem; background: #4299e1; color: white; border: none; padding: 0.5rem 1rem; border-radius: 4px; cursor: pointer; font-weight: bold; transition: background 0.2s; }
        .copy-btn:hover { background: #3182ce; }
        .copy-btn:active { background: #2b6cb0; }
        .header-msg { text-align: center; margin-bottom: 2rem; color: #4a5568; }
        .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }
        @media (max-width: 600px) { .grid { grid-template-columns: 1fr; } }
    </style>
</head>
<body>
    <div class="container">
        <a href="https://github.com/jamubc/Canvas_Downloader" target="_blank" class="header-link">
            <svg height="32" aria-hidden="true" viewBox="0 0 16 16" version="1.1" width="32" data-view-component="true" style="fill: #1a202c;">
                <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"></path>
            </svg>
            <h1 style="margin-bottom:0; padding-bottom:0; border:none;">Canvas_Downloader</h1>
        </a>
        <p class="header-msg">Fill in the fields below to generate your command. Fields marked with <strong>*</strong> are required.</p>
        
        <form id="builder-form">
            <div class="form-group">
                <label for="api-token">API Token *</label>
                <input type="password" id="api-token" placeholder="Canvas API token">
                <div class="help-text">Your Canvas API token with read‑only permissions.</div>
            </div>

            <div class="grid">
                <div class="form-group">
                    <label for="course-id">Course ID *</label>
                    <input type="text" id="course-id" placeholder="e.g. 12345">
                    <div class="help-text">Numeric ID of the Canvas course.</div>
                </div>

                <div class="form-group">
                    <label for="output-dir">Output Directory *</label>
                    <div style="display: flex; gap: 0.5rem;">
                        <input type="text" id="output-dir" placeholder="./downloads/course_name" style="flex: 1;">
                        <button type="button" onclick="browseDirectory()" style="padding: 0 1rem; border: 1px solid #cbd5e0; background: #edf2f7; border-radius: 4px; cursor: pointer; font-weight: 500; color: #4a5568; white-space: nowrap;">📁 Browse...</button>
                    </div>
                    <div class="help-text">Where the files will be saved.</div>
                </div>
            </div>

            <div class="form-group">
                <label for="canvas-url">Canvas Instance URL</label>
                <input type="text" id="canvas-url" value="https://canvas.instructure.com">
                <div class="help-text">Base URL of your Canvas instance (e.g. https://canvas.ubc.ca). Default: https://canvas.instructure.com</div>
            </div>

            <div class="form-group">
                <label for="ignore-pattern">Ignore Patterns</label>
                <input type="text" id="ignore-pattern" placeholder="e.g. *.md, *.txt">
                <div class="help-text">Comma-separated glob patterns to ignore.</div>
            </div>

            <h3>Options</h3>
            <div class="form-group" style="padding: 1rem; background: #fdfdfd; border: 1px solid #eaeaea; border-radius: 4px;">
                <div class="checkbox-group">
                    <input type="checkbox" id="no-structure">
                    <label for="no-structure">Flatten structure (--no-structure)</label>
                </div>
                <div class="help-text" style="margin-bottom: 1rem;">Flatten all module files into a single directory (default is organized by module name).</div>

                <div class="checkbox-group">
                    <input type="checkbox" id="no-optimize">
                    <label for="no-optimize">Disable optimization (--no-optimize)</label>
                </div>
                <div class="help-text" style="margin-bottom: 1rem;">Disable parallel downloads and rate-limit optimization.</div>

                <div class="checkbox-group">
                    <input type="checkbox" id="include-assignments">
                    <label for="include-assignments">Download Assignments (--include-assignments)</label>
                </div>
                <div class="help-text" style="margin-bottom: 1rem;">Download assignments and their descriptions/attachments.</div>

                <div class="checkbox-group">
                    <input type="checkbox" id="include-submissions">
                    <label for="include-submissions">Download Submissions (--include-submissions)</label>
                </div>
                <div class="help-text" style="margin-bottom: 1rem;">Download user's submissions (e.g. graded PDFs) for assignments.</div>

                <div class="checkbox-group">
                    <input type="checkbox" id="force">
                    <label for="force">Force redownload (--force)</label>
                </div>
                <div class="help-text">Force redownload of all files (ignore existing files).</div>
            </div>
        </form>

        <div class="result-box">
            <button class="copy-btn" id="copy-btn" onclick="copyCommand()">📋 Copy Command</button>
            <div style="margin-bottom: 0.5rem; font-size: 0.85rem; color: #a0aec0; text-transform: uppercase;">Generated Command:</div>
            <code id="command-output">canvas-downloader --api-token "YOUR_TOKEN" --course-id "COURSE_ID" --output-dir "OUTPUT_DIR"</code>
        </div>
    </div>

    <script>
        const inputs = document.querySelectorAll('input');
        const commandOutput = document.getElementById('command-output');
        const copyBtn = document.getElementById('copy-btn');

        async function browseDirectory() {
            try {
                const response = await fetch('/api/select-dir');
                if (response.ok) {
                    const data = await response.json();
                    if (data.error && data.error.length > 0) {
                        alert("Could not open file browser:\\n" + data.error);
                    } else if (data.path && data.path.length > 0) {
                        const dirInput = document.getElementById('output-dir');
                        dirInput.value = data.path;
                        updateCommand(); // trigger a re-render
                    }
                }
            } catch (err) {
                console.error('Failed to select directory:', err);
                alert('Could not connect to the local command builder server.');
            }
        }

        function updateCommand() {
            const apiToken = document.getElementById('api-token').value.trim() || 'YOUR_TOKEN';
            const courseId = document.getElementById('course-id').value.trim() || 'COURSE_ID';
            const outputDir = document.getElementById('output-dir').value.trim() || 'OUTPUT_DIR';
            const canvasUrl = document.getElementById('canvas-url').value.trim();
            const ignorePatternStr = document.getElementById('ignore-pattern').value.trim();
            
            const noStructure = document.getElementById('no-structure').checked;
            const noOptimize = document.getElementById('no-optimize').checked;
            const includeAssignments = document.getElementById('include-assignments').checked;
            const includeSubmissions = document.getElementById('include-submissions').checked;
            const force = document.getElementById('force').checked;

            let cmd = ['canvas-downloader'];
            
            // Required flags
            cmd.push(`--api-token "${apiToken}"`);
            cmd.push(`--course-id "${courseId}"`);
            cmd.push(`--output-dir "${outputDir}"`);
            
            // Optional URL
            if (canvasUrl && canvasUrl !== 'https://canvas.instructure.com') {
                cmd.push(`--canvas-url "${canvasUrl}"`);
            }
            
            // Ignore patterns
            if (ignorePatternStr) {
                const patterns = ignorePatternStr.split(',').map(p => p.trim()).filter(p => p.length > 0);
                patterns.forEach(p => {
                    cmd.push(`--ignore-pattern "${p}"`);
                });
            }

            // Boolean flags
            if (noStructure) cmd.push('--no-structure');
            if (noOptimize) cmd.push('--no-optimize');
            if (includeAssignments) cmd.push('--include-assignments');
            if (includeSubmissions) cmd.push('--include-submissions');
            if (force) cmd.push('--force');

            commandOutput.textContent = cmd.join(' ');
            
            // Reset button text if user changes something
            if (copyBtn.textContent !== '📋 Copy Command') {
                copyBtn.textContent = '📋 Copy Command';
                copyBtn.style.background = '#4299e1';
            }
        }

        function copyCommand() {
            const text = commandOutput.textContent;
            navigator.clipboard.writeText(text).then(() => {
                copyBtn.textContent = '✅ Copied!';
                copyBtn.style.background = '#48bb78';
                setTimeout(() => {
                    copyBtn.textContent = '📋 Copy Command';
                    copyBtn.style.background = '#4299e1';
                }, 2000);
            }).catch(err => {
                console.error('Failed to copy: ', err);
                alert('Failed to copy command to clipboard. Please copy it manually.');
            });
        }

        inputs.forEach(input => {
            input.addEventListener('input', updateCommand);
            input.addEventListener('change', updateCommand);
        });

        // Initialize display
        updateCommand();
    </script>
</body>
</html>
"""

class BuilderRequestHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(HTML_TEMPLATE.encode('utf-8'))
        elif self.path == '/api/select-dir':
            selected_dir = ""
            error_msg = ""
            try:
                if sys.platform == 'darwin':
                    # Use native macOS AppleScript prompt (guaranteed to work without Tkinter)
                    script = 'tell application "System Events" to activate\n' \
                             'tell application "System Events" to return POSIX path of (choose folder with prompt "Select Output Directory")'
                    result = subprocess.run(['osascript', '-e', script], capture_type=subprocess.PIPE, text=True)
                    if result.returncode == 0:
                        selected_dir = result.stdout.strip()
                elif sys.platform == 'win32':
                    # Windows native COM fallback could be used, but Tkinter is almost always included on Windows Python
                    import tkinter as tk
                    from tkinter import filedialog
                    root = tk.Tk()
                    root.withdraw()
                    root.attributes('-topmost', True)
                    selected_dir = filedialog.askdirectory(parent=root, title="Select Output Directory", mustexist=False)
                    root.destroy()
                else:
                    # Linux fallback
                    import tkinter as tk
                    from tkinter import filedialog
                    root = tk.Tk()
                    root.withdraw()
                    selected_dir = filedialog.askdirectory(parent=root, title="Select Output Directory", mustexist=False)
                    root.destroy()
            except ImportError:
                error_msg = "Python's 'tkinter' module is missing from your system, so the native file browser is unavailable."
                print(f"File dialog failed: {error_msg}")
            except Exception as e:
                error_msg = str(e)
                print(f"File dialog failed: {error_msg}")

            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"path": selected_dir, "error": error_msg}).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()
            
    # Silence terminal logging for cleaner output
    def log_message(self, format, *args):
        pass

def start_server():
    # Use port 0 to let the OS pick an available port
    with socketserver.TCPServer(("127.0.0.1", 0), BuilderRequestHandler) as httpd:
        port = httpd.server_address[1]
        url = f"http://127.0.0.1:{port}"
        print(f"\\n✅ Command Builder started!")
        print(f"👉 Opening {url} in your default browser...")
        print(f"Press Ctrl+C to stop the builder.\\n")
        
        # Open the browser automatically
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\\nStopping builder server.")

if __name__ == "__main__":
    start_server()
