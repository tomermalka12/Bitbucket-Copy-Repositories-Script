###### Start Safe Header ######
# Developed by: Tomer Malka Pinto
# Purpose: Mirror Bitbucket Repository Permissions with Dry-Run Confirmation Step
# date: 12/08/2026
# version: 1.6.0
###### End Safe Header ########

import os
import sys
import requests
from colorama import Fore, Style, init
import pyfiglet
from dotenv import load_dotenv

load_dotenv()
init(autoreset=True)

def visual_start_script():
    figlet = pyfiglet.Figlet(font="slant")
    big_title = figlet.renderText("Bitbucket Copy Repositories Script")
    border = "=" * 70

    print(Fore.CYAN + Style.BRIGHT + border)
    print(Fore.GREEN + Style.BRIGHT + big_title)
    print(Fore.CYAN + Style.BRIGHT + border)

    print(f"  {Fore.GREEN}{Style.BRIGHT}Developed by:{Style.RESET_ALL} Tomer Malka Pinto")
    print(f"  {Fore.GREEN}{Style.BRIGHT}Version:{Style.RESET_ALL}      1.6.0")
    print(Fore.CYAN + Style.BRIGHT + border + "\n")

def get_bitbucket_token():
    token = os.getenv("BITBUCKET_TOKEN")
    if not token:
        print(f"{Fore.RED}Error: BITBUCKET_TOKEN environment variable is not set.")
        sys.exit(1)
    return token

def get_interactive_inputs():
    workspace = input("Enter Workspace Slug: ").strip()
    source_user = input("Enter Source User (username or UUID): ").strip()
    target_user = input("Enter Target User (username or UUID): ").strip()

    if not workspace or not source_user or not target_user:
        print(f"{Fore.RED}Error: Workspace, Source User, and Target User are all required.")
        sys.exit(1)

    return workspace, source_user, target_user

def get_user_uuid(user_identifier, headers):
    url = f"https://api.bitbucket.org/2.0/users/{user_identifier}"
    res = requests.get(url, headers=headers)
    if res.status_code == 200:
        return res.json().get("uuid")
    
    print(f"{Fore.RED}Error fetching UUID for user '{user_identifier}': {res.status_code} - {res.text}")
    sys.exit(1)

def get_workspace_repositories(workspace, headers):
    repositories = []
    url = f"https://api.bitbucket.org/2.0/repositories/{workspace}"

    while url:
        res = requests.get(url, headers=headers)
        if res.status_code == 200:
            data = res.json()
            repositories.extend(data.get("values", []))
            url = data.get("next")
        else:
            print(f"{Fore.RED}Error fetching repositories for workspace '{workspace}': {res.status_code}")
            break

    return repositories

def get_explicit_permission(workspace, repo_slug, user_uuid, headers):
    url = f"https://api.bitbucket.org/2.0/repositories/{workspace}/{repo_slug}/permissions-config/users/{user_uuid}"
    res = requests.get(url, headers=headers)
    if res.status_code == 200:
        return res.json().get("permission")  # 'read', 'write', or 'admin'
    return None

def grant_explicit_permission(workspace, repo_slug, target_uuid, permission, headers):
    url = f"https://api.bitbucket.org/2.0/repositories/{workspace}/{repo_slug}/permissions-config/users/{target_uuid}"
    payload = {"permission": permission}
    res = requests.put(url, json=payload, headers=headers)

    if res.status_code in [200, 201]:
        print(f"  {Fore.GREEN}✔ Granted '{permission}' permission on '{repo_slug}'")
        return True
    else:
        print(f"  {Fore.RED}✖ Failed on '{repo_slug}': {res.status_code} - {res.text}")
        return False

def main():
    visual_start_script()
    token = get_bitbucket_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    workspace, source_user, target_user = get_interactive_inputs()

    print(f"\n{Fore.CYAN}Resolving user UUIDs...")
    source_uuid = get_user_uuid(source_user, headers)
    target_uuid = get_user_uuid(target_user, headers)

    print(f"{Fore.CYAN}Fetching all repositories in workspace '{workspace}'...")
    repos = get_workspace_repositories(workspace, headers)

    if not repos:
        print(f"{Fore.YELLOW}No repositories found in workspace '{workspace}'.")
        return

    print(f"{Fore.CYAN}Found {len(repos)} total repositories. Scanning permissions (Dry-Run Phase)...\n")

    pending_mirrors = []

    for idx, repo in enumerate(repos, 1):
        repo_name = repo.get("name", repo["slug"])
        repo_slug = repo["slug"]
        
        print(f"[{idx}/{len(repos)}] Checking Repository: {Fore.WHITE}{Style.BRIGHT}{repo_name}{Style.RESET_ALL} ({repo_slug})")

        permission = get_explicit_permission(workspace, repo_slug, source_uuid, headers)

        if permission:
            print(f"  {Fore.YELLOW}➜ PENDING MIRROR:{Style.RESET_ALL} Source user has '{permission}' permission")
            pending_mirrors.append({"slug": repo_slug, "name": repo_name, "permission": permission})
        else:
            print(f"  {Fore.LIGHTBLACK_EX}• Skipped (No explicit permission set for source user){Style.RESET_ALL}")

    # Display Dry-Run Summary
    print("\n" + Fore.CYAN + "=" * 70)
    print(Fore.YELLOW + Style.BRIGHT + "                     DRY-RUN PREVIEW")
    print(Fore.CYAN + "=" * 70)

    if not pending_mirrors:
        print(f"{Fore.YELLOW}No explicit permissions found for source user in this workspace. Nothing to mirror.")
        return

    print(f"{Fore.WHITE}The following {len(pending_mirrors)} repository/repositories will be updated:\n")
    for item in pending_mirrors:
        print(f"  • {Fore.GREEN}{item['name']}{Style.RESET_ALL} ({item['slug']}) -> Will grant '{Fore.MAGENTA}{item['permission']}{Style.RESET_ALL}'")

    print(Fore.CYAN + "=" * 70 + "\n")

    # Interactive Confirmation Prompt
    confirm = input(f"{Fore.CYAN}{Style.BRIGHT}Do you want to apply these permission changes to target user '{target_user}'? (y/N): {Style.RESET_ALL}").strip().lower()

    if confirm != 'y':
        print(f"\n{Fore.YELLOW}Operation canceled. No permission changes were made.")
        return

    # Execution Phase
    print(f"\n{Fore.CYAN}Applying permission changes...\n")
    successful_mirrors = []

    for item in pending_mirrors:
        print(f"Updating '{item['name']}'...")
        success = grant_explicit_permission(workspace, item['slug'], target_uuid, item['permission'], headers)
        if success:
            successful_mirrors.append(item)

    print("\n" + Fore.CYAN + "=" * 70)
    print(Fore.GREEN + Style.BRIGHT + "                     EXECUTION SUMMARY")
    print(Fore.CYAN + "=" * 70)
    print(f"{Fore.GREEN}Successfully updated {len(successful_mirrors)} of {len(pending_mirrors)} repositories.{Style.RESET_ALL}\n")

if __name__ == "__main__":
    main()


