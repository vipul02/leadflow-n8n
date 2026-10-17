// n8n Code node: "Parse AI score". Reads Claude's structured JSON and merges it onto the lead.
// Falls back to a rule-based score if the AI call failed, so no lead is ever dropped.
const leads = $('Normalize lead').all();

function ruleScore(lead) {
  let score = 20;
  if (lead.business_email) score += 25;
  if ((lead.company_size ?? 0) >= 50) score += 20;
  if (/\$?\d/.test(lead.budget)) score += 15;
  if (/week|month|asap|urgent|now/i.test(lead.timeline)) score += 10;
  if ((lead.message ?? '').length > 80) score += 10;
  return Math.min(score, 100);
}

return $input.all().map((item, i) => {
  const lead = leads[i]?.json ?? {};
  const res = item.json;
  let ai = null;

  if (res?.stop_reason !== 'refusal' && Array.isArray(res?.content)) {
    const text = res.content.find((b) => b.type === 'text')?.text;
    try { ai = text ? JSON.parse(text) : null; } catch { ai = null; }
  }

  const score = ai ? Math.max(0, Math.min(100, Math.round(ai.score))) : ruleScore(lead);
  return {
    json: {
      ...lead,
      score,
      tier: score >= 70 ? 'hot' : score >= 40 ? 'warm' : 'cold',
      intent: ai?.intent ?? 'unknown',
      summary: ai?.summary ?? 'Scored with fallback rules (AI unavailable).',
      next_action: ai?.next_action ?? 'Review manually',
      scored_by: ai ? 'claude' : 'rules',
    },
  };
});
