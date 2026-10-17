#!/bin/sh
# Sends a sample lead to the LeadFlow webhook. Usage: ./test-lead.sh [webhook-url]
URL=${1:-http://localhost:5678/webhook/lead}
curl -s -X POST "$URL" -H "Content-Type: application/json" -d '{
  "name": "Priya Shah",
  "email": "priya@acmelogistics.com",
  "company": "Acme Logistics",
  "company_size": "120",
  "budget": "$5,000",
  "timeline": "within 2 weeks",
  "message": "We spend 20 hours a week copying orders from email into our ERP and want an AI automation."
}'
echo
