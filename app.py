from fastapi import FastAPI, HTTPException
from celery.result import AsyncResult  
import uuid
import json
from models import PRDetails, CodeAnalysisRequest
from tasks import analyze_pr_task, analyze_code_task, fetch_pr_details 
from fastapi.responses import JSONResponse
import logging
from celery_config import app as celery_app

logger = logging.getLogger(__name__)
app = FastAPI()

@app.post("/analyze-pr")
def analyze_pr(pr_details: PRDetails):
    
    """
    Initiates asynchronous analysis of a pull request and returns immediate details.

    Input:
        JSON request body containing a PRDetails object.

    Function:
        1. Parses the request body to get the PR details (PRDetails object).
        2. Generates a unique task ID.
        3. Converts the PR details to a dictionary.
        4. Starts an asynchronous Celery task `analyze_pr_task` with the task ID and PR details dictionary.
        5. Fetches the pull request details from GitHub using `fetch_pr_details`.
        6. Constructs a response dictionary containing the task ID, PR details, and analysis results (which will be filled in later by the asynchronous task).
        7. Returns a JSON response with the response dictionary.
        8. Logs any exceptions and returns a JSON error response with status code 500.


    Output:
        JSON response with:
            - task_id: Unique identifier for the asynchronous analysis task.
            - repo: URL of the repository containing the pull request.
            - pr_number: Pull request number.
            - title: Title of the pull request (if available).
            - author: Login name of the pull request author (if available).
            - status: Current status of the pull request (e.g., "open", "closed").
            - mergeable: Whether the pull request is mergeable (if available).
        - Status code 500 with an error message if an exception occurs.
    """


    task_id = str(uuid.uuid4()) 
    
    pr_details_dict = pr_details.dict()
    task = analyze_pr_task.apply_async(args=[task_id, pr_details_dict])
    
    try:
        pr_data = fetch_pr_details(pr_details.repo_url, pr_details.pr_number, pr_details.github_token)
        logging.info(pr_data)
        response_data = {
            "task_id": task.id,
            "repo": pr_details.repo_url,
            "pr_number": pr_details.pr_number,
            "title": pr_data.get("title"),
            "author": pr_data.get("user", {}).get("login"),
            "status": pr_data.get("state"),
            "mergeable": pr_data.get("mergeable"),
        }
        
        return JSONResponse(content=response_data)
    
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/analyze-code")
def analyze_code(request: CodeAnalysisRequest):
    """
    Initiates asynchronous code analysis and returns the analysis result when complete.

    Input:
        JSON request body containing a CodeAnalysisRequest object.

    Function:
        1. Parses the request body to get the code analysis request (CodeAnalysisRequest object).
        2. Generates a unique task ID.
        3. Converts the request object to a dictionary.
        4. Starts an asynchronous Celery task `analyze_code_task` with the task ID and request dictionary.
        5. Waits for the Celery task result with a timeout of 30 seconds.
        6. Checks if the task result is a dictionary.
        7. If the result is a dictionary and contains analysis for each file:
            - Attempts to parse the analysis content for each file as JSON (assuming it's wrapped in code fences).
        8. Constructs a response dictionary with the status ("completed"), task ID, and the raw analysis result.
        9. Returns a JSON response with the response dictionary.
        10. Logs any exceptions and returns a JSON error response with status code 500.


    Output:
        JSON response with:
            - status: "completed" (once analysis is finished).
            - task_id: Unique identifier for the asynchronous analysis task.
            - result: The complete analysis result dictionary from the Celery task.
        - Status code 500 with an error message if an exception occurs.
    """

    try:
        task_id = str(uuid.uuid4())
        task_result = analyze_code_task.apply_async(args=[task_id, request.dict()])
        raw_result = task_result.get(timeout=30)
        
        if isinstance(raw_result, dict):
            for file_analysis in raw_result.get("result", {}).get("analysis", []):
                
                if "analysis" in file_analysis and isinstance(file_analysis["analysis"], str):
                    file_analysis["analysis"] = json.loads(file_analysis["analysis"].strip("```json\n").strip("```"))
        
        response_data = {
            "status": "completed",
            "task_id": task_id,
            "result": raw_result
        }
        
        return JSONResponse(content=response_data)
    except Exception as e:
        logging.error(f"Error processing task: {str(e)}")
        return JSONResponse(
            content={"task_id": task_id, "error": str(e)},
            status_code=500
        )


@app.get("/status/{task_id}")
def get_status(task_id: str):
    """
    Retrieves the status of an asynchronous task.

    Input:
        task_id: Unique identifier for the task (string).

    Function:
        1. Creates a Celery AsyncResult object using the provided task ID.
        2. Logs the task state for informational purposes.
        3. Checks the task state:
            - If "PENDING": return status "pending".
            - If "STARTED": return status "processing".
            - If "SUCCESS": return status "completed" with the task result.
            - If "FAILURE": return status "failed" with the error message.
            - Otherwise, return status "unknown".
        4. Returns a JSON response with the status information.

    Output:
        JSON response with:
            - task_id: The same task ID provided in the request.
            - status: One of "pending", "processing", "completed", "failed", or "unknown".
            - result (optional): The task result if the status is "completed".
            - error (optional): Error message if the status is "failed".
    """

    task = AsyncResult(task_id, app=celery_app)  
    logger.info(f"Task {task_id} state: {task.state}")  
    
    if task.state == "PENDING":
        return {"task_id": task.id, "status": "pending"}
    elif task.state == "STARTED":
        return {"task_id": task.id, "status": "processing"}
    elif task.state == "SUCCESS":
        return {"task_id": task.id, "status": "completed", "result": task.result}
    elif task.state == "FAILURE":
        return {"task_id": task.id, "status": "failed", "error": str(task.info)} 
    else:
        return {"task_id": task.id, "status": "unknown"}
