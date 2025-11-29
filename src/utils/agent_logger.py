"""
Agent Logger - Logs agent activities and events.
ENHANCED: Better log file naming with query slug + metadata headers
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional


class AgentLogger:
    """Centralized logging for all agents."""
    
    def __init__(self, logs_dir: str = "logs"):
        self.logs_dir = Path(logs_dir)
        self.logs_dir.mkdir(exist_ok=True)
        
        self.run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.logs: List[Dict[str, Any]] = []
        self.metadata: Dict[str, Any] = {}
        self.start_time = datetime.now()
    
    def set_metadata(self, query: str, **kwargs):
        """Set metadata for this run."""
        self.metadata = {
            "run_id": self.run_id,
            "query": query,
            "query_slug": self._generate_query_slug(query),
            "timestamp": self.start_time.isoformat(),
            "date": self.start_time.strftime("%Y-%m-%d"),
            "time": self.start_time.strftime("%H:%M:%S"),
            **kwargs
        }
    
    def _generate_query_slug(self, query: str, max_length: int = 50) -> str:
        """
        Convert query to filename-safe slug.
        
        Examples:
            "Why is my CPC increasing?" -> "why_is_cpc_increasing"
            "Which campaigns should I pause?" -> "which_campaigns_pause"
        """
        # Convert to lowercase
        slug = query.lower()
        
        # Remove special characters
        slug = re.sub(r'[^a-z0-9\s]', '', slug)
        
        # Replace spaces with underscores
        slug = re.sub(r'\s+', '_', slug.strip())
        
        # Truncate if too long
        if len(slug) > max_length:
            slug = slug[:max_length].rsplit('_', 1)[0]  # Break at word boundary
        
        return slug
    
    def log_agent_action(
        self,
        agent_name: str,
        event: str,
        data: Optional[Dict[str, Any]] = None,
        status: str = "info"
    ):
        """Log an agent action."""
        log_entry = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "agent": agent_name,
            "event": event,
            "status": status,
            "data": data or {}
        }
        
        self.logs.append(log_entry)
        
        # Console output
        if status == "error":
            print(f"❌ [{agent_name}] {event}: {data}")
        elif status == "success":
            # Don't print success - too verbose
            pass
        else:
            # Don't print info - too verbose
            pass
    
    def log_error(self, agent_name: str, error_message: str, context: Optional[Dict] = None):
        """Log an error."""
        self.log_agent_action(
            agent_name,
            "error",
            {
                "error": error_message,
                "context": context or {}
            },
            status="error"
        )
    
    def save_logs(self):
        """Save logs to file with enhanced naming and metadata."""
        end_time = datetime.now()
        duration = (end_time - self.start_time).total_seconds()
        
        # Update metadata with final stats
        self.metadata.update({
            "duration_seconds": duration,
            "end_time": end_time.isoformat(),
            "total_events": len(self.logs),
            "status": "success" if not any(log['status'] == 'error' for log in self.logs) else "error"
        })
        
        # ✅ NEW: Enhanced filename with query slug
        query_slug = self.metadata.get('query_slug', 'unknown_query')
        filename = f"{self.run_id}_{query_slug}.json"
        log_path = self.logs_dir / filename
        
        # Build complete log structure with metadata header
        log_data = {
            "metadata": self.metadata,
            "summary": self._generate_summary(),
            "events": self.logs
        }
        
        # Save to file
        with open(log_path, 'w') as f:
            json.dump(log_data, f, indent=2)
        
        print(f"Logs saved to {log_path}")
    
    def _generate_summary(self) -> Dict[str, Any]:
        """Generate a summary of the run."""
        
        # Count events by agent
        agent_events = {}
        for log in self.logs:
            agent = log['agent']
            agent_events[agent] = agent_events.get(agent, 0) + 1
        
        # Count errors
        errors = [log for log in self.logs if log['status'] == 'error']
        
        # Extract key results from events
        results = {}
        for log in self.logs:
            if log['event'] == 'hypotheses_generated':
                results['hypotheses_count'] = log['data'].get('count', 0)
            elif log['event'] == 'validation_complete':
                results['validated_count'] = log['data'].get('validated', 0)
            elif log['event'] == 'recommendations_generated':
                results['recommendations_count'] = log['data'].get('campaigns_analyzed', 0)
            elif log['event'] == 'data_loaded':
                results['records_analyzed'] = log['data'].get('records', 0)
        
        return {
            "total_events": len(self.logs),
            "events_by_agent": agent_events,
            "errors_count": len(errors),
            "errors": [{"agent": e['agent'], "message": e['data'].get('error', '')} for e in errors],
            "results": results
        }
    
    def get_logs(self) -> List[Dict[str, Any]]:
        """Return all logs."""
        return self.logs
    
    def get_logs_by_agent(self, agent_name: str) -> List[Dict[str, Any]]:
        """Get logs for specific agent."""
        return [log for log in self.logs if log['agent'] == agent_name]
