"""
Script to push the full Attendance Management System to GitHub repository:
https://github.com/subi123-subi/Attednance_2026
"""

import sys
import os
import getpass
import dulwich.porcelain as dp

REPO_PATH = os.path.dirname(os.path.abspath(__file__))
REMOTE_REPO = "github.com/subi123-subi/Attednance_2026.git"

def main():
    print("=" * 65)
    print(" GitHub Auto-Pusher for WorkPulse Attendance System")
    print(f" Target Repository: https://{REMOTE_REPO}")
    print("=" * 65)
    
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        if len(sys.argv) > 1:
            token = sys.argv[1].strip()
        else:
            print("\nGitHub requires a Personal Access Token (PAT) for authenticated push.")
            print("To generate one: Go to https://github.com/settings/tokens -> Generate New Token (Classic) -> Check 'repo' scope.")
            token = input("\nEnter your GitHub Personal Access Token (or paste it here): ").strip()

    if not token:
        print("\n[ERROR] GitHub token cannot be empty. Aborting.")
        return

    # Construct authenticated URL
    auth_url = f"https://oauth2:{token}@{REMOTE_REPO}"
    
    print("\n1. Preparing local repository...")
    try:
        repo = dp.open_repo(REPO_PATH)
    except:
        repo = dp.init(REPO_PATH)

    dp.add(REPO_PATH)
    try:
        dp.commit(REPO_PATH, message=b"Initial commit: WorkPulse Enterprise Attendance & HR Management System")
        print("   Committed latest files.")
    except Exception as e:
        print(f"   Note on commit: {e}")

    print("\n2. Pushing to GitHub (main branch)...")
    try:
        dp.push(repo, auth_url, refspecs=b"refs/heads/master:refs/heads/main", force=True)
        print("\n[SUCCESS] Successfully pushed all project files to:")
        print(f"👉 https://github.com/subi123-subi/Attednance_2026")
    except Exception as e:
        # Fallback to master/main
        try:
            dp.push(repo, auth_url, refspecs=b"refs/heads/master:refs/heads/master", force=True)
            print("\n[SUCCESS] Successfully pushed all project files to:")
            print(f"👉 https://github.com/subi123-subi/Attednance_2026")
        except Exception as err2:
            print(f"\n[ERROR] Push failed: {e} | {err2}")
            print("\nPlease check your token has write/push permissions to repository subi123-subi/Attednance_2026.")

if __name__ == "__main__":
    main()
