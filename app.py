import os
import re
from flask import Flask, jsonify, request, send_from_directory

app = Flask(__name__, static_url_path='/static', static_folder='static')
WORKSPACE_DIR = os.path.expanduser('~/')

@app.route('/')
def index():
    return app.send_static_file('index.html')

@app.route('/graph')
def graph_view():
    return app.send_static_file('graph.html')

@app.route('/api/tree')
def get_tree():
    path = request.args.get('path', '')
    full_path = os.path.join(WORKSPACE_DIR, path)
    
    if not os.path.exists(full_path):
        return jsonify({'error': 'Path does not exist'}), 404

    items = []
    try:
        for entry in os.scandir(full_path):
            if entry.name.startswith('.'):
                continue
            items.append({
                'name': entry.name,
                'path': os.path.relpath(entry.path, WORKSPACE_DIR),
                'is_dir': entry.is_dir()
            })
        items.sort(key=lambda x: (not x['is_dir'], x['name'].lower()))
    except Exception as e:
        return jsonify({'error': str(e)}), 500

    return jsonify(items)

@app.route('/api/file', methods=['GET', 'POST'])
def file_operations():
    if request.method == 'POST':
        path = request.json.get('path', '')
        content = request.json.get('content', '')
        full_path = os.path.join(WORKSPACE_DIR, path)
        try:
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return jsonify({'success': True})
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    else:
        path = request.args.get('path', '')
        full_path = os.path.join(WORKSPACE_DIR, path)
        if not os.path.isfile(full_path):
            return jsonify({'error': 'File not found'}), 404
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return jsonify({'content': content})
        except Exception as e:
            return jsonify({'error': str(e)}), 500


@app.route('/api/architecture')
def get_architecture():
    # Provide a path to a Spring Boot project directory (relative to WORKSPACE_DIR)
    target_dir = request.args.get('path', '') 
    root_path = os.path.join(WORKSPACE_DIR, target_dir)
    
    if not os.path.isdir(root_path):
         return jsonify({'error': 'Directory not found'}), 404
         
    nodes = []
    edges = []
    class_info = {}

    class_pattern = re.compile(r'(?:public|protected|private)?\s*(?:abstract\s+)?(?:class|interface|record)\s+(\w+)')
    annotation_pattern = re.compile(r'@(RestController|Controller|Service|Repository|Component|Entity|Configuration)')
    field_pattern = re.compile(r'(?:private|protected|public)\s+(?:final\s+)?([A-Z]\w+)(?:<.*>)?\s+\w+\s*;')
    constructor_param_pattern = re.compile(r'([A-Z]\w+)\s+\w+[,)]')

    # Pass 1: Discover classes
    for root, _, files in os.walk(root_path):
        for file in files:
            if file.endswith('.java'):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        class_match = class_pattern.search(content)
                        if class_match:
                            class_name = class_match.group(1)
                            
                            group = 'Other'
                            ann_match = annotation_pattern.search(content)
                            if ann_match:
                                ann = ann_match.group(1)
                                if ann in ['RestController', 'Controller']: group = 'Controller'
                                elif ann == 'Service': group = 'Service'
                                elif ann == 'Repository': group = 'Repository'
                                elif ann == 'Entity': group = 'Entity'
                                elif ann == 'Configuration': group = 'Configuration'
                                elif ann == 'Component': group = 'Component'
                            else:
                                if 'Dto' in class_name or 'Request' in class_name or 'Response' in class_name:
                                    group = 'DTO'
                                elif 'Exception' in class_name:
                                    group = 'Exception'
                                    
                            class_info[class_name] = {
                                'filepath': os.path.relpath(filepath, WORKSPACE_DIR),
                                'group': group,
                                'content': content
                            }
                            nodes.append({
                                'id': class_name, 
                                'label': class_name, 
                                'title': os.path.relpath(filepath, WORKSPACE_DIR),
                                'group': group,
                                'content': content
                            })
                except Exception:
                    continue

    # Pass 2: Find Dependencies
    for class_name, info in class_info.items():
        content = info['content']
        fields = field_pattern.findall(content)
        params = constructor_param_pattern.findall(content)
        
        dependencies = set(fields + params)
        for dep in dependencies:
            if dep in class_info and dep != class_name:
                edges.append({
                    'from': class_name, 
                    'to': dep,
                    'arrows': 'to'
                })
                
    return jsonify({'nodes': nodes, 'edges': edges})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
