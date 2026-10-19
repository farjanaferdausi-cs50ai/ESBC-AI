import { useEffect, useRef, useState } from "react";
import "./styles.css";

const API = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

const EXAMPLES = [
  "What documents are needed for death registration?",
  "How do I apply for a death certificate online?",
  "মৃত্যু নিবন্ধনের জন্য কী কী কাগজ লাগে?",
];

function renderInline(text, sources) {
  return text
    .split(/(\*\*[^*]+\*\*|\[\d+\])/g)
    .filter(Boolean)
    .map((part, i) => {
      if (part.startsWith("**") && part.endsWith("**")) {
        return <strong key={i}>{part.slice(2, -2)}</strong>;
      }
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

function BotMessage({ m }) {
  if (m.error) {
    return <p className="error">{m.text}</p>;
  }
  const sources = m.sources || [];
  return (
    <>
      <div className="answer">
        {m.text.split("\n").map((line, i) =>
          line.trim() ? <p key={i}>{renderInline(line, sources)}</p> : null
        )}
      </div>
      <div className="badges">
        <span className={`badge ${m.confident ? "ok" : "warn"}`}>
          {m.confident ? "Grounded in official sources" : "Not sure"}
        </span>
        <span className="badge neutral">{m.language === "bn" ? "Bangla" : "English"}</span>
        {m.topScore != null && <span className="badge neutral">match {m.topScore.toFixed(2)}</span>}
      </div>
      {sources.length > 0 && (
        <div className="sources">
          <div className="sources-title">Sources</div>
          {sources.map((s) => (
            <a key={s.id} className="source" href={s.url} target="_blank" rel="noreferrer">
              <span className="source-id">{s.id}</span>
              <span className="source-body">
                <span className="source-name">{s.title}</span>
                <span className="source-meta">Checked on {s.date_checked}</span>
              </span>
            </a>
          ))}
        </div>
      )}
    </>
  );
}

export default function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [plain, setPlain] = useState(false);
  const [loading, setLoading] = useState(false);
  const endRef = useRef(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  async function send(text) {
    const question = text.trim();
    if (question.length < 2 || loading) return;
    setMessages((prev) => [...prev, { role: "user", text: question }]);
    setInput("");
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: question, plain_mode: plain }),
      });
      if (!res.ok) throw new Error(`Server returned ${res.status}`);
      const data = await res.json();
      setMessages((prev) => [
        ...prev,
        {
          role: "bot",
          text: data.answer,
          sources: data.sources,
          confident: data.confident,
          language: data.language,
          topScore: data.top_score,
        },
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: "bot", error: true, text: "The assistant is waking up or unavailable. Please try again in a moment." },
      ]);
    } finally {
      setLoading(false);
    }
  }
cat > src/App.jsx << 'EOF'
import { useEffect, useRef, useState } from "react";
import "./styles.css";

const API = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

const EXAMPLES = [
  "What documents are needed for death registration?",
  "How do I apply for a death certificate online?",
  "মৃত্যু নিবন্ধনের জন্য কী কী কাগজ লাগে?",
];

function renderInline(text, sources) {
  return text
    .split(/(\*\*[^*]+\*\*|\[\d+\])/g)
    .filter(Boolean)
    .map((part, i) => {
      if (part.startsWith("**") && part.endsWith("**")) {
        return <strong key={i}>{part.slice(2, -2)}</strong>;
      }
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

function BotMessage({ m }) {
  if (m.error) {
    return <p className="error">{m.text}</p>;
  }
  const sources = m.sources || [];
  return (
    <>
      <div className="answer">
        {m.text.split("\n").map((line, i) =>
          line.trim() ? <p key={i}>{renderInline(line, sources)}</p> : null
        )}
      </div>
      <div className="badges">
        <span className={`badge ${m.confident ? "ok" : "warn"}`}>
          {m.confident ? "Grounded in official sources" : "Not sure"}
        </span>
        <span className="badge neutral">{m.language === "bn" ? "Bangla" : "English"}</span>
        {m.topScore != null && <span className="badge neutral">match {m.topScore.toFixed(2)}</span>}
      </div>
      {sources.length > 0 && (
        <div className="sources">
          <div className="sources-title">Sources</div>
          {sources.map((s) => (
            <a key={s.id} className="source" href={s.url} target="_blank" rel="noreferrer">
              <span className="source-id">{s.id}</span>
              <span className="source-body">
                <span className="source-name">{s.title}</span>
                <span className="source-meta">Checked on {s.date_checked}</span>
              </span>
            </a>
          ))}
        </div>
      )}
    </>
  );
}

export default function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [plain, setPlain] = useState(false);
  const [loading, setLoading] = useState(false);
  const endRef = useRef(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  async function send(text) {
    const question = text.trim();
    if (question.length < 2 || loading) return;
    setMessages((prev) => [...prev, { role: "user", text: question }]);
    setInput("");
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: question, plain_mode: plain }),
      });
      if (!res.ok) throw new Error(`Server returned ${res.status}`);
      const data = await res.json();
      setMessages((prev) => [
        ...prev,
        {
          role: "bot",
          text: data.answer,
          sources: data.sources,
          confident: data.confident,
          language: data.language,
          topScore: data.top_score,
        },
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: "bot", error: true, text: "The assistant is waking up or unavailable. Please try again in a moment." },
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="app">
      <div className="glow glow-a" />
      <div className="glow glow-b" />

      <header className="topbar">
        <div className="brand">
          <div className="logo">E</div>
          <div>
            <div className="brand-name">ESBC-AI</div>
            <div className="brand-sub">Easy Service for Bangladeshi Citizens</div>
          </div>
        </div>
        <label className="toggle" title="Explain in very simple words">
          <input type="checkbox" checked={plain} onChange={(e) => setPlain(e.target.checked)} />
          <span className="track"><span className="thumb" /></span>
          <span className="toggle-label">Plain language</span>
        </label>
      </header>

      <main className="chat">
        {messages.length === 0 && (
          <section className="hero">
            <h1>Government services, <span className="grad">explained clearly.</span></h1>
            <p>
              Ask in English or Bangla. Every answer is grounded in official government sources
              and cited, and if I am not sure, I say so.
            </p>
            <div className="chips">
              {EXAMPLES.map((q) => (
                <button key={q} className="chip" onClick={() => send(q)}>{q}</button>
              ))}
            </div>
          </section>
        )}

        {messages.map((m, i) =>
          m.role === "user" ? (
            <div key={i} className="row user"><div className="bubble user">{m.text}</div></div>
          ) : (
            <div key={i} className="row bot">
              <div className="avatar">E</div>
              <div className="bubble bot"><BotMessage m={m} /></div>
            </div>
          )
        )}

        {loading && (
          <div className="row bot">
            <div className="avatar">E</div>
            <div className="bubble bot"><div className="typing"><i /><i /><i /></div></div>
          </div>
        )}
        <div ref={endRef} />
      </main>

      <footer className="composer-wrap">
        <form className="composer" onSubmit={(e) => { e.preventDefault(); send(input); }}>
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about a government service..."
            maxLength={1000}
          />
          <button type="submit" disabled={loading || input.trim().length < 2}>Ask</button>
        </form>
        <div className="credit">
          Designed and built by Farjana Ferdausi | Ostad AI &amp; ML Engineering Bootcamp, Batch 6 Capstone
        </div>
      </footer>
    </div>
  );
}
