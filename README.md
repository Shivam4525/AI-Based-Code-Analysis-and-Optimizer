# AI-Based Code Analysis & Optimization Tool

An AI-assisted web application designed to analyze source code, identify selected code-quality and security issues, explain findings, and propose possible code corrections. The project combines static analysis tools with a locally hosted CodeLlama model through Ollama.

> **Project Status:** Academic and development project. Analysis coverage depends on the implemented analyzers and rules. AI-generated corrections are suggestions and should be reviewed and tested before use.

## Table of Contents

1. [Overview](#overview)
2. [Objectives](#objectives)
3. [Features](#features)
4. [Technology Stack](#technology-stack)
5. [Project Structure](#project-structure)
6. [System Requirements](#system-requirements)
7. [Installation and Setup](#installation-and-setup)
8. [Environment Configuration](#environment-configuration)
9. [Running the Application](#running-the-application)
10. [API Endpoints](#api-endpoints)
11. [System Workflow](#system-workflow)
12. [Code Validation](#code-validation)
13. [Security and Privacy](#security-and-privacy)
14. [Limitations](#limitations)
15. [Troubleshooting](#troubleshooting)
16. [Future Enhancements](#future-enhancements)
17. [License](#license)
18. [Author](#author)

## 1. Overview

The AI-Based Code Analysis & Optimization Tool is a web-based application that helps developers examine source code and understand potential problems before using or deploying it.

The application combines traditional static analysis with AI-assisted explanations and candidate fixes. Static analysis tools identify issues covered by their configured rules, while the AI model can help explain selected problems and suggest possible improvements.

The application provides a web interface for submitting code, viewing findings, and reviewing analysis results. MySQL is used to store user account information and relevant analysis records.

The primary goal is to make code analysis more accessible while helping developers understand potential bugs, security weaknesses, and code-quality concerns.

## 2. Objectives

The main objectives of this project are:

- To analyze source code using configured static analysis tools.
- To identify potential programming errors and code-quality issues.
- To detect selected security-related patterns.
- To provide explanations that help users understand reported issues.
- To generate candidate code corrections using AI assistance.
- To validate proposed changes using available validation checks.
- To calculate and present a code-quality score based on implemented checks.
- To provide a web interface for submitting code and viewing reports.
- To store user and analysis information in a MySQL database.
- To combine rule-based analysis with AI-assisted programming support.

## 3. Features

### 3.1 Source Code Analysis

The application examines submitted source code using the analyzers registered in the backend. Depending on the selected language and configured tools, it can report detectable programming and code-quality issues.

### 3.2 Automatic Language Detection

The application can attempt to identify the programming language from submitted code or use a language selected by the user.

Language detection and analyzer availability are separate: detecting a language does not necessarily mean a corresponding analyzer is enabled.

### 3.3 Issue Classification

Analysis findings can include information such as:

- Issue category
- Severity level
- Source line number
- Issue description
- Source-code snippet
- Suggested remediation

The exact details depend on the analyzer and finding.

### 3.4 Security Analysis

The application includes security-oriented scanning rules for selected potentially unsafe code patterns. Findings can help users investigate possible vulnerabilities and understand recommended remediation.

Security findings should be reviewed in context. Static scanning cannot guarantee that every vulnerability will be detected.

### 3.5 AI-Assisted Explanations

The application integrates Ollama with the CodeLlama model to support explanations of programming issues and possible improvements.

AI-generated explanations may be incomplete or incorrect, so they should be treated as assistance rather than authoritative verification.

### 3.6 Candidate Code Fixes

The AI integration can propose corrected code for supported cases. Available validation mechanisms can check proposed changes before the application reports their verification status.

A proposed fix should not be considered fully correct simply because it passes syntax or static checks.

### 3.7 Code Quality Scoring

The application calculates a project-defined quality score based on its implemented analysis and scoring logic. The report can also summarize issue severity and categories.

The score is an indicator produced by this application, not a universal software-quality standard.

### 3.8 User Authentication

The backend provides registration and login functionality. User authentication is integrated with the application's account-management workflow.

### 3.9 Analysis History

The application includes backend functionality for working with analysis history and storing relevant analysis records in MySQL.

The available history operations depend on the current implementation and database configuration.

### 3.10 Web-Based Interface

The frontend uses HTML, CSS, and JavaScript to provide the application's interface. Users can interact with the analysis functionality and review returned results through a web browser.

## 4. Technology Stack

| Component | Technology | Purpose |
|---|---|---|
| Backend | Python | Application logic and analysis coordination |
| Web framework | Flask | API endpoints and request handling |
| Frontend | HTML5 | Web-page structure |
| Styling | CSS3 | Layout and visual presentation |
| Frontend interaction | JavaScript | User interaction and API communication |
| Database | MySQL | User and analysis data storage |
| AI runtime | Ollama | Local language-model integration |
| AI model | CodeLlama | AI-assisted explanations and candidate fixes |
| Python analysis | Pylint and project-specific rules | Selected code-quality and programming checks |
| JavaScript analysis | ESLint and configured security plugin | JavaScript analysis |
| Authentication | JWT and password hashing | Authentication and account security |

## 5. Project Structure

The main project components are organized approximately as follows:

```text
AI-Code-Tester/
│
├── backend/
│   ├── app.py
│   ├── config.py
│   │
│   ├── routes/
│   │   ├── analyze.py
│   │   ├── auth.py
│   │   ├── history.py
│   │   └── report.py
│   │
│   ├── analyzers/
│   │   ├── registry.py
│   │   ├── python_analyzer.py
│   │   ├── javascript_analyzer.py
│   │   └── other analyzer modules
│   │
│   ├── services/
│   │   ├── ollama.py
│   │   ├── validation.py
│   │   ├── scoring.py
│   │   ├── js_tools.py
│   │   ├── js_fixer.py
│   │   └── other service modules
│   │
│   ├── database/
│   │   └── mysql.py
│   │
│   ├── js-tools/
│   │   └── package.json
│   │
│   └── requirements.txt
│
├── frontend/
│   ├── index.html
│   ├── editor.html
│   ├── dashboard.html
│   ├── history.html
│   └── report.html
│
├── requirements.txt
└── README.md
```

**Note:** This is a high-level overview. The exact files in your local project may differ as development continues. Check the current source tree for the complete list of modules.

The analyzer registry in `backend/analyzers/registry.py` should be used to determine which language analyzers are currently registered.

## 6. System Requirements

Before installing the application, ensure the following software is available:

- Python compatible with the project's installed dependencies
- MySQL Server
- Node.js and npm for JavaScript analysis tools
- Ollama
- The configured CodeLlama model
- A modern web browser
- Sufficient memory and disk space for the AI model

AI analysis performance depends on the computer's available resources, model size, source-code length, and enabled analysis tools.

## 7. Installation and Setup

### Step 1: Clone the Repository

Open a terminal and run:

```bash
git clone https://github.com/Shivam4525/AI-Based-Code-Analysis-and-Optimizer.git
```

Move into the cloned project directory:

```bash
cd AI-Based-Code-Analysis-and-Optimizer
```

If your local folder has a different name, use that folder name instead.

### Step 2: Create a Python Virtual Environment

On Windows, run:

```powershell
py -m venv .venv
```

Activate the environment in PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Alternatively, use Command Prompt:

```bat
.venv\Scripts\activate.bat
```

A virtual environment keeps the project's Python dependencies separate from other Python applications.

### Step 3: Install Python Dependencies

From the project root, run:

```powershell
python -m pip install -r .\backend\requirements.txt
```

If your project uses the root-level `requirements.txt` instead, check which dependency file contains the packages required by your current backend.

### Step 4: Install JavaScript Dependencies

Move into the JavaScript tools directory:

```powershell
cd backend\js-tools
```

Install the dependencies:

```powershell
npm install
```

Return to the project root:

```powershell
cd ..\..
```

Ensure Node.js and npm are installed and available in your terminal.

### Step 5: Configure MySQL

1. Start MySQL Server.
2. Connect to MySQL using an account with database-creation privileges.
3. Create the application database.
4. Ensure the required application tables exist.
5. Configure the backend to use the correct database credentials.

Example SQL for creating the database:

```sql
CREATE DATABASE ai_code_tester
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;
```

The application expects the tables required by its database and route modules to exist. Use a reviewed database schema that matches the current source code.

**Important:** Do not publish a database backup containing real user information, password hashes, analysis history, or submitted source code.

### Step 6: Install and Configure Ollama

Install Ollama from its official website:

https://ollama.com/

Download the configured CodeLlama model:

```bash
ollama pull codellama
```

Check which models are available:

```bash
ollama list
```

The default project configuration expects Ollama to be available at:

```text
http://localhost:11434
```

The configured model name is:

```text
codellama
```

The actual model name must match the model installed in Ollama and the value configured for the backend.

### Step 7: Configure Environment Variables

The application reads configuration values from environment variables.

Example for Windows PowerShell:

```powershell
$env:SECRET_KEY = "replace-with-a-long-random-secret"
$env:JWT_SECRET = "replace-with-another-long-random-secret"

$env:DB_HOST = "localhost"
$env:DB_PORT = "3306"
$env:DB_USER = "your_mysql_user"
$env:DB_PASSWORD = "your_mysql_password"
$env:DB_NAME = "ai_code_tester"

$env:OLLAMA_HOST = "http://localhost:11434"
$env:OLLAMA_MODEL = "codellama"

$env:FLASK_DEBUG = "False"
```

Replace the example values with your actual local configuration.

These commands set variables for the current PowerShell session. Configure environment variables appropriately for your deployment environment.

**Security warning:** Never commit real passwords, JWT secrets, private keys, or other credentials to a public repository.

## 8. Running the Application

### Step 1: Start the Backend

From the project root, run:

```powershell
cd backend
python app.py
```

The Flask server uses port `5000` by default unless the application configuration specifies otherwise.

Keep the backend terminal open while using the application.

### Step 2: Open the Frontend

Open the frontend directory:

```text
frontend/
```

Use the project's existing frontend setup or a local web server, such as the VS Code Live Server extension, to open the interface.

Ensure the frontend API base URL points to the correct Flask backend address.

For a local backend, this is commonly:

```text
http://localhost:5000
```

The exact address depends on your current configuration.

### Step 3: Use the Application

The general workflow is:

1. Open the web interface.
2. Enter or submit source code.
3. Select a language or use automatic detection where available.
4. Run the analysis.
5. Review the reported issues and severity levels.
6. Read the explanations and suggested remediations.
7. Review any AI-generated code correction.
8. Validate and test proposed changes before using them.

## 9. API Endpoints

The backend provides API routes for analysis, authentication, and history.

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/api/health` | Checks API status |
| `GET` | `/api/languages` | Lists registered analysis languages |
| `POST` | `/api/analyze` | Submits source code for analysis |
| `POST` | `/api/auth/register` | Registers a user |
| `POST` | `/api/auth/login` | Authenticates a user |
| Various | `/api/history` | Provides analysis-history operations, depending on the route implementation |

Consult the corresponding files under `backend/routes/` for the current request parameters, authentication requirements, and response formats.

### Health Check Example

If the health endpoint is enabled at the documented path, test it with:

```bash
curl http://localhost:5000/api/health
```

The endpoint should return a response indicating whether the API is running. The exact response fields depend on the implementation.

### Code Analysis Example

Example request to the analysis endpoint:

```bash
curl -X POST http://localhost:5000/api/analyze \
  -H "Content-Type: application/json" \
  -d "{\"code\":\"def add(a, b):\\n    return a + b\\n\",\"filename\":\"example.py\",\"language\":\"auto\",\"use_ai\":false}"
```

This example submits a short Python function for analysis. The actual request fields and response structure should be checked against `backend/routes/analyze.py`.

The analysis response may contain the detected language, issue findings, severity summaries, quality score, and AI/fix-related information, depending on the request and analysis result.

## 10. System Workflow

The application follows this general workflow:

1. **Code Submission:** The user submits source code through the frontend or API.
2. **Language Selection:** The backend uses the requested language or attempts automatic detection.
3. **Static Analysis:** The registered analyzer examines the code using its available rules and tools.
4. **Security Scanning:** Configured security checks identify selected potentially unsafe patterns.
5. **Finding Processing:** The backend processes findings, including issue categories, severity, and source locations where available.
6. **Quality Scoring:** The application calculates a project-defined score and creates summaries.
7. **AI Assistance:** When enabled and applicable, Ollama and CodeLlama can generate explanations or candidate code corrections.
8. **Validation:** Available validation mechanisms check proposed changes.
9. **Result Presentation:** The frontend displays the analysis information for the user to review.

Static analysis and AI assistance serve different purposes. Static analysis produces rule-based findings, while AI-generated content provides suggestions that may require additional verification.

## 11. Code Validation

The application includes validation mechanisms for proposed code changes.

Depending on the language and available tools, validation may include:

- Syntax checking
- Selected static-analysis checks
- Checks for certain undefined names
- Detection of selected invalid or incomplete code patterns

These checks can help identify some problems in proposed fixes before they are presented as validated.

However, passing the available checks does not guarantee that the code:

- Produces the intended output
- Handles every edge case
- Works correctly with the complete application
- Is free from security vulnerabilities
- Meets performance requirements
- Is safe for production deployment

Run appropriate automated tests and review the changes before adopting a fix.

## 12. Security and Privacy

Security is important when analyzing code and managing user information.

### Recommended Practices

- Never commit database passwords, signing secrets, API keys, or private credentials.
- Do not publish database backups containing real account information or password hashes.
- Avoid submitting confidential source code unless you are authorised to do so.
- Use strong, unique values for application and JWT secrets.
- Use a dedicated MySQL account with only the required permissions.
- Disable Flask debug mode in production.
- Validate uploaded files and user input.
- Review AI-generated changes before applying them.
- Keep Python and Node.js dependencies updated.
- Use HTTPS and appropriate access controls when deploying the application publicly.

Ollama can process model prompts locally when configured for local execution, but the complete application's privacy characteristics also depend on its database, network, logging, and deployment configuration.

## 13. Limitations

- Static analysis detects only issues covered by the enabled tools and rules.
- Language detection does not guarantee that a language analyzer is available.
- AI-generated explanations and corrections may be inaccurate or incomplete.
- Syntax validation does not establish functional correctness.
- Passing static checks does not prove that code is secure.
- The quality score is based on the project's own scoring logic.
- Large source files and slower computers can increase analysis time.
- AI assistance requires Ollama to be available and the configured model to be installed.
- Database-backed features require a correctly configured MySQL database and the required tables.
- The actual coverage and output depend on the current implementation and configuration.

## 14. Troubleshooting

### MySQL Connection Error

Check the following:

- MySQL Server is running.
- The database name is correct.
- The configured username and password are valid.
- The database user has the required permissions.
- The required tables exist.

### Ollama Is Not Responding

Check that Ollama is installed and running.

List the installed models:

```bash
ollama list
```

Confirm that the configured model is installed and that `OLLAMA_HOST` points to the correct address.

### AI Fixes Are Unavailable

AI fix generation may be unavailable when:

- Ollama is not running.
- The configured model is missing.
- A request times out.
- The submitted language or code pattern is unsupported by the fix workflow.
- The application skips AI processing for a particular input.

Review the backend logs for additional information.

### Unsupported Language

Call the language-list endpoint:

```text
GET /api/languages
```

Check the registered analyzer list. A language being detected does not necessarily mean that it is supported for full analysis.

### JavaScript Analysis Is Not Working

Install the JavaScript tooling dependencies:

```powershell
cd backend\js-tools
npm install
```

Check that Node.js and npm are available in the terminal running the backend.

### Frontend Cannot Connect to Flask

- Confirm that the Flask backend is running.
- Check the configured API base URL.
- Check the browser developer console for network or JavaScript errors.
- Verify CORS settings if the frontend and backend run on different origins.

## 15. Development Checks

To check Python files for syntax errors, run this command from the backend directory:

```powershell
python -m compileall .
```

This checks Python syntax. It does not replace functional tests, API tests, security testing, or end-to-end testing.

After modifying the analyzers or validation services, test both valid and invalid code samples to check that findings and proposed fixes behave as expected.

## 16. Future Enhancements

Possible future improvements include:

- Expanded language-analyzer coverage
- More context-aware bug detection
- Additional security rules
- Automated regression tests for suggested fixes
- Cross-file and project-level analysis
- Improved handling of large source files
- Downloadable reports in additional formats
- Analysis-history trends and comparisons
- Performance improvements through caching and reduced duplicate model calls
- More comprehensive validation and testing of candidate fixes
- Deployment configuration for a hosted environment

These are potential enhancements and should not be interpreted as features already implemented.

## 17. License

No license is specified in this repository at the time this README was prepared.

Unless a license is added, use, modification, and redistribution remain subject to applicable copyright law.

## 18. Author

**Shivam Gupta**

**Project Title:** AI-Based Code Analysis & Optimization Tool

**Repository:**  
https://github.com/Shivam4525/AI-Based-Code-Analysis-and-Optimizer
