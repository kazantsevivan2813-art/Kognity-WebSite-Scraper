import os
import re
from pathlib import Path

def get_class_overview_structure(class_path):
    """Get the overview structure for a class"""
    overview_path = os.path.join(class_path, 'overview')
    
    if not os.path.exists(overview_path):
        return None
    
    folders = []
    total_files = 0
    
    for folder_name in sorted(os.listdir(overview_path)):
        folder_path = os.path.join(overview_path, folder_name)
        if os.path.isdir(folder_path):
            files = []
            for file_name in sorted(os.listdir(folder_path)):
                if file_name.endswith('.mhtml'):
                    abs_path = os.path.abspath(os.path.join(folder_path, file_name))
                    file_url = 'file:///' + abs_path.replace('\\', '/')
                    
                    # Extract section number and title
                    match = re.match(r'^(\d+\.\d+),_(.+)\.mhtml$', file_name)
                    if match:
                        section_num = match.group(1)
                        title = match.group(2).replace('_', ' ')
                        files.append({
                            'section': section_num,
                            'title': title,
                            'url': file_url,
                            'filename': file_name
                        })
                        total_files += 1
            
            if files:
                folders.append({
                    'name': folder_name,
                    'files': files
                })
    
    return {'folders': folders, 'total_files': total_files}

def create_overview_navigation_html():
    """Create an HTML navigation page matching navigation.html style"""
    
    # Collect all class data
    all_classes = []
    total_classes = 0
    total_sections = 0
    total_files = 0
    
    base_dirs = ['downloads']
    
    for base_dir in base_dirs:
        if not os.path.exists(base_dir):
            continue
        
        for class_name in sorted(os.listdir(base_dir)):
            class_path = os.path.join(base_dir, class_name)
            if os.path.isdir(class_path):
                structure = get_class_overview_structure(class_path)
                
                if structure:
                    total_classes += 1
                    total_sections += len(structure['folders'])
                    total_files += structure['total_files']
                    
                    all_classes.append({
                        'name': class_name,
                        'base_dir': base_dir,
                        'folders': structure['folders'],
                        'file_count': structure['total_files']
                    })
    
    # Generate HTML
    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>IB DP Section Navigation</title>
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
            flex-wrap: wrap;
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
            display: none;
        }}
        
        .class-content.active {{
            display: block;
        }}
        
        .folder-section {{
            margin-bottom: 25px;
            border-left: 3px solid #e2e8f0;
            padding-left: 20px;
        }}
        
        .folder-header {{
            font-size: 18px;
            font-weight: 600;
            color: #4a5568;
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
        
        .folder-header:hover {{
            background: #edf2f7;
            transform: translateX(3px);
        }}
        
        .folder-content {{
            padding-top: 15px;
            display: none;
        }}
        
        .folder-content.active {{
            display: block;
        }}
        
        .file-list {{
            list-style: none;
            padding: 0;
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
        
        .section-badge {{
            background: #667eea;
            color: white;
            padding: 4px 10px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: bold;
        }}
        
        .toggle-icon {{
            color: white;
            font-size: 16px;
            transition: transform 0.3s;
        }}
        
        .toggle-icon.open {{
            transform: rotate(90deg);
        }}
        
        .toggle-icon-small {{
            color: #667eea;
            font-size: 12px;
            transition: transform 0.3s;
        }}
        
        .toggle-icon-small.open {{
            transform: rotate(90deg);
        }}
        
        .hidden {{
            display: none;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📚 IB DP Course Section Navigation</h1>
            <p>Browse all your course materials organized by sections</p>
            <div class="stats">
                <div class="stat">
                    <div class="stat-label">Courses</div>
                    <div class="stat-value">{total_classes}</div>
                </div>
                <div class="stat">
                    <div class="stat-label">Sections</div>
                    <div class="stat-value">{total_sections}</div>
                </div>
                <div class="stat">
                    <div class="stat-label">Files</div>
                    <div class="stat-value">{total_files}</div>
                </div>
            </div>
        </div>
        
        <div class="content" id="content">
'''
    
    # Add each class
    for cls in all_classes:
        class_id = cls['name'].replace(' ', '_').replace('[', '').replace(']', '')
        html += f'''
            <div class="class-section" data-class-name="{cls['name'].lower()}">
                <div class="class-header" onclick="toggleClass('{class_id}')">
                    <div>
                        <div class="class-title">{cls['name']}</div>
                    </div>
                    <div style="display: flex; gap: 15px; align-items: center;">
                        <span class="class-badge">{cls['file_count']} files</span>
                        <span class="toggle-icon" id="toggle-{class_id}">▶</span>
                    </div>
                </div>
                <div class="class-content" id="class-{class_id}">
'''
        
        # Add folders
        for folder in cls['folders']:
            folder_id = f"{class_id}_{folder['name'].replace(' ', '_').replace('[', '').replace(']', '')}"
            
            # Extract folder section number (e.g., "0 Introduction" -> "0")
            folder_match = re.match(r'^(\d+)\s+', folder['name'])
            folder_section = folder_match.group(1) if folder_match else folder['name']
            folder_display = f"Section {folder_section}"
            
            html += f'''
                    <div class="folder-section">
                        <div class="folder-header" onclick="toggleFolder('{folder_id}')">
                            <span>{folder_display}</span>
                            <div style="display: flex; gap: 10px; align-items: center;">
                                <span style="color: #718096; font-size: 14px;">{len(folder['files'])} files</span>
                                <span class="toggle-icon-small" id="toggle-{folder_id}">▶</span>
                            </div>
                        </div>
                        <div class="folder-content" id="folder-{folder_id}">
                            <ul class="file-list">
'''
            
            # Add files
            for file in folder['files']:
                file_display = f"Section {file['section']}"
                html += f'''
                                <li class="file-item" data-search="{file['section']} section">
                                    <a href="{file['url']}" class="file-link" target="_blank">
                                        <span class="file-icon">📄</span>
                                        <span class="file-name">{file_display}</span>
                                    </a>
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
    
    # Add JavaScript and close HTML
    html += '''
        </div>
    </div>
    
    <script>
        function toggleClass(classId) {
            const content = document.getElementById('class-' + classId);
            const icon = document.getElementById('toggle-' + classId);
            
            content.classList.toggle('active');
            icon.classList.toggle('open');
        }
        
        function toggleFolder(folderId) {
            const content = document.getElementById('folder-' + folderId);
            const icon = document.getElementById('toggle-' + folderId);
            
            content.classList.toggle('active');
            icon.classList.toggle('open');
        }
        
        // Search functionality
        const searchInput = document.getElementById('searchInput');
        searchInput.addEventListener('input', function(e) {
            const searchTerm = e.target.value.toLowerCase();
            const classSections = document.querySelectorAll('.class-section');
            
            classSections.forEach(section => {
                const className = section.getAttribute('data-class-name');
                const fileItems = section.querySelectorAll('.file-item');
                let hasVisibleFiles = false;
                
                fileItems.forEach(item => {
                    const searchData = item.getAttribute('data-search');
                    if (searchData.includes(searchTerm) || className.includes(searchTerm)) {
                        item.style.display = 'flex';
                        hasVisibleFiles = true;
                    } else {
                        item.style.display = 'none';
                    }
                });
                
                // Show/hide entire class section based on matches
                if (hasVisibleFiles || searchTerm === '') {
                    section.style.display = 'block';
                } else {
                    section.style.display = 'none';
                }
                
                // Auto-expand sections when searching
                if (searchTerm !== '' && hasVisibleFiles) {
                    const classContent = section.querySelector('.class-content');
                    const folderContents = section.querySelectorAll('.folder-content');
                    classContent.classList.add('active');
                    folderContents.forEach(fc => fc.classList.add('active'));
                    
                    const classIcon = section.querySelector('.toggle-icon');
                    const folderIcons = section.querySelectorAll('.toggle-icon-small');
                    if (classIcon) classIcon.classList.add('open');
                    folderIcons.forEach(fi => fi.classList.add('open'));
                }
            });
        });
    </script>
</body>
</html>
'''
    
    return html

def main():
    """Generate the navigation HTML file"""
    
    print("="*70)
    print("CREATING OVERVIEW NAVIGATION PAGE")
    print("="*70)
    print()
    
    html_content = create_overview_navigation_html()
    
    output_file = 'section_navigation.html'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    abs_path = os.path.abspath(output_file)
    print(f"[SUCCESS] Navigation file created: {output_file}")
    print(f"  Full path: {abs_path}")
    print()
    print("Open this file in your browser to navigate all IB courses!")

if __name__ == '__main__':
    main()

