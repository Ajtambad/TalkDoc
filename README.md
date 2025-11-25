# TalkDocAI
AI assisted document filler

## Overview

A simple system that lets users upload a document, answer questions through a chat interface, and download a completed version of the document. The backend extracts placeholders, asks the user for the required information, fills the document, and returns the final file.

## How It Works

#### Upload
User uploads a document to `/uploadfile/`. The backend creates a session, extracts placeholders, and generates the first question.

<img width="1918" height="795" alt="TalkDoc Landing Page" src="https://github.com/user-attachments/assets/9e2e1644-9b6f-44d7-b3f0-c95491c4baec" />

#### Chat
The frontend sends each user response to `/chat/` with the session ID.
The backend saves history, updates the document, and returns the next question until all fields are complete.

<img width="1918" height="892" alt="TalkDoc Chat Page" src="https://github.com/user-attachments/assets/c11077c6-d50b-4b7b-ac6c-8071645f5489" />

#### Download
Once finished, the user downloads the filled document via `/download/{session_id}`.

<img width="1918" height="892" alt="TalkDoc Download Document" src="https://github.com/user-attachments/assets/e1465f97-0a7a-4d3e-9827-69ec81ff0cba" />

## Endpoints

`POST /uploadfile/` – start session and extract placeholders

`POST /chat/`– send response and receive next question

`GET /download/{session_id}` – download final document

<img width="2774" height="1116" alt="Untitled-2025-11-24-2239" src="https://github.com/user-attachments/assets/8ef61f79-83d7-4048-ba99-b90f64de36fb" />
