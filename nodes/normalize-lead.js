// n8n Code node: "Normalize lead". Cleans the raw form submission and adds simple enrichment.
const FREE_EMAIL = new Set(['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'icloud.com', 'aol.com', 'proton.me', 'protonmail.com']);

return $input.all().map((item) => {
  const raw = item.json.body ?? item.json;
  const clean = (v) => (typeof v === 'string' ? v.trim() : v ?? '');

  const email = clean(raw.email).toLowerCase();
  const domain = email.includes('@') ? email.split('@')[1] : '';
  const [firstName, ...rest] = clean(raw.name).split(/\s+/);
  const employees = Number(String(raw.company_size ?? '').replace(/[^0-9]/g, '')) || null;

  return {
    json: {
      submitted_at: new Date().toISOString(),
      first_name: firstName || '',
      last_name: rest.join(' '),
      email,
      email_valid: /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email),
      company: clean(raw.company),
      company_domain: domain,
      business_email: Boolean(domain) && !FREE_EMAIL.has(domain),
      company_size: employees,
      budget: clean(raw.budget),
      timeline: clean(raw.timeline),
      message: clean(raw.message).slice(0, 2000),
      source: clean(raw.source) || 'website',
    },
  };
});
