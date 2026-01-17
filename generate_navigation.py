"""
Generate HTML Navigation Page for MHTML Files
Scans the downloads folder and creates an interactive navigation page
"""

import os
import json
from pathlib import Path
from datetime import datetime

DOWNLOADS_DIR = Path('downloads')
OUTPUT_HTML = 'navigation.html'


def scan_mhtml_files():
    """Scan downloads folder and build file hierarchy"""
    print("Scanning downloads folder for all content files...")
    
    if not DOWNLOADS_DIR.exists():
        print(f"[ERROR] Downloads directory not found: {DOWNLOADS_DIR}")
        return {}
    
    # Structure: {class_name: {tab: {topic: [files]}}}
    hierarchy = {}
    total_files = 0
    file_types = {'mhtml': 0, 'html': 0, 'json': 0, 'other': 0}
    
    # Scan each class folder
    for class_folder in sorted(DOWNLOADS_DIR.iterdir()):
        if not class_folder.is_dir():
            continue
        
        class_name = class_folder.name
        print(f"  [+] Scanning: {class_name}")
        
        hierarchy[class_name] = {}
        
        # Scan tabs (overview, assignments, book, practice, etc.)
        for tab_folder in sorted(class_folder.iterdir()):
            if not tab_folder.is_dir():
                continue
            
            tab_name = tab_folder.name
            hierarchy[class_name][tab_name] = {}
            
            # Check if this is assignments folder (different structure)
            if tab_name == 'assignments':
                # Assignments folder has files directly, not in subfolders
                files_list = []
                
                # Scan for HTML and MHTML files (skip JSON)
                for file_path in sorted(tab_folder.iterdir()):
                    if file_path.is_file():
                        ext = file_path.suffix.lower().lstrip('.')
                        if ext in ['html', 'mhtml']:  # Removed 'json'
                            file_info = {
                                'name': file_path.name,
                                'path': str(file_path.relative_to(DOWNLOADS_DIR)),
                                'size': file_path.stat().st_size,
                                'modified': datetime.fromtimestamp(file_path.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
                                'type': ext
                            }
                            files_list.append(file_info)
                            total_files += 1
                            file_types[ext] = file_types.get(ext, 0) + 1
                
                # Store files directly without "Files" topic wrapper
                if files_list:
                    hierarchy[class_name][tab_name] = files_list
            else:
                # Regular tabs (overview, book, etc.) have topic subfolders
                # Scan topics within each tab
                for topic_folder in sorted(tab_folder.iterdir()):
                    if not topic_folder.is_dir():
                        continue
                    
                    topic_name = topic_folder.name
                    
                    # Find all content files in this topic
                    files_list = []
                    
                    # Scan for MHTML and HTML files (skip JSON)
                    for pattern in ['*.mhtml', '*.html']:  # Removed '*.json'
                        for file_path in sorted(topic_folder.glob(pattern)):
                            ext = file_path.suffix.lower().lstrip('.')
                            file_info = {
                                'name': file_path.name,
                                'path': str(file_path.relative_to(DOWNLOADS_DIR)),
                                'size': file_path.stat().st_size,
                                'modified': datetime.fromtimestamp(file_path.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
                                'type': ext
                            }
                            files_list.append(file_info)
                            total_files += 1
                            file_types[ext] = file_types.get(ext, 0) + 1
                    
                    if files_list:
                        hierarchy[class_name][tab_name][topic_name] = files_list
            
            # Remove empty tabs
            if not hierarchy[class_name][tab_name]:
                del hierarchy[class_name][tab_name]
        
        # Remove empty classes
        if not hierarchy[class_name]:
            del hierarchy[class_name]
    
    print(f"\n[OK] Found {total_files} total files")
    print(f"  - MHTML files: {file_types.get('mhtml', 0)}")
    print(f"  - HTML files: {file_types.get('html', 0)}")
    print(f"[OK] Found {len(hierarchy)} classes\n")
    
    return hierarchy


def format_file_size(size_bytes):
    """Format file size in human-readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"


def generate_html(hierarchy):
    """Generate HTML navigation page"""
    print("Generating HTML navigation page...")
    
    # Count totals
    total_classes = len(hierarchy)
    total_files = 0
    for class_data in hierarchy.values():
        for tab_data in class_data.values():
            if isinstance(tab_data, list):
                # Assignments: files directly
                total_files += len(tab_data)
            else:
                # Overview/other tabs: topics with files
                for files in tab_data.values():
                    total_files += len(files)
    
    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Kognity Content Navigation</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}
        
        .header {{
            background: white;
            border-radius: 12px;
            padding: 30px;
            margin-bottom: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        
        .header h1 {{
            color: #2d3748;
            font-size: 32px;
            margin-bottom: 10px;
        }}
        
        .header p {{
            color: #718096;
            font-size: 16px;
        }}
        
        .stats {{
            display: flex;
            gap: 20px;
            margin-top: 20px;
        }}
        
        .stat {{
            background: #f7fafc;
            padding: 15px 25px;
            border-radius: 8px;
            border-left: 4px solid #667eea;
        }}
        
        .stat-label {{
            color: #718096;
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        
        .stat-value {{
            color: #2d3748;
            font-size: 24px;
            font-weight: bold;
            margin-top: 5px;
        }}
        
        .search-bar {{
            background: white;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        
        .search-input {{
            width: 100%;
            padding: 15px 20px;
            border: 2px solid #e2e8f0;
            border-radius: 8px;
            font-size: 16px;
            transition: all 0.3s;
        }}
        
        .search-input:focus {{
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }}
        
        .content {{
            background: white;
            border-radius: 12px;
            padding: 30px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        
        .class-section {{
            margin-bottom: 40px;
        }}
        
        .class-header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px 25px;
            border-radius: 8px;
            cursor: pointer;
            display: flex;
            justify-content: space-between;
            align-items: center;
            transition: transform 0.2s;
        }}
        
        .class-header:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
        }}
        
        .class-title {{
            font-size: 20px;
            font-weight: 600;
        }}
        
        .class-badge {{
            background: rgba(255,255,255,0.2);
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 14px;
        }}
        
        .class-content {{
            padding: 20px 0;
        }}
        
        .tab-section {{
            margin-bottom: 25px;
            border-left: 3px solid #e2e8f0;
            padding-left: 20px;
        }}
        
        .tab-header {{
            font-size: 18px;
            font-weight: 600;
            color: #4a5568;
            text-transform: capitalize;
            margin-bottom: 15px;
            padding: 12px 15px;
            background: #f7fafc;
            border-radius: 6px;
            cursor: pointer;
            display: flex;
            justify-content: space-between;
            align-items: center;
            transition: all 0.2s;
        }}
        
        .tab-header:hover {{
            background: #edf2f7;
            transform: translateX(3px);
        }}
        
        .tab-content {{
            padding-top: 15px;
        }}
        
        .topic-section {{
            margin-bottom: 20px;
        }}
        
        .topic-header {{
            font-size: 16px;
            font-weight: 600;
            color: #2d3748;
            padding: 10px 15px;
            background: #f7fafc;
            border-radius: 6px;
            cursor: pointer;
            display: flex;
            justify-content: space-between;
            align-items: center;
            transition: all 0.2s;
            border-left: 3px solid #667eea;
        }}
        
        .topic-header:hover {{
            background: #edf2f7;
            border-left-color: #764ba2;
        }}
        
        .topic-content {{
            padding-top: 10px;
        }}
        
        .toggle-icon-small {{
            color: #667eea;
            font-size: 12px;
            transition: transform 0.3s;
        }}
        
        .toggle-icon-small.open {{
            transform: rotate(90deg);
        }}
        
        .file-list {{
            list-style: none;
            padding-left: 20px;
        }}
        
        .file-item {{
            padding: 12px 15px;
            margin: 5px 0;
            background: white;
            border: 1px solid #e2e8f0;
            border-radius: 6px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            transition: all 0.2s;
        }}
        
        .file-item:hover {{
            background: #f7fafc;
            border-color: #667eea;
            transform: translateX(5px);
        }}
        
        .file-link {{
            color: #2d3748;
            text-decoration: none;
            flex: 1;
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        
        .file-icon {{
            color: #667eea;
            font-size: 20px;
        }}
        
        .file-name {{
            flex: 1;
        }}
        
        .file-meta {{
            display: flex;
            gap: 15px;
            font-size: 12px;
            color: #718096;
        }}
        
        .toggle-icon {{
            transition: transform 0.3s;
        }}
        
        .toggle-icon.open {{
            transform: rotate(90deg);
        }}
        
        .collapsed {{
            display: none;
        }}
        
        .no-results {{
            text-align: center;
            padding: 60px 20px;
            color: #718096;
        }}
        
        .no-results-icon {{
            font-size: 64px;
            margin-bottom: 20px;
        }}
        
        @media (max-width: 768px) {{
            .stats {{
                flex-direction: column;
            }}
            
            .file-meta {{
                flex-direction: column;
                gap: 5px;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📚 Kognity Content Navigation</h1>
            <p>Browse and access all your downloaded content (Overview & Assignments)</p>
            <div class="stats">
                <div class="stat">
                    <div class="stat-label">Total Classes</div>
                    <div class="stat-value">{total_classes}</div>
                </div>
                <div class="stat">
                    <div class="stat-label">Total Files</div>
                    <div class="stat-value">{total_files}</div>
                </div>
                <div class="stat">
                    <div class="stat-label">Generated</div>
                    <div class="stat-value">{datetime.now().strftime('%Y-%m-%d')}</div>
                </div>
            </div>
        </div>
        
        <div class="search-bar">
            <input type="text" class="search-input" id="searchInput" placeholder="🔍 Search for classes, topics, or files...">
        </div>
        
        <div class="content" id="content">
'''
    
    # Generate hierarchy
    for class_name, class_data in hierarchy.items():
        # Count files in this class
        file_count = 0
        for tab_data in class_data.values():
            if isinstance(tab_data, list):
                file_count += len(tab_data)
            else:
                for files in tab_data.values():
                    file_count += len(files)
        
        html += f'''
            <div class="class-section" data-class-name="{class_name.lower()}">
                <div class="class-header" onclick="toggleClass(this)">
                    <div class="class-title">{class_name}</div>
                    <div class="class-badge">{file_count} files</div>
                    <span class="toggle-icon">▶</span>
                </div>
                <div class="class-content collapsed">
'''
        
        for tab_name, tab_data in class_data.items():
            # Check if tab_data is a list (files directly, like assignments) or dict (topics with files)
            if isinstance(tab_data, list):
                # Assignments: files directly without topics
                files = tab_data
                tab_file_count = len(files)
                html += f'''
                    <div class="tab-section">
                        <div class="tab-header" onclick="toggleSection(this)">
                            <div>📂 {tab_name} <span style="color: #718096; font-size: 14px; font-weight: normal;">({tab_file_count} files)</span></div>
                            <span class="toggle-icon-small">▶</span>
                        </div>
                        <div class="tab-content collapsed">
                            <ul class="file-list">
'''
                
                for file_info in files:
                    file_path = file_info['path'].replace('\\', '/')
                    file_size = format_file_size(file_info['size'])
                    file_type = file_info.get('type', 'mhtml')
                    
                    # Choose icon based on file type
                    if file_type == 'html':
                        icon = '🌐'
                    else:  # mhtml
                        icon = '📄'
                    
                    html += f'''
                                <li class="file-item" data-file-name="{file_info['name'].lower()}">
                                    <a href="downloads/{file_path}" class="file-link" target="_blank">
                                        <span class="file-icon">{icon}</span>
                                        <span class="file-name">{file_info['name']}</span>
                                    </a>
                                    <div class="file-meta">
                                        <span>{file_size}</span>
                                        <span>{file_info['modified']}</span>
                                    </div>
                                </li>
'''
                
                html += '''
                            </ul>
                        </div>
                    </div>
'''
            else:
                # Overview and other tabs: topics with files
                tab_file_count = sum(len(files) for files in tab_data.values())
                html += f'''
                    <div class="tab-section">
                        <div class="tab-header" onclick="toggleSection(this)">
                            <div>📂 {tab_name} <span style="color: #718096; font-size: 14px; font-weight: normal;">({tab_file_count} files)</span></div>
                            <span class="toggle-icon-small">▶</span>
                        </div>
                        <div class="tab-content collapsed">
'''
            
                for topic_name, files in tab_data.items():
                    html += f'''
                            <div class="topic-section" data-topic-name="{topic_name.lower()}">
                                <div class="topic-header" onclick="toggleSection(this)">
                                    <div>{topic_name} <span style="color: #718096; font-size: 13px; font-weight: normal;">({len(files)} files)</span></div>
                                    <span class="toggle-icon-small">▶</span>
                                </div>
                                <div class="topic-content collapsed">
                                    <ul class="file-list">
'''
                    
                    for file_info in files:
                        file_path = file_info['path'].replace('\\', '/')
                        file_size = format_file_size(file_info['size'])
                        file_type = file_info.get('type', 'mhtml')
                        
                        # Choose icon based on file type
                        if file_type == 'html':
                            icon = '🌐'
                        else:  # mhtml
                            icon = '📄'
                        
                        html += f'''
                                <li class="file-item" data-file-name="{file_info['name'].lower()}">
                                    <a href="downloads/{file_path}" class="file-link" target="_blank">
                                        <span class="file-icon">{icon}</span>
                                        <span class="file-name">{file_info['name']}</span>
                                    </a>
                                    <div class="file-meta">
                                        <span>{file_size}</span>
                                        <span>{file_info['modified']}</span>
                                    </div>
                                </li>
'''
                    
                    html += '''
                                    </ul>
                                </div>
                            </div>
'''
            
                html += '''
                        </div>
                    </div>
'''
        
        html += '''
                </div>
            </div>
'''
    
    html += '''
        </div>
    </div>
    
    <script>
        function toggleClass(header) {
            const content = header.nextElementSibling;
            const icon = header.querySelector('.toggle-icon');
            
            content.classList.toggle('collapsed');
            icon.classList.toggle('open');
        }
        
        function toggleSection(header) {
            const content = header.nextElementSibling;
            const icon = header.querySelector('.toggle-icon-small');
            
            content.classList.toggle('collapsed');
            icon.classList.toggle('open');
        }
        
        // Search functionality
        const searchInput = document.getElementById('searchInput');
        const contentDiv = document.getElementById('content');
        
        searchInput.addEventListener('input', function(e) {
            const searchTerm = e.target.value.toLowerCase().trim();
            
            if (!searchTerm) {
                // Show all
                document.querySelectorAll('.class-section').forEach(section => {
                    section.style.display = 'block';
                });
                document.querySelectorAll('.tab-section, .topic-section, .file-item').forEach(el => {
                    el.style.display = '';
                });
                
                // Collapse all classes, tabs, and topics
                document.querySelectorAll('.class-content, .tab-content, .topic-content').forEach(content => {
                    content.classList.add('collapsed');
                });
                document.querySelectorAll('.toggle-icon, .toggle-icon-small').forEach(icon => {
                    icon.classList.remove('open');
                });
                
                return;
            }
            
            let hasResults = false;
            
            // Search through all class sections
            document.querySelectorAll('.class-section').forEach(classSection => {
                const className = classSection.dataset.className || '';
                let classHasMatch = className.includes(searchTerm);
                let classHasVisibleContent = false;
                
                // Check tabs
                classSection.querySelectorAll('.tab-section').forEach(tabSection => {
                    let tabHasVisibleContent = false;
                    
                    // Check if tab has topics (overview) or files directly (assignments)
                    const topicSections = tabSection.querySelectorAll('.topic-section');
                    const directFiles = tabSection.querySelectorAll('.tab-content > .file-list > .file-item');
                    
                    if (topicSections.length > 0) {
                        // Tab has topics (overview)
                        topicSections.forEach(topicSection => {
                            const topicName = topicSection.dataset.topicName || '';
                            let topicHasMatch = topicName.includes(searchTerm);
                            let topicHasVisibleFiles = false;
                            
                            // Check files
                            topicSection.querySelectorAll('.file-item').forEach(fileItem => {
                                const fileName = fileItem.dataset.fileName || '';
                                const matches = fileName.includes(searchTerm) || topicHasMatch || classHasMatch;
                                
                                if (matches) {
                                    fileItem.style.display = '';
                                    topicHasVisibleFiles = true;
                                } else {
                                    fileItem.style.display = 'none';
                                }
                            });
                            
                            if (topicHasVisibleFiles) {
                                topicSection.style.display = '';
                                tabHasVisibleContent = true;
                            } else {
                                topicSection.style.display = 'none';
                            }
                        });
                    } else if (directFiles.length > 0) {
                        // Tab has files directly (assignments)
                        directFiles.forEach(fileItem => {
                            const fileName = fileItem.dataset.fileName || '';
                            const matches = fileName.includes(searchTerm) || classHasMatch;
                            
                            if (matches) {
                                fileItem.style.display = '';
                                tabHasVisibleContent = true;
                            } else {
                                fileItem.style.display = 'none';
                            }
                        });
                    }
                    
                    if (tabHasVisibleContent) {
                        tabSection.style.display = '';
                        classHasVisibleContent = true;
                    } else {
                        tabSection.style.display = 'none';
                    }
                });
                
                if (classHasVisibleContent) {
                    classSection.style.display = 'block';
                    // Expand the class to show results
                    const classContent = classSection.querySelector('.class-content');
                    const classIcon = classSection.querySelector('.toggle-icon');
                    classContent.classList.remove('collapsed');
                    classIcon.classList.add('open');
                    
                    // Also expand all visible tabs and topics
                    classSection.querySelectorAll('.tab-section').forEach(tab => {
                        if (tab.style.display !== 'none') {
                            const tabContent = tab.querySelector('.tab-content');
                            const tabIcon = tab.querySelector('.toggle-icon-small');
                            if (tabContent && tabIcon) {
                                tabContent.classList.remove('collapsed');
                                tabIcon.classList.add('open');
                            }
                        }
                    });
                    
                    classSection.querySelectorAll('.topic-section').forEach(topic => {
                        if (topic.style.display !== 'none') {
                            const topicContent = topic.querySelector('.topic-content');
                            const topicIcon = topic.querySelector('.toggle-icon-small');
                            if (topicContent && topicIcon) {
                                topicContent.classList.remove('collapsed');
                                topicIcon.classList.add('open');
                            }
                        }
                    });
                    
                    hasResults = true;
                } else {
                    classSection.style.display = 'none';
                }
            });
            
            // Show no results message
            if (!hasResults) {
                if (!document.getElementById('noResults')) {
                    const noResults = document.createElement('div');
                    noResults.id = 'noResults';
                    noResults.className = 'no-results';
                    noResults.innerHTML = `
                        <div class="no-results-icon">🔍</div>
                        <h2>No results found</h2>
                        <p>Try a different search term</p>
                    `;
                    contentDiv.appendChild(noResults);
                }
            } else {
                const noResults = document.getElementById('noResults');
                if (noResults) {
                    noResults.remove();
                }
            }
        });
    </script>
</body>
</html>
'''
    
    return html


def main():
    print("="*60)
    print("MHTML Navigation Generator")
    print("="*60)
    print()
    
    # Scan files
    hierarchy = scan_mhtml_files()
    
    if not hierarchy:
        print("[ERROR] No files found in downloads folder")
        return
    
    # Generate HTML
    html_content = generate_html(hierarchy)
    
    # Save HTML file
    try:
        with open(OUTPUT_HTML, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"[OK] Generated navigation page: {OUTPUT_HTML}")
        print(f"\n[INFO] Open {OUTPUT_HTML} in your browser to view all files")
        print(f"[INFO] Full path: {os.path.abspath(OUTPUT_HTML)}")
        
    except Exception as e:
        print(f"[ERROR] Error saving HTML file: {e}")
        return
    
    print("\n" + "="*60)


if __name__ == "__main__":
    main()

