import os
import subprocess
import shutil
import requests
import toml

# Get the path to the codex.toml file
script_dir = os.path.dirname(os.path.abspath(__file__))
codex_path = os.path.join(script_dir, "codex.toml")

# Load the contents of codex.toml
with open(codex_path, "r") as file:
    codex_data = toml.load(file)

# Access the sections and their lists
plugins_list = codex_data["plugins"]["list"]
scripts_list = codex_data["scripts"]["list"]
mods_list = codex_data["mods"]["list"]
apps_list = codex_data["apps"]["list"]

# Function to get the last commit date of a file in a repository
def get_last_commit_date(repo_url):
    print(f"Repository address: {repo_url}")
    parts = repo_url.split("/")
    owner = parts[3]
    repo_name = parts[4].split(".git")[0]
    branches = ["main", "master"]  # List of branches to try
    
    for branch in branches:
        api_url = f"https://api.github.com/repos/{owner}/{repo_name}/commits/{branch}"
        headers = {"Accept": "application/vnd.github.v3+json"}
        
        try:
            response = requests.get(api_url, headers=headers)
            response.raise_for_status()
            commit_data = response.json()
            last_commit_date = commit_data["commit"]["author"]["date"]
            return last_commit_date
        except requests.HTTPError as e:
            if response.status_code == 422:
                print(f"Error fetching last commit date for {repo_url}: Unprocessable Entity")
            else:
                print(f"Error fetching last commit date for {repo_url}: {e}")
        except Exception as e:
            print(f"Error fetching last commit date for {repo_url}: {e}")
    
    # If all attempts fail, return None
    return None

def get_repository_description(owner, repo_name):
    branches = ["main", "master"]  # List of branches to try
    
    for branch in branches:
        api_url = f"https://api.github.com/repos/{owner}/{repo_name}/contents/README.md?ref={branch}"
        headers = {"Accept": "application/vnd.github.v3+json"}

        try:
            response = requests.get(api_url, headers=headers)
            response.raise_for_status()
            readme_data = response.json()
            description = base64.b64decode(readme_data["content"]).decode('utf-8')
            return description.strip()
        except requests.RequestException as e:
            print(f"Error fetching repository description for {owner}/{repo_name} on branch {branch}: {e}")
        except Exception as e:
            print(f"Error fetching repository description for {owner}/{repo_name} on branch {branch}: {e}")
    
    # If all attempts fail, return None
    return None

def add_submodule(addon_path, folder_name):
    parts = addon_path.split("/")
    owner = parts[3]
    repo_name = parts[4].split(".git")[0]
    branches = ["main", "master"]  # List of branches to try
    last_commit_date = None
    description = None
    addon_name = None

    # Create the author folder if it doesn't exist
    author_folder = os.path.join(folder_name, owner)

    for branch in branches:
        # Attempt to retrieve last commit date and description for the branch
        last_commit_date = get_last_commit_date(addon_path, branch)
        description = get_repository_description(owner, repo_name)

        if last_commit_date and description:
            break  # Break the loop if both last commit date and description are successfully retrieved

    if not (last_commit_date and description):
        print(f"Failed to fetch last commit date and description for {addon_path}. Skipping...")
        return None

    # Check if the submodule already exists in the index
    submodule_path = os.path.join(author_folder, repo_name)
    if os.path.exists(submodule_path):
        print(f"Submodule {submodule_path} already exists. Skipping...")
        return {
            "path": addon_path,
            "owner": owner,
            "addon_name": addon_name,
            "repo_name": repo_name,
            "repo_path": parts[0] + "//" + parts[2] + "/" + parts[3] + "/" + parts[4],
            "branch": branch,
            "last_commit_date": last_commit_date,
            "description": description
        }

    # Check if the submodule already exists in .gitmodules
    with open(".gitmodules", "r") as gitmodules_file:
        gitmodules_content = gitmodules_file.read()
        if submodule_path in gitmodules_content:
            print(f"Submodule {submodule_path} already exists in .gitmodules. Skipping...")
            return None

    # Construct the clone URL
    clone_url = f"https://github.com/{owner}/{repo_name}.git"

    # Add the repository as a submodule within the author folder
    subprocess.run(["git", "submodule", "add", "--branch", branch, clone_url, submodule_path], cwd=os.getcwd())  # Set working directory

    return {
        "path": addon_path,
        "owner": owner,
        "addon_name": addon_name,
        "repo_name": repo_name,
        "repo_path": parts[0] + "//" + parts[2] + "/" + parts[3] + "/" + parts[4],
        "branch": branch,
        "last_commit_date": last_commit_date,
        "description": description
    }

def remove_submodules(submodules_list, folder_name):
    # Remove entries from the .gitmodules file and update the index
    for submodule_url in submodules_list:
        parts = submodule_url.split("/")
        author = parts[3]
        repo_name = parts[4].split(".git")[0]
        submodule_path = os.path.join("Plugins", author, repo_name)
        subprocess.run(["git", "config", "-f", ".gitmodules", "--remove-section", f"submodule.{submodule_path}"])
        #subprocess.run(["git", "rm", "-r", "--cached", submodule_path])

    # Stage changes to .gitmodules
    subprocess.run(["git", "add", ".gitmodules"])

    # Commit the changes to .gitmodules
    subprocess.run(["git", "commit", "-m", "Remove submodule entries from .gitmodules"])

    # Remove the submodule directories
    for submodule_url in submodules_list:
        parts = submodule_url.split("/")
        author = parts[3]
        repo_name = parts[4].split(".git")[0]
        submodule_path = os.path.join(folder_name, author, repo_name)
        if os.path.exists(submodule_path):
            try:
                shutil.rmtree(submodule_path)
            except FileNotFoundError:
                pass
        else:
            print(f"Submodule {submodule_path} does not exist. Skipping deletion...")


    # Commit the changes
    subprocess.run(["git", "add", "."])
    subprocess.run(["git", "commit", "-m", "Remove submodules"])


def main():
    subprocess.run(["git", "config", "--global", "user.email", "70115207+V0r-T3x@users.noreply.github.com"])
    subprocess.run(["git", "config", "--global", "user.name", "V0r-T3x"])

    app_info_dict = {}
    mod_info_dict = {}
    plugin_info_dict = {}
    script_info_dict = {}

    # Add plugin repositories as submodules and collect information
    for plugin_url in plugins_list:
        submodule_info = add_submodule(plugin_url, "Plugins")
        #print(submodule_info)
        owner = submodule_info['owner']
        if owner not in plugin_info_dict:
            plugin_info_dict[owner] = []
        plugin_info_dict[owner].append(submodule_info)

    # Add mod repositories as submodules and collect information
    for mod_url in mods_list:
        submodule_info = add_submodule(mod_url, "Mods")
        #print(submodule_info)
        owner = submodule_info['owner']
        if owner not in mod_info_dict:
            mod_info_dict[owner] = []
        mod_info_dict[owner].append(submodule_info)

    # Initialize and update submodules
    subprocess.run(["git", "submodule", "init"], cwd=os.getcwd())  # Set working directory
    subprocess.run(["git", "submodule", "update"], cwd=os.getcwd())  # Set working directory

    # Create a new readme.md file
    with open("readme.md", "w") as readme_file:
        # Write plugin information to readme.md
        readme_file.write("# Plugins\n")
        for owner, plugins in sorted(plugin_info_dict.items()):
            readme_file.write(f"## {owner}\n")
            for plugin_info in sorted(plugins, key=lambda x: x['repo_name']):
                readme_file.write(f"- [{plugin_info['addon_name']}]({plugin_info['path']})\n")
                readme_file.write(f"  - Last Commit Date: {plugin_info['last_commit_date']}\n")
                readme_file.write(f"  - Repository path: {plugin_info['repo_path']}\n")
                readme_file.write(f"  - Description: {plugin_info['description']}\n\n")

        # Write mod information to readme.md
        readme_file.write("# Mods\n")
        for owner, mods in sorted(mod_info_dict.items()):
            readme_file.write(f"## {owner}\n")
            for mod_info in sorted(mods, key=lambda x: x['repo_name']):
                readme_file.write(f"- [{mod_info['addon_name']}]({mod_info['path']})\n")
                readme_file.write(f"  - Last Commit Date: {mod_info['last_commit_date']}\n")
                readme_file.write(f"  - Repository path: {mod_info['repo_path']}\n")
                readme_file.write(f"  - Description: {mod_info['description']}\n\n")


    # Remove plugins submodules and author folders
    #remove_submodules(plugins_list, "Plugins")

    # Remove mods submodules and author folders
    #remove_submodules(mods_list, "Mods")

    # Commit and push changes
    subprocess.run(["git", "add", "."], cwd=os.getcwd())  # Set working directory
    subprocess.run(["git", "commit", "-m", "Add and remove submodules"], cwd=os.getcwd())  # Set working directory
    subprocess.run(["git", "push"], cwd=os.getcwd())  # Set working directory

if __name__ == "__main__":
    main()
