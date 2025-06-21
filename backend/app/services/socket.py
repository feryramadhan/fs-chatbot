from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import boto3
import json
import botocore
from dotenv import load_dotenv
import asyncio
import os

load_dotenv()

router = APIRouter()

region = os.getenv("AWS_REGION")
access_key_id = os.getenv("ACCESS_KEY_ID")
secret_access_key = os.getenv("SECRET_ACCESS_KEY")
agent_id = os.getenv("AGENT_ID")
agent_alias_id = os.getenv("AGENT_ALIAS_ID")
session_id = os.getenv("SESSION_ID")
guardrail_id = os.getenv("GUARDRAIL_ID")
guardrail_version = os.getenv("GUARDRAIL_VERSION")

bedrock_agent_runtime = boto3.client(
    'bedrock-agent-runtime',  # Use agent service
    region_name=region,
    aws_access_key_id=access_key_id,
    aws_secret_access_key=secret_access_key,
)

bedrock_runtime = boto3.client(
    'bedrock-runtime',
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


async def apply_guardrail(text, guardrail_id, guardrail_version="DRAFT"):
    """Apply guardrail to text using ApplyGuardrail API"""
    try:
        response = bedrock_runtime.apply_guardrail(
            guardrailIdentifier=guardrail_id,
            guardrailVersion=guardrail_version,
            content=[{"text": {"text": text}}],  
            enableTrace=True
        )
        
        # Log result guardrail
        if response.get('usage'):
            print(f"Guardrail usage: {response['usage']}")
        
        # Check if content is filtered
        if response.get('results', {}).get('contentFilterResults', {}).get('filtered', False):
            return None
        
        # If not filtered, return processed output
        return response.get('output', {}).get('text', text)
    
    except Exception as e:
        print(f"Error applying guardrail: {str(e)}")
        # If error, return original text
        return text

async def process_bedrock_response(response):
    """Process response from Bedrock agent and apply guardrail if configured"""
    completion = ""
    if 'completionStream' in response:
       completion = process_event_stream(response['completionStream'])
    elif 'completion' in response:
        if isinstance(response['completion'], dict) and 'bytes' in response['completion']:
            completion = response['completion']['bytes'].decode('utf-8')
        elif isinstance(response['completion'], botocore.eventstream.EventStream):
            completion = process_event_stream(response['completion'])
        elif isinstance(response['completion'], str):
            completion = response['completion']
        else:
            completion = "Error: Unexpected response format"
    else:
        completion = "Error: Unable to process response"
    
    # Apply guardrail if ID is available
    if guardrail_id and completion:
        try:
            response = bedrock_runtime.apply_guardrail(
                guardrailIdentifier=guardrail_id,
                guardrailVersion=guardrail_version,
                content=[{"text": {"text": completion}}],
                source="INPUT" 
            )
            
            # Check if content was filtered
            if response.get('results', {}).get('contentFilterResults', {}).get('filtered', False):
                return None
            
            # Return processed output
            print("Guardrail applied successfully")
            return response.get('output', {}).get('text', completion)
        except Exception as e:
            print(f"Error applying guardrail: {str(e)}")
    
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
                    inputText=request_data.get("content", ""),
                    enableTrace=True
                )
                
                completion = await process_bedrock_response(response)
                
                await websocket.send_text(json.dumps({
                    "response": completion
                }))

            except Exception as e:
                await websocket.send_text(json.dumps({
                    "error": str(e)
                }))

    except WebSocketDisconnect:
        print("WebSocket disconnected")