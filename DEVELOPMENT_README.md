# CampusRecall: Development workflow and technology overview

## What we built

CampusRecall is an interactive AI memory and task assistant for everyday campus life. It helps people turn conversations, screenshots, and spoken thoughts into tasks, plans, and useful memories.

For example, “Meet Maya tomorrow at six, and remember the restaurant Sam recommended” can become a scheduled task and a separate saved memory. The user reviews and confirms the information before saving it.

The project was developed iteratively with Codex assistance, moving from a small task-extraction prototype to an interactive tech-expo experience.

## Languages and formats

| Language or format | How it is used |
| --- | --- |
| **Python** | Main application language: interface, AI requests, task handling, image processing, and exports. |
| **SQL** | Creates, reads, updates, and deletes records in the local SQLite database. |
| **JSON** | Carries conversation context and structured task/memory responses between the app and Gemini. |
| **TOML** | Defines the Streamlit theme and supports deployment secrets configuration. |
| **Markdown** | Project documentation and some interface text. |
| **iCalendar (`.ics`)** | Represents calendar events and reminder preferences for export. |
| **CSV and PDF** | Provide spreadsheet and printable takeaway files. |

The interface is written with Python and Streamlit widgets. This project does not have a separately authored HTML, CSS, or JavaScript frontend; Streamlit renders the browser interface.

## Tools and libraries

| Tool | Role |
| --- | --- |
| **Streamlit** | Builds the web interface, forms, navigation screens, audio recording controls, file uploads, and session state. |
| **Google Gemini** | Interprets text, screenshots, and recordings; suggests tasks and memories; asks clarifying questions; answers questions about supplied saved records. The default model is `gemini-3.5-flash-lite`. |
| **Google Gen AI SDK (`google-genai`)** | Connects the Python application to Gemini. |
| **SQLite / Python `sqlite3`** | Stores Personal-mode records in a local database. |
| **ReportLab** | Generates printable PDF recall cards. |
| **Pillow** | Fits campus photos into the rotating banner. It is available through the installed dependencies. |
| **python-dotenv** | Reads local configuration from `.env`. |
| **Python `datetime` and `zoneinfo`** | Handles dates, event lengths, and the America/Chicago time zone; converts timed calendar events to UTC. |
| **Python `unittest`** | Tests storage, validation, exports, and application behavior. |
| **Streamlit AppTest** | Exercises the interface without needing a browser or live AI requests. |
| **mypy** | Checks Python code for type-related mistakes during development. |
| **Git and GitHub** | Track source changes and host the project repository. |
| **Python virtual environment and pip** | Isolate and install project dependencies. |
| **Streamlit Community Cloud** | The selected deployment route for running the Python app online from GitHub. Account setup, deployment, and secret configuration happen on the hosting platform. |

## How development progressed

### 1. Define the problem

The starting idea was to bridge the gap between hearing or thinking of something and remembering to act on it. The scope included assignments, lunch plans, meeting friends, follow-ups, and recommendations.

### 2. Build the initial prototype

The first version accepted pasted text or an uploaded image. Gemini extracted action items and possible deadlines. Users could review suggestions, save tasks locally, mark them complete, delete them, and export a CSV.

### 3. Add conversation and memories

The prototype expanded into a conversational assistant. Conversation history and existing drafts provide context for follow-up questions. Tasks and memories became separate record types, allowing the app to keep useful facts that do not require a deadline.

Voice capture was added using Streamlit's microphone widget. The recording is sent to Gemini for interpretation; the app does not run a local speech-recognition model.

### 4. Organize the interaction

The interface was divided into five screens:

- **Capture:** Type, speak, or attach a screenshot.
- **Review:** Edit suggested cards and confirm what to save.
- **Today:** See today's plans, overdue tasks, and unscheduled tasks.
- **My recall:** Search, edit, complete, and delete saved items.
- **Take away:** Download a PDF, spreadsheet, or calendar file.

Capture and Review are separate views within the same Streamlit application. Scheduling fields are grouped under “Date & reminder,” with source context available in an expander.

### 5. Improve dates, calendars, and reminders

Free-text date entry was replaced with date and time pickers. Date-only plans are supported as all-day events, while timed plans can carry a reminder preference and event length.

The app generates `.ics` files with calendar events and optional `VALARM` alerts. It also creates Google Calendar links that open prefilled event drafts. Users import or save the event themselves.

CampusRecall does not deliver notifications from a background service. The calendar app handles alerts after import, subject to its notification settings. Google Calendar links use the calendar's default alerts rather than transferring the custom reminder preference.

### 6. Prepare the expo experience

Expo mode hides the Personal workspace. Each visitor uses temporary session storage and can download their takeaway before the session is cleared. A “Next visitor” control resets the interaction between guests.

The interface uses maroon and gold, locally bundled ULM photos, and shorter text. A photo fragment refreshes every eight seconds without rerunning the task form.

Completing a task earns one star and displays a toast. Stars reflect currently completed tasks: reopening or deleting a completed task removes its star. Repeated toggling does not accumulate additional stars.

An offline demonstration mode was explored during development and later removed. The current assistant requires an online Gemini connection; sample buttons only fill example text for the live assistant.

### 7. Separate code responsibilities

| File or directory | Responsibility |
| --- | --- |
| `app.py` | Interface, navigation, session state, visitor workflow, task forms, completion stars, and rotating photos. |
| `recall.py` | Gemini requests, response validation, SQLite access, record editing, error messages, and export generation. |
| `expo.py` | Example prompts for the live assistant. |
| `assets/` | Campus photos, PDF font, image source notes, and font license. |
| `.streamlit/config.toml` | Maroon-and-gold theme configuration. |
| `requirements.txt` | Runtime dependency requirements. |
| `tests/` | Storage, export, error-handling, and interface tests. |
| `.env` | Local API configuration; excluded from Git. |
| `.gitignore` | Excludes secrets, databases, virtual environments, and local caches. |
| `README.md` | Setup and operating instructions. |
| `DEVELOPMENT_README.md` | This development and technology overview. |

### 8. Test and refine

Development included automated checks for database migration, record ownership, duplicate handling, invalid dates, calendar alarms, safe exports, conversation flow, task editing, visitor reset, and completion stars.

AI requests are mocked in interface tests so those checks do not spend API quota. The app was also checked in a running Streamlit instance, the browser layout was inspected, and a generated PDF was rendered for visual review.

Typical verification commands:

```sh
python -m unittest discover -s tests
mypy app.py recall.py expo.py --ignore-missing-imports --check-untyped-defs
```

Real Gemini availability, browser microphone permissions, and calendar notifications still depend on external services and device settings.

### 9. Prepare sharing and deployment

The source was committed with Git and pushed to [darmeydm/CampusRecall](https://github.com/darmeydm/CampusRecall). The API key and local task database were excluded.

GitHub stores the source code. GitHub Pages cannot directly run this Python Streamlit app. Streamlit Community Cloud was selected as the deployment route, using the `main` branch and `app.py` as the entry point. The hosted API key belongs in the platform's Secrets settings rather than the repository.

## What happens during a request

1. The visitor submits text, audio, or an image through Capture.
2. The app checks that input and server-side API configuration are available.
3. It sends Gemini the submission, recent conversation, current drafts, saved records in the active workspace, and the current Chicago time.
4. Gemini returns JSON containing a reply and suggested records.
5. Python checks the response and normalizes titles, categories, kinds, and dates.
6. The app opens Review when there are draft cards. The user can edit details or return to the conversation for clarification.
7. Confirmed items are saved to visitor session state or the Personal SQLite database.
8. The user completes tasks, earns stars, recalls saved information, or exports a takeaway.

This is an AI-assisted workflow with user confirmation. It does not independently contact people, book events, or change a calendar.

## Storage and privacy

- **Visitor mode:** Items stay in the current Streamlit session and can disappear when that session is reset or lost. There are no visitor accounts or cross-device synchronization.
- **Personal mode:** Records persist in local SQLite storage. This mode is hidden by default and is intended for local use; it does not provide account authentication.
- **Credentials:** Server environment variables take precedence over `.env`, with Streamlit secrets as a fallback. The key is not shown in the website's input controls.
- **AI processing:** Submitted content and the supplied workspace context are sent to Gemini when the assistant is invoked. Saved records are supplied directly as context; the app does not use a vector database or train a custom model.

## A short explanation for the expo

> “CampusRecall is a Python web app built with Streamlit and powered by Gemini. It turns everyday messages, screenshots, and spoken thoughts into tasks and memories. Users review the suggestions, save what matters, and take away a printable card or calendar event. We use SQLite for local personal storage, session state for visitors, and a star system to celebrate completed tasks.”
