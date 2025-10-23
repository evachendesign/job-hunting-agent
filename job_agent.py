# %%
# %%
import os
import requests
import json
from dotenv import load_dotenv
from openai import OpenAI

# ANSI color codes
class Colors:
    CYAN = '\033[96m'
    YELLOW = '\033[93m'
    GREEN = '\033[92m'
    RED = '\033[91m'
    MAGENTA = '\033[95m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
# Load environment variables
load_dotenv()

# Initialize the FirecrawlApp with your API key
firecrawl_api_key = os.getenv("FIRECRAWL_API_KEY")
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Set the jobs page URL
jobs_page_url = "https://www.google.com/about/careers/applications/jobs/results"

# Resume
resume_paste = """"
Eva Chen
Product Designer based in Greater Seattle Area, 4 years experience designing mobile and web applications.

EDUCATION:
University of Michigan • 2023
Master of Science
Human-Computer Interaction

California College of the Arts • 2017
Bachelor of Fine Arts
Graphic Design

Miami University • 2014
Bachelor of Science
Accountancy

CERTIFICATIONS:
AI Products and Services • 2024
Massachusetts Institute of Tech
Machine Learning // Deep Learning // Natural Language Processing // Generative AI // AI Product Design Lifecycle

PROFESSIONAL EXPERIENCE:
Individual Product Developer
Bellevue, WA, United States // Oct.2025 to present
Developed an AI-Podcast from scratch using mutiple APIs and multiple AI agent tools. Research users with AI agent tools. Earned first 2000 users with MVP Version.

T-Mobile • Product Designer
Bellevue, WA, United States // 2023 TO Oct.2025
Sole Lead Designer for the account management vertical, collaborating with 10+ stakeholders to redesign the account dashboard, resulting in 1,000 fewer customer support calls per month and enhanced users self-service capabilities.
Led the design of the Manage tab, a key tab of the TLife apps 5-tab structure, utilizing traffic analytics and user research to deliver data-driven designs that contributed to the apps ranking as the #1 Free Lifestyle app in the Apple App Store.

Currents AI • Founding Product Designer
Remote, United States // 2024 TO Oct.2025
Led the end-to-end design of an AI-powered platform enabling small e-commerce businesses to analyze and understand customer sentiments from social media feedback. Collaborated with engineers to train and refine natural language processing models, ensuring outputs aligned with market analysis needs. Achieved rapid user adoption, garnering over 2,000 users and converting 10+ to paid subscribers within the first week post-launch.

Indeed.com • UX Design Intern
Seattle, WA, United States // 2022
Developed a system providing customized guidance to help users enhance their profiles and stand out in the job market.
Collaborated with data scientists to ensure feasibility, led innovative design workshops, and conducted concept testing, yielded positive results.

University of Michigan Hospital • UX Research Intern
Ann Arbor, MI, United States // 2021 TO 2022
Enhanced the surgical safety report system by researching and implementing recommendations to streamline surgical data entry, significantly saving time for nurses and improving the medical safety learning database. Employed methods including contextual inquiries, usability testing, and heuristic evaluations to optimize staff efficiency and system functionality.

General Motors • Product Designer
Shanghai, China // 2019 TO 2021
Led the design of a chatbot, partnering seamlessly with engineering teams to navigate security barriers and elevate the user experience on Buick vehicles.
Led the comprehensive redesign of the Fleet Service Platform, enhancing data visualization to improve vehicle inventory monitoring, which increased the platforms revenue contribution to 50 PERCENT of the departments earnings.
Spearheaded the design and iterations of an internal tool, boosting customer service efficiency. Established and maintained the design system, collaborated with project managers to adapt to evolving user needs, expanding the user base from 20 to 3,000.

Adinnet Design Agency • UX Designer
Shanghai, China // 2018 to 2019
Designed a cargo management tool for the worlds second- largest ocean shipping company, enhancing tracking, cargo handling, and billing workflows.

"""

# First, scrape the jobs page using Firecrawl
try:
    response = requests.post(
        "https://api.firecrawl.dev/v1/scrape",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {firecrawl_api_key}"
        },
        json={
            "url": jobs_page_url,
            "formats": ["markdown"]
        }
    )
    
    if response.status_code == 200:
        result = response.json()
        if result.get('success'):
            html_content = result['data']['markdown']
            # Define the O1 prompt for extracting apply links
            prompt = f"""
            Extract up to 5 job application links from the given markdown content.
            Return the result as a JSON object with a single key 'apply_links' containing an array of strings (the links).
            The output should be a valid JSON object, with no additional text.
            Do not include any JSON markdown formatting or code block indicators.
            Provide only the raw JSON object as the response.

            Example of the expected format:
            {{"apply_links": ["https://example.com/job1", "https://example.com/job2", ...]}}

            Markdown content:
            {html_content[:100000]}
            """
            print(f"{Colors.GREEN}Successfully scraped the jobs page{Colors.RESET}")
        else:
            print(f"{Colors.RED}Failed to scrape the jobs page: {result.get('message', 'Unknown error')}{Colors.RESET}")
            html_content = ""
    else:
        print(f"{Colors.RED}Error {response.status_code}: {response.text}{Colors.RESET}")
        html_content = ""
except requests.RequestException as e:
    print(f"{Colors.RED}An error occurred while scraping: {str(e)}{Colors.RESET}")
    html_content = ""
except json.JSONDecodeError as e:
    print(f"{Colors.RED}Error decoding JSON response: {str(e)}{Colors.RESET}")
    html_content = ""
except Exception as e:
    print(f"{Colors.RED}An unexpected error occurred while scraping: {str(e)}{Colors.RESET}")
    html_content = ""

# Extract apply links from the scraped HTML using O1
apply_links = []
if html_content:
    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )
        
        if completion.choices:
            print(completion.choices[0].message.content)
            result = json.loads(completion.choices[0].message.content.strip())
        
            apply_links = result['apply_links']
            print(f"{Colors.GREEN}Successfully extracted {len(apply_links)} apply links{Colors.RESET}")
        else:
            print(f"{Colors.RED}No apply links extracted{Colors.RESET}")
    except json.JSONDecodeError as e:
        print(f"{Colors.RED}Error decoding JSON from OpenAI response: {str(e)}{Colors.RESET}")
    except KeyError as e:
        print(f"{Colors.RED}Expected key not found in OpenAI response: {str(e)}{Colors.RESET}")
    except Exception as e:
        print(f"{Colors.RED}An unexpected error occurred during extraction: {str(e)}{Colors.RESET}")
else:
    print(f"{Colors.RED}No HTML content to process{Colors.RESET}")

# Initialize a list to store the extracted data
extracted_data = []


# %%
print(f"{Colors.CYAN}Apply links:{Colors.RESET}")
for link in apply_links:
    print(f"{Colors.YELLOW}{link}{Colors.RESET}")

# %%
# Process each apply link
for index, link in enumerate(apply_links):
    try:
        response = requests.post(
            "https://api.firecrawl.dev/v1/scrape",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {firecrawl_api_key}"
            },
            json={
                "url": link,
                "formats": ["extract"],
                "actions": [{
                    "type": "click",
                    "selector": "#job-overview"
                }],
                "extract": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "job_title": {"type": "string"},
                            "sub_division_of_organization": {"type": "string"},
                            "key_skills": {"type": "array", "items": {"type": "string"}},
                            "compensation": {"type": "string"},
                            "location": {"type": "string"},
                            "apply_link": {"type": "string"}
                        },
                        "required": ["job_title", "sub_division_of_organization", "key_skills", "compensation", "location", "apply_link"]
                    }
                }
            }
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                extracted_data.append(result['data']['extract'])
                print(f"{Colors.GREEN}Data extracted for job {index}{Colors.RESET}")
            else:
                print(f"")
        else:
            print(f"")
    except Exception as e:
        print(f"")


# %%
# %%
# Print the extracted data
print(f"{Colors.CYAN}Extracted data:{Colors.RESET}")
for job in extracted_data:
    print(json.dumps(job, indent=2))
    print(f"{Colors.MAGENTA}{'-' * 50}{Colors.RESET}")


# %%




# Use o1-preview to choose which jobs should be applied to based on the resume
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
{resume_paste}

And the following job listings:
{json.dumps(extracted_data, indent=2)}
"""

completion = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": prompt
                }
            ]
        }
    ]
)

raw_response_text = (completion.choices[0].message.content or "").strip()

# Be tolerant to any extra text around the JSON array
try:
    recommended_jobs = json.loads(raw_response_text)
except json.JSONDecodeError:
    start_idx = raw_response_text.find('[')
    end_idx = raw_response_text.rfind(']')
    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
        try:
            recommended_jobs = json.loads(raw_response_text[start_idx:end_idx+1])
        except Exception as e:
            print(f"{Colors.RED}Failed to parse JSON array from model output: {str(e)}{Colors.RESET}")
            print(raw_response_text)
            recommended_jobs = []
    else:
        print(f"{Colors.RED}Model did not return a JSON array as requested.{Colors.RESET}")
        print(raw_response_text)
        recommended_jobs = []

print(f"{Colors.CYAN}Recommended jobs:{Colors.RESET}")
print(json.dumps(recommended_jobs, indent=2))

