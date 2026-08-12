###### Start Safe Header ######
# Developed by: Tomer Malka Pinto
# Purpose: Automate Bitbucket Repositories copying flow
# date: 12/08/2026
# version: 1.0.0
###### End Safe Header ########

import os
import sys
from colorama import Fore, Style, init
import pyfiglet
import requests

init(autoreset=True)

def Visual_start_script():
    figlet = pyfiglet.Figlet(font="slant")
    big_title = figlet.renderText("Bitbucket Copy Repositories Script")
    border = "=" * 70

    print(Fore.CYAN + Style.BRIGHT + border)
    print(Fore.GREEN + Style.BRIGHT + big_title)
    print(Fore.CYAN + Style.BRIGHT + border)

    # Developer details
    print(
        f"  {Fore.GREEN}{Style.BRIGHT}Developed by:{Style.RESET_ALL} Tomer Malka Pinto"
    )
    print(f"  {Fore.GREEN}{Style.BRIGHT}Version:{Style.RESET_ALL}      1.0.0")
    print(Fore.CYAN + Style.BRIGHT + border + "\n")

Visual_start_script()

def get_bitbucket_token():
    """Get an access token for Bitbucket API."""
    token = os.getenv("BITBUCKET_TOKEN")
    if not token:
        print(f"{Fore.RED}Error: BITBUCKET_TOKEN environment variable is not set.")
        sys.exit(1)
    return token

def get_users_from_input():
    source_user = input("Enter Source User (username or UUID): ").strip()
    target_user = input("Enter Target User (username or UUID): ").strip()

    if not source_user or not target_user:
        print(f"{Fore.RED}Error: Both source and target users are required.")
        sys.exit(1)

    return source_user, target_user

def get_user_uuid(user_identifier, headers):
    """Fetch the target user's UUID given a username or UUID."""
    url = f"https://api.bitbucket.org/2.0/users/{user_identifier}"
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        user_data = response.json()
        return user_data.get("uuid")
    else:
        print(f"{Fore.RED}Error: Unable to fetch user UUID for {user_identifier}.")
        sys.exit(1)

def get_repositories(user_uuid, headers):
    """Fetch all repositories for a given user UUID."""
    url = f"https://api.bitbucket.org/2.0/repositories/{user_uuid}"
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        repos_data = response.json()
        return repos_data.get("values", [])
    else:
        print(f"{Fore.RED}Error: Unable to fetch repositories for user UUID {user_uuid}.")
        sys.exit(1) 

def copy_repository(source_repo, target_user_uuid, headers):
    """Copy a repository from the source user to the target user."""
    repo_name = source_repo.get("name")
    source_repo_slug = source_repo.get("slug")
    source_repo_owner = source_repo.get("owner", {}).get("username")

    # Construct the URL for copying the repository
    copy_url = f"https://api.bitbucket.org/2.0/repositories/{target_user_uuid}/{repo_name}"

    # Prepare the payload for copying
    payload = {
        "scm": source_repo.get("scm"),
        "is_private": source_repo.get("is_private"),
        "fork_policy": source_repo.get("fork_policy"),
        "description": source_repo.get("description"),
        "has_issues": source_repo.get("has_issues"),
        "has_wiki": source_repo.get("has_wiki"),
        "language": source_repo.get("language"),
        "mainbranch": {"name": source_repo.get("mainbranch", {}).get("name")},
    }

    response = requests.post(copy_url, json=payload, headers=headers)

    if response.status_code == 201:
        print(f"{Fore.GREEN}Successfully copied repository '{repo_name}' to target user.")
    else:
        print(f"{Fore.RED}Error: Failed to copy repository '{repo_name}'. Status Code: {response.status_code}")

def main():
    bitbucket_token = get_bitbucket_token()
    headers = {"Authorization": f"Bearer {bitbucket_token}"}

    source_user, target_user = get_users_from_input()

    source_user_uuid = get_user_uuid(source_user, headers)
    target_user_uuid = get_user_uuid(target_user, headers)

    repositories = get_repositories(source_user_uuid, headers)

    if not repositories:
        print(f"{Fore.YELLOW}No repositories found for source user '{source_user}'.")
        return

    for repo in repositories:
        copy_repository(repo, target_user_uuid, headers)

if __name__ == "__main__":
    main()

