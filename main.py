from flask import Flask, request, jsonify, send_file, abort
import os
import json
import base64
import requests

app = Flask(__name__)

SITES_DIR = 'sites'
os.makedirs(SITES_DIR, exist_ok=True)

GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN')
REPO_OWNER = 'LambWebRemastered'  # Replace with your GitHub org or username
REPO_NAME = 'API'  # Replace with your repository name
BRANCH = 'main'

def upload_to_github(filepath, filename):
    if not GITHUB_TOKEN:
        return 'error', 'Missing GITHUB_TOKEN environment variable.'

    api_url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/sites/{filename}"

    with open(filepath, 'rb') as f:
        content = base64.b64encode(f.read()).decode('utf-8')

    get_response = requests.get(api_url, headers={
        'Authorization': f'token {GITHUB_TOKEN}',
        'Accept': 'application/vnd.github.v3+json'
    })

    sha = None
    if get_response.status_code == 200:
        sha = get_response.json().get('sha')

    payload = {
        'message': f'Upload {filename}',
        'content': content,
        'branch': BRANCH
    }

    if sha:
        payload['sha'] = sha

    put_response = requests.put(api_url, headers={
        'Authorization': f'token {GITHUB_TOKEN}',
        'Accept': 'application/vnd.github.v3+json'
    }, json=payload)

    if put_response.status_code in [200, 201]:
        return 'success', put_response.json()
    else:
        return 'error', put_response.json()

@app.route('/save_site', methods=['POST'])
def save_website_site():
    data = request.get_json()
    if data is None or 'domain' not in data:
        return jsonify({'error': 'Invalid site data or missing domain'}), 400

    domain = data['domain']
    filename = f"{domain}.json"
    filepath = os.path.join(SITES_DIR, filename)

    with open(filepath, 'w') as site_file:
        json.dump(data, site_file)

    status, result = upload_to_github(filepath, filename)
    return jsonify({'message': 'Site saved', 'filename': filename, 'upload_status': status, 'upload_result': result}), 201

@app.route('/get_site/<name_tld>', methods=['GET'])
def get_website_site(name_tld):
    filename = f"{name_tld}.json"
    filepath = os.path.join(SITES_DIR, filename)
    if not os.path.exists(filepath):
        return abort(404, description="Site not found")
    return send_file(filepath, mimetype='application/json')

@app.route('/search_domains', methods=['GET'])
def search_domains():
    query = request.args.get('query', '')
    matching_domains = []

    for site_filename in os.listdir(SITES_DIR):
        if query.lower() in site_filename.lower():
            domain = site_filename.rsplit('.', 1)[0]
            matching_domains.append(domain)

    return jsonify({'query': query, 'matching_domains': matching_domains})

@app.route('/search_by_owner', methods=['GET'])
def search_by_owner():
    owner_value = request.args.get('owner', '')
    matching_domains = []

    for site_filename in os.listdir(SITES_DIR):
        filepath = os.path.join(SITES_DIR, site_filename)
        with open(filepath, 'r') as site_file:
            site_data = json.load(site_file)
            info = site_data.get('Info', {})
            if info.get('owner', '').lower() == owner_value.lower():
                domain = site_filename.rsplit('.', 1)[0]
                matching_domains.append(domain)

    return jsonify({'owner': owner_value, 'matching_domains': matching_domains})

@app.route('/delete_site', methods=['POST', 'GET'])
def delete_website_site():
    site = request.args.get('site', '')
    if not site:
        return jsonify({'error': 'Site parameter is missing'}), 400

    filename = f"{site}.json"
    filepath = os.path.join(SITES_DIR, filename)

    if not os.path.exists(filepath):
        return abort(404, description="Site not found")

    os.remove(filepath)
    return jsonify({'message': f'Site {site} deleted successfully.'})

def sync_all_sites_to_github():
    uploaded = []
    for site_filename in os.listdir(SITES_DIR):
        if not site_filename.endswith('.json'):
            continue
        filepath = os.path.join(SITES_DIR, site_filename)
        status, result = upload_to_github(filepath, site_filename)
        uploaded.append({
            'filename': site_filename,
            'status': status,
            'result': result
        })
    return uploaded

@app.route('/sync_all', methods=['POST'])
def sync_all():
    results = sync_all_sites_to_github()
    return jsonify({'synced': results})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
