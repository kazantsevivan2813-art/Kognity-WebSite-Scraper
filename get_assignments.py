"""
Get assignments from Kognity API using saved cookies and subject IDs from folders.
"""

import os
import json
import re
import requests
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv('config.env')

WEBSITE_URL = os.getenv('WEBSITE_URL')
COOKIE_FILE = 'cookies.json'
DOWNLOADS_DIR = Path('downloads')


def load_cookies():
    """Load cookies from file and convert to requests format"""
    if not os.path.exists(COOKIE_FILE):
        print(f"❌ Cookie file not found: {COOKIE_FILE}")
        return None
    
    try:
        with open(COOKIE_FILE, 'r') as f:
            cookie_data = json.load(f)
        
        # Convert Selenium cookies to requests format
        cookies = {}
        for cookie in cookie_data.get('cookies', []):
            cookies[cookie['name']] = cookie['value']
        
        print(f"✓ Loaded {len(cookies)} cookies from {COOKIE_FILE}")
        return cookies
    except Exception as e:
        print(f"❌ Error loading cookies: {e}")
        return None


def get_subject_ids_from_folders():
    """Scan downloads folder and extract class IDs from folder names
    
    Note: In Kognity, sid (class_id) is used as subject_id in API calls.
    Folder format: "Class_ IB DP Biology SL_HL FE2025 [sid-422]"
    """
    subject_ids = []
    
    if not DOWNLOADS_DIR.exists():
        print(f"❌ Downloads directory not found: {DOWNLOADS_DIR}")
        return subject_ids
    
    print(f"\n📁 Scanning {DOWNLOADS_DIR} for class folders...")
    
    # Pattern to match [sid-XXX] in folder names (class_id)
    pattern = r'\[sid-(\d+)\]'
    
    for folder in DOWNLOADS_DIR.iterdir():
        if folder.is_dir():
            folder_name = folder.name
            match = re.search(pattern, folder_name)
            
            if match:
                class_id = match.group(1)
                subject_ids.append({
                    'id': class_id,  # class_id (sid) - used as subject_id in API
                    'name': folder_name,
                    'path': folder
                })
                print(f"  ✓ Found class ID (sid) {class_id}: {folder_name}")
            else:
                print(f"  ⚠ No class ID found in: {folder_name}")
    
    print(f"\n✓ Found {len(subject_ids)} classes with IDs\n")
    return subject_ids


def get_subject_node_id(subject_id, cookies):
    """Get subject_node_id from subject tree
    
    Args:
        subject_id: The class_id (sid) extracted from folder name, used as subject_id in API
        cookies: Session cookies
    
    Returns:
        subject_node_id from the first item in subject_tree array
    """
    if not WEBSITE_URL:
        print(f"❌ WEBSITE_URL not set in config.env")
        return None
    
    # Construct API URL for subject tree
    # subject_id here is the class_id (sid) from the URL
    api_url = f"{WEBSITE_URL}api/schoolstaff/staff/subject/{subject_id}/"
    
    print(f"🌐 API URL: {api_url}")
    print(f"📡 Fetching subject tree for class ID (sid): {subject_id}...")
    
    try:
        # Make GET request with cookies
        response = requests.get(api_url, cookies=cookies, timeout=30)
        
        # Check response status
        if response.status_code == 200:
            print(f"✓ Success! Status code: {response.status_code}")
            data = response.json()
            
            # Extract subject_tree array
            subject_tree = data.get('subject_tree', [])
            
            if subject_tree and len(subject_tree) > 0:
                # Get first item's id
                subject_node_id = subject_tree[0].get('id')
                print(f"✓ Subject tree has {len(subject_tree)} items")
                print(f"✓ First item ID (subject_node_id): {subject_node_id}")
                
                return subject_node_id
            else:
                print(f"⚠ subject_tree is empty or not found")
                return None
        else:
            print(f"❌ Error! Status code: {response.status_code}")
            print(f"Response: {response.text[:200]}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"❌ Failed to parse JSON: {e}")
        print(f"Response text: {response.text[:200]}")
        return None


def get_exam_style_questions(subject_id, subject_node_id, cookies):
    """Fetch ALL exam style questions for a subject using subject_node_id (handles pagination)"""
    if not WEBSITE_URL:
        print(f"❌ WEBSITE_URL not set in config.env")
        return None
    
    # Start with first page
    api_url = f"{WEBSITE_URL}api/schoolstaff/subjects/{subject_id}/exam_style_questions/?page=1&page_size=100&subject_node_id={subject_node_id}&min_marks=&max_marks="
    
    print(f"\n🌐 Starting API URL: {api_url}")
    print(f"📡 Fetching exam style questions...")
    print(f"📌 Subject ID: {subject_id}")
    print(f"📌 Subject Node ID: {subject_node_id}")
    
    all_results = []
    total_count = 0
    page = 1
    
    try:
        while api_url:
            print(f"📄 Fetching page {page}...")
            
            # Make GET request with cookies
            response = requests.get(api_url, cookies=cookies, timeout=30)
            
            # Check response status
            if response.status_code != 200:
                print(f"❌ Error! Status code: {response.status_code}")
                print(f"Response: {response.text[:200]}")
                break
            
            data = response.json()
            
            # Extract results from this page
            page_results = data.get('results', [])
            all_results.extend(page_results)
            
            # Get total count (only from first page)
            if page == 1:
                total_count = data.get('count', 0)
                print(f"✓ Total questions available: {total_count}")
            
            print(f"✓ Page {page}: Got {len(page_results)} questions (Total so far: {len(all_results)})")
            
            # Get next page URL
            api_url = data.get('next')
            page += 1
            
            # Safety check: don't loop forever
            if page > 100:
                print(f"⚠ Stopped at page 100 for safety")
                break
        
        # Return combined data in same format as original API
        combined_data = {
            'count': total_count,
            'results': all_results,
            'next': None,
            'previous': None
        }
        
        print(f"\n✓ Success! Fetched ALL {len(all_results)} questions out of {total_count} total")
        return combined_data
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"❌ Failed to parse JSON: {e}")
        return None


def generate_html_page(exam_questions, subject_name, subject_id, output_file):
    """Generate an HTML page displaying exam questions"""
    
    # Extract results from API response
    if isinstance(exam_questions, dict):
        questions = exam_questions.get('results', [])
        total_count = exam_questions.get('count', len(questions))
    else:
        questions = exam_questions if isinstance(exam_questions, list) else []
        total_count = len(questions)
    
    print(f"\n📄 Generating HTML page with {len(questions)} questions...")
    
    # Generate HTML
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Exam Questions - {subject_name}</title>
    <script id="MathJax-script" async src="tex-mml-chtml.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background-color: #f5f5f5;
            padding: 20px;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background-color: white;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
        }}
        
        .header h1 {{
            font-size: 28px;
            margin-bottom: 8px;
        }}
        
        .header p {{
            opacity: 0.9;
            font-size: 14px;
        }}
        
        .stats {{
            display: flex;
            gap: 20px;
            margin-top: 15px;
        }}
        
        .stat {{
            background: rgba(255,255,255,0.2);
            padding: 10px 15px;
            border-radius: 5px;
        }}
        
        .stat-label {{
            font-size: 12px;
            opacity: 0.8;
        }}
        
        .stat-value {{
            font-size: 20px;
            font-weight: bold;
            margin-top: 5px;
        }}
        
        .search-bar {{
            padding: 20px 30px;
            border-bottom: 1px solid #e0e0e0;
        }}
        
        .search-input {{
            width: 100%;
            padding: 12px 20px;
            border: 2px solid #e0e0e0;
            border-radius: 6px;
            font-size: 14px;
            transition: border-color 0.3s;
        }}
        
        .search-input:focus {{
            outline: none;
            border-color: #667eea;
        }}
        
        .table-container {{
            overflow-x: auto;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        
        thead {{
            background-color: #f8f9fa;
            border-bottom: 2px solid #e0e0e0;
        }}
        
        th {{
            padding: 15px 20px;
            text-align: left;
            font-size: 13px;
            font-weight: 600;
            color: #495057;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        
        td {{
            padding: 15px 20px;
            border-bottom: 1px solid #f0f0f0;
            vertical-align: top;
        }}
        
        tr:hover {{
            background-color: #f8f9fa;
        }}
        
        .checkbox {{
            width: 18px;
            height: 18px;
            cursor: pointer;
        }}
        
        .question-text {{
            color: #333;
            line-height: 1.5;
            max-width: 600px;
        }}
        
        .badge {{
            display: inline-block;
            padding: 4px 10px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 600;
            margin-right: 5px;
            text-transform: uppercase;
        }}
        
        .badge-sl {{
            background-color: #e3f2fd;
            color: #1976d2;
        }}
        
        .badge-hl {{
            background-color: #fff3e0;
            color: #f57c00;
        }}
        
        .badge-core {{
            background-color: #e8f5e9;
            color: #388e3c;
        }}
        
        .badge-extended {{
            background-color: #fff3e0;
            color: #f57c00;
        }}
        
        .badge-paper {{
            background-color: #e8d5f5;
            color: #7b1fa2;
        }}
        
        .marks {{
            font-weight: 600;
            color: #667eea;
            font-size: 16px;
        }}
        
        .search-icon {{
            cursor: pointer;
            color: #667eea;
            font-size: 18px;
        }}
        
        .no-data {{
            text-align: center;
            padding: 60px 20px;
            color: #999;
        }}
        
        .footer {{
            padding: 20px 30px;
            text-align: center;
            background-color: #f8f9fa;
            color: #666;
            font-size: 13px;
        }}
        
        /* Modal styles */
        .modal {{
            display: none;
            position: fixed;
            z-index: 1000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            overflow: auto;
            background-color: rgba(0, 0, 0, 0.5);
            animation: fadeIn 0.3s;
        }}
        
        @keyframes fadeIn {{
            from {{ opacity: 0; }}
            to {{ opacity: 1; }}
        }}
        
        .modal-content {{
            background-color: white;
            margin: 2% auto;
            padding: 0;
            border-radius: 8px;
            width: 90%;
            max-width: 1000px;
            max-height: 90vh;
            overflow: hidden;
            box-shadow: 0 4px 20px rgba(0,0,0,0.3);
            animation: slideDown 0.3s;
        }}
        
        @keyframes slideDown {{
            from {{
                transform: translateY(-50px);
                opacity: 0;
            }}
            to {{
                transform: translateY(0);
                opacity: 1;
            }}
        }}
        
        .modal-header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px 30px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        
        .modal-header h2 {{
            margin: 0;
            font-size: 24px;
        }}
        
        .modal-close {{
            color: white;
            font-size: 32px;
            font-weight: bold;
            cursor: pointer;
            background: none;
            border: none;
            padding: 0;
            width: 32px;
            height: 32px;
            line-height: 32px;
            text-align: center;
            transition: transform 0.2s;
        }}
        
        .modal-close:hover {{
            transform: scale(1.2);
        }}
        
        .modal-body {{
            padding: 30px;
            max-height: calc(90vh - 150px);
            overflow-y: auto;
        }}
        
        .modal-section {{
            margin-bottom: 30px;
        }}
        
        .modal-section-title {{
            font-size: 18px;
            font-weight: 600;
            color: #667eea;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 2px solid #e0e0e0;
        }}
        
        .modal-section-content {{
            line-height: 1.8;
            color: #333;
        }}
        
        .modal-section-content table {{
            margin: 15px 0;
        }}
        
        .modal-section-content figure {{
            margin: 15px 0;
        }}
        
        .clickable-row {{
            cursor: pointer;
        }}
        
        .clickable-row:hover {{
            background-color: #f0f7ff !important;
        }}
        
        /* Pagination styles */
        .pagination-container {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 20px 30px;
            border-top: 1px solid #e0e0e0;
            background-color: #fafafa;
        }}
        
        .pagination-info {{
            color: #666;
            font-size: 14px;
        }}
        
        .pagination {{
            display: flex;
            gap: 5px;
            align-items: center;
        }}
        
        .pagination button {{
            padding: 8px 12px;
            border: 1px solid #e0e0e0;
            background-color: white;
            color: #333;
            cursor: pointer;
            border-radius: 4px;
            font-size: 14px;
            transition: all 0.3s;
        }}
        
        .pagination button:hover:not(:disabled) {{
            background-color: #667eea;
            color: white;
            border-color: #667eea;
        }}
        
        .pagination button:disabled {{
            cursor: not-allowed;
            opacity: 0.5;
        }}
        
        .pagination button.active {{
            background-color: #667eea;
            color: white;
            border-color: #667eea;
        }}
        
        .page-size-selector {{
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        
        .page-size-selector select {{
            padding: 6px 10px;
            border: 1px solid #e0e0e0;
            border-radius: 4px;
            font-size: 14px;
            cursor: pointer;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{subject_name}</h1>
            <p>Subject ID: {subject_id}</p>
            <div class="stats">
                <div class="stat">
                    <div class="stat-label">Total Questions</div>
                    <div class="stat-value">{total_count}</div>
                </div>
                <div class="stat">
                    <div class="stat-label">Displayed</div>
                    <div class="stat-value">{len(questions)}</div>
                </div>
            </div>
        </div>
        
        <div class="search-bar">
            <input type="text" class="search-input" id="searchInput" placeholder="Search questions by text..." onkeyup="filterByQuestion()">
        </div>
        
        <div class="table-container">
            <table id="questionsTable">
                <thead>
                    <tr>
                        <th style="width: 50px;">Sent</th>
                        <th>Question</th>
                        <th style="width: 120px;">Level</th>
                        <th style="width: 120px;">Paper</th>
                        <th style="width: 80px;">Marks</th>
                        <th style="width: 50px;"></th>
                    </tr>
                </thead>
                <tbody>
"""
    
    # Add question rows
    if questions:
        for idx, q in enumerate(questions):
            # Extract question data from question_html
            question_html = q.get('question_html', 'N/A')
            # Strip HTML tags for display in table
            question_text = re.sub('<[^<]+?>', '', question_html)  # Remove HTML tags
            question_text = question_text.replace('&nbsp;', ' ').replace('&thinsp;', ' ')
            question_text = ' '.join(question_text.split())  # Clean whitespace
            if len(question_text) > 200:
                question_text = question_text[:200] + '...'
            
            # Get levels from attributes.levels
            levels_data = q.get('attributes', {}).get('levels', [])
            level_names = [lvl.get('name', '') for lvl in levels_data]
            level_badges = ' '.join([f'<span class="badge badge-{lvl.lower().replace(" ", "-")}">{lvl}</span>' for lvl in level_names])
            
            # Get paper from papertype.name
            papertype = q.get('papertype', {})
            paper = papertype.get('name', 'N/A') if papertype else 'N/A'
            paper_badge = f'<span class="badge badge-paper">{paper}</span>' if paper != 'N/A' else ''
            
            # Get marks
            marks = q.get('marks', 'N/A')
            
            # Get subject node info
            subjectnode_mappings = q.get('subjectnode_mappings', [])
            subject_node = subjectnode_mappings[0].get('number_including_ancestors', '') if subjectnode_mappings else ''
            
            # Add subject node prefix to question if available
            question_display = f"<strong>[{subject_node}]</strong> {question_text}" if subject_node else question_text
            
            # Get full question and answer HTML
            question_html = q.get('question_html', 'No question available')
            answer_html = q.get('answer_explanation_html', 'No answer available')
            
            # Escape quotes for HTML attributes
            question_html_escaped = question_html.replace('"', '&quot;').replace("'", '&#39;')
            answer_html_escaped = answer_html.replace('"', '&quot;').replace("'", '&#39;')
            
            # Create modal title
            modal_title = f"[{subject_node}] {paper} - {marks} marks" if subject_node else f"{paper} - {marks} marks"
            modal_title_escaped = modal_title.replace('"', '&quot;').replace("'", '&#39;')
            
            html_content += f"""
                    <tr class="clickable-row" data-question="{question_html_escaped}" data-answer="{answer_html_escaped}" data-title="{modal_title_escaped}">
                        <td><input type="checkbox" class="checkbox" onclick="event.stopPropagation()"></td>
                        <td class="question-text">{question_display}</td>
                        <td>{level_badges if level_badges else 'N/A'}</td>
                        <td>{paper_badge}</td>
                        <td class="marks">{marks}</td>
                        <td><span class="search-icon">🔍</span></td>
                    </tr>
"""
    else:
        html_content += """
                    <tr>
                        <td colspan="6" class="no-data">No questions found</td>
                    </tr>
"""
    
    # Close HTML
    html_content += """
                </tbody>
            </table>
        </div>
        
        <div class="pagination-container">
            <div class="page-size-selector">
                <label>Show:</label>
                <select id="pageSizeSelect" onchange="changePageSize()">
                    <option value="25">25</option>
                    <option value="50" selected>50</option>
                    <option value="100">100</option>
                    <option value="200">200</option>
                </select>
                <span>per page</span>
            </div>
            
            <div class="pagination-info" id="paginationInfo">
                Showing 1-50 of 213
            </div>
            
            <div class="pagination" id="paginationControls">
                <!-- Pagination buttons will be generated by JavaScript -->
            </div>
        </div>
        
        <div class="footer">
            Generated on """ + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + """ | Total: """ + str(total_count) + """ questions
        </div>
    </div>
    
    <!-- Modal -->
    <div id="questionModal" class="modal">
        <div class="modal-content">
            <div class="modal-header">
                <h2 id="modalTitle">Question Details</h2>
                <button class="modal-close" onclick="closeModal()">&times;</button>
            </div>
            <div class="modal-body">
                <div class="modal-section">
                    <div class="modal-section-title">Question</div>
                    <div class="modal-section-content" id="modalQuestion"></div>
                </div>
                <div class="modal-section">
                    <div class="modal-section-title">Answer & Explanation</div>
                    <div class="modal-section-content" id="modalAnswer"></div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        let currentPage = 1;
        let pageSize = 50;
        let searchTerm = '';
        
        function getAllRows() {
            const table = document.getElementById('questionsTable');
            const rows = Array.from(table.getElementsByTagName('tr')).slice(1); // Skip header
            return rows;
        }
        
        function getFilteredRows() {
            const allRows = getAllRows();
            if (!searchTerm) {
                return allRows;
            }
            
            return allRows.filter(row => {
                const questionCell = row.getElementsByTagName('td')[1];
                if (questionCell) {
                    const textValue = questionCell.textContent || questionCell.innerText;
                    return textValue.toLowerCase().indexOf(searchTerm) > -1;
                }
                return false;
            });
        }
        
        function displayPage() {
            const allRows = getAllRows();
            const filteredRows = getFilteredRows();
            
            // Hide all rows first
            allRows.forEach(row => row.style.display = 'none');
            
            // Calculate pagination
            const totalFiltered = filteredRows.length;
            const totalPages = Math.ceil(totalFiltered / pageSize);
            currentPage = Math.min(currentPage, Math.max(1, totalPages));
            
            const startIndex = (currentPage - 1) * pageSize;
            const endIndex = Math.min(startIndex + pageSize, totalFiltered);
            
            // Show only current page rows
            for (let i = startIndex; i < endIndex; i++) {
                filteredRows[i].style.display = '';
            }
            
            // Update pagination info
            updatePaginationInfo(startIndex + 1, endIndex, totalFiltered);
            updatePaginationControls(currentPage, totalPages);
        }
        
        function updatePaginationInfo(start, end, total) {
            const info = document.getElementById('paginationInfo');
            if (total === 0) {
                info.textContent = 'No results found';
            } else {
                info.textContent = `Showing ${start}-${end} of ${total}`;
            }
        }
        
        function updatePaginationControls(current, total) {
            const controls = document.getElementById('paginationControls');
            controls.innerHTML = '';
            
            if (total <= 1) return;
            
            // Previous button
            const prevBtn = document.createElement('button');
            prevBtn.textContent = '« Previous';
            prevBtn.disabled = current === 1;
            prevBtn.onclick = () => goToPage(current - 1);
            controls.appendChild(prevBtn);
            
            // Page numbers
            const maxButtons = 5;
            let startPage = Math.max(1, current - Math.floor(maxButtons / 2));
            let endPage = Math.min(total, startPage + maxButtons - 1);
            
            if (endPage - startPage < maxButtons - 1) {
                startPage = Math.max(1, endPage - maxButtons + 1);
            }
            
            if (startPage > 1) {
                const firstBtn = document.createElement('button');
                firstBtn.textContent = '1';
                firstBtn.onclick = () => goToPage(1);
                controls.appendChild(firstBtn);
                
                if (startPage > 2) {
                    const dots = document.createElement('span');
                    dots.textContent = '...';
                    dots.style.padding = '0 5px';
                    controls.appendChild(dots);
                }
            }
            
            for (let i = startPage; i <= endPage; i++) {
                const btn = document.createElement('button');
                btn.textContent = i;
                btn.onclick = () => goToPage(i);
                if (i === current) {
                    btn.classList.add('active');
                }
                controls.appendChild(btn);
            }
            
            if (endPage < total) {
                if (endPage < total - 1) {
                    const dots = document.createElement('span');
                    dots.textContent = '...';
                    dots.style.padding = '0 5px';
                    controls.appendChild(dots);
                }
                
                const lastBtn = document.createElement('button');
                lastBtn.textContent = total;
                lastBtn.onclick = () => goToPage(total);
                controls.appendChild(lastBtn);
            }
            
            // Next button
            const nextBtn = document.createElement('button');
            nextBtn.textContent = 'Next »';
            nextBtn.disabled = current === total;
            nextBtn.onclick = () => goToPage(current + 1);
            controls.appendChild(nextBtn);
        }
        
        function goToPage(page) {
            currentPage = page;
            displayPage();
            window.scrollTo({ top: 0, behavior: 'smooth' });
        }
        
        function changePageSize() {
            pageSize = parseInt(document.getElementById('pageSizeSelect').value);
            currentPage = 1;
            displayPage();
        }
        
        function filterByQuestion() {
            const input = document.getElementById('searchInput');
            searchTerm = input.value.toLowerCase();
            currentPage = 1;
            displayPage();
        }
        
        async function openModal(questionHtml, answerHtml, title) {
            const modal = document.getElementById('questionModal');
            const qEl = document.getElementById('modalQuestion');
            const aEl = document.getElementById('modalAnswer');

            qEl.innerHTML = questionHtml;
            aEl.innerHTML = answerHtml || '<p style="color: #999;">No answer available</p>';
            document.getElementById('modalTitle').textContent = title || 'Question Details';

            modal.style.display = 'block';
            document.body.style.overflow = 'hidden';

            if (window.MathJax?.typesetPromise) {
            await new Promise(requestAnimationFrame); // optional, helps layout
            await MathJax.typesetPromise([qEl, aEl]);
            }
        }
        
        function closeModal() {
            document.getElementById('questionModal').style.display = 'none';
            document.body.style.overflow = 'auto'; // Restore scrolling
        }
        
        // Close modal when clicking outside
        window.onclick = function(event) {
            const modal = document.getElementById('questionModal');
            if (event.target == modal) {
                closeModal();
            }
        }
        
        // Close modal with Escape key
        document.addEventListener('keydown', function(event) {
            if (event.key === 'Escape') {
                closeModal();
            }
        });
        
        // Initialize on page load
        document.addEventListener('DOMContentLoaded', function() {
            // Initialize pagination
            displayPage();
            
            // Add click handlers to all table rows
            const table = document.getElementById('questionsTable');
            const rows = table.getElementsByTagName('tr');
            
            for (let i = 1; i < rows.length; i++) {
                const row = rows[i];
                if (row.classList.contains('clickable-row')) {
                    row.addEventListener('click', function(e) {
                        // Don't trigger if clicking checkbox
                        if (e.target.type === 'checkbox') {
                            return;
                        }
                        const questionHtml = this.getAttribute('data-question');
                        const answerHtml = this.getAttribute('data-answer');
                        const title = this.getAttribute('data-title') || 'Question Details';
                        openModal(questionHtml, answerHtml, title);
                    });
                }
            }
        });
    </script>
</body>
</html>
"""
    
    # Save HTML file
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"✓ HTML page generated: {output_file}")
        print(f"✓ Open in browser to view: file:///{os.path.abspath(output_file)}")
        return True
    except Exception as e:
        print(f"❌ Error generating HTML: {e}")
        return False


def main():
    print("="*60)
    print("Kognity Assignments Fetcher")
    print("="*60)
    
    # Load cookies
    cookies = load_cookies()
    if not cookies:
        print("\n❌ Cannot proceed without cookies. Please run the scraper first to save cookies.")
        return
    
    # Get subject IDs from folder names
    subjects = get_subject_ids_from_folders()
    
    if not subjects:
        print("❌ No subjects found. Please run the scraper first to create subject folders.")
        return
    
    # Process each subject
    print("="*60)
    print(f"Processing {len(subjects)} subject(s)...")
    print("="*60)
    
    successful_subjects = []
    failed_subjects = []
    
    for idx, subject in enumerate(subjects, 1):
        print(f"\n{'='*60}")
        print(f"[{idx}/{len(subjects)}] Processing: {subject['name']}")
        print(f"Subject ID: {subject['id']}")
        print(f"{'='*60}\n")
        
        try:
            # Create assignments folder in the class folder
            class_folder = subject['path']
            assignments_folder = class_folder / 'assignments'
            assignments_folder.mkdir(exist_ok=True)
            print(f"✓ Created/verified assignments folder: {assignments_folder}\n")
            
            # Step 1: Get subject_node_id from subject tree
            print("STEP 1: Getting subject tree and subject_node_id...")
            print("-"*60)
            subject_node_id = get_subject_node_id(subject['id'], cookies)
            
            if not subject_node_id:
                print(f"\n❌ Failed to get subject_node_id for {subject['name']}")
                failed_subjects.append({
                    'name': subject['name'],
                    'id': subject['id'],
                    'reason': 'Failed to get subject_node_id'
                })
                continue
            
            print(f"\n✓ Successfully extracted subject_node_id: {subject_node_id}")
            
            # Step 2: Get exam style questions using subject_node_id
            print("\n" + "="*60)
            print("STEP 2: Getting exam style questions...")
            print("="*60)
            exam_questions = get_exam_style_questions(subject['id'], subject_node_id, cookies)
            
            if exam_questions:
                print("\n" + "="*60)
                print("📋 EXAM STYLE QUESTIONS API RESPONSE:")
                print("="*60)
                
                # Save JSON to assignments folder
                json_file = assignments_folder / f"exam_questions_subject_{subject['id']}.json"
                with open(json_file, 'w', encoding='utf-8') as f:
                    json.dump(exam_questions, f, indent=2, ensure_ascii=False)
                print(f"✓ Saved JSON response to: {json_file}")
                
                # Print summary
                print("\n" + "="*60)
                print("📊 SUMMARY:")
                print("="*60)
                questions_count = 0
                if isinstance(exam_questions, dict):
                    print(f"Response keys: {list(exam_questions.keys())}")
                    if 'results' in exam_questions:
                        questions_count = len(exam_questions.get('results', []))
                        print(f"Number of results: {questions_count}")
                    if 'count' in exam_questions:
                        print(f"Total count: {exam_questions.get('count')}")
                elif isinstance(exam_questions, list):
                    questions_count = len(exam_questions)
                    print(f"Number of items: {questions_count}")
                    if exam_questions:
                        print(f"First item keys: {list(exam_questions[0].keys()) if isinstance(exam_questions[0], dict) else 'N/A'}")
                
                # Generate HTML page in assignments folder
                print("\n" + "="*60)
                print("STEP 3: Generating HTML page...")
                print("="*60)
                html_file = assignments_folder / "Exam-style assignment.html"
                if generate_html_page(exam_questions, subject['name'], subject['id'], html_file):
                    successful_subjects.append({
                        'name': subject['name'],
                        'id': subject['id'],
                        'questions': questions_count
                    })
                else:
                    failed_subjects.append({
                        'name': subject['name'],
                        'id': subject['id'],
                        'reason': 'Failed to generate HTML'
                    })
            else:
                print("\n❌ Failed to fetch exam style questions")
                failed_subjects.append({
                    'name': subject['name'],
                    'id': subject['id'],
                    'reason': 'Failed to fetch exam questions'
                })
        
        except Exception as e:
            print(f"\n❌ Error processing {subject['name']}: {e}")
            failed_subjects.append({
                'name': subject['name'],
                'id': subject['id'],
                'reason': f'Exception: {str(e)}'
            })
    
    # Final summary
    print("\n" + "="*60)
    print("📊 FINAL SUMMARY")
    print("="*60)
    print(f"\n✓ Successfully processed: {len(successful_subjects)}/{len(subjects)} subjects\n")
    
    if successful_subjects:
        print("Successful subjects:")
        for s in successful_subjects:
            print(f"  ✓ {s['name']} (ID: {s['id']}) - {s['questions']} questions")
    
    if failed_subjects:
        print(f"\n❌ Failed subjects: {len(failed_subjects)}\n")
        for s in failed_subjects:
            print(f"  ✗ {s['name']} (ID: {s['id']}) - {s['reason']}")
    
    print("\n" + "="*60)


if __name__ == "__main__":
    main()

