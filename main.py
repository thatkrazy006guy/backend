import os
import json, re, pysrt, uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from github import Github

app = FastAPI()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO_NAME = "thatkrazy006guy/purestream-filters"
INDEX_PATH = "filters/index.json"

class ReportRequest(BaseModel):
    tmdb_id: int
    media_type: str
    title: str
    season: int = None
    episode: int = None

def generate_csv(srt_text):
    subs = pysrt.from_string(srt_text)
    lines = ["start_time,end_time,keyword,category"]
    pattern = re.compile(r"\b(fuck|shit|bitch|asshole)\b", re.IGNORECASE)
    
    for sub in subs:
        match = pattern.search(sub.text)
        if match:
            start = f"{sub.start.hours:02d}:{sub.start.minutes:02d}:{sub.start.seconds:02d}.{sub.start.milliseconds:03d}"
            end = f"{sub.end.hours:02d}:{sub.end.minutes:02d}:{sub.end.seconds:02d}.{sub.end.milliseconds:03d}"
            lines.append(f"{start},{end},{match.group(0).lower()},profanity")
    return "\n".join(lines)

@app.post("/api/report-title")
def report_title(req: ReportRequest):
    item_key = f"{req.media_type}_{req.tmdb_id}" + (f"_s{req.season}e{req.episode}" if req.media_type == "tv" else "")
    csv_path = f"filters/{req.media_type}/{item_key}.csv"
    
    gh = Github(GITHUB_TOKEN)
    repo = gh.get_repo(REPO_NAME)
    
    # Check for duplicates
    index_file = repo.get_contents(INDEX_PATH)
    index_data = json.loads(index_file.decoded_content.decode("utf-8"))
    
    if item_key in index_data:
        return {"status": "exists", "csv_url": index_data[item_key]["csv_url"]}

    # Mock Subtitle Fetching (Replace with actual OpenSubtitles API call)
    srt_text = "1\n00:01:20,000 --> 00:01:23,500\nWhat the fuck are you doing?"
    csv_content = generate_csv(srt_text)

    # Commit new CSV
    repo.create_file(csv_path, f"Add {req.title}", csv_content, branch="main")

    # Update Index
    csv_url = f"https://raw.githubusercontent.com/{REPO_NAME}/main/{csv_path}"
    index_data[item_key] = {"title": req.title, "csv_url": csv_url}
    repo.update_file(INDEX_PATH, f"Index {req.title}", json.dumps(index_data, indent=2), index_file.sha, branch="main")

    return {"status": "created", "csv_url": csv_url}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)