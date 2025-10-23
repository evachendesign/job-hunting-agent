import os
import json
from typing import List, Dict, Any, Optional

import requests
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from openai import OpenAI


load_dotenv()

DEFAULT_JOBS_URL = "https://www.google.com/about/careers/applications/jobs/results"

firecrawl_api_key = os.getenv("FIRECRAWL_API_KEY")
if not firecrawl_api_key:
    raise RuntimeError("FIRECRAWL_API_KEY is not set")

openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    raise RuntimeError("OPENAI_API_KEY is not set")

client = OpenAI(api_key=openai_api_key)


class ApplyRequest(BaseModel):
    resume: str
    jobs_page_url: Optional[str] = None
    max_jobs: int = Field(default=30, ge=1, le=100)


class ApplyResponse(BaseModel):
    apply_links: List[str]
    extracted_data: List[Dict[str, Any]]
    recommended_jobs: List[Dict[str, Any]]


app = FastAPI(title="Job Hunt Agent API")


def _parse_json_object(text: str) -> Optional[Dict[str, Any]]:
    try:
        return json.loads(text)
    except Exception:
        pass
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except Exception:
            return None
    return None


def _parse_json_array(text: str) -> Optional[List[Any]]:
    try:
        return json.loads(text)
    except Exception:
        pass
    start = text.find("[")
    end = text.rfind("]")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except Exception:
            return None
    return None


def _scrape_markdown(url: str) -> str:
    response = requests.post(
        "https://api.firecrawl.dev/v1/scrape",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {firecrawl_api_key}",
        },
        json={"url": url, "formats": ["markdown"]},
        timeout=60,
    )
    if response.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Firecrawl error {response.status_code}: {response.text}")
    payload = response.json()
    if not payload.get("success"):
        raise HTTPException(status_code=502, detail=payload.get("message", "Firecrawl scrape failed"))
    return payload["data"]["markdown"]


def _extract_apply_links(markdown: str, max_jobs: int) -> List[str]:
    prompt = f"""
    Extract up to {max_jobs} job application links from the given markdown content.
    Return the result as a JSON object with a single key 'apply_links' containing an array of strings (the links).
    The output should be a valid JSON object, with no additional text.
    Do not include any JSON markdown formatting or code block indicators.
    Provide only the raw JSON object as the response.

    Example of the expected format:
    {{"apply_links": ["https://example.com/job1", "https://example.com/job2", ...]}}

    Markdown content:
    {markdown[:100000]}
    """
    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
    )
    content = (completion.choices[0].message.content or "").strip()
    obj = _parse_json_object(content)
    if not obj or "apply_links" not in obj or not isinstance(obj["apply_links"], list):
        raise HTTPException(status_code=502, detail="Failed to extract apply links from model output")
    links = [link for link in obj["apply_links"] if isinstance(link, str)]
    return links[:max_jobs]


def _scrape_job_details(link: str) -> Optional[Dict[str, Any]]:
    try:
        response = requests.post(
            "https://api.firecrawl.dev/v1/scrape",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {firecrawl_api_key}",
            },
            json={
                "url": link,
                "formats": ["extract"],
                "actions": [{"type": "click", "selector": "#job-overview"}],
                "extract": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "job_title": {"type": "string"},
                            "sub_division_of_organization": {"type": "string"},
                            "key_skills": {"type": "array", "items": {"type": "string"}},
                            "compensation": {"type": "string"},
                            "location": {"type": "string"},
                            "apply_link": {"type": "string"},
                        },
                        "required": [
                            "job_title",
                            "sub_division_of_organization",
                            "key_skills",
                            "compensation",
                            "location",
                            "apply_link",
                        ],
                    }
                },
            },
            timeout=120,
        )
        if response.status_code != 200:
            return None
        payload = response.json()
        if not payload.get("success"):
            return None
        return payload["data"]["extract"]
    except Exception:
        return None


def _recommend_jobs(resume: str, extracted_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    prompt = f"""
    Please analyze the resume and job listings, and return a JSON list of the top 3 roles that best fit the candidate's experience and skills. Include only the job title, compensation, and apply link for each recommended role. The output should be a valid JSON array of objects in the following format, with no additional text:

    [
      {{
        "job_title": "Job Title",
        "compensation": "Compensation (if available, otherwise empty string)",
        "apply_link": "Application URL"
      }},
      ...
    ]

    Based on the following resume:
    {resume}

    And the following job listings:
    {json.dumps(extracted_data, indent=2)}
    """
    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
    )
    raw = (completion.choices[0].message.content or "").strip()
    arr = _parse_json_array(raw)
    if not isinstance(arr, list):
        return []
    return [item for item in arr if isinstance(item, dict)]


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/apply", response_model=ApplyResponse)
def apply(request: ApplyRequest) -> ApplyResponse:
    jobs_page_url = request.jobs_page_url or DEFAULT_JOBS_URL
    markdown = _scrape_markdown(jobs_page_url)
    apply_links = _extract_apply_links(markdown, request.max_jobs)

    extracted_data: List[Dict[str, Any]] = []
    for link in apply_links:
        details = _scrape_job_details(link)
        if details:
            extracted_data.append(details)

    recommended_jobs = _recommend_jobs(request.resume, extracted_data)

    return ApplyResponse(
        apply_links=apply_links,
        extracted_data=extracted_data,
        recommended_jobs=recommended_jobs,
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)


