###### Start Safe Header ######
# Developed by: Tomer Malka Pinto
# Purpose: Mirror Bitbucket Explicit Individual Repo Permissions Only
# date: 12/08/2026
# version: 2.6.0
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
    print(f"  {Fore.GREEN}{Style.BRIGHT}Version:{Style.RESET_ALL}      2.6.0 (Strict Permission Matching)")
    print(Fore.CYAN + Style.BRIGHT + border + "\n")

def get_bitbucket_token():
    token = os.getenv("BITBUCKET_TOKEN")
    if not token:
        print(f"{Fore.RED}Error: BITBUCKET_TOKEN is not set in environment or .env file.")
        sys.exit(1)
    return token

def get_interactive_inputs():
    workspace = os.getenv("BITBUCKET_WORKSPACE")
    if not workspace:
        workspace = input("Enter Workspace Slug: ").strip()

    source_user = input("Enter Source User (Username, Email, or UUID): ").strip()
    target_user = input("Enter Target User (Username, Email, or UUID): ").strip()

    if not workspace or not source_user or not target_user:
        print(f"{Fore.RED}Error: Workspace, Source User, and Target User are all required.")
        sys.exit(1)

    return workspace.strip(), source_user, target_user

def get_user_uuid(user_identifier, workspace, headers):
    user_identifier = user_identifier.strip()

    if user_identifier.startswith("{") and user_identifier.endswith("}"):
        return user_identifier

    raw_term = user_identifier.split("@")[0].lower() if "@" in user_identifier else user_identifier.lower()
    clean_term = raw_term.replace(".", " ").replace("_", " ").replace("-", " ")
    search_parts = [p for p in clean_term.split() if len(p) > 1]

    print(f"{Fore.CYAN}Searching workspace '{workspace}' members for '{user_identifier}'...")

    url = f"https://api.bitbucket.org/2.0/workspaces/{workspace}/members"
    all_members = []

    while url:
        res = requests.get(url, headers=headers)
        if res.status_code == 200:
            data = res.json()
            for member in data.get("values", []):
                user = member.get("user", {})
                display_name = user.get("display_name", "")
                nickname = user.get("nickname", "")
                uuid = user.get("uuid", "")

                if not uuid:
                    continue

                all_members.append({"name": display_name, "nickname": nickname, "uuid": uuid})
                d_lower = display_name.lower()
                n_lower = nickname.lower()

                if raw_term in [d_lower, n_lower] or clean_term in [d_lower, n_lower]:
                    print(f"  {Fore.GREEN}✔ Matched user:{Style.RESET_ALL} {display_name} ({uuid})")
                    return uuid

                if search_parts and all(part in d_lower or part in n_lower for part in search_parts):
                    print(f"  {Fore.GREEN}✔ Matched user:{Style.RESET_ALL} {display_name} ({uuid})")
                    return uuid

            url = data.get("next")
        else:
            break

    url = f"https://api.bitbucket.org/2.0/users/{user_identifier}"
    res = requests.get(url, headers=headers)
    if res.status_code == 200:
        return res.json().get("uuid")

    print(f"\n{Fore.RED}Error: Could not resolve '{user_identifier}' in workspace '{workspace}'.")
    if all_members:
        print(f"\n{Fore.YELLOW}Available members in workspace '{workspace}':")
        for m in all_members[:15]:
            print(f"  • Name: {Fore.WHITE}{m['name']}{Style.RESET_ALL} | Handle/Nickname: {Fore.CYAN}{m['nickname']}{Style.RESET_ALL}")
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

def get_explicit_permission(workspace, repo_slug, source_uuid, headers):
    # Keep curly braces intact in UUID as required by Bitbucket REST API
    url = f"https://api.bitbucket.org/2.0/repositories/{workspace}/{repo_slug}/permissions-config/users/{source_uuid}"
    res = requests.get(url, headers=headers)
    
    if res.status_code == 200:
        perm = res.json().get("permission")
        # Only treat actual permission levels ('read', 'write', 'admin') as valid access
        if perm and str(perm).lower() in ["read", "write", "admin"]:
            return str(perm).lower()
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
    source_uuid = get_user_uuid(source_user, workspace, headers)
    target_uuid = get_user_uuid(target_user, workspace, headers)

    print(f"\n{Fore.CYAN}Fetching all repositories in workspace '{workspace}'...")
    repos = get_workspace_repositories(workspace, headers)

    if not repos:
        print(f"{Fore.YELLOW}No repositories found in workspace '{workspace}'.")
        return

    print(f"{Fore.CYAN}Found {len(repos)} total repositories. Scanning for EXPLICIT direct permissions...\n")

    pending_mirrors = []

    for idx, repo in enumerate(repos, 1):
        repo_name = repo.get("name", repo["slug"])
        repo_slug = repo["slug"]

        permission = get_explicit_permission(workspace, repo_slug, source_uuid, headers)

        if permission:
            print(f"[{idx}/{len(repos)}] {Fore.GREEN}✔ Explicit Access Found:{Style.RESET_ALL} {repo_name} ({permission.upper()})")
            pending_mirrors.append({"slug": repo_slug, "name": repo_name, "permission": permission})
        else:
            print(f"[{idx}/{len(repos)}] {Fore.LIGHTBLACK_EX}• Skipped (No direct permission / Inherited via Group){Style.RESET_ALL}: {repo_name}")

    # ==========================================
    # POST-SCAN SUMMARY & DRY-RUN PREVIEW
    # ==========================================
    print("\n" + Fore.CYAN + "=" * 70)
    print(Fore.YELLOW + Style.BRIGHT + "               SCAN COMPLETE & REPOSITORY MIRROR SUMMARY")
    print(Fore.CYAN + "=" * 70)
    print(f" Total Repositories Scanned : {Fore.WHITE}{len(repos)}{Style.RESET_ALL}")
    print(f" Explicit Permissions Found : {Fore.GREEN}{len(pending_mirrors)}{Style.RESET_ALL}")
    print(Fore.CYAN + "-" * 70)

    if not pending_mirrors:
        print(f"{Fore.YELLOW}No explicit individual permissions found for source user in workspace '{workspace}'. Nothing to mirror.\n")
        return

    print(f"\nThe following {len(pending_mirrors)} repository/repositories will be granted to target user '{target_user}':\n")
    for idx, item in enumerate(pending_mirrors, 1):
        print(f"  {idx:2d}. {Fore.GREEN}{item['name']:<40}{Style.RESET_ALL} ({item['slug']}) -> Permission: {Fore.MAGENTA}{item['permission'].upper()}{Style.RESET_ALL}")

    print("\n" + Fore.CYAN + "=" * 70 + "\n")

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