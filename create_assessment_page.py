"""
Create assessment pages for each class with navigation between subject names.
Extracts sid and cid from folder names, fetches subject tree, and generates HTML.
"""

import os
import json
import re
import shutil
import requests
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime
from collections import defaultdict

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


def get_class_info_from_folder(folder_name):
    """Extract sid and cid from folder name format: 'Class Name [sid-134-cid-706265]'"""
    # Pattern to match [sid-XXX-cid-YYY]
    pattern = r'\[sid-(\d+)-cid-(\d+)\]'
    match = re.search(pattern, folder_name)
    
    if match:
        sid = match.group(1)
        cid = match.group(2)
        return {'sid': sid, 'cid': cid, 'name': folder_name}
    return None


def get_subject_tree_children(sid, cookies):
    """Get subject tree children from API"""
    if not WEBSITE_URL:
        print(f"❌ WEBSITE_URL not set in config.env")
        return None
    
    api_url = f"{WEBSITE_URL}api/schoolstaff/staff/subject/{sid}/"
    
    print(f"🌐 Fetching subject tree: {api_url}")
    
    try:
        response = requests.get(api_url, cookies=cookies, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            subject_tree = data.get('subject_tree', None)
            
            # Handle structure: subject_tree is a list with one item that contains 'children'
            children = []
            if isinstance(subject_tree, list):
                if len(subject_tree) > 0 and isinstance(subject_tree[0], dict):
                    # Get the first item (which is a dict) and extract its 'children' field
                    children = subject_tree[0].get('children', [])
                else:
                    print(f"⚠ subject_tree list is empty or first item is not a dict")
                    return None
            elif isinstance(subject_tree, dict):
                # Handle case where subject_tree is directly a dict with 'children' key
                children = subject_tree.get('children', [])
            else:
                print(f"⚠ Unexpected subject_tree type: {type(subject_tree)}")
                return None
            
            print(f"✓ Found {len(children)} children in subject tree")
            
            # Extract id and name from each child
            nodes = []
            for child in children:
                if isinstance(child, dict):
                    node_id = child.get('id')
                    node_name = child.get('name')
                    if node_id and node_name:
                        nodes.append({'id': node_id, 'name': node_name})
                        print(f"  - {node_name} (ID: {node_id})")
            
            return nodes if nodes else None
        else:
            print(f"❌ Error! Status code: {response.status_code}")
            print(f"Response: {response.text[:200]}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"❌ Failed to parse JSON: {e}")
        return None


def get_questions_for_node(sid, cid, startnode_id, cookies):
    """Get questions for a specific node"""
    if not WEBSITE_URL:
        print(f"❌ WEBSITE_URL not set in config.env")
        return []
    
    api_url = f"{WEBSITE_URL}api/schoolstaff/assignments/subjects/{sid}/questions/?page_size=700&startnode_id={startnode_id}&exclude-hidden-nodes-for-subject-class-id={cid}"
    
    try:
        response = requests.get(api_url, cookies=cookies, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            results = data.get('results', [])
            print(f"  ✓ Fetched {len(results)} questions for node {startnode_id}")
            return results
        else:
            print(f"  ❌ Error! Status code: {response.status_code}")
            return []
            
    except requests.exceptions.RequestException as e:
        print(f"  ❌ Request failed: {e}")
        return []
    except json.JSONDecodeError as e:
        print(f"  ❌ Failed to parse JSON: {e}")
        return []


def get_difficulty_sort_key(difficulty):
    """Return sort key for difficulty (null first, then easy, medium, hard)"""
    if difficulty is None:
        return 0
    elif difficulty == 'difficulty-easy':
        return 1
    elif difficulty == 'difficulty-medium':
        return 2
    elif difficulty == 'difficulty-hard':
        return 3
    else:
        return 4


def generate_assessment_html(class_name, sid, cid, nodes_data, output_file):
    """Generate HTML page with navigation and questions"""
    
    # Organize questions by node
    all_questions = []
    for node in nodes_data:
        for question in node.get('questions', []):
            question['node_id'] = node['id']
            question['node_name'] = node['name']
            all_questions.append(question)
    
    # Sort questions by difficulty
    all_questions.sort(key=lambda q: (
        get_difficulty_sort_key(q.get('difficulty')),
        q.get('id', 0)
    ))
    
    # Group questions by node for navigation
    questions_by_node = defaultdict(list)
    for question in all_questions:
        questions_by_node[question['node_id']].append(question)
    
    # Generate difficulty badge HTML
    def get_difficulty_badge(difficulty):
        if difficulty is None:
            return '<span class="badge badge-null">No Difficulty</span>'
        elif difficulty == 'difficulty-easy':
            return '<span class="badge badge-easy">Easy</span>'
        elif difficulty == 'difficulty-medium':
            return '<span class="badge badge-medium">Medium</span>'
        elif difficulty == 'difficulty-hard':
            return '<span class="badge badge-hard">Hard</span>'
        return ''
    
    # Generate node navigation HTML
    nav_items = []
    for node in nodes_data:
        node_id = node['id']
        node_name = node['name']
        question_count = len(questions_by_node.get(node_id, []))
        nav_items.append(f'''
            <a href="#node-{node_id}" class="nav-item" data-node-id="{node_id}">
                <span class="nav-name">{node_name}</span>
                <span class="nav-count">{question_count}</span>
            </a>
        ''')
    
    nav_html = ''.join(nav_items)
    
    # Generate questions HTML by node
    questions_html = ''
    for node in nodes_data:
        node_id = node['id']
        node_name = node['name']
        questions = questions_by_node.get(node_id, [])
        
        if not questions:
            continue
        
        questions_html += f'''
        <div id="node-{node_id}" class="node-section">
            <div class="node-header">
                <h2 class="node-title">{node_name}</h2>
                <span class="node-question-count">{len(questions)} Questions</span>
            </div>
            <div class="node-questions">
        '''
        
        for idx, q in enumerate(questions, 1):
            question_html = q.get('question_html', 'No question available')
            question_id = q.get('id', 'N/A')
            difficulty = q.get('difficulty')
            difficulty_badge = get_difficulty_badge(difficulty)
            
            # Escape quotes for HTML attributes
            question_html_escaped = question_html.replace('"', '&quot;').replace("'", '&#39;')
            
            questions_html += f'''
                <div class="question-card" data-question-id="{question_id}" data-difficulty="{difficulty or 'null'}">
                    <div class="question-header">
                        <span class="question-number">Q{idx}</span>
                        <div class="question-meta">
                            {difficulty_badge}
                        </div>
                        <span class="question-id">ID: {question_id}</span>
                    </div>
                    <div class="question-content" data-question="{question_html_escaped}">
                        {question_html}
                    </div>
                </div>
            '''
        
        questions_html += '''
            </div>
        </div>
        '''
    
    html_content = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Assessment - {class_name}</title>
    <script id="MathJax-script" async src="tex-mml-chtml.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background-color: #f8f9fa;
            color: #333;
            line-height: 1.6;
        }}
        
        /* Top Navigation Bar */
        .top-nav {{
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 15px 30px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            z-index: 1000;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        
        .top-nav h1 {{
            font-size: 20px;
            font-weight: 600;
        }}
        
        .top-nav-info {{
            font-size: 12px;
            opacity: 0.9;
        }}
        
        /* Sidebar */
        .sidebar {{
            position: fixed;
            left: 0;
            top: 60px;
            width: 280px;
            height: calc(100vh - 60px);
            background-color: #2c3e50;
            color: white;
            overflow-y: auto;
            z-index: 900;
            border-right: 1px solid rgba(255,255,255,0.1);
        }}
        
        .sidebar-search {{
            padding: 15px;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }}
        
        .sidebar-search input {{
            width: 100%;
            padding: 10px 15px;
            background: rgba(255,255,255,0.1);
            border: 1px solid rgba(255,255,255,0.2);
            border-radius: 6px;
            color: white;
            font-size: 14px;
        }}
        
        .sidebar-search input::placeholder {{
            color: rgba(255,255,255,0.6);
        }}
        
        .nav-items {{
            padding: 10px;
        }}
        
        .nav-item {{
            display: block;
            padding: 12px 15px;
            margin-bottom: 6px;
            background-color: rgba(255,255,255,0.05);
            border-radius: 6px;
            text-decoration: none;
            color: white;
            transition: all 0.2s;
            cursor: pointer;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-left: 3px solid transparent;
        }}
        
        .nav-item:hover {{
            background-color: rgba(255,255,255,0.1);
            border-left-color: #3498db;
            transform: translateX(3px);
        }}
        
        .nav-item.active {{
            background-color: #3498db;
            border-left-color: #2980b9;
            font-weight: 600;
        }}
        
        .nav-name {{
            flex: 1;
            font-size: 13px;
            line-height: 1.4;
            word-break: break-word;
        }}
        
        .nav-count {{
            background-color: rgba(255,255,255,0.2);
            padding: 3px 8px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: bold;
            margin-left: 10px;
            min-width: 30px;
            text-align: center;
        }}
        
        .nav-item.active .nav-count {{
            background-color: rgba(255,255,255,0.3);
        }}
        
        /* Main Content */
        .content {{
            margin-left: 280px;
            margin-top: 60px;
            padding: 30px;
            max-width: 1400px;
        }}
        
        /* Controls Bar */
        .controls-bar {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 25px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            display: flex;
            gap: 15px;
            align-items: center;
            flex-wrap: wrap;
            position: sticky;
            top: 80px;
            z-index: 100;
        }}
        
        .control-group {{
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        
        .control-group label {{
            font-weight: 600;
            font-size: 13px;
            color: #555;
            white-space: nowrap;
        }}
        
        .control-group select {{
            padding: 8px 12px;
            border: 2px solid #e0e0e0;
            border-radius: 6px;
            font-size: 13px;
            cursor: pointer;
            background: white;
            transition: border-color 0.2s;
        }}
        
        .control-group select:focus {{
            outline: none;
            border-color: #667eea;
        }}
        
        .search-box {{
            flex: 1;
            min-width: 250px;
            position: relative;
        }}
        
        .search-box input {{
            width: 100%;
            padding: 8px 35px 8px 12px;
            border: 2px solid #e0e0e0;
            border-radius: 6px;
            font-size: 13px;
            transition: border-color 0.2s;
        }}
        
        .search-box input:focus {{
            outline: none;
            border-color: #667eea;
        }}
        
        .search-icon {{
            position: absolute;
            right: 12px;
            top: 50%;
            transform: translateY(-50%);
            color: #999;
            font-size: 16px;
        }}
        
        /* Topic Sections */
        .node-section {{
            background-color: white;
            border-radius: 8px;
            margin-bottom: 25px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            overflow: hidden;
        }}
        
        .node-header {{
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            padding: 20px 25px;
            border-bottom: 2px solid #e0e0e0;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        
        .node-title {{
            font-size: 20px;
            font-weight: 600;
            color: #2c3e50;
            margin: 0;
        }}
        
        .node-question-count {{
            background: #667eea;
            color: white;
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
        }}
        
        .node-questions {{
            padding: 20px 25px;
        }}
        
        /* Question Cards */
        .question-card {{
            border: 1px solid #e8e8e8;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 15px;
            transition: all 0.3s;
            background: #fafafa;
            display: none; /* Initially hidden, pagination will show them */
        }}
        
        .question-card:hover {{
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            border-color: #667eea;
            transform: translateY(-2px);
        }}
        
        .question-header {{
            display: flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 15px;
            padding-bottom: 12px;
            border-bottom: 1px solid #e8e8e8;
        }}
        
        .question-number {{
            font-weight: 700;
            color: #667eea;
            font-size: 16px;
            min-width: 50px;
        }}
        
        .question-meta {{
            display: flex;
            align-items: center;
            gap: 10px;
            flex: 1;
        }}
        
        .question-id {{
            margin-left: auto;
            font-size: 11px;
            color: #999;
            font-family: monospace;
        }}
        
        .question-content {{
            line-height: 1.8;
            color: #333;
            font-size: 15px;
        }}
        
        .question-content p {{
            margin-bottom: 10px;
        }}
        
        .question-content:last-child p:last-child {{
            margin-bottom: 0;
        }}
        
        /* Badges */
        .badge {{
            display: inline-block;
            padding: 5px 10px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        
        .badge-null {{
            background-color: #e8e8e8;
            color: #666;
        }}
        
        .badge-easy {{
            background-color: #c8e6c9;
            color: #2e7d32;
        }}
        
        .badge-medium {{
            background-color: #fff3e0;
            color: #f57c00;
        }}
        
        .badge-hard {{
            background-color: #ffcdd2;
            color: #c62828;
        }}
        
        .hidden {{
            display: none !important;
        }}
        
        /* Scrollbar Styling */
        .sidebar::-webkit-scrollbar {{
            width: 6px;
        }}
        
        .sidebar::-webkit-scrollbar-track {{
            background: rgba(255,255,255,0.05);
        }}
        
        .sidebar::-webkit-scrollbar-thumb {{
            background: rgba(255,255,255,0.2);
            border-radius: 3px;
        }}
        
        .sidebar::-webkit-scrollbar-thumb:hover {{
            background: rgba(255,255,255,0.3);
        }}
        
        /* Responsive */
        @media (max-width: 1024px) {{
            .sidebar {{
                width: 250px;
            }}
            .content {{
                margin-left: 250px;
            }}
        }}
        
        @media (max-width: 768px) {{
            .sidebar {{
                transform: translateX(-100%);
                transition: transform 0.3s;
            }}
            .content {{
                margin-left: 0;
            }}
        }}
        
        /* Loading State */
        .loading {{
            text-align: center;
            padding: 40px;
            color: #999;
        }}
        
        /* Empty State */
        .empty-state {{
            text-align: center;
            padding: 60px 20px;
            color: #999;
        }}
        
        .empty-state h3 {{
            font-size: 18px;
            margin-bottom: 10px;
            color: #666;
        }}
        
        /* Pagination */
        .pagination-container {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            margin-top: 25px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 15px;
        }}
        
        .pagination-info {{
            font-size: 14px;
            color: #666;
        }}
        
        .pagination-controls {{
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        
        .pagination-btn {{
            padding: 8px 14px;
            border: 2px solid #e0e0e0;
            background: white;
            color: #667eea;
            border-radius: 6px;
            cursor: pointer;
            font-size: 13px;
            font-weight: 600;
            transition: all 0.2s;
            min-width: 40px;
            text-align: center;
        }}
        
        .pagination-btn:hover:not(:disabled) {{
            background: #667eea;
            color: white;
            border-color: #667eea;
            transform: translateY(-1px);
        }}
        
        .pagination-btn:disabled {{
            opacity: 0.5;
            cursor: not-allowed;
        }}
        
        .pagination-btn.active {{
            background: #667eea;
            color: white;
            border-color: #667eea;
        }}
        
        .pagination-page-size {{
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        
        .pagination-page-size label {{
            font-size: 13px;
            color: #666;
            font-weight: 600;
        }}
        
        .pagination-page-size select {{
            padding: 6px 10px;
            border: 2px solid #e0e0e0;
            border-radius: 6px;
            font-size: 13px;
            cursor: pointer;
            background: white;
        }}
        
        .pagination-page-size select:focus {{
            outline: none;
            border-color: #667eea;
        }}
    </style>
</head>
<body>
    <div class="top-nav">
        <div>
            <h1>{class_name}</h1>
            <div class="top-nav-info">SID: {sid} | CID: {cid} | Total: {len(all_questions)} Questions</div>
        </div>
    </div>
    
    <div class="sidebar">
        <div class="sidebar-search">
            <input type="text" id="navSearch" placeholder="Search topics..." onkeyup="filterNav()">
        </div>
        <div class="nav-items" id="navItems">
            {nav_html}
        </div>
    </div>
    
    <div class="content">
        <div class="controls-bar">
            <div class="control-group">
                <label>Difficulty:</label>
                <select id="difficultyFilter" onchange="filterQuestions()">
                    <option value="all">All</option>
                    <option value="null">No Difficulty</option>
                    <option value="difficulty-easy">Easy</option>
                    <option value="difficulty-medium">Medium</option>
                    <option value="difficulty-hard">Hard</option>
                </select>
            </div>
            
            <div class="control-group">
                <label>Topic:</label>
                <select id="topicFilter" onchange="filterQuestions()">
                    <option value="all">All Topics</option>
                    {''.join([f'<option value="{node["id"]}">{node["name"]}</option>' for node in nodes_data])}
                </select>
            </div>
            
            <div class="search-box">
                <input type="text" id="searchInput" placeholder="Search questions..." onkeyup="filterQuestions()">
                <span class="search-icon">🔍</span>
            </div>
        </div>
        
        <div class="questions-container" id="questionsContainer">
            {questions_html}
        </div>
        
        <div class="pagination-container" id="paginationContainer">
            <div class="pagination-info" id="paginationInfo">
                Showing 1-10 of {len(all_questions)} questions
            </div>
            
            <div class="pagination-controls" id="paginationControls">
                <!-- Pagination buttons will be generated by JavaScript -->
            </div>
            
            <div class="pagination-page-size">
                <label>Per page:</label>
                <select id="pageSizeSelect" onchange="changePageSize()">
                    <option value="10" selected>10</option>
                    <option value="25">25</option>
                    <option value="50">50</option>
                    <option value="100">100</option>
                </select>
            </div>
        </div>
    </div>
    
    <script>
        // Navigation filtering
        function filterNav() {{
            const searchTerm = document.getElementById('navSearch').value.toLowerCase();
            const navItems = document.querySelectorAll('.nav-item');
            
            navItems.forEach(item => {{
                const name = item.querySelector('.nav-name').textContent.toLowerCase();
                if (name.includes(searchTerm)) {{
                    item.style.display = 'block';
                }} else {{
                    item.style.display = 'none';
                }}
            }});
        }}
        
        // Navigate to topic when clicking sidebar item
        function navigateToTopic(nodeId) {{
            // Set topic filter
            const topicFilter = document.getElementById('topicFilter');
            if (topicFilter) {{
                topicFilter.value = nodeId;
            }}
            
            // Clear other filters to show all questions for this topic
            const difficultyFilter = document.getElementById('difficultyFilter');
            const searchInput = document.getElementById('searchInput');
            if (difficultyFilter) difficultyFilter.value = 'all';
            if (searchInput) searchInput.value = '';
            
            // Apply filters and reset to first page
            currentPage = 1;
            filterQuestions();
            
            // Wait for pagination to update, then scroll to section
            setTimeout(() => {{
                const target = document.getElementById(`node-${{nodeId}}`);
                if (target && target.style.display !== 'none') {{
                    const offset = 80;
                    const elementPosition = target.getBoundingClientRect().top;
                    const offsetPosition = elementPosition + window.pageYOffset - offset;
                    
                    window.scrollTo({{
                        top: offsetPosition,
                        behavior: 'smooth'
                    }});
                }}
            }}, 100);
        }}
        
        // Smooth scroll to node section with active state update
        document.querySelectorAll('.nav-item').forEach(item => {{
            item.addEventListener('click', function(e) {{
                e.preventDefault();
                const nodeId = this.getAttribute('data-node-id');
                
                // Update active nav item
                document.querySelectorAll('.nav-item').forEach(nav => nav.classList.remove('active'));
                this.classList.add('active');
                
                // Navigate to topic
                navigateToTopic(nodeId);
            }});
        }});
        
        // Update active nav on scroll
        let lastScrollTop = 0;
        const navItems = document.querySelectorAll('.nav-item');
        const nodeSections = document.querySelectorAll('.node-section');
        
        function updateActiveNav() {{
            const scrollPos = window.scrollY + 100;
            
            nodeSections.forEach(section => {{
                const sectionTop = section.offsetTop;
                const sectionHeight = section.offsetHeight;
                const sectionId = section.id.replace('node-', '');
                
                if (scrollPos >= sectionTop && scrollPos < sectionTop + sectionHeight) {{
                    navItems.forEach(nav => nav.classList.remove('active'));
                    const activeNav = document.querySelector(`[data-node-id="${{sectionId}}"]`);
                    if (activeNav) {{
                        activeNav.classList.add('active');
                    }}
                }}
            }});
        }}
        
        window.addEventListener('scroll', updateActiveNav);
        updateActiveNav(); // Initial call
        
        // Pagination state
        let currentPage = 1;
        let pageSize = 10;
        
        // Get all visible questions (after filtering)
        function getVisibleQuestions() {{
            const allCards = document.querySelectorAll('.question-card');
            const visibleCards = Array.from(allCards).filter(card => !card.classList.contains('hidden'));
            return visibleCards;
        }}
        
        // Update pagination display
        function updatePagination() {{
            const visibleQuestions = getVisibleQuestions();
            const totalQuestions = visibleQuestions.length;
            const totalPages = Math.ceil(totalQuestions / pageSize);
            
            // Update current page if it's out of bounds
            if (currentPage > totalPages && totalPages > 0) {{
                currentPage = totalPages;
            }} else if (currentPage < 1) {{
                currentPage = 1;
            }}
            
            // Hide all questions first
            visibleQuestions.forEach(card => {{
                card.style.display = 'none';
            }});
            
            // Show questions for current page
            const startIndex = (currentPage - 1) * pageSize;
            const endIndex = Math.min(startIndex + pageSize, totalQuestions);
            const questionsToShow = [];
            
            for (let i = startIndex; i < endIndex; i++) {{
                if (visibleQuestions[i]) {{
                    visibleQuestions[i].style.display = 'block';
                    questionsToShow.push(visibleQuestions[i]);
                }}
            }}
            
            // Hide/show topic sections based on whether they have visible questions on current page
            const nodeSections = document.querySelectorAll('.node-section');
            nodeSections.forEach(section => {{
                const sectionQuestions = Array.from(section.querySelectorAll('.question-card'));
                const visibleInSection = sectionQuestions.filter(q => {{
                    const isVisible = !q.classList.contains('hidden');
                    const isOnCurrentPage = questionsToShow.includes(q);
                    return isVisible && isOnCurrentPage;
                }});
                
                if (visibleInSection.length === 0) {{
                    section.style.display = 'none';
                }} else {{
                    section.style.display = 'block';
                }}
            }});
            
            // Update pagination info
            const infoElement = document.getElementById('paginationInfo');
            if (totalQuestions === 0) {{
                infoElement.textContent = 'No questions found';
            }} else {{
                infoElement.textContent = `Showing ${{startIndex + 1}}-${{endIndex}} of ${{totalQuestions}} questions`;
            }}
            
            // Update pagination controls
            renderPaginationControls(totalPages);
        }}
        
        // Render pagination buttons
        function renderPaginationControls(totalPages) {{
            const container = document.getElementById('paginationControls');
            container.innerHTML = '';
            
            if (totalPages <= 1) {{
                return;
            }}
            
            // Previous button
            const prevBtn = document.createElement('button');
            prevBtn.className = 'pagination-btn';
            prevBtn.textContent = '‹ Prev';
            prevBtn.disabled = currentPage === 1;
            prevBtn.onclick = () => goToPage(currentPage - 1);
            container.appendChild(prevBtn);
            
            // Page numbers
            const maxButtons = 7;
            let startPage = Math.max(1, currentPage - Math.floor(maxButtons / 2));
            let endPage = Math.min(totalPages, startPage + maxButtons - 1);
            
            if (endPage - startPage < maxButtons - 1) {{
                startPage = Math.max(1, endPage - maxButtons + 1);
            }}
            
            // First page
            if (startPage > 1) {{
                const firstBtn = document.createElement('button');
                firstBtn.className = 'pagination-btn';
                firstBtn.textContent = '1';
                firstBtn.onclick = () => goToPage(1);
                container.appendChild(firstBtn);
                
                if (startPage > 2) {{
                    const dots = document.createElement('span');
                    dots.textContent = '...';
                    dots.style.padding = '0 5px';
                    dots.style.color = '#666';
                    container.appendChild(dots);
                }}
            }}
            
            // Page number buttons
            for (let i = startPage; i <= endPage; i++) {{
                const btn = document.createElement('button');
                btn.className = 'pagination-btn';
                if (i === currentPage) {{
                    btn.classList.add('active');
                }}
                btn.textContent = i;
                btn.onclick = () => goToPage(i);
                container.appendChild(btn);
            }}
            
            // Last page
            if (endPage < totalPages) {{
                if (endPage < totalPages - 1) {{
                    const dots = document.createElement('span');
                    dots.textContent = '...';
                    dots.style.padding = '0 5px';
                    dots.style.color = '#666';
                    container.appendChild(dots);
                }}
                
                const lastBtn = document.createElement('button');
                lastBtn.className = 'pagination-btn';
                lastBtn.textContent = totalPages;
                lastBtn.onclick = () => goToPage(totalPages);
                container.appendChild(lastBtn);
            }}
            
            // Next button
            const nextBtn = document.createElement('button');
            nextBtn.className = 'pagination-btn';
            nextBtn.textContent = 'Next ›';
            nextBtn.disabled = currentPage === totalPages;
            nextBtn.onclick = () => goToPage(currentPage + 1);
            container.appendChild(nextBtn);
        }}
        
        // Go to specific page
        function goToPage(page) {{
            currentPage = page;
            updatePagination();
            window.scrollTo({{
                top: 0,
                behavior: 'smooth'
            }});
        }}
        
        // Change page size
        function changePageSize() {{
            pageSize = parseInt(document.getElementById('pageSizeSelect').value);
            currentPage = 1;
            updatePagination();
        }}
        
        // Filter questions
        function filterQuestions() {{
            const difficultyFilter = document.getElementById('difficultyFilter').value;
            const topicFilter = document.getElementById('topicFilter').value;
            const searchTerm = document.getElementById('searchInput').value.toLowerCase();
            
            const questionCards = document.querySelectorAll('.question-card');
            const nodeSections = document.querySelectorAll('.node-section');
            
            let visibleCount = 0;
            
            questionCards.forEach(card => {{
                const difficulty = card.getAttribute('data-difficulty');
                const nodeSection = card.closest('.node-section');
                const nodeId = nodeSection ? nodeSection.id.replace('node-', '') : '';
                const questionContent = card.querySelector('.question-content').textContent.toLowerCase();
                
                let show = true;
                
                // Filter by difficulty
                if (difficultyFilter !== 'all') {{
                    if (difficultyFilter === 'null' && difficulty !== 'null') {{
                        show = false;
                    }} else if (difficultyFilter !== 'null' && difficulty !== difficultyFilter) {{
                        show = false;
                    }}
                }}
                
                // Filter by topic
                if (topicFilter !== 'all' && nodeId !== topicFilter) {{
                    show = false;
                }}
                
                // Filter by search term
                if (searchTerm && !questionContent.includes(searchTerm)) {{
                    show = false;
                }}
                
                if (show) {{
                    card.classList.remove('hidden');
                    visibleCount++;
                }} else {{
                    card.classList.add('hidden');
                }}
            }});
            
            // Update section counts (but don't hide sections here - pagination will handle visibility)
            nodeSections.forEach(section => {{
                const visibleQuestions = section.querySelectorAll('.question-card:not(.hidden)');
                const countElement = section.querySelector('.node-question-count');
                if (countElement) {{
                    countElement.textContent = `${{visibleQuestions.length}} Questions`;
                }}
            }});
            
            // Reset to first page and update pagination
            currentPage = 1;
            updatePagination();
        }}
        
        // Initialize MathJax
        if (window.MathJax?.typesetPromise) {{
            window.addEventListener('load', function() {{
                MathJax.typesetPromise().then(() => {{
                    console.log('MathJax rendering complete');
                }});
            }});
        }}
        
        // Initialize pagination on page load
        window.addEventListener('load', function() {{
            updatePagination();
        }});
    </script>
</body>
</html>'''
    
    # Save HTML file
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"✓ HTML page generated: {output_file}")
        return True
    except Exception as e:
        print(f"❌ Error generating HTML: {e}")
        return False


def copy_mathjax_script(assignments_folder):
    """Copy MathJax script to assignments folder if it exists in root"""
    mathjax_source = Path('tex-mml-chtml.js')
    mathjax_dest = assignments_folder / 'tex-mml-chtml.js'
    
    if mathjax_source.exists() and not mathjax_dest.exists():
        try:
            shutil.copy2(mathjax_source, mathjax_dest)
            print(f"✓ Copied MathJax script to assignments folder")
            return True
        except Exception as e:
            print(f"⚠ Could not copy MathJax script: {e}")
            return False
    return True


def process_class_folder(class_folder):
    """Process a single class folder"""
    folder_name = class_folder.name
    print(f"\n{'='*60}")
    print(f"Processing: {folder_name}")
    print(f"{'='*60}\n")
    
    # Extract sid and cid
    class_info = get_class_info_from_folder(folder_name)
    if not class_info:
        print(f"❌ Could not extract sid/cid from folder name: {folder_name}")
        print(f"   Expected format: 'Class Name [sid-XXX-cid-YYY]'")
        return False
    
    sid = class_info['sid']
    cid = class_info['cid']
    print(f"✓ Extracted SID: {sid}, CID: {cid}")
    
    # Load cookies
    cookies = load_cookies()
    if not cookies:
        print("❌ Cannot proceed without cookies")
        return False
    
    # Get subject tree children
    print("\n📡 Fetching subject tree children...")
    nodes = get_subject_tree_children(sid, cookies)
    
    if not nodes:
        print("❌ No nodes found in subject tree")
        return False
    
    # Get questions for each node
    print("\n📡 Fetching questions for each node...")
    nodes_data = []
    for node in nodes:
        print(f"\n  Fetching questions for: {node['name']} (ID: {node['id']})")
        questions = get_questions_for_node(sid, cid, node['id'], cookies)
        nodes_data.append({
            'id': node['id'],
            'name': node['name'],
            'questions': questions
        })
    
    # Generate HTML
    print("\n📄 Generating HTML page...")
    assignments_folder = class_folder / 'assignments'
    assignments_folder.mkdir(exist_ok=True)
    
    # Copy MathJax script if needed
    copy_mathjax_script(assignments_folder)
    
    output_file = assignments_folder / 'Question assignment.html'
    
    if generate_assessment_html(class_info['name'], sid, cid, nodes_data, output_file):
        print(f"\n✓ Successfully created assessment page for {folder_name}")
        return True
    else:
        print(f"\n❌ Failed to create assessment page for {folder_name}")
        return False


def main():
    print("="*60)
    print("Assessment Page Generator")
    print("="*60)
    
    if not DOWNLOADS_DIR.exists():
        print(f"❌ Downloads directory not found: {DOWNLOADS_DIR}")
        return
    
    # Get all class folders
    class_folders = [f for f in DOWNLOADS_DIR.iterdir() if f.is_dir()]
    
    if not class_folders:
        print("❌ No class folders found in downloads directory")
        return
    
    print(f"\n📁 Found {len(class_folders)} class folder(s)\n")
    
    successful = 0
    failed = 0
    
    for class_folder in class_folders:
        try:
            if process_class_folder(class_folder):
                successful += 1
            else:
                failed += 1
        except Exception as e:
            print(f"\n❌ Error processing {class_folder.name}: {e}")
            failed += 1
    
    print("\n" + "="*60)
    print("📊 FINAL SUMMARY")
    print("="*60)
    print(f"✓ Successfully processed: {successful}/{len(class_folders)} classes")
    print(f"❌ Failed: {failed}/{len(class_folders)} classes")
    print("="*60)


if __name__ == "__main__":
    main()

