from datetime import datetime
import requests
import time

GH_ACCESS_TOKEN = '<gh-access-token>'
GH_REPO_ID = '1181927'

GL_ACCESS_TOKEN = '<gl-access-token>'
GL_NAMESPACE = 'bitcoin'
GL_API_BASE = "https://gitlab.sighash.org/api/v4/"

headers = {
    'Content-Type': 'application/json',
    'PRIVATE-TOKEN': GL_ACCESS_TOKEN,
}

import_data = {
    'personal_access_token': GH_ACCESS_TOKEN,
    'repo_id': GH_REPO_ID,
    'target_namespace': GL_NAMESPACE,
    'optional_stages': {
        'single_endpoint_issue_events_import': True,
        'single_endpoint_notes_import': True,
        'attachments_import': False,
        'collaborators_import': False,
    },
}


def check_import_status(gl_project_id):
    while True:
        status_url = f"{GL_API_BASE}projects/{gl_project_id}/import"
        response = requests.get(status_url, headers=headers)
        if response.status_code == 200:
            status = response.json().get('import_status')
            if status == "finished":
                print("Import finished.")
                break
            elif status == "failed":
                print("Import failed with response:", response.json())
                break
            elif status == "started":
                # Wait for 10 minutes, then check import status again
                time.sleep(600)
            else:
                print("ERROR: Unexpected import status:", status)
                exit(1)
        else:
            print("ERROR: Failed to get import status:", response.status_code)
            exit(1)


def delete_project(gl_project_id):
    delete_url = f"{GL_API_BASE}projects/{gl_project_id}"
    response = requests.delete(delete_url, headers=headers)
    return response.status_code


def download_export(gl_project_id):
    export_url = f"{GL_API_BASE}projects/{gl_project_id}/export/download"
    response = requests.get(export_url, headers=headers, stream=True)
    if response.status_code == 200:
        content_disposition = response.headers.get('Content-Disposition')
        if content_disposition:
            filename = content_disposition.split('filename=')[-1].strip('"')
        else:
            filename = "gitlab_backup.tar.gz"

        date_prefix = datetime.now().strftime('%Y-%m-%d_')
        filename_with_date = f"{date_prefix}{filename}"

        with open(filename_with_date, 'wb') as file:
            for chunk in response.iter_content(chunk_size=8192):
                file.write(chunk)
        print(f"Exported backup saved to {filename}")
    else:
        print(f"ERROR: Failed to download export with status code: \
              {response.status_code}")
        exit(1)


while True:
    import_url = f"{GL_API_BASE}import/github"
    import_response = requests.post(import_url,
                                    json=import_data,
                                    headers=headers)

    if import_response.status_code == 200:
        gl_id = import_response.json().get('id')
        print(f"New import started (ID {gl_id}).")

        check_import_status(gl_id)

        delete_status_code = delete_project(gl_id)

        if delete_status_code == 200 or delete_status_code == 204:
            print("Project deleted.")
        else:
            print(f"ERROR: Project deletion failed: {delete_status_code}")
            exit(1)
    else:
        print(f"ERROR: Project import could not be started: \
              {import_response.status_code}")
        exit(1)

    download_export(gl_id)

    time.sleep(60)
