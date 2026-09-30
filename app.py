import os
import re
import sys
from flask import Flask, jsonify, request, Response, stream_with_context
import json

app = Flask(__name__, static_url_path='/static', static_folder='static')

def resolve_path(raw: str) -> str:
    """Accept absolute paths OR paths relative to home dir."""
    raw = raw.strip()
    if os.path.isabs(raw):
        return raw
    return os.path.expanduser(os.path.join('~', raw))

# ─── Pages ────────────────────────────────────────────────────────────────────
@app.route('/')
def index():
    return app.send_static_file('makepad_real.html')

# ─── File Tree ────────────────────────────────────────────────────────────────
@app.route('/api/tree')
def get_tree():
    raw  = request.args.get('path', '')
    full = resolve_path(raw) if raw else os.path.expanduser('~')

    if not os.path.exists(full):
        return jsonify({'error': f'Path not found: {full}'}), 404

    items = []
    try:
        for entry in sorted(os.scandir(full), key=lambda e: (not e.is_dir(), e.name.lower())):
            if entry.name.startswith('.'):
                continue
            items.append({'name': entry.name, 'path': entry.path, 'is_dir': entry.is_dir()})
    except PermissionError as e:
        return jsonify({'error': str(e)}), 403

    return jsonify(items)

# ─── File Read / Write ────────────────────────────────────────────────────────
@app.route('/api/file', methods=['GET', 'POST'])
def file_ops():
    if request.method == 'POST':
        data    = request.json or {}
        path    = data.get('path', '')
        content = data.get('content', '')
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            return jsonify({'success': True})
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    else:
        path = request.args.get('path', '')
        if not os.path.isfile(path):
            return jsonify({'error': 'File not found'}), 404
        try:
            with open(path, 'r', encoding='utf-8', errors='replace') as f:
                return jsonify({'content': f.read()})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

# ─── Architecture Scanner (streaming progress) ────────────────────────────────
@app.route('/api/architecture')
def get_architecture():
    raw       = request.args.get('path', '')
    root_path = resolve_path(raw)

    if not os.path.isdir(root_path):
        return jsonify({'error': f'Directory not found: {root_path}'}), 404

    def stream():
        nodes      = []
        class_info = {}

        # Regex patterns
        class_pat  = re.compile(r'(?:public|protected|private)?\s*(?:abstract\s+)?(?:class|interface|record|enum)\s+(\w+)')
        ann_pat    = re.compile(r'@(RestController|Controller|Service|Repository|Component|Entity|Configuration|Mapper|FeignClient|EventListener)')
        field_pat  = re.compile(r'(?:private|protected|public)\s+(?:(?:static|final)\s+)*([A-Z]\w+)(?:<[^>]+>)?\s+\w+\s*[;=]')
        ctor_pat   = re.compile(r'([A-Z]\w+)\s+\w+\s*[,)]')
        autowired_pat = re.compile(r'@(?:Autowired|Inject)\s+(?:private\s+)?([A-Z]\w+)')

        # Collect all java files first
        java_files = []
        for root, dirs, files in os.walk(root_path):
            # Skip build/target dirs
            dirs[:] = [d for d in dirs if d not in ('target', 'build', '.git', 'node_modules', '.idea', 'out')]
            for f in files:
                if f.endswith('.java'):
                    java_files.append(os.path.join(root, f))

        total = len(java_files)
        yield f"data: {json.dumps({'progress': 0, 'total': total, 'message': f'Found {total} Java files...'})}\n\n"

        # Pass 1: Discover classes
        for idx, filepath in enumerate(java_files):
            try:
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                class_match = class_pat.search(content)
                if not class_match:
                    continue

                class_name = class_match.group(1)

                # Determine group
                group = 'Other'
                ann_match = ann_pat.search(content)
                if ann_match:
                    ann = ann_match.group(1)
                    group_map = {
                        'RestController': 'Controller', 'Controller': 'Controller',
                        'Service': 'Service', 'Repository': 'Repository',
                        'Entity': 'Entity', 'Configuration': 'Configuration',
                        'Component': 'Component', 'Mapper': 'Mapper',
                        'FeignClient': 'FeignClient', 'EventListener': 'EventListener'
                    }
                    group = group_map.get(ann, 'Other')
                else:
                    n = class_name
                    if any(x in n for x in ('DTO','Dto','Request','Response','Model')):
                        group = 'DTO'
                    elif 'Exception' in n or 'Error' in n:
                        group = 'Exception'
                    elif 'Util' in n or 'Helper' in n or 'Constants' in n:
                        group = 'Util'
                    elif 'Test' in n:
                        group = 'Test'

                package_match = re.search(r'^package\s+([\w.]+);', content, re.MULTILINE)
                package = package_match.group(1) if package_match else ''

                class_info[class_name] = {'filepath': filepath, 'group': group, 'content': content, 'package': package}
                nodes.append({
                    'id': class_name, 'label': class_name,
                    'title': filepath, 'group': group,
                    'content': content, 'package': package,
                    'filepath': filepath
                })

            except Exception:
                continue

            if idx % 10 == 0:
                yield f"data: {json.dumps({'progress': idx+1, 'total': total, 'message': f'Scanning... ({idx+1}/{total})'})}\n\n"

        # Pass 2: Build dependency edges
        edges = []
        yield f"data: {json.dumps({'progress': total, 'total': total, 'message': 'Building dependency graph...'})}\n\n"

        for class_name, info in class_info.items():
            content = info['content']
            deps = set()
            deps.update(field_pat.findall(content))
            deps.update(ctor_pat.findall(content))
            deps.update(autowired_pat.findall(content))

            for dep in deps:
                if dep in class_info and dep != class_name:
                    edges.append({'from': class_name, 'to': dep, 'arrows': 'to'})

        # Final payload
        yield f"data: {json.dumps({'done': True, 'nodes': nodes, 'edges': edges})}\n\n"

    return Response(stream_with_context(stream()), mimetype='text/event-stream',
                    headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})

if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
    print(f"\n🚀  Spring Canvas IDE running at  http://127.0.0.1:{port}\n")
    app.run(debug=False, port=port, threaded=True)
