import json
import os
import subprocess
import sys


def main() -> int:
    url = os.getenv("API_URL", "http://localhost:8000/apply")

    sample_resume = (
        "Eva Chen — Product Designer, 4 years designing mobile and web apps. "
        "Experience: T-Mobile (account management redesign, Manage tab), Currents AI (AI platform), "
        "GM (chatbot, internal tools), Indeed (profile guidance system), UM Hospital (safety report system)."
    )

    payload = {
        "resume": sample_resume,
        # Omit jobs_page_url to use API default
        "max_jobs": 5,
    }

    cmd = [
        "curl",
        "-s",
        "-X",
        "POST",
        url,
        "-H",
        "Content-Type: application/json",
        "-d",
        json.dumps(payload),
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    except FileNotFoundError:
        print("curl not found. Please install curl or run the request manually.", file=sys.stderr)
        return 1

    if result.returncode != 0:
        print(result.stderr or "Request failed", file=sys.stderr)
        return result.returncode

    # Print raw response from API
    print(result.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


