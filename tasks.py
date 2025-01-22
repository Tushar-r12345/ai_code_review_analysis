from celery_config import app  # Import Celery app configuration
import requests
from models import PRDetails
from groq import Groq
from typing import Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from models import CodeAnalysisRequest
import logging

groq_client = Groq(api_key="Please add your GROQ Api key here")

def fetch_pr_details(repo_url: str, pr_number: int, token: Optional[str] = None):
    
    """
    Fetches details of a pull request from GitHub.

    Input:
    - repo_url: The URL of the GitHub repository (e.g., "https://github.com/owner/repo").
    - pr_number: The pull request number (an integer).
    - token (Optional): A GitHub personal access token for authentication (a string).

    Function:
    1. Extracts the owner and repository name from the repo_url.
    2. Constructs the GitHub API URL for the pull request.
    3. Creates a headers dictionary for the request. If a token is provided, adds an "Authorization" header.
    4. Sends a GET request to the GitHub API.
    5. Checks the response status code. If it's not 200 (OK), raises an exception with the status code and error message.
    6. Parses the JSON response and returns it.

    Output:
    - A dictionary containing the pull request details (JSON response from the GitHub API).
    - Raises an exception if the request fails (status code other than 200).
    """

    parts = repo_url.rstrip("/").split("/")
    owner, repo = parts[-2], parts[-1]
    pr_api_url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}"

    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    response = requests.get(pr_api_url, headers=headers)
    if response.status_code != 200:
        raise Exception(f"Failed to fetch PR details: {response.status_code} {response.text}")

    return response.json()

@app.task(bind=True, max_retries=3)
def analyze_pr_task(self,task_id: str, pr_details_dict: dict):
    
    """
    Analyzes a pull request and extracts relevant information.

    Input:
    - self: The Celery task instance (used for retrying).
    - task_id: A unique identifier for the task (string).
    - pr_details_dict: A dictionary containing pull request details necessary for fetching information (Dict[str, Any]). It is expected to have keys corresponding to the attributes of PRDetails class.

    Function:
    1. Prints the task arguments for debugging.
    2. Creates a PRDetails object from the input dictionary.
    3. Fetches detailed PR data from GitHub using the provided details via fetch_pr_details function.
    4. Extracts relevant information from the fetched PR data (title, author, status, mergeable status).
    5. Constructs a result dictionary containing the extracted information.
    6. Prints the result dictionary for debugging.
    7. Returns a dictionary with the result.

    Output:
    - A dictionary containing the analysis result
    - Retries the task up to `max_retries` (3) if an exception occurs during processing.
    - Raises the original exception after the maximum number of retries is reached.
    """


    try:
        print(f"Task arguments: {task_id}, {pr_details_dict}")
        pr_details = PRDetails(**pr_details_dict)
        pr_data = fetch_pr_details(pr_details.repo_url, pr_details.pr_number, pr_details.github_token)

        result = {
            "repo": pr_details.repo_url,
            "pr_number": pr_details.pr_number,
            "title": pr_data.get("title"),
            "author": pr_data.get("user", {}).get("login"),
            "status": pr_data.get("state"),
            "mergeable": pr_data.get("mergeable"),
        }

        print(result)
        return {"result": result}

    except Exception as e:
        raise self.retry(exc=e)  

def fetch_pr_files(repo_url: str, pr_number: int, token: Optional[str] = None):
    parts = repo_url.rstrip("/").split("/")
    owner, repo = parts[-2], parts[-1]
    files_api_url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/files"

    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    response = requests.get(files_api_url, headers=headers)
    if response.status_code != 200:
        raise Exception(f"Failed to fetch PR files: {response.status_code} {response.text}")

    print(f"fetch pr files : {response.text}")
    return response.json()

def fetch_file_content(raw_url: str, token: Optional[str] = None):
    
    """Fetches PR files from GitHub.

    Input:
        repo_url: Repository URL (e.g., "https://github.com/owner/repo").
        pr_number: Pull request number.
        token (Optional): GitHub personal access token.

    Returns:
        A list of dictionaries representing PR files.
        Raises an exception on API errors (non-200 status).
    """


    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    response = requests.get(raw_url, headers=headers)
    if response.status_code != 200:
        raise Exception(f"Failed to fetch file content: {response.status_code} {response.text}")

    print(f"file content: {response.text}")
    return response.text


@app.task(bind=True, max_retries=3)
def analyze_code_task(self,task_id: str, request_data: dict):
    """Analyzes code from a pull request using a Groq model.

    Input:
        task_id: Unique identifier for the task (string).
        request_data: Dictionary containing request details (Dict[str, Any]). It's expected to have keys corresponding to the attributes of CodeAnalysisRequest class.

    Function:
        1. Creates a CodeAnalysisRequest object from the input data.
        2. Fetches the list of files associated with the pull request.
        3. Iterates over each file:
            - Fetches the file content.
            - Constructs a formatted prompt for the Groq model, including instructions and expected output format.
            - Calls the Groq client to get code analysis using the prompt and specified model.
            - Extracts the analysis content from the Groq response.
            - Creates a dictionary containing the filename and analysis result (or error message).
            - Appends the file analysis result to the overall results list.
        4. Returns a dictionary with the repository URL, pull request number, and the list of file analysis results.
        5. Logs and raises an exception if any error occurs during processing.


    Output:
        A dictionary containing the analysis results

    """

    try:
        request = CodeAnalysisRequest(**request_data)
        pr_files = fetch_pr_files(request.repo_url, request.pr_number, request.github_token)
        analysis_results = []

        for file in pr_files:
            file_name = file["filename"]
            raw_url = file["raw_url"]

            try:
                content = fetch_file_content(raw_url, request.github_token)

                header = (
                    f"You are a code analysis AI agent powered by the Groq platform.\n"
                    f"Your task is to analyze the provided code snippet using the model: {request.model_name}.\n\n"
                    "### Instructions:\n"
                    "Analyze the code for the following:\n"
                    "1. **Code style and formatting issues** (e.g., indentation, naming conventions)\n"
                    "2. **Potential bugs or errors** (e.g., null pointer exceptions, incorrect logic)\n"
                    "3. **Performance improvements** (e.g., optimize loops, reduce memory usage)\n"
                    "4. **Best practices** (e.g., modularization, documentation, coding standards)\n"
                )

                input_code = (
                    "\n### Input Code:\n"
                    "```\n"
                    f"{content}\n"
                    "```\n"
                )

                output_format = (
                    "\n### Expected Output:\n"
                    "You will provide the analysis in JSON format. The JSON should include:\n"
                    "- A list of **issues** for each file, specifying:\n"
                    "  - Type of issue (e.g., 'style', 'bug', 'performance')\n"
                    "  - Line number\n"
                    "  - Description of the issue\n"
                    "  - Suggestions for improvement\n"
                    "- A **summary** with:\n"
                    "  - Total files analyzed\n"
                    "  - Total issues found\n"
                    "  - Critical issues count (if applicable)\n\n"
                )

                full_prompt = header + input_code + output_format

                chat_completion = groq_client.chat.completions.create(
                    messages=[{"role": "system", "content": full_prompt}],
                    model=request.model_name
                )

                if hasattr(chat_completion, 'choices') and isinstance(chat_completion.choices, list):
                    analysis_content = chat_completion.choices[0].message.content
                else:
                    raise Exception("Unexpected format from Groq client response.")

                analysis = {
                    "name": file_name,
                    "analysis": analysis_content
                }
                analysis_results.append(analysis)
            except Exception as e:
                analysis_results.append({"name": file_name, "error": str(e)})
        
        return {
            "repo_url": request.repo_url,
            "pr_number": request.pr_number,
            "analysis": analysis_results,
        }

    except Exception as e:
        logging.error(f"Error processing task {task_id}: {str(e)}")
        raise Exception(f"Task failed: {str(e)}")
