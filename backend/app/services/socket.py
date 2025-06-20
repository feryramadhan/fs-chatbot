from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import boto3
import json
import botocore
from dotenv import load_dotenv
import os

load_dotenv()

router = APIRouter()

region = os.getenv("AWS_REGION")
access_key_id = os.getenv("ACCESS_KEY_ID")
secret_access_key = os.getenv("SECRET_ACCESS_KEY")
agent_id = os.getenv("AGENT_ID")
agent_alias_id = os.getenv("AGENT_ALIAS_ID")
session_id = os.getenv("SESSION_ID")

bedrock_agent_runtime = boto3.client(
    'bedrock-agent-runtime',  # Use agent service
    region_name=region,
    aws_access_key_id=access_key_id,
    aws_secret_access_key=secret_access_key,
)

def process_event_stream(event_stream):
    """Helper function to process event stream from response"""
    completion = ""
    if event_stream:
       for event in event_stream:
            if 'chunk' in event:
               completion += event['chunk']['bytes'].decode('utf-8')
    return completion


async def process_bedrock_response(response):
    completion = ""
    if 'completionStream' in response:
       completion =  process_event_stream(response['completionStream'])

    elif 'completion' in response:
          if isinstance(response['completion'], dict) and  'bytes' in  response['completion']:
              completion =  response['completion']['bytes'].decode('utf-8')

          elif isinstance(response['completion'], botocore.eventstream.EventStream):
              completion= process_event_stream(response['completion'])

          elif isinstance(response['completion'], str):
              completion = response['completion']

          else:
               completion=  "Error: Unexpected response format in completion key"
    else :
       completion ="Error: Unable to process response"

    return completion


@router.websocket("/ws/bedrock-chat")
async def websocket_bedrock_agent(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            request_data = json.loads(data)
            
            try:
                response = bedrock_agent_runtime.invoke_agent(
                    agentId=agent_id,  
                    agentAliasId=agent_alias_id, 
                    sessionId=session_id,
                    inputText=request_data.get("content", "")
                )
                
                # Parse response from agent
                completion = await process_bedrock_response(response)
                
                # Send response to client
                await websocket.send_text(json.dumps({
                    "response": completion
                }))

            except Exception as e:
                await websocket.send_text(json.dumps({
                    "error": str(e)
                }))

    except WebSocketDisconnect:
        print("WebSocket disconnected")