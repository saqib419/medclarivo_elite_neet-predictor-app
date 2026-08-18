from openai import OpenAI
import os
from pathlib import Path

client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=os.environ["NVIDIA_API_KEY"]
)

PROJECT_ROOT = Path.cwd()

IGNORE_DIRS = {
    "node_modules",
    ".git",
    ".next",
    "dist",
    "build",
    "__pycache__",
    ".venv",
    "venv"
}

IGNORE_FILES = {
    ".env",
    ".env.local",
    ".env.production",
    ".env.development",
    "package-lock.json"
}


def safe_path(filename):
    path = (PROJECT_ROOT / filename).resolve()

    try:
        path.relative_to(PROJECT_ROOT.resolve())
    except ValueError:
        return None

    return path


def is_safe(path):
    if not path.is_file():
        return False

    relative = path.relative_to(PROJECT_ROOT)

    if any(part in IGNORE_DIRS for part in relative.parts):
        return False

    if path.name in IGNORE_FILES:
        return False

    return True


def read_file(filename):
    path = safe_path(filename)

    if path is None:
        print("Access denied.")
        return

    if not path.exists():
        print(f"File not found: {filename}")
        return

    if not is_safe(path):
        print("Access denied: protected file.")
        return

    try:
        content = path.read_text(errors="ignore")
        print(f"\n===== {filename} =====\n")
        print(content)
        print("\n===== END FILE =====\n")
    except Exception as e:
        print("Could not read file:", e)


def search_project(keyword):
    keyword = keyword.lower()
    found = []

    for path in PROJECT_ROOT.rglob("*"):

        if not is_safe(path):
            continue

        try:
            content = path.read_text(errors="ignore")
        except Exception:
            continue

        if keyword in content.lower():
            found.append(path.relative_to(PROJECT_ROOT))

    if not found:
        print("No matching files found.")
        return

    for path in found:
        print(path)


def collect_files(filenames):
    context = []

    for filename in filenames:

        path = safe_path(filename)

        if path is None or not path.exists() or not is_safe(path):
            continue

        try:
            content = path.read_text(errors="ignore")
        except Exception:
            continue

        # Prevent accidentally sending enormous files.
        if len(content) > 40000:
            content = content[:40000] + "\n...[FILE TRUNCATED]..."

        context.append(
            f"\n===== FILE: {filename} =====\n"
            f"{content}\n"
            f"===== END FILE: {filename} =====\n"
        )

    return "\n".join(context)


def ask_nemotron(question, filenames):

    print("\nReading requested files...\n")

    context = collect_files(filenames)

    if not context:
        print("No readable project files were supplied.")
        return

    system_prompt = """
You are a senior software engineer debugging a real project.

The user has supplied the actual source files below.

IMPORTANT:

- Analyze ONLY the supplied source code.
- Do not invent files, functions, APIs, or behavior.
- Do not claim a file is missing if its contents are supplied.
- Do not give generic debugging advice.
- Clearly distinguish confirmed evidence from hypotheses.
- Do not modify files.
- Do not claim you executed the application.

When investigating a bug, trace the actual code flow and identify the most likely root cause.

Give:
1. Root cause
2. Evidence
3. Exact code path
4. Contributing issues
5. Exact recommended fix
6. Files that need changing
7. How to test the fix
"""

    user_prompt = f"""
USER REQUEST:

{question}

THE ACTUAL PROJECT FILES:

{context}

Analyze these files and answer the request using the actual code.
"""

    print("Sending the selected files to Nemotron...\n")

    try:
        response = client.chat.completions.create(
            model="nvidia/nemotron-3-super-120b-a12b",
            messages=[
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": user_prompt
                }
            ],
            max_tokens=6000
        )

        print("\n================ NEMOTRON ================\n")
        print(response.choices[0].message.content)
        print("\n===========================================\n")

    except Exception as e:
        print("\nNemotron request failed:")
        print(e)


print("======================================")
print("       Nemotron MedClarivo Agent")
print("======================================")
print()
print("Commands:")
print("  read <file>")
print("  search <keyword>")
print("  debug <question>")
print("  exit")
print()

while True:

    try:
        command = input("You: ").strip()

    except KeyboardInterrupt:
        print("\nExiting...")
        break

    if not command:
        continue

    if command.lower() == "exit":
        break

    if command.lower().startswith("read "):
        filename = command[5:].strip()
        read_file(filename)
        continue

    if command.lower().startswith("search "):
        keyword = command[7:].strip()
        search_project(keyword)
        continue

    if command.lower().startswith("debug "):

        question = command[6:].strip()

        files = [
            "src/pages/CollegesBrowse.jsx",
            "src/lib/api.js",
            "src/components/CollegeRow.jsx",
            "api/colleges.js",
            "api/colleges/[slug].js",
            "src/lib/predictor.js"
        ]

        ask_nemotron(question, files)
        continue

    print("Unknown command.")
    print("Use: read <file>, search <keyword>, debug <question>, or exit.")
