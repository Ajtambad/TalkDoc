from spire.doc import *
from spire.doc.documents import *
from openai import OpenAI
from pydantic import BaseModel
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import os
from tempfile import NamedTemporaryFile
import json
import asyncio
import random
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
FRONTEND_URL = os.getenv("REACT_APP_FRONTEND_URL")
BACKEND_URL = os.getenv('BACKEND_URL')

origins = [FRONTEND_URL, BACKEND_URL]

client = OpenAI(api_key=OPENAI_API_KEY)

sessions = {}

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    user_response: str
    index: int

class Placeholder(BaseModel):
    placeholder_text: str
    context:str
    field_name: str

class ResponseFormat(BaseModel):
    placeholders: list[Placeholder]


def create_session(document):
    with open('v4_uuids.txt') as f:
        session_id = str(random.choice(f.readlines()).strip())

    placeholders = []

    sessions[session_id] = {
        "document":document,
        "placeholders":placeholders,
        "conversation_history":[],
        "collected_data":[],
        "current_state": "initial",
    }

    return session_id

def add_to_history(session_id, user_response):
    sessions[session_id]["conversation_history"].append({"role": "user", "content": user_response})
    return

async def analyze_user_response(session_id):
    prompt = """
    
    Based on the conversation history and the user's latest response in it, return a json response with the following fields:

    {
        "message": "response to user",
        "action": "skip/clarify/next_field",
        "field_update": {
                        "field_name": 
                        "value": 
                        }
        }
    }

    Make sure the field_name is the placeholder we are looking to fill.
    Determine the action field based on the following scenarios:

    1. If the answer is appropriate for the question asked and can help with filling the appropriate placeholder, mark action as "next_field"
    2. If the answer seems incorrect or inappropriate or if there are ambiguities and more questions need to be asked for better clarity, mark action as "clarify" and mark field_name within field_update as null
    3. If the user indicates the current field is not actually a placeholder or shouldn't be filled, mark action as "skip" and mark field_name within field_update as null
    4. Make sure the json format specified is followed accurately. 
    """

    llm_response = client.chat.completions.create(
        model="gpt-5-nano",
        messages=[
            {"role": "system", "content": prompt},
            {
                "role": "user",
                "content": f"Conversation History: {sessions[session_id]["conversation_history"]}",
            },
        ],
    )

    response_text = llm_response.choices[0].message.content
    response_json = json.loads(response_text)
    action = response_json["action"]
    field_update = response_json["field_update"]

    return action, field_update

def update_field(session_id: str, field_update: str, index: int):
    sessions[session_id]["collected_data"].append(field_update)
    document = sessions[session_id]["document"]
    section_idx, paragraph_idx = sessions[session_id]["placeholders"][index]["section_idx"], sessions[session_id]["placeholders"][index]["paragraph_idx"]
    paragraph = document.Sections[section_idx].Paragraphs[paragraph_idx]
    placeholder_text, user_response = sessions[session_id]["placeholders"][index]["placeholder_text"], field_update["value"]
    print(f"Pre updated Paragraph: {paragraph.Text}")
    # paragraph.Text = paragraph.Text.replace(placeholder_text, str(user_response))
    paragraph.Replace(placeholder_text, str(user_response), False, False)
    document.Sections[section_idx].Paragraphs[paragraph_idx].Text = paragraph.Text
    print(f"Updated Paragraph: {paragraph.Text}")
    return


@app.get("/download/{session_id}")
async def download_document(session_id: str):

    file_path = f"updated_document.docx"
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(
        path = file_path,
        filename = f"updated_document_{session_id}",
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )

@app.get("/")
async def root():
    return {"message": "Hello World"}


    
@app.post("/uploadfile/")
async def upload_file(file: UploadFile = File(...)):
    
    with NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    document = Document()
    document.LoadFromFile(tmp_path)

    os.remove(tmp_path)

    session_id = create_session(document) #Create a new session and get the session ID.
    print(f"session_id: {session_id}")
    sessions[session_id]["placeholders"] = await compile_placeholders(client, document) #Extract placeholders and store in session.
    
    if sessions[session_id]["placeholders"]:
        first_question = await generate_first_question(session_id)
        return {"session_id": session_id, "message": first_question}
    else:
        return {"session_id": session_id, "message": "No placeholders found in the document. Please upload a different document."}

async def generate_first_question(session_id):
    placeholders = sessions[session_id]["placeholders"]
    placeholder = placeholders[0]

    prompt = """
    You are an intelligent conversational assistant helping users fill out placeholders in a document. 
    Generate a question based on the placeholder and the context provided. Refer to the following guidelines: 
    
    - This is the first question to be presented to the user, so make sure to greet them and provide a brief overview of how you're going to ask them questions and help them fill the document based on your answers.
    - The question should be asked with the intent to fill in the blank/missing information.  
    - Make sure to reference the placeholder in the question so the user knows which placeholder is being referred to.

    """

    question = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": prompt},
            {
                "role": "user",
                "content": f"Placeholder: {placeholder["placeholder_text"]}\nContext: {placeholder["context"]}",
            },
        ],
    )

    first_question = question.choices[0].message.content
    sessions[session_id]["conversation_history"].append({"role": "assistant", "content": first_question})
    sessions[session_id]["current_state"] = "collecting"

    return first_question

    
async def generate_questions_with_context(session_id, action, index):

    if index >= len(sessions[session_id]["placeholders"]):
        return ''


    placeholders = sessions[session_id]["placeholders"]
    
    collected_data = sessions[session_id]["collected_data"]
    conversation_history = sessions[session_id]["conversation_history"]

    prompt = f""" 
            You are an intelligent legal document assistant helping users fill out a document with placeholders.
            Generate a question based on the placeholder and the context provided. Refer to the following guidelines: 

            - Guide users through filling required fields conversationally
            - Ask clarifying questions when answers are unclear or potentially incorrect
            - Provide context when users seem confused
            - Be professional but friendly

            Already collected: {collected_data}
            Conversation so far: {conversation_history}
            action to be taken based on analysis of user's answer: {action}
            current placeholder to ask the question about: {placeholders[index]["placeholder_text"]}
                                
            Based on the user's last message and the action determined after user response analysis, make one of these decisions:
            1. If action says "clarify" - ask follow-up questions, point out if the answer feels incorrect/inappropriate or provide more information if the user has asked for clarity. Determine your response based on context from all the data being provided to you.
            2. If action says "next_field", acknowledge and ask questions about the placeholder being passed currently. Take help of the all the information being provided to frame your question.

            In terms of asking questions, follow these guidelines:
            - The question should be asked with the intent to fill in the placeholder.  
            - Make sure to reference the placeholder in the question so the user knows which placeholder is being referred to.
            - Make sure you ask the question ONLY about the placeholder in question, especially if there are multiple placeholders in that particular paragraph. Provide additional context if asked. 
            """

    question = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": prompt},
            {
                "role": "user",
                "content": f"Placeholder: {placeholders[index]["placeholder_text"]}\nContext: {placeholders[index]["context"]}",
            },
        ],
    )

    question = question.choices[0].message.content
    sessions[session_id]["conversation_history"].append({"role": "assistant", "content": question})

    return question

async def extract_placeholders(client, paragraph, section_idx, paragraph_idx):
    response = client.responses.parse(
                model="gpt-5-mini",
                input=[
                    {"role": "system", "content": "Extract the placeholders from the text and provide surrounding context (the sentence containing the placeholder. Use as much around it as necessary). If there are no placeholders, return empty string for placeholder_text. Placeholders are generally of the 'form ____', '[text]', 'text:_______', 'text:   ', etc. Do not mistake normal text for placeholders. When in doubt, assume something is a placeholder."},
                    {
                        "role": "user",
                        "content": paragraph.Text,
                    },
                ],
                store=False,
                text_format=ResponseFormat,
            )
    
    return response, section_idx, paragraph_idx

async def compile_placeholders(client, document):
    placeholders = []

    tasks = []
    for i in range(document.Sections.Count):
        section = document.Sections[i]
        for j in range(section.Paragraphs.Count):
            paragraph = section.Paragraphs[j]

            if not paragraph.Text:
                continue
            
            tasks.append(extract_placeholders(client, paragraph, i, j))
        
    results = await asyncio.gather(*tasks)

    for response, section_idx, paragraph_idx in results:
        for placeholder in response.output_parsed.placeholders:
            if placeholder.placeholder_text:
                placeholders.append({"placeholder_text": placeholder.placeholder_text, "context": placeholder.context, "section_idx": int(section_idx), "paragraph_idx": int(paragraph_idx) })


    return placeholders

@app.post("/chat/")
async def chat(session_id: str, data: ChatRequest):
    user_response, index = data.user_response, data.index

    print(user_response, index)
    if sessions[session_id]["current_state"] == "collecting":
        add_to_history(session_id, user_response)
        action, field_update = await analyze_user_response(session_id)
        if field_update and field_update["field_name"] and action == "next_field":
            update_field(session_id, field_update, index)
            index += 1
        if action == "skip":
            index += 1
            action = "next_field"
        question = await generate_questions_with_context(session_id, action, index)
        if question:
            return {"completed": False, "message": question, "next_index": index}
        else:
            sessions[session_id]["current_state"] = "complete"
    
    if sessions[session_id]["current_state"] == "complete":
        document = sessions[session_id]["document"]
        document.SaveToFile("updated_document.docx", FileFormat.Docx)      
        return {"completed": True, "message": "File is ready for download", "next_index": index}