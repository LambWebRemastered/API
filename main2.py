from flask import Flask, request, jsonify, send_file, abort
import os
import json
from github import Github
from threading import Thread
import time

app = Flask(__name__)

SITES_DIR = 'sites2'
os.makedirs(SITES_DIR, exist_ok=True)

GITHUB_REPO = "LambWebRemastered/API"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

def upload_to_github(filename, content):
    if not GITHUB_TOKEN:
        return {"upload_status": "error", "upload_result": "Missing GITHUB_TOKEN environment variable."}
    g = Github(GITHUB_TOKEN)
    repo = g.get_repo(GITHUB_REPO)
    try:
        contents = repo.get_contents(f"sites2/{filename}")
        repo.update_file(contents.path, f"Update {filename}", content, contents.sha)
    except:
        repo.create_file(f"sites/{filename}", f"Add {filename}", content)
    return {"upload_status": "success", "upload_result": f"{filename} uploaded to GitHub."}

def delete_from_github(filename):
    if not GITHUB_TOKEN:
        return {"delete_status": "error", "delete_result": "Missing GITHUB_TOKEN environment variable."}
    g = Github(GITHUB_TOKEN)
    repo = g.get_repo(GITHUB_REPO)
    try:
        contents = repo.get_contents(f"sites/{filename}")
        repo.delete_file(contents.path, f"Delete {filename}", contents.sha)
        return {"delete_status": "success", "delete_result": f"{filename} deleted from GitHub."}
    except:
        return {"delete_status": "error", "delete_result": f"{filename} not found in GitHub."}

def sync_sites_folder():
    while True:
        if GITHUB_TOKEN:
            g = Github(GITHUB_TOKEN)
            repo = g.get_repo(GITHUB_REPO)
            for filename in os.listdir(SITES_DIR):
                filepath = os.path.join(SITES_DIR, filename)
                with open(filepath, 'r') as f:
                    content = f.read()
                try:
                    contents = repo.get_contents(f"sites/{filename}")
                    repo.update_file(contents.path, f"Auto-sync update {filename}", content, contents.sha)
                except:
                    repo.create_file(f"sites/{filename}", f"Auto-sync add {filename}", content)
        time.sleep(60)

@app.route('/save_site', methods=['POST'])
def save_website_site():
    data = request.get_json()
    
    if data is None or 'Info' not in data or 'Name' not in data['Info'] or 'tld' not in data['Info']:
        return jsonify({'error': 'Invalid site data or missing Info.Name or Info.tld'}), 400
    
    domain = f"{data['Info']['Name']}{data['Info']['tld']}"
    filename = f"{domain}.json"
    filepath = os.path.join(SITES_DIR, filename)
    
    with open(filepath, 'w') as site_file:
        json.dump(data, site_file)

    with open(filepath, 'r') as f:
        content = f.read()
    
    github_result = upload_to_github(filename, content)
    return jsonify({'message': 'Site saved', 'filename': filename, **github_result}), 201

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
        domain = site_filename.rsplit('.', 1)[0]
        if query.lower() in domain.lower():
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
            if str(info.get('owner', '')).lower() == owner_value.lower():
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
    github_result = delete_from_github(filename)
    return jsonify({'message': f'Site {site} deleted successfully.', **github_result})

if __name__ == '__main__':
    Thread(target=sync_sites_folder, daemon=True).start()
    app.run(host='0.0.0.0', port=5000, debug=True)
