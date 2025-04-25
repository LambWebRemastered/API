import json
import requests
from github import Github
from base64 import b64encode
from threading import Thread
import time

app = Flask(__name__)
SITES_DIR = 'sites'
@@ -36,6 +37,22 @@ def delete_from_github(filename):
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
@@ -97,4 +114,5 @@ def delete_website_site():
return jsonify({'message': f'Site {site} deleted successfully.', **github_result})

if __name__ == '__main__':
    Thread(target=sync_sites_folder, daemon=True).start()
app.run(host='0.0.0.0', port=5000, debug=True)
