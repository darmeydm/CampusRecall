# CampusRecall

Capture a thought, clarify it, confirm what matters, and take it with you. Built with Streamlit and Gemini, with a maroon-and-gold expo interface.

## Start locally

Python 3.10+:

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Put your Gemini key in `.env` in the project folder. The key is loaded on the server and no key field is shown on the website:

```dotenv
GEMINI_API_KEY = "your-key-here"
```

Environment variables take precedence over `.env`; Streamlit secrets are also supported as a fallback. `.env` is ignored by Git. Never commit secrets. The default model is `gemini-2.5-flash-lite`; Set the GEMINI_MODEL environment variable to use a different model.

## Expo walkthrough

1. Ask: “What is one thing you don't want to forget today?” Expo mode is enabled by default and hides Personal mode entirely.
2. Choose a sample, type a thought, record your voice, or upload a screenshot. Click **Help me remember**.
3. The app opens a separate **Review** screen with organized cards. Answer any clarification through **Back to conversation**, then return to Review.
4. Use the **date picker** and optional **time picker**. A date without a time becomes an all-day plan. No date means unscheduled. Memories ignore scheduling fields. Dates use America/Chicago.
5. Choose **Remind me**: no reminder, at the scheduled time, 10 or 30 minutes before, an hour before, or a day before. Timed reminders require both date and time. Choose the calendar event length: 15–120 minutes.
6. Save reviewed items. Open **My recall** or **Today** to complete, delete, or **Edit saved item**. Edits include title, kind, category, scheduling, and reminder settings.
7. Download a printable **PDF recall card**, CSV, or calendar file from **Take away**. Individual scheduled cards also have calendar actions.
8. Click **Next visitor · clear session** between visitors. It clears visitor items, conversation, drafts, attachments, and previous input.

### Calendar reminders

**Calendar + reminder** downloads an `.ics` file containing the selected alert (`VALARM`). Import it into your calendar, then check that your calendar retained the alert and that notifications are enabled on your device. Calendar apps differ in how they treat imported alerts.

**Add to Google Calendar** opens a prefilled event for you to review and save. It uses the calendar's default notification settings; the link does not transfer CampusRecall's custom reminder choice. Use the `.ics` download to carry that preference.

Date-only plans export as all-day events without a timed alert. Unscheduled tasks, memories, and completed tasks are excluded from calendar exports. Event length is user-selected, not inferred from the conversation. CampusRecall does not send background notifications, messages, or emails.

## Personal workspace

Expo mode is on by default. To access your saved local Personal workspace outside the event, stop the server and run:

```sh
CAMPUSRECALL_EXPO_MODE=false streamlit run app.py
```

Restart normally for the expo. There is no in-app switch to disable expo protection. This is local configuration, not multi-user authentication; do not expose Personal mode publicly.

Existing `campusrecall.db` tasks migrate in place, preserving their data and adding reminder/duration fields. For automated checks, `CAMPUSRECALL_DB` selects separate storage. Visitor items stay in the current Streamlit session and disappear when it is reset or lost. Download before leaving.

## Privacy and device setup

Gemini receives submitted content/attachments, the current conversation, drafts, and saved records in the active workspace only when the live assistant is invoked. Use fictional or consented information. API usage may incur charges.

Microphone capture needs browser permission and localhost or HTTPS. Only one attachment per request, up to 15 MB. Check the microphone on your expo device before presenting.

The interface uses ULM's maroon and gold palette and campus photography. See [asset sources and font license](assets/SOURCES.md). CampusRecall is a student project, not an official university service. The bundled PDF font supports common Latin characters; not every script or emoji is available.

## Checks

```sh
python -m unittest discover -s tests
mypy app.py recall.py expo.py --ignore-missing-imports --check-untyped-defs
```

Tests cover legacy migration, owner-scoped saving/editing, duplicates, invalid dates, calendar alarms, all-day export, safe CSV/PDF generation, conversation flow, visitor reset, and date/reminder editing. Automated UI tests use mocked AI and isolated/session storage. Live Gemini and device notifications still need manual checks.

## Interface and stars

Capture stays focused on the conversation. Review is a separate screen with two-column cards, grouped scheduling controls, and expandable source context. After saving, the app opens My recall.

The locally bundled ULM photo banner rotates every eight seconds in an isolated Streamlit fragment; photo refreshes do not rerun capture or review forms.

Each currently completed task counts as one star. A toast celebrates completion. Reopening, deleting, or changing a completed task into a memory removes that star; repeated completion does not accumulate extra stars. Personal stars are derived from saved completion status. Visitor stars reset with the visitor session. Memories do not earn completion stars.
