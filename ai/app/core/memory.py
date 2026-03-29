"""Patient Session and Memory Management."""

import json
import logging
import uuid
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class PatientSession(BaseModel):
    """Represents an active patient reasoning session."""
    session_id: str
    structured_data: Dict[str, Any]
    history: List[Dict[str, str]] = []

    def add_interaction(self, user_query: str, assistant_response: str):
        self.history.append({"role": "user", "content": user_query})
        self.history.append({"role": "assistant", "content": assistant_response})
        
        # Prevent context window explosion: Keep last 10 turns (5 Q/A pairs)
        if len(self.history) > 10:
            self.history = self.history[-10:]

    def format_context_for_prompt(self) -> str:
        """Dynamically formats the patient data to be injected into the RAG prompt."""
        
        # We want to highlight abnormal labs specifically for the LLM
        abnormal_labs = [
            lab for lab in self.structured_data.get("labs", [])
            if lab.get("flag") in ["High", "Low", "Critical"]
        ]
        
        context_str = f"--- PATIENT DEMOGRAPHICS ---\n"
        demo = self.structured_data.get("demographics", {})
        context_str += f"Age: {demo.get('age', 'Unknown')}, Gender: {demo.get('gender', 'Unknown')}\n\n"
        
        context_str += f"--- ACTIVE PROBLEMS & HISTORY ---\n"
        context_str += f"Problems: {', '.join(self.structured_data.get('active_problems', []))}\n"
        context_str += f"Narrative: {self.structured_data.get('unstructured_narrative', '')}\n\n"
        
        context_str += f"--- MEDICATIONS & ALLERGIES ---\n"
        context_str += f"Medications: {', '.join(self.structured_data.get('medications', []))}\n"
        context_str += f"Allergies: {', '.join(self.structured_data.get('allergies', []))}\n\n"
        
        if abnormal_labs:
            context_str += f"!!! ABNORMAL / CRITICAL LABS !!!\n"
            for lab in abnormal_labs:
                context_str += f"- {lab.get('test_name')}: {lab.get('value')} {lab.get('unit', '')} (FLAG: {lab.get('flag')})\n"
            context_str += "\n"
        
        context_str += f"--- ALL EXTRACTED LABS ---\n"
        for lab in self.structured_data.get("labs", []):
             if lab.get("flag") not in ["High", "Low", "Critical"]:
                context_str += f"- {lab.get('test_name')}: {lab.get('value')} {lab.get('unit', '')} (Normal)\n"
            
        return context_str


class SessionManager:
    """Manages active patient context sessions (In-Memory MVP)."""
    
    def __init__(self):
        # In a real enterprise app, this would be Redis or a Database
        self._sessions: Dict[str, PatientSession] = {}

    def create_session(self, structured_data: Dict[str, Any]) -> str:
        session_id = str(uuid.uuid4())
        session = PatientSession(
            session_id=session_id,
            structured_data=structured_data,
            history=[]
        )
        self._sessions[session_id] = session
        return session_id

    def get_session(self, session_id: str) -> Optional[PatientSession]:
        return self._sessions.get(session_id)

    def delete_session(self, session_id: str):
        if session_id in self._sessions:
            del self._sessions[session_id]


# Singleton instance
_session_manager = SessionManager()

def get_session_manager() -> SessionManager:
    return _session_manager
