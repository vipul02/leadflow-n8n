"""Builds leadflow.workflow.json (importable into n8n) from the node code in nodes/."""

import json
from pathlib import Path

ROOT = Path(__file__).parent
code = lambda name: (ROOT / "nodes" / name).read_text()

SYSTEM = (
    "You are a B2B sales qualification analyst. Score inbound leads from 0 to 100 for how likely they are "
    "to become a paying client of an AI automation and data engineering agency. Weigh budget, timeline, "
    "company size, business email and how specific the need is. Be strict: vague or spam-like leads score low."
)

SCHEMA = {
    "type": "object",
    "properties": {
        "score": {"type": "integer", "description": "0-100 lead quality score"},
        "intent": {"type": "string", "enum": ["high", "medium", "low", "spam"]},
        "summary": {"type": "string", "description": "One sentence on what the lead needs"},
        "next_action": {"type": "string", "description": "Recommended next step for sales"},
    },
    "required": ["score", "intent", "summary", "next_action"],
    "additionalProperties": False,
}

claude_body = (
    "={{ JSON.stringify({"
    " model: 'claude-opus-5-5',"
    " max_tokens: 2048,"
    " fallbacks: 'default',"
    " output_config: { effort: 'low', format: { type: 'json_schema', schema: " + json.dumps(SCHEMA) + " } },"
    " system: " + json.dumps(SYSTEM) + ","
    " messages: [{ role: 'user', content: 'Score this lead:\\n' + JSON.stringify($json, null, 2) }]"
    " }) }}"
)

slack_text = (
    "=:fire: *Hot lead ({{ $json.score }}/100)*: {{ $json.first_name }} {{ $json.last_name }} at "
    "{{ $json.company || $json.company_domain }}\n"
    "{{ $json.summary }}\n*Next step:* {{ $json.next_action }}\n{{ $json.email }}"
)


def node(id_, name, type_, version, pos, params, **extra):
    return {"id": id_, "name": name, "type": type_, "typeVersion": version, "position": pos, "parameters": params, **extra}


sheet_params = lambda tab: {
    "operation": "append",
    "documentId": {"__rl": True, "mode": "url", "value": "https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID"},
    "sheetName": {"__rl": True, "mode": "name", "value": tab},
    "columns": {"mappingMode": "autoMapInputData", "value": {}},
    "options": {},
}

nodes = [
    node("1", "New lead (form webhook)", "n8n-nodes-base.webhook", 2, [0, 300],
         {"httpMethod": "POST", "path": "lead", "responseMode": "responseNode", "options": {}},
         webhookId="leadflow-intake"),
    node("2", "Normalize lead", "n8n-nodes-base.code", 2, [240, 300], {"jsCode": code("normalize-lead.js")}),
    node("3", "AI lead scoring (Claude)", "n8n-nodes-base.httpRequest", 4.2, [480, 300], {
        "method": "POST",
        "url": "https://api.anthropic.com/v1/messages",
        "authentication": "genericCredentialType",
        "genericAuthType": "httpHeaderAuth",
        "sendHeaders": True,
        "headerParameters": {"parameters": [
            {"name": "anthropic-version", "value": "2023-06-01"},
            {"name": "anthropic-beta", "value": "server-side-fallback-2026-07-01"},
        ]},
        "sendBody": True,
        "specifyBody": "json",
        "jsonBody": claude_body,
        "options": {"timeout": 60000},
    }, onError="continueRegularOutput", retryOnFail=True, maxTries=3),
    node("4", "Parse AI score", "n8n-nodes-base.code", 2, [720, 300], {"jsCode": code("parse-score.js")}),
    node("5", "Hot lead? (score >= 70)", "n8n-nodes-base.if", 2.2, [960, 300], {
        "conditions": {
            "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "strict", "version": 2},
            "conditions": [{"id": "hot", "leftValue": "={{ $json.score }}", "rightValue": 70,
                            "operator": {"type": "number", "operation": "gte"}}],
            "combinator": "and",
        },
        "options": {},
    }),
    node("6", "Alert sales in Slack", "n8n-nodes-base.slack", 2.2, [1220, 160], {
        "select": "channel",
        "channelId": {"__rl": True, "mode": "name", "value": "#sales-hot-leads"},
        "text": slack_text,
        "otherOptions": {},
    }),
    node("7", "Add to CRM sheet (Hot leads)", "n8n-nodes-base.googleSheets", 4.5, [1220, 340], sheet_params("Hot leads")),
    node("8", "Add to nurture list", "n8n-nodes-base.googleSheets", 4.5, [1220, 520], sheet_params("Nurture")),
    node("9", "Reply to form", "n8n-nodes-base.respondToWebhook", 1.1, [1480, 300], {
        "respondWith": "json",
        "responseBody": "={{ JSON.stringify({ ok: true, message: 'Thanks! We will be in touch shortly.' }) }}",
        "options": {},
    }),
]

link = lambda target, index=0: {"node": target, "type": "main", "index": index}
connections = {
    "New lead (form webhook)": {"main": [[link("Normalize lead")]]},
    "Normalize lead": {"main": [[link("AI lead scoring (Claude)")]]},
    "AI lead scoring (Claude)": {"main": [[link("Parse AI score")]]},
    "Parse AI score": {"main": [[link("Hot lead? (score >= 70)")]]},
    "Hot lead? (score >= 70)": {"main": [
        [link("Alert sales in Slack"), link("Add to CRM sheet (Hot leads)")],
        [link("Add to nurture list")],
    ]},
    "Add to CRM sheet (Hot leads)": {"main": [[link("Reply to form")]]},
    "Add to nurture list": {"main": [[link("Reply to form")]]},
}

workflow = {
    "name": "LeadFlow: AI lead scoring and routing",
    "nodes": nodes,
    "connections": connections,
    "settings": {"executionOrder": "v1"},
    "pinData": {},
}

(ROOT / "leadflow.workflow.json").write_text(json.dumps(workflow, indent=2))
print(f"Wrote leadflow.workflow.json with {len(nodes)} nodes")
