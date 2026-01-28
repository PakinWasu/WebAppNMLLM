# LLM Analysis System with Human-in-the-Loop (HITL) Workflow

## Overview

This system integrates Ollama (Local LLM) into the FastAPI backend to analyze network configurations with strict context isolation, evidence-based responses, and a Human-in-the-Loop workflow for quality assurance.

## Architecture

### Core Components

1. **LLM Service** (`services/llm_service.py`)
   - Async communication with Ollama API
   - Context isolation enforcement
   - Evidence-based prompt engineering
   - Performance metrics tracking

2. **Accuracy Tracker** (`services/accuracy_tracker.py`)
   - Compares AI draft vs Human verified version
   - Calculates accuracy scores
   - Generates diff summaries for UI

3. **Analysis Models** (`models/analysis.py`)
   - Pydantic models for type safety
   - HITL workflow status tracking
   - Performance metrics storage

4. **Analysis Router** (`routers/analysis.py`)
   - REST API endpoints
   - HITL workflow management
   - Performance metrics API

## Key Features

### 1. Context Isolation

The LLM analyzes data **ONLY** from the specific device within its project:

```python
# System prompt enforces:
"CONTEXT ISOLATION: You are analyzing ONLY the device '{device_name}' 
from the provided configuration data. Do NOT reference or mix data 
from other devices or projects."
```

### 2. Evidence-Based Responses

The system prompt forces the LLM to:
- Base analysis ONLY on provided configuration data
- Respond with "Data not available" if information is missing
- Cite specific configuration values when making claims
- Avoid hallucination

### 3. Human-in-the-Loop (HITL) Workflow

**Draft → Review → Verified**

1. **Draft** (`pending_review`): AI generates analysis
2. **Review**: Human operator reviews and edits
3. **Verified** (`verified`): Human confirms final version

### 4. Performance & Accuracy Tracking

- **Latency**: Tracks inference time (ms)
- **Token Usage**: Prompt, completion, and total tokens
- **Accuracy Score**: Percentage of fields that matched AI draft
- **Metrics Storage**: Saved in `performance_logs` collection

## API Endpoints

### Create Analysis

```http
POST /projects/{project_id}/analysis
Content-Type: application/json

{
  "device_name": "CORE1",
  "analysis_type": "security_audit",
  "custom_prompt": null,
  "include_original_content": false
}
```

**Response:**
```json
{
  "analysis_id": "uuid",
  "project_id": "project_id",
  "device_name": "CORE1",
  "analysis_type": "security_audit",
  "ai_draft": {...},
  "ai_draft_text": "Full AI response...",
  "status": "pending_review",
  "llm_metrics": {
    "inference_time_ms": 1234.5,
    "token_usage": {
      "prompt_tokens": 500,
      "completion_tokens": 300,
      "total_tokens": 800
    },
    "model_name": "qwen2.5:7b"
  }
}
```

### Verify Analysis (HITL)

```http
POST /projects/{project_id}/analysis/verify
Content-Type: application/json

{
  "analysis_id": "uuid",
  "verified_content": {
    "summary": "Human-edited summary",
    "findings": [...],
    "recommendations": [...]
  },
  "comments": "Fixed incorrect VLAN assignment",
  "status": "verified"
}
```

**Response includes:**
- `accuracy_metrics`: Accuracy score and field changes
- `diff_summary`: Summary of changes for UI display

### List Analyses

```http
GET /projects/{project_id}/analysis?device_name=CORE1&status=verified
```

### Get Performance Metrics

```http
GET /projects/{project_id}/analysis/performance/metrics?device_name=CORE1&limit=50
```

## Analysis Types

1. **security_audit**: Security vulnerabilities, ACLs, user accounts
2. **performance_review**: Interface utilization, STP, routing efficiency
3. **configuration_compliance**: Standards compliance, best practices
4. **network_topology**: Interface connections, VLANs, neighbors
5. **best_practices**: Configuration recommendations
6. **custom**: Custom prompt analysis

## MongoDB Collections

### `analyses`
Stores analysis documents with:
- AI draft and verified version
- HITL workflow status
- LLM metrics
- Accuracy metrics (after verification)

### `performance_logs`
Stores performance metrics for dashboarding:
- Inference time
- Token usage
- Accuracy scores
- Timestamps

## Accuracy Calculation

Accuracy is calculated by comparing flattened dictionaries:

```python
accuracy_score = (total_fields - corrected_fields) / total_fields * 100
```

The system tracks:
- **Total fields**: All fields in analysis
- **Corrected fields**: Fields changed by human
- **Field changes**: Detailed list of modifications

## Usage Example

```python
# 1. Create analysis
response = await client.post(
    f"/projects/{project_id}/analysis",
    json={
        "device_name": "CORE1",
        "analysis_type": "security_audit"
    }
)
analysis = response.json()

# 2. Human reviews and edits
verified_content = {
    "summary": "Updated summary with corrections",
    "findings": [...],
    "recommendations": [...]
}

# 3. Verify analysis
verify_response = await client.post(
    f"/projects/{project_id}/analysis/verify",
    json={
        "analysis_id": analysis["analysis_id"],
        "verified_content": verified_content,
        "comments": "Fixed incorrect findings",
        "status": "verified"
    }
)

# 4. Check accuracy
verified_analysis = verify_response.json()
print(f"Accuracy: {verified_analysis['accuracy_metrics']['accuracy_score']}%")
print(f"Changes: {verified_analysis['diff_summary']}")
```

## Configuration

Settings in `core/settings.py`:

```python
AI_MODEL_NAME: str = "qwen2.5:7b"
AI_MODEL_ENDPOINT: str = "http://host.docker.internal:11434"
```

## Error Handling

- **Timeout**: 600s timeout for Ollama requests
- **JSON Parsing**: Falls back to text format if JSON parsing fails
- **Context Missing**: Returns 404 if device not found
- **Already Verified**: Prevents re-verification

## Performance Considerations

- **Async Operations**: All LLM calls are async
- **Token Limits**: Original content truncated to 5000 chars if included
- **Temperature**: Set to 0.3 for more factual responses
- **Metrics Logging**: Non-blocking performance logging

## Future Enhancements

1. Batch analysis for multiple devices
2. Analysis templates and presets
3. Automated accuracy threshold alerts
4. Integration with notification system
5. Analysis versioning and history
