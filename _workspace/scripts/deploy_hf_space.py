"""
One-shot HF Space deploy for credit-universe-api.
- Generates LOGIN/SESSION secrets
- Uploads _hf_space/ folder to the Space
- Registers Space secrets via HfApi
- Prints credentials ONCE at the end (caller must record them)

Usage:
    HF_TOKEN=hf_xxx /opt/anaconda3/bin/python3 deploy_hf_space.py \\
        --repo TheLoves/CreditUniverse \\
        --folder /path/to/_hf_space
"""
from __future__ import annotations

import argparse
import os
import secrets
import sys
import time

from huggingface_hub import HfApi, upload_folder


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--repo", required=True, help="HF Space repo_id, e.g. TheLoves/CreditUniverse")
    p.add_argument("--folder", required=True, help="Local _hf_space directory")
    args = p.parse_args()

    token = os.environ.get("HF_TOKEN")
    if not token:
        print("ERR: HF_TOKEN env var not set", file=sys.stderr)
        return 2

    login_username = "creditrisk_" + secrets.token_urlsafe(6)
    login_password = secrets.token_urlsafe(24)
    session_secret = secrets.token_urlsafe(32)

    api = HfApi(token=token)

    # Sanity — verify token + space access
    print(f"[1/4] Verifying access to {args.repo} ...", flush=True)
    info = api.space_info(repo_id=args.repo)
    print(f"      OK — sdk={info.sdk}, private={info.private}")

    # Upload
    print(f"[2/4] Uploading {args.folder} (this may take 5-15 min for ~317MB) ...", flush=True)
    t0 = time.time()
    upload_folder(
        folder_path=args.folder,
        repo_id=args.repo,
        repo_type="space",
        token=token,
        commit_message="Initial deploy: backend + 22-row dataset baked-in",
    )
    print(f"      uploaded in {time.time()-t0:.1f}s")

    # Secrets
    print("[3/4] Setting Space secrets ...", flush=True)
    for k, v in (
        ("LOGIN_USERNAME", login_username),
        ("LOGIN_PASSWORD", login_password),
        ("SESSION_SECRET", session_secret),
    ):
        api.add_space_secret(repo_id=args.repo, key=k, value=v)
        print(f"      set {k}")

    # Restart Space so secrets become effective on first build
    print("[4/4] Restarting Space ...", flush=True)
    api.restart_space(repo_id=args.repo)

    # Final report — record these immediately
    print("\n" + "=" * 60)
    print("CREDENTIALS — record these now (will not be shown again)")
    print("=" * 60)
    print(f"LOGIN_USERNAME = {login_username}")
    print(f"LOGIN_PASSWORD = {login_password}")
    print(f"SESSION_SECRET = {session_secret}")
    print("=" * 60)
    print(f"\nSpace URL:     https://huggingface.co/spaces/{args.repo}")
    print(f"Direct URL:    https://{args.repo.replace('/', '-').lower()}.hf.space")
    print(f"Healthcheck:   https://{args.repo.replace('/', '-').lower()}.hf.space/api/healthz")
    print("\nBuild status:  https://huggingface.co/spaces/" + args.repo + " → 'Logs' tab")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
