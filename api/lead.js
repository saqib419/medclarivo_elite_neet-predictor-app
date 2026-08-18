// POST /api/lead  { name, phone, email, city, score, category, quota, state, rank }
export default async function handler(req, res) {
  if (req.method !== "POST") {
    res.setHeader("Allow", "POST");
    return res.status(405).json({ error: "Method not allowed" });
  }

  const body = typeof req.body === "string" ? safeParse(req.body) : req.body || {};
  const { name, phone, email, city, score, category, quota, state, rank } = body;

  if (!name || !String(name).trim()) {
    return res.status(400).json({ error: "name is required" });
  }
  const digits = String(phone || "").replace(/\D/g, "").slice(-10);
  if (!/^[6-9]\d{9}$/.test(digits)) {
    return res.status(400).json({ error: "a valid 10-digit phone number is required" });
  }
  if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(String(email))) {
    return res.status(400).json({ error: "a valid email is required" });
  }
  if (!city || !String(city).trim()) {
    return res.status(400).json({ error: "city is required" });
  }

  const webhookUrl = process.env.LEAD_WEBHOOK_URL;
  if (!webhookUrl) {
    console.error("LEAD_WEBHOOK_URL is not set");
    return res.status(200).json({ ok: true, stored: false });
  }

  try {
    await fetch(webhookUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name: String(name).trim(),
        phone: digits,
        email: String(email).trim(),
        city: String(city).trim(),
        score,
        category,
        quota,
        state,
        rank,
      }),
    });
    return res.status(200).json({ ok: true, stored: true });
  } catch (err) {
    console.error("Failed to forward lead to sheet:", err);
    return res.status(200).json({ ok: true, stored: false });
  }
}

function safeParse(str) {
  try {
    return JSON.parse(str);
  } catch {
    return {};
  }
}
