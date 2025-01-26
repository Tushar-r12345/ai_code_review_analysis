# Asynchronous Pull Request and Code Analysis

This project provides a framework for asynchronously analyzing pull requests and code using a Groq model and Celery tasks.

## Project Setup

**Prerequisites:**

*   Python 3.x
*   Celery
*   Redis
*   pydantic
*   FastAPI
*   Groq client library (assuming a specific library is used)
*   Additional libraries based on your implementation (e.g., `requests` for GitHub API interaction)

**Installation:**

1.  Clone this repository:

    ```bash
    git clone https://github.com/Tushar-r12345/ai_code_review_analysis.git
    cd https://github.com/Tushar-r12345/ai_code_review_analysis.git
    ```

2.  Create a virtual environment (recommended):

    ```bash
    python3 -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  Install the required libraries using `pip`:

    ```bash
    pip install -r requirements.txt
    ```
    ```

**Running the Application:**

Open **two** separate terminal windows:

**Terminal 1 (Celery Worker):**
    - celery -A tasks worker --pool=solo -l info

**Terminal 2 (Uvicorn/Swagger UI):**
    - uvicorn app:app --reload

## API Documentation

**API Endpoints:**

*   **POST /analyze-pr**

    *   Initiates asynchronous analysis of a pull request and returns immediate details.
    *   Request body: JSON containing a `PRDetails` object (see Data Models).
    *   Response (200 OK):

        ```json
        {
            "task_id": "unique_task_id",
            "repo": "repository_url",
            "pr_number": 123,
            "title": "pull_request_title",
            "author": "author_username",
            "status": "open"
        }
        ```

    *   Response (500 Internal Server Error):

        ```json
        {
            "error": "error_message"
        }
        ```

*   **POST /analyze-code**

    *   Initiates asynchronous code analysis and returns the analysis result when complete.
    *   Request body: JSON containing a `CodeAnalysisRequest` object (see Data Models).
    *   Response (200 OK):

        ```json
        {
            "status": "completed",
            "task_id": "unique_task_id",
            "result": { /* ... Analysis result ... */ }
        }
        ```

    *   Response (500 Internal Server Error):

        ```json
        {
            "task_id": "unique_task_id",
            "error": "error_message"
        }
        ```

*   **GET /status/{task_id}**

    *   Retrieves the status of an asynchronous task.
    *   Path parameter: `{task_id}` (unique identifier for the task).
    *   Response (200 OK):

        ```json
        {
            "task_id": "unique_task_id",
            "status": "pending" | "processing" | "completed" | "failed" | "unknown",
            "result": { /* ... Task result (if status is "completed") ... */ },
            "error": "error_message" // only if status is failed
        }
        ```

**Data Models:**

*   **PRDetails:** (Example)

    ```json
    {
        "repo_url": "[https://github.com/owner/repo](https://github.com/owner/repo)",
        "pr_number": 123,
        "github_token": "your_github_token"
    }
    ```

*   **CodeAnalysisRequest:** (Example)

    ```json
    {
        "repo_url": "[https://github.com/owner/repo](https://github.com/owner/repo)",
        "pr_number": 123,
        "github_token": "your_github_token",
        "model_name": "groq_model_name"
    }
    ```

## Design Decisions

*   **Asynchronous Tasks:** Celery is used for asynchronous task execution, allowing the API to respond promptly while analysis is ongoing in the background.
*   **Modular Design:** The code is divided into separate functions for handling API requests, Celery tasks, and data retrieval, promoting maintainability.
*   **Error Handling:** Exceptions are handled throughout the code, with logging and informative error messages in the API responses.
*   **JSON Communication:** Data is exchanged between API endpoints and Celery tasks using JSON for a flexible and language-agnostic approach.
*   **Groq LPU Engine Usage:** The project leverages the Groq LPU (Language Processing Unit) engine. This allows us to efficiently utilize different language models for code analysis. The Groq platform's architecture enables concurrent execution of diverse models, optimizing resource utilization and potentially improving analysis performance. This is particularly beneficial when needing to analyze code with different models or for different types of analysis (e.g., style checking vs. security vulnerability detection).


## Future Improvements

*   **Detailed Code Analysis:** The current implementation might require further development to provide more comprehensive code analysis results.
*   **Scalability:** Consider improvements for handling larger workloads and potentially distributed task execution.
*   **Security Enhancements:** Implement robust authentication and authorization mechanisms for API access and data security.
*   **Documentation Expansion:** Provide more detailed API reference documentation and code comments for better understanding.
*   **Frontend Integration:** Develop a frontend interface to interact with the API for a user-friendly experience.
*   **Input Validation:** Add more robust input validation to the API endpoints to prevent invalid data from being processed.
*   **Rate Limiting:** Implement rate limiting to prevent abuse of the API.

This is a foundational project that can be extended upon to create a more comprehensive and robust pull request and code analysis system.
