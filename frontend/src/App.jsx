import { useEffect, useRef, useState } from "react";
import "./styles.css";

const API = (import.meta.env.VITE_API_URL || "http://127.0.0.1:8000").replace(/\/$/, "");

const EXAMPLES = [
  "What documents are needed for a death certificate?",
  "How much is a 64-page, 10-year e-passport?",
  "\u09ac\u09af\u09bc\u09b8\u09cd\u0995 \u09ad\u09be\u09a4\u09be \u09aa\u09c7\u09a4\u09c7 \u0995\u09a4 \u09ac\u09af\u09bc\u09b8 \u09b2\u09be\u0997\u09c7?",
];

function useApiStatus() {
  const [status, setStatus] = useState("checking");
  const [meta, setMeta] = useState(null);
  useEffect(() => {
    let stop = false;
    async function ping(attempt) {
      try {
        const ctrl = new AbortController();
        const timer = setTimeout(() => ctrl.abort(), 25000);
        const res = await fetch(`${API}/api/meta`, { signal: ctrl.signal });
        clearTimeout(timer);
        if (!res.ok) throw new Error("bad status");
        const data = await res.json();
        if (stop) return;
        setMeta(data);
        if (data.ready) {
          setStatus("online");
        } else {
          setStatus("degraded");
          if (attempt < 20) setTimeout(() => ping(attempt + 1), 4000);
        }
      } catch {
        if (stop) return;
        setStatus(attempt < 12 ? "waking" : "offline");
        if (attempt < 12) setTimeout(() => ping(attempt + 1), 5000);
      }
    }
    ping(0);
    return () => { stop = true; };
  }, []);
  return { status, meta };
}

function renderInline(text, sources) {
  return text
    .split(/(\*\*[^*]+\*\*|\[\d+\])/g)
    .filter(Boolean)
    .map((part, i) => {
      if (part.startsWith("**") && part.endsWith("**")) return <strong key={i}>{part.slice(2, -2)}</strong>;
      const m = part.match(/^\[(\d+)\]$/);
      if (m) {
        const src = sources.find((s) => s.id === Number(m[1]));
        if (src) {
          return (
            <a key={i} className="cite" href={src.url} target="_blank" rel="noreferrer" title={src.title}>
              {m[1]}
            </a>
          );
        }
      }
      return part;
    });
}

function Answer({ text, sources }) {
  const blocks = [];
  let list = null;
  for (const raw of text.split("\n")) {
    const line = raw.trim();
    if (!line) { list = null; continue; }
    const ol = line.match(/^(\d+)[.)]\s+(.*)$/);
    const ul = line.match(/^[-*\u2022]\s+(.*)$/);
    if (ol || ul) {
      const type = ol ? "ol" : "ul";
      if (!list || list.type !== type) { list = { type, items: [] }; blocks.push(list); }
      list.items.push(ol ? ol[2] : ul[1]);
    } else {
      list = null;
      blocks.push({ type: "p", text: line });
    }
  }
  return blocks.map((b, i) => {
    if (b.type === "p") return <p key={i}>{renderInline(b.text, sources)}</p>;
    const Tag = b.type;
    return <Tag key={i}>{b.items.map((t, j) => <li key={j}>{renderInline(t, sources)}</li>)}</Tag>;
  });
}

function BotMessage({ m, onPrint }) {
  const [copied, setCopied] = useState(false);
  if (m.error) return <p className="error">{m.text}</p>;
  const sources = m.sources || [];
  async function copy() {
    try {
      await navigator.clipboard.writeText(m.text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch { /* clipboard unavailable */ }
  }
  return (
    <>
      <div className="answer"><Answer text={m.text} sources={sources} /></div>
      <div className="meta-row">
        <span className={`chip-badge ${m.confident ? "ok" : "warn"}`}>
          {m.confident ? "Grounded in official sources" : "Not sure"}
        </span>
        <span className="chip-badge">{m.language === "bn" ? "Bangla" : "English"}</span>
        {m.topScore != null && <span className="chip-badge">match {m.topScore.toFixed(2)}</span>}
        <span className="spacer" />
        <button className="ghost" onClick={copy}>{copied ? "Copied" : "Copy"}</button>
        <button className="ghost" onClick={onPrint}>Print</button>
      </div>
      {sources.length > 0 && (
        <div className="sources">
          <div className="sources-title">Sources</div>
          {sources.map((s) => (
            <a key={s.id} className="source" href={s.url} target="_blank" rel="noreferrer">
              <span className="source-id">{s.id}</span>
              <span className="source-body">
                <span className="source-name">{s.title}</span>
                <span className="source-meta">
                  {s.url.replace(/^https?:\/\//, "").replace(/\/$/, "")} · checked {s.date_checked}
                </span>
              </span>
            </a>
          ))}
        </div>
      )}
    </>
  );
}

function Field({ label, children }) {
  return (
    <label className="field">
      <span>{label}</span>
      {children}
    </label>
  );
}

function DeathGuide({ onSubmit }) {
  const [where, setWhere] = useState("in a hospital or clinic");
  const [when, setWhen] = useState("within 45 days");
  return (
    <section className="panel">
      <h2>Death certificate guide</h2>
      <p className="panel-sub">Answer two questions and I will build a checklist from the official sources, including the fee and any current notice.</p>
      <div className="form-grid">
        <Field label="Where did the death occur?">
          <select value={where} onChange={(e) => setWhere(e.target.value)}>
            <option value="in a hospital or clinic">Hospital or clinic</option>
            <option value="at home">At home</option>
            <option value="unnaturally, for example in an accident">Unnatural death</option>
          </select>
        </Field>
        <Field label="How long ago?">
          <select value={when} onChange={(e) => setWhen(e.target.value)}>
            <option value="within 45 days">Within 45 days</option>
            <option value="between 46 days and 5 years ago">46 days to 5 years</option>
            <option value="more than 5 years ago">More than 5 years</option>
          </select>
        </Field>
      </div>
      <button className="primary" onClick={() => onSubmit(
        `I need to register a death. The person died ${where}, ${when}. Give me a step-by-step checklist: the documents I need, the fee, where to submit the application, and any current notice that affects me.`
      )}>Build my checklist</button>
    </section>
  );
}

function BenefitFinder({ onSubmit }) {
  const [kind, setKind] = useState("the old age allowance");
  const [age, setAge] = useState("66");
  const [sex, setSex] = useState("female");
  const [income, setIncome] = useState("30000");
  return (
    <section className="panel">
      <h2>Allowance finder</h2>
      <p className="panel-sub">Check the rules of a social allowance against your situation. Amounts and rules come from the official page with its date.</p>
      <div className="form-grid">
        <Field label="Allowance">
          <select value={kind} onChange={(e) => setKind(e.target.value)}>
            <option value="the old age allowance">Old age allowance</option>
            <option value="the widow and abandoned wife allowance">Widow and abandoned wife allowance</option>
            <option value="the financial support for patients with cancer, kidney disease, liver cirrhosis, paralysis, heart disease, leukemia or thalassemia">Serious disease support</option>
            <option value="the allowance for disadvantaged communities">Disadvantaged communities</option>
          </select>
        </Field>
        <Field label="Age">
          <input type="number" min="1" max="120" value={age} onChange={(e) => setAge(e.target.value)} />
        </Field>
        <Field label="Sex">
          <select value={sex} onChange={(e) => setSex(e.target.value)}>
            <option value="female">Female</option>
            <option value="male">Male</option>
          </select>
        </Field>
        <Field label="Yearly household income (BDT)">
          <input type="number" min="0" step="1000" value={income} onChange={(e) => setIncome(e.target.value)} />
        </Field>
      </div>
      <button className="primary" onClick={() => onSubmit(
        `Am I likely eligible for ${kind}? I am ${age} years old, ${sex}, with a yearly household income of about ${income} BDT. List the eligibility rules, the amount, the documents I need and how to apply.`
      )}>Check eligibility</button>
    </section>
  );
}

export default function App() {
  const { status, meta } = useApiStatus();
  const [tab, setTab] = useState("ask");
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [plain, setPlain] = useState(false);
  const [loading, setLoading] = useState(false);
  const [printId, setPrintId] = useState(null);
  const endRef = useRef(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, loading]);

  useEffect(() => {
    const clear = () => setPrintId(null);
    window.addEventListener("afterprint", clear);
    return () => window.removeEventListener("afterprint", clear);
  }, []);

  async function send(text) {
    const question = text.trim();
    if (question.length < 2 || loading) return;
    setTab("ask");
    setMessages((prev) => [...prev, { role: "user", text: question }]);
    setInput("");
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: question, plain_mode: plain }),
      });
      if (!res.ok) {
        let detail = "";
        try { detail = (await res.json()).detail || ""; } catch { /* no JSON body */ }
        const failure = new Error(typeof detail === "string" ? detail : "");
        failure.fromServer = true;
        throw failure;
      }
      const data = await res.json();
      setMessages((prev) => [...prev, {
        role: "bot", text: data.answer, sources: data.sources,
        confident: data.confident, language: data.language, topScore: data.top_score,
      }]);
    } catch (err) {
      setMessages((prev) => [...prev, {
        role: "bot", error: true,
        text: err.fromServer && err.message
          ? err.message
          : "The assistant is waking up or temporarily unavailable. Please try again in a moment.",
      }]);
    } finally {
      setLoading(false);
    }
  }

  function printMessage(index) {
    setPrintId(index);
    setTimeout(() => window.print(), 60);
  }

  const statusText = {
    checking: "Connecting",
    waking: "Waking the server",
    online: "Online",
    degraded: "Preparing knowledge base",
    offline: "Offline",
  }[status];

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <div className="logo">E</div>
          <div>
            <div className="brand-name">ESBC-AI</div>
            <div className="brand-sub">Easy Service for Bangladeshi Citizens</div>
          </div>
        </div>
        <div className="top-actions">
          <span className={`status ${status}`}><i />{statusText}</span>
          <label className="toggle" title="Explain in very simple words">
            <input type="checkbox" checked={plain} onChange={(e) => setPlain(e.target.checked)} />
            <span className="track"><span className="thumb" /></span>
            <span className="toggle-label">Plain language</span>
          </label>
        </div>
      </header>

      <nav className="tabs" aria-label="Modes">
        {[["ask", "Ask"], ["death", "Death certificate guide"], ["benefit", "Allowance finder"]].map(([id, label]) => (
          <button key={id} className={tab === id ? "tab active" : "tab"} onClick={() => setTab(id)}>{label}</button>
        ))}
      </nav>

      <main className="content">
        {tab === "death" && <DeathGuide onSubmit={send} />}
        {tab === "benefit" && <BenefitFinder onSubmit={send} />}

        {tab === "ask" && messages.length === 0 && (
          <section className="hero">
            <h1>Government services, <span className="grad">explained clearly.</span></h1>
            <p>
              Ask in English or Bangla. Every answer is built from official government sources, shows
              where it came from and when I checked it, and says so when I am not sure.
            </p>
            {meta?.ready && (
              <div className="stats">
                <div><b>{meta.documents}</b><span>official pages</span></div>
                <div><b>{meta.services.length}</b><span>service areas</span></div>
                <div><b>{meta.last_checked}</b><span>last verified</span></div>
              </div>
            )}
            <div className="chips">
              {EXAMPLES.map((q) => (
                <button key={q} className="chip" onClick={() => send(q)}>{q}</button>
              ))}
            </div>
          </section>
        )}

        {tab === "ask" && messages.map((m, i) =>
          m.role === "user" ? (
            <div key={i} className="row user"><div className="bubble user">{m.text}</div></div>
          ) : (
            <div key={i} className={`row bot ${printId === i ? "print-target" : ""}`}>
              <div className="avatar">E</div>
              <div className="bubble bot">
                <BotMessage m={m} onPrint={() => printMessage(i)} />
                <div className="print-note">Generated by ESBC-AI. Not an official government document. Please confirm with the official office.</div>
              </div>
            </div>
          )
        )}

        {tab === "ask" && loading && (
          <div className="row bot">
            <div className="avatar">E</div>
            <div className="bubble bot"><div className="typing"><i /><i /><i /></div></div>
          </div>
        )}
        <div ref={endRef} />
      </main>

      {tab === "ask" && (
        <footer className="composer-wrap">
          <form className="composer" onSubmit={(e) => { e.preventDefault(); send(input); }}>
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about a government service..."
              maxLength={1000}
              aria-label="Your question"
            />
            <button type="submit" disabled={loading || input.trim().length < 2}>Ask</button>
          </form>
        </footer>
      )}

      <div className="credit">
        Not an official government service. Verify with the relevant office before you apply or pay.
        <br />
        Designed and built by Farjana Ferdausi | Ostad AI &amp; ML Engineering Bootcamp, Batch 6 Capstone
      </div>
    </div>
  );
}
