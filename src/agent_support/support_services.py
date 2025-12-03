import json
import logging
import uuid

from http import HTTPStatus
from typing import Any, List, Optional, Union

from google.protobuf import struct_pb2 as _struct_pb2

from a2a.types import (
    TaskState,
    Message,
    Role,
    TextPart,
    TaskStatusUpdateEvent,
    TaskStatus,
    DataPart,
    Part,
)
from a2a.utils import new_agent_text_message

from . import ServiceConfig
from .entities import ListSessionsRequest
from .storage import FirestoreSessionService

logger = logging.getLogger(__name__)


def convert_session_to_streaming_events(session: Any) -> List[dict[str, Any]]:
    """
    Convert session events into the same format as the streaming response.
    
    This function transforms session events from Firestore into the format used
    by the streaming API for consistency. Only agent responses are included
    (user messages are filtered out).
    
    Args:
        session: Session object with events and state
        
    Returns:
        List of events in streaming format with keys:
        - agent: event author
        - type: "function_call", "function_response", "text", or "json"
        - content: the actual content
        - function_name: name of the function if applicable
        - lastResponse: boolean (True for final response)
        - state: current state (for final responses)
    """
    events = session.events if hasattr(session, "events") else []
    session_state = session.state if hasattr(session, "state") else {}
    
    streaming_events = []
    
    # Filter out user messages and track agent events only
    agent_events = []
    for event in events:
        author = getattr(event, "author", None)
        if author:
            agent_events.append(event)
    
    if not agent_events:
        return streaming_events
    
    # Track the last event that updates data_analyst_response to mark it as final
    last_data_analyst_event_idx = None
    for idx, event in enumerate(agent_events):
        if hasattr(event, "actions") and event.actions:
            # Try to access state_delta from EventActions
            state_delta = None
            if hasattr(event.actions, "state_delta"):
                state_delta = event.actions.state_delta
            elif hasattr(event.actions, "__dict__"):
                state_delta = getattr(event.actions, "state_delta", None)
            
            if state_delta and isinstance(state_delta, dict):
                if "data_analyst_response" in state_delta:
                    last_data_analyst_event_idx = idx
    
    # If no data_analyst_response found, mark the last agent event as final
    if last_data_analyst_event_idx is None and agent_events:
        last_data_analyst_event_idx = len(agent_events) - 1
    
    for idx, event in enumerate(agent_events):
        if not hasattr(event, "content") or not event.content:
            continue
        if not hasattr(event.content, "parts") or not event.content.parts:
            continue
            
        is_final = (idx == last_data_analyst_event_idx)
        author = getattr(event, "author", None)
        
        for part in event.content.parts:
            # Handle function calls
            if hasattr(part, "function_call") and getattr(part, "function_call", None):
                function_call = part.function_call
                function_name = None
                if hasattr(function_call, "name"):
                    function_name = function_call.name
                elif isinstance(function_call, dict):
                    function_name = function_call.get("name")
                
                streaming_events.append({
                    "agent": author,
                    "type": "function_call",
                    "content": f"Running '{function_name}'...",
                    "function_name": function_name,
                    "lastResponse": False,
                    "timestamp": getattr(event, "timestamp", None),
                })
            
            # Handle function responses
            elif hasattr(part, "function_response") and getattr(part, "function_response", None):
                function_response = part.function_response
                function_name = None
                if hasattr(function_response, "name"):
                    function_name = function_response.name
                elif isinstance(function_response, dict):
                    function_name = function_response.get("name")
                
                streaming_events.append({
                    "agent": author,
                    "type": "function_response",
                    "content": f"Finished running '{function_name}'.",
                    "function_name": function_name,
                    "lastResponse": False,
                    "timestamp": getattr(event, "timestamp", None),
                })
            
            # Handle text content
            elif hasattr(part, "text") and getattr(part, "text", None):
                text_content = part.text
                if not text_content:
                    continue
                
                # Check if it's a partial/streaming response
                is_partial = False
                if hasattr(event, "partial"):
                    partial_val = event.partial
                    is_partial = partial_val is True
                
                # For partial responses, yield as streaming text
                if is_partial:
                    streaming_events.append({
                        "agent": author,
                        "type": "text",
                        "content": text_content,
                        "function_name": None,
                        "lastResponse": False,
                        "timestamp": getattr(event, "timestamp", None),
                    })
                else:
                    # For complete responses, try to parse as JSON
                    try:
                        parsed_content = json.loads(text_content)
                        response_type = "json"
                        final_content = parsed_content
                    except (json.JSONDecodeError, TypeError, AttributeError):
                        response_type = "text"
                        final_content = text_content
                    
                    # Build the response event
                    response_event = {
                        "agent": author,
                        "type": response_type,
                        "content": final_content,
                        "function_name": None,
                        "lastResponse": is_final,
                        "timestamp": getattr(event, "timestamp", None),
                    }
                    
                    # Include state for final responses
                    if is_final:
                        response_event["state"] = session_state
                    
                    streaming_events.append(response_event)
    
    return streaming_events


def _serialize_message(msg: Message) -> dict[str, Any]:
    """Serialize A2A Message to dictionary."""
    result = {
        "role": str(msg.role) if hasattr(msg, "role") else None,
        "message_id": msg.message_id if hasattr(msg, "message_id") else None,
        "task_id": msg.task_id if hasattr(msg, "task_id") else None,
        "context_id": msg.context_id if hasattr(msg, "context_id") else None,
    }
    
    # Handle parts
    if hasattr(msg, "parts") and msg.parts:
        parts_list = []
        for part in msg.parts:
            part_dict = {}
            if hasattr(part, "root"):
                root = part.root
                if hasattr(root, "text") and root.text:
                    part_dict["text"] = root.text
                elif hasattr(root, "data") and root.data:
                    part_dict["data"] = root.data
            parts_list.append(part_dict)
        result["parts"] = parts_list
    elif hasattr(msg, "text") and msg.text:
        result["text"] = msg.text
    
    # Handle metadata (protobuf Struct)
    if hasattr(msg, "metadata") and msg.metadata:
        if isinstance(msg.metadata, _struct_pb2.Struct):
            # Convert protobuf Struct to dict
            result["metadata"] = dict(msg.metadata)
        elif hasattr(msg.metadata, "__dict__"):
            result["metadata"] = dict(msg.metadata.__dict__)
        elif isinstance(msg.metadata, dict):
            result["metadata"] = msg.metadata
    
    return result


def _serialize_a2a_event(event: Union[TaskStatusUpdateEvent, dict[str, Any]]) -> dict[str, Any]:
    """
    Serialize A2A event to JSON-serializable dictionary.
    
    Args:
        event: A2A event (TaskStatusUpdateEvent or dict)
        
    Returns:
        JSON-serializable dictionary representation
    """
    if isinstance(event, dict):
        # Already a dict, but need to serialize nested A2A objects
        result = {}
        for key, value in event.items():
            if key == "message" and isinstance(value, Message):
                result[key] = _serialize_message(value)
            elif key == "state" and isinstance(value, TaskState):
                result[key] = value.name if hasattr(value, "name") else str(value)
            elif key == "metadata" and isinstance(value, _struct_pb2.Struct):
                result[key] = dict(value)
            else:
                result[key] = value
        return result
    elif isinstance(event, TaskStatusUpdateEvent):
        # Serialize TaskStatusUpdateEvent
        result = {
            "type": "task_status_update",
            "status": {
                "state": event.status.state.name if hasattr(event.status.state, "name") else str(event.status.state),
            },
            "final": event.final,
            "context_id": event.context_id,
            "task_id": event.task_id,
        }
        
        # Serialize message
        if hasattr(event.status, "message") and event.status.message:
            result["status"]["message"] = _serialize_message(event.status.message)
        
        return result
    else:
        # Fallback: try to convert to dict
        if hasattr(event, "to_dict"):
            return event.to_dict()
        elif hasattr(event, "__dict__"):
            return event.__dict__
        else:
            return {"error": "Unable to serialize event"}


def convert_streaming_events_to_a2a_format(
    streaming_events: List[dict[str, Any]], 
    context_id: str,
    task_id: Optional[str] = None
) -> List[Union[TaskStatusUpdateEvent, dict[str, Any]]]:
    """
    Convert streaming events to A2A format as used in PilotXAgentExecutor.
    
    This function transforms streaming events into the A2A message format that
    matches what the agent executor produces. Uses actual A2A types.
    
    Args:
        streaming_events: List of streaming events from convert_session_to_streaming_events
        context_id: Session/context ID for the messages
        task_id: Optional task ID for the messages
        
    Returns:
        List of A2A-formatted events with TaskStatusUpdateEvent and status update dicts
    """
    a2a_events = []
    final_state = None
    
    # Generate task_id once if not provided
    task_id = task_id or str(uuid.uuid4())
    
    # Store events with their timestamps for sorting
    events_with_timestamps = []
    seq = 0
    for event in streaming_events:
        seq = int(seq + 1)
        if not event.get("content"):
            continue
        
        event_type = event.get("type")
        last_response = event.get("lastResponse", False)
        agent = event.get("agent")
        content = event.get("content")
        function_name = event.get("function_name")
        timestamp = event.get("timestamp")
        role = Role.user if agent == "user" else Role.agent
        
        # Generate message ID for each event
        message_id = str(uuid.uuid4())
        
        if last_response:
            # For lastResponse events, create message with metadata
            # Similar to updater.update_status(TaskState.working, message=message, metadata=metadata)
            if event_type == "text":
                message = new_agent_text_message(
                    text=content,
                    context_id=context_id,
                    task_id=task_id,
                )
            elif event_type == "json":
                message = Message(
                    role=role,
                    parts=[Part(root=DataPart(data=content))],
                    message_id=message_id,
                    task_id=task_id,
                    context_id=context_id,
                )
            else:
                # Default to text for other types
                message = new_agent_text_message(
                    text=str(content),
                    context_id=context_id,
                    task_id=task_id,
                )
            
            metadata = {
                "type": event_type,
                "finished": False,
                "lastResponse": last_response,
                "agent": agent,
                "sequenceNo": seq,
            }
            
            # Store as dict for JSON serialization (matching updater.update_status pattern)
            events_with_timestamps.append({
                "event": {
                    "type": "status_update",
                    "state": TaskState.working,
                    "message": message,
                    "metadata": metadata,
                },
                "timestamp": timestamp,
            })
            
            # Store state if present for final status update
            if "state" in event:
                final_state = event["state"]
        else:
            # For partial/streaming responses, create TaskStatusUpdateEvent
            metadata = _struct_pb2.Struct()
            metadata.update(
                {
                    "type": event_type,
                    "lastResponse": last_response,
                    "finished": False,
                    "agent": agent,
                    "function_name": function_name,
                    "sequenceNo": seq,
                }
            )
            
            # Create parts based on type
            if event_type == "json":
                parts = [Part(root=DataPart(data=content))]
            else:
                parts = [Part(root=TextPart(text=content))]
            
            message = Message(
                role=role,
                parts=parts,
                message_id=message_id,
                task_id=task_id,
                context_id=context_id,
                metadata=metadata,
            )
            
            events_with_timestamps.append({
                "event": TaskStatusUpdateEvent(
                    status=TaskStatus(
                        state=TaskState.working,
                        message=message,
                    ),
                    final=False,
                    context_id=context_id,
                    task_id=task_id,
                ),
                "timestamp": timestamp,
            })
    
    # Add final status update if we have state (matching the executor's final update)
    if final_state is not None:
        final_message = new_agent_text_message(
            text="done",
            context_id=context_id,
            task_id=task_id,
        )
        
        final_metadata = {
            **final_state,
            "type": "status",
            "lastResponse": True,
            "turnComplete": True,
            "agent": "Orchestrator",
            "sequenceNo": int(seq + 1),
        }
        
        # Use the last timestamp from events, or None if no events
        final_timestamp = (
            max(
                (e["timestamp"] for e in events_with_timestamps if e["timestamp"] is not None),
                default=None
            )
            if events_with_timestamps
            else None
        )
        
        events_with_timestamps.append({
            "event": {
                "type": "status_update",
                "state": TaskState.completed,
                "message": final_message,
                "metadata": final_metadata,
            },
            "timestamp": final_timestamp,
        })
    
    # Sort events by timestamp (ascending order), handling None timestamps
    def get_sort_key(item: dict[str, Any]) -> float:
        timestamp = item.get("timestamp")
        if timestamp is None:
            # Put None timestamps at the end
            return float('inf')
        return float(timestamp)
    
    events_with_timestamps.sort(key=get_sort_key)
    
    # Extract just the events in sorted order
    a2a_events = [item["event"] for item in events_with_timestamps]
    
    return a2a_events


class AgentSupportService:
    def __init__(self):
        self.app_name = ServiceConfig.get_or_create_instance().appName
        self.conversations = FirestoreSessionService()

    async def list_sessions(self, request: ListSessionsRequest, user_id: str) -> dict:
        sessions, cursor = await self.conversations.list_sessions(
            app_name=self.app_name,
            user_id=user_id,
            page_size=request.pageSize,
            cursor=request.cursor,
        )
        return {"sessions": sessions.model_dump().get("sessions"), "cursor": cursor}

    async def get_session(self, session_id: str, user_id: str) -> dict:
        session = await self.conversations.get_session(
            app_name=self.app_name,
            user_id=user_id,
            session_id=session_id,
        )
        # Convert session events into streaming format
        streaming_events = convert_session_to_streaming_events(session)
        # Convert streaming events to A2A format
        a2a_events = convert_streaming_events_to_a2a_format(
            streaming_events=streaming_events,
            context_id=session_id,
        )
        # Serialize A2A events to JSON-serializable format
        serialized_events = [_serialize_a2a_event(event) for event in a2a_events]

        return {
            "id": session.id if hasattr(session, "id") else session_id,
            "app_name": session.app_name if hasattr(session, "app_name") else self.app_name,
            "user_id": session.user_id if hasattr(session, "user_id") else user_id,
            "state": session.state if hasattr(session, "state") else {},
            "events": serialized_events,
            "last_update_time": (
                session.last_update_time 
                if hasattr(session, "last_update_time") 
                else None
            ),
        }
