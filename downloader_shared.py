import os
import requests
from urllib.parse import urljoin

import pdfkit
import html2text
from bs4 import BeautifulSoup
from tqdm import tqdm
from pathlib import Path
import fnmatch
import time
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor
from collections import defaultdict

class DownloadStats:
    def __init__(self):
        self.total_files = 0
        self.total_size = 0
        self.file_types = defaultdict(int)
        self.start_time = time.time()

    def add_download(self, filename, size):
        self.total_files += 1
        self.total_size += size
        ext = Path(filename).suffix.lower() or "no_extension"
        self.file_types[ext] += 1

    def print_summary(self):
        elapsed = time.time() - self.start_time
        print("\n\n" + "="*40)
        print("          DOWNLOAD FINISHED!          ")
        print("="*40)
        print(f"Total Time:     {elapsed:.2f} seconds")
        print(f"Total Files:    {self.total_files}")
        
        # Format size readable
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if self.total_size < 1024.0:
                print(f"Total Size:     {self.total_size:.2f} {unit}")
                break
            self.total_size /= 1024.0
            
        print("-" * 40)
        print("File Types:")
        for ext, count in sorted(self.file_types.items(), key=lambda x: -x[1]):
            print(f"  {ext:<10}: {count}")
        print("="*40 + "\n")


class CanvasSession:
    def __init__(self, token, optimize=True):
        self.optimize = optimize
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        # Connection pooling
        adapter = requests.adapters.HTTPAdapter(pool_connections=10, pool_maxsize=10)
        self.session.mount('https://', adapter)
        self.session.mount('http://', adapter)

    def get(self, url, **kwargs):
        # Always use the internal session; implement custom rate limiting if optimize=True
        # Note: requests.Session automatically handles keep-alive
        if not self.optimize:
            resp = self.session.get(url, **kwargs)
            return resp

        # Optimization / Rate Limiting logic
        while True:
            try:
                resp = self.session.get(url, **kwargs)
                
                # Handle 429 Too Many Requests explicitly
                if resp.status_code == 429:
                    retry_after = 5 # default
                    if 'Retry-After' in resp.headers:
                        try:
                            retry_after = int(resp.headers['Retry-After'])
                        except ValueError:
                            pass
                    
                    print(f"\nRate limit reached (429). Sleeping for {retry_after} seconds...")
                    time.sleep(retry_after)
                    continue # Retry request
                
                # Check Leaky Bucket Headers
                try:
                    remaining = resp.headers.get('X-Rate-Limit-Remaining')
                    # If remaining cost is low (e.g. < 5.0), throttle slightly
                    if remaining:
                        val = float(remaining)
                        if val < 10.0:
                            # small proactive sleep
                             time.sleep(1.0)
                except ValueError:
                    pass

                return resp
            except requests.exceptions.RequestException as e:
                # Basic connection retry logic could go here, but for now we raise or print
                print(f"Request failed: {e}")
                raise e

def download_specific_courses(course_ids, token, output_dir, base_url="https://canvas.instructure.com/api/v1", no_structure=False, ignore_patterns=None, optimize=True, include_assignments=False, include_submissions=False, force=False):
    """
    Download files and linked module pages from specific Canvas courses.
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # Initialize our smart session and stats
    session = CanvasSession(token, optimize=optimize)
    stats = DownloadStats()

    for course_id in course_ids:
        print(f"Processing course {course_id}...")
        download_course_files(course_id, session, output_dir, base_url, optimize, stats, force)
        download_course_modules(course_id, session, output_dir, base_url, no_structure, ignore_patterns, optimize, stats, force)
        
        if include_assignments:
             download_course_assignments(course_id, session, output_dir, base_url, ignore_patterns, optimize, stats, force, include_submissions)

    # Print summary at the very end
    stats.print_summary()



def download_course_assignments(course_id, session, output_dir, base_url, ignore_patterns, optimize, stats, force, include_submissions):
    """Helper: Download assignments and their attached files/descriptions."""
    assignments_url = f"{base_url}/courses/{course_id}/assignments?per_page=100"
    
    try:
        response = session.get(assignments_url)
        response.raise_for_status()
        assignments = response.json()
    except Exception as e:
        print(f"Error fetching assignments: {e}")
        return

    print(f"Found {len(assignments)} assignments. Processing...")
    
    save_folder = Path(output_dir) / str(course_id) / "Assignments"
    save_folder.mkdir(parents=True, exist_ok=True)
    
    # We will process assignments in parallel if optimized
    def process_assignment(assignment):
        name = assignment.get('name', 'Untitled')
        assignment_id = assignment.get('id')
        safe_name = "".join([c for c in name if c.isalpha() or c.isdigit() or c in (' ', '-', '_')]).strip()
        assignment_folder = save_folder / safe_name
        assignment_folder.mkdir(parents=True, exist_ok=True)
        
        # 1. Save Description as HTML
        description = assignment.get('description')
        if description:
             # Logic for HTML file sync? It's small, maybe just overwrite or check content match (hard)
             # Let's just always write it for now, it's fast.
             with open(assignment_folder / "instructions.html", 'w', encoding='utf-8') as f:
                 size = f.write(description)
                 stats.add_download("instructions.html", size)
             
             # Parse description for embedded files
             soup = BeautifulSoup(description, "html.parser")
             links = soup.find_all('a', href=True)
             for link in links:
                 href = link['href']
                 
                 # Logic to catch more Canvas file links
                 # Common patterns: /courses/xxx/files/yyy/download, /files/yyy/download
                 if "/files/" in href or "/courses/" in href:
                     # Skip external links that are clearly not Canvas files if you want, but for now we trust the heuristic
                     if "canvas" not in href and not href.startswith("/"):
                          # External link? Maybe keep it if it's a file?
                          pass

                     full_url = urljoin(base_url, href)
                     
                     # Force download suffix logic
                     if "/files/" in full_url:
                        if "download" not in full_url and "download_frd" not in full_url:
                            if "?" in full_url:
                                parts = full_url.split("?")
                                full_url = f"{parts[0]}/download?{parts[1]}"
                            else:
                                full_url = f"{full_url}/download"

                     download_linked_file(full_url, session, assignment_folder, ignore_patterns=ignore_patterns, stats=stats, force=force)
        
        # 2. Download direct attachments (if any)
        if 'attachments' in assignment:
            for att in assignment['attachments']:
                dl_url = att.get('url')
                fname = att.get('filename') # Explicit filename from metadata
                if dl_url:
                     download_linked_file(dl_url, session, assignment_folder, filename=fname, ignore_patterns=ignore_patterns, stats=stats, force=force)

        # 3. Download Submissions (if requested)
        if include_submissions and assignment_id:
             process_submission(course_id, assignment_id, session, base_url, assignment_folder, ignore_patterns, stats, force)

    if optimize:
        with ThreadPoolExecutor(max_workers=5) as executor:
            list(tqdm(executor.map(process_assignment, assignments), total=len(assignments), desc=f"Downloading Assignments"))
    else:
        for assignment in tqdm(assignments, desc="Downloading Assignments"):
            process_assignment(assignment)


def process_submission(course_id, assignment_id, session, base_url, assignment_folder, ignore_patterns, stats, force):
    """Helper: Download user submissions for an assignment."""
    # Get the single user's submission
    sub_url = f"{base_url}/courses/{course_id}/assignments/{assignment_id}/submissions/self"
    try:
        resp = session.get(sub_url)
        if resp.status_code == 404:
             return # No submission
        resp.raise_for_status()
        sub = resp.json()
    except Exception:
        return

    sub_folder = assignment_folder / "Submissions"
    
    # Check if there are attachments (raw files uploaded by student)
    if 'attachments' in sub:
        sub_folder.mkdir(parents=True, exist_ok=True)
        for att in sub['attachments']:
            dl_url = att.get('url')
            fname = att.get('filename')
            if dl_url:
                download_linked_file(dl_url, session, sub_folder, filename=fname, ignore_patterns=ignore_patterns, stats=stats, force=force)

    # Check for annotated PDF preview (DocViewer)
    # This is for when the teacher has graded/annotated the file, or if it's a rendered view
    preview_url = sub.get('preview_url')
    if preview_url:
         download_annotated_pdf(preview_url, sub_folder, session, stats, force)


def download_annotated_pdf(preview_url, output_folder, session, stats, force):
    """
    Downloads the 'annotated.pdf' from Canvas DocViewer logic.
    Ref: https://community.canvaslms.com/t5/Question-Forum/Download-annotated-submissions-via-API/m-p/153466
    """
    try:
        # First get the redirect to the actual docviewer session
        response = session.get(preview_url, allow_redirects=True)
        docviewer_url = response.url
        
        if '/view' in docviewer_url:
            base_view_url = docviewer_url.split('/view')[0]
            annotated_url = f"{base_view_url}/annotated.pdf"
            output_folder.mkdir(parents=True, exist_ok=True)
            output_path = output_folder / "annotated_submission.pdf"

            # Sync check
            if not force and output_path.exists():
                 # We can't easily check size/readiness without making calls, but let's assume if it's there it's good
                 # Or we could rely on the file size check later if we fetch metadata headers
                 pass 

            # Trigger generation
            session.post(annotated_url)
            
            # Poll
            ready_url = f"{annotated_url}/is_ready"
            attempts = 0
            while attempts < 10: # Don't wait forever
                r = session.get(ready_url).json()
                if r.get('ready'):
                    # Download
                    file_resp = session.get(annotated_url)
                    with open(output_path, 'wb') as f:
                        size = f.write(file_resp.content)
                        if stats: stats.add_download("annotated_submission.pdf", size)
                    break
                time.sleep(1)
                attempts += 1
    except Exception:
        pass # Silently fail for complex docviewer errors to avoid spamming console matches


def download_all_courses(token, output_dir, base_url="https://canvas.instructure.com/api/v1"):
    # This function is less used but we'll update it to match the shared signature style roughly
    # For now, it delegates to download_specific_courses
    session = CanvasSession(token, optimize=True) # Default optimize for "all"
    api_url = f"{base_url}/courses?enrollment_state=active&per_page=100"
    
    response = session.get(api_url)
    response.raise_for_status()
    courses = response.json()

    course_ids = [course['id'] for course in courses]
    print(f"Found {len(course_ids)} courses.")

    # Re-use the smart internal logic
    download_specific_courses(course_ids, token, output_dir, base_url)


def download_course_files(course_id, session, output_dir, base_url, optimize, stats, force):
    """Helper: Download all uploaded files in a course."""
    files_url = f"{base_url}/courses/{course_id}/files?per_page=100"
    save_folder = Path(output_dir) / str(course_id) / "Files"
    # save_folder.mkdir(parents=True, exist_ok=True) <--- Defer creation

    # Collect all file metadata first
    all_files_metadata = []

    try:
        while files_url:
            resp = session.get(files_url)
            if resp.status_code == 403:
                print(f"Warning: Access denied (403) for course files at {files_url}. Skipping file download.")
                return
            resp.raise_for_status()
            chunk = resp.json()
            all_files_metadata.extend(chunk)
            
            files_url = None
            if 'next' in resp.links:
                files_url = resp.links['next']['url']
        
        # Now download them
        if not all_files_metadata:
             return
             
        # Only create folder if we actually have files and access
        save_folder.mkdir(parents=True, exist_ok=True)
        
        # Define the work function
        def do_download(file_info):
            file_name = file_info['filename']
            file_url_api = file_info['url']
            file_size = file_info.get('size', -1)
            file_path = save_folder / file_name
            
            # Sync Logic: Skip if exists and size matches
            if not force and file_path.exists():
                local_size = file_path.stat().st_size
                if local_size == file_size:
                    # print(f"Skipping existing file (synced): {file_name}")
                    return

            try:
                # The file_url in the API response is usually a redirect to the actual storage
                # We use our session to get it.
                # Note: This is an API call, so it costs quota.
                file_resp = session.get(file_url_api)
                file_resp.raise_for_status()
                with open(file_path, 'wb') as f:
                    size = f.write(file_resp.content)
                    stats.add_download(file_name, size)

            except Exception as e:
                print(f"Failed to download {file_name}: {e}")

        # Execute
        if optimize:
            # Use a conservative worker count for API-bound requests
            with ThreadPoolExecutor(max_workers=5) as executor:
                list(tqdm(executor.map(do_download, all_files_metadata), total=len(all_files_metadata), desc=f"Downloading course {course_id} files (Optimized)"))
        else:
            for file_info in tqdm(all_files_metadata, desc=f"Downloading course {course_id} files"):
                 do_download(file_info)

    except requests.exceptions.RequestException as e:
        print(f"Error downloading files for course {course_id}: {e}")


def download_course_modules(course_id, session, output_dir, base_url, no_structure, ignore_patterns, optimize, stats, force):
    """Helper: Download module item linked files in a course."""
    modules_url = f"{base_url}/courses/{course_id}/modules?per_page=100"
    response = session.get(modules_url)
    response.raise_for_status()
    modules = response.json()
    
    base_save_folder = Path(output_dir) / str(course_id) / "Modules"
    base_save_folder.mkdir(parents=True, exist_ok=True)

    print(f"Found {len(modules)} modules. processing...")

    for module in modules:
        module_name = module['name']
        module_id = module['id']
        
        # Decide folder structure
        if no_structure:
            save_folder = base_save_folder
        else:
            safe_name = "".join([c for c in module_name if c.isalpha() or c.isdigit() or c in (' ', '-', '_')]).strip()
            save_folder = base_save_folder / safe_name
            save_folder.mkdir(parents=True, exist_ok=True)

        items_url = f"{base_url}/courses/{course_id}/modules/{module_id}/items?per_page=100"
        items_resp = session.get(items_url)
        items_resp.raise_for_status()
        items = items_resp.json()
        
        # Collect tasks for this module
        download_tasks = []

        for item in items:
            if item['type'] == "File":
                file_url = item.get('url')
                if file_url:
                    download_tasks.append({
                        'type': 'File',
                        'url': file_url,
                        'folder': save_folder
                    })
            
            elif item['type'] == "Page":
                download_tasks.append({
                    'type': 'Page',
                    'page_url': item.get('page_url'),
                    'folder': save_folder
                })

        # Helper to process a single task
        def process_task(task):
            if task['type'] == 'File':
                # Fetch metadata
                try:
                    meta_resp = session.get(task['url'])
                    if meta_resp.status_code == 200:
                        data = meta_resp.json()
                        d_url = data.get('url')
                        fname = data.get('filename')
                        fsize = data.get('size', -1)
                        
                        if should_ignore(fname, ignore_patterns):
                            return # Skip silently or print
                            
                        # Sync Logic for Module Files
                        if d_url and fname and not force:
                            f_path = task['folder'] / fname
                            if f_path.exists() and f_path.stat().st_size == fsize:
                                 return # Skip

                        if d_url and fname:
                            download_linked_file(d_url, session, task['folder'], fname, ignore_patterns, stats, force)
                except Exception as e:
                    print(f"Error processing file task: {e}")

            elif task['type'] == 'Page':
                try:
                    p_url = f"{base_url}/courses/{course_id}/pages/{task['page_url']}"
                    p_resp = session.get(p_url)
                    p_resp.raise_for_status()
                    body = p_resp.json().get('body', '')
                    soup = BeautifulSoup(body, "html.parser")
                    links = soup.find_all('a', href=True)
                    for link in links:
                         href = link['href']
                         if "/files/" in href or "download" in href:
                             full_url = urljoin(base_url, href)
                             download_linked_file(full_url, session, task['folder'], ignore_patterns=ignore_patterns, stats=stats, force=force)
                except Exception as e:
                    print(f"Error processing page task: {e}")

        # Run tasks
        if optimize and download_tasks:
             # Max workers 5 for mixed API/Downloading
             with ThreadPoolExecutor(max_workers=5) as executor:
                 futures = [executor.submit(process_task, t) for t in download_tasks]
                 # Wait for all to complete
                 for f in concurrent.futures.as_completed(futures):
                     pass 
        else:
             for t in download_tasks:
                 process_task(t)





def should_ignore(filename, ignore_patterns):
    if not filename or not ignore_patterns:
        return False
    for pattern in ignore_patterns:
        if fnmatch.fnmatch(filename, pattern):
            return True
    return False

import re
import mimetypes

def download_linked_file(url, session, save_folder, filename=None, ignore_patterns=None, stats=None, force=False):
    """Helper: Download linked files inside a module page."""
    if not url.startswith("http"):
         return 

    try:
        # We use stream=True so headers are fetched first, allowing filename extraction/check
        response = session.get(url, stream=True)
        response.raise_for_status()
    except Exception as e:
        print(f"Failed to download {url}: {e}")
        return

    # Attempt to extract correct filename from headers vs URL
    server_filename = None
    cd = response.headers.get("content-disposition")
    if cd:
        # Try simple regex for filename="..."
        # This handles the most common case. For full RFC comp., would need more.
        matches = re.findall(r'filename="?([^"]+)"?', cd)
        if matches:
            server_filename = matches[0]

    # If no filename passed, or if the URL-derived one is bad ("download"), use server one
    if not filename:
        parsed_url = requests.utils.urlparse(url)
        filename = os.path.basename(parsed_url.path)
        if not filename or "%" in filename:
             from urllib.parse import unquote
             filename = unquote(filename)
    
    # Check for bad filenames
    if not filename or filename.strip() == "" or filename == "download" or filename == "downloaded_file":
        if server_filename:
             filename = server_filename
        else:
             filename = "downloaded_file"
    
    # If still no extension or "download", try mimetype
    root, ext = os.path.splitext(filename)
    if not ext or filename == "downloaded_file":
        ct = response.headers.get("content-type", "").split(";")[0].strip()
        guessed_ext = mimetypes.guess_extension(ct)
        if guessed_ext:
            if filename == "downloaded_file":
                filename = f"file{guessed_ext}"
            else:
                filename = f"{filename}{guessed_ext}"

    # Validation: If content-type is text/html, this is probably a login page or error, not the file.
    ct = response.headers.get('content-type', '').lower()
    if 'text/html' in ct and not filename.endswith('.html'):
         # We can try to see if we can extract a better name or just fail
         # print(f"Warning: {url} returned HTML instead of a file. It might be a preview page.")
         return 

    
    if should_ignore(filename, ignore_patterns):
        print(f"Skipping ignored file: {filename}")
        return

    file_path = save_folder / filename
    total_size = int(response.headers.get('content-length', 0))
    
    # Check Sync logic
    if not force and file_path.exists():
        local_size = file_path.stat().st_size
        # If sizes match, we assume it's the same file.
        if local_size == total_size:
            return

    try: 
        # Use standard library open and write
        with open(file_path, 'wb') as f, tqdm(
            desc=filename,
            total=total_size,
            unit='B',
            unit_scale=True,
            unit_divisor=1024,
            leave=True
        ) as bar:
            downloaded = 0
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    size = f.write(chunk)
                    downloaded += size
                    bar.update(size)
            
            if stats:
                stats.add_download(filename, downloaded)
    except Exception as e:
         print(f"Error writing file {filename}: {e}")
