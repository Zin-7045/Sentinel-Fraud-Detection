import { useState, useEffect, useRef, useCallback } from "react";
import { LineChart, Line, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ScatterChart, Scatter, Cell, RadarChart, Radar, PolarGrid, PolarAngleAxis } from "recharts";

// ─── CONSTANTS ───────────────────────────────────────────────────────────────
const FRAUD_TYPES = ["Card Skimming", "Account Takeover", "Synthetic ID", "Money Mule", "Phishing", "CNP Fraud"];
const REGIONS = ["NA-EAST", "EU-WEST", "APAC", "LATAM", "ME-AF", "NA-WEST"];
const MERCHANTS = ["TechMart Pro", "GlobalPay", "SwiftShop", "NexCommerce", "PayHub", "CryptoXchange", "LuxuryGoods", "BetaPay"];
const STATUS = ["FLAGGED", "REVIEWING", "CONFIRMED", "CLEARED", "BLOCKED"];
const CHANNELS = ["WEB", "MOBILE", "ATM", "POS", "API"];

function seededRand(seed) {
  let s = seed;
  return () => { s = (s * 9301 + 49297) % 233280; return s / 233280; };
}

function genTransaction(id, r) {
  const amount = Math.floor(r() * 50000) / 100 + 0.5;
  const riskScore = Math.min(99, Math.floor(r() * 100 + (amount > 300 ? 20 : 0)));
  const isFraud = riskScore > 72 || (r() < 0.06);
  return {
    id: `TXN-${String(id).padStart(7, "0")}`,
    timestamp: new Date(Date.now() - Math.floor(r() * 3600000)).toISOString(),
    amount,
    merchant: MERCHANTS[Math.floor(r() * MERCHANTS.length)],
    region: REGIONS[Math.floor(r() * REGIONS.length)],
    channel: CHANNELS[Math.floor(r() * CHANNELS.length)],
    fraudType: isFraud ? FRAUD_TYPES[Math.floor(r() * FRAUD_TYPES.length)] : null,
    riskScore,
    status: isFraud ? STATUS[Math.floor(r() * 3)] : STATUS[Math.floor(r() * 2) + 3],
    userId: `USR-${String(Math.floor(r() * 9999)).padStart(4, "0")}`,
    isFraud,
    lat: (r() - 0.5) * 160,
    lng: (r() - 0.5) * 360,
    processingMs: Math.floor(r() * 120 + 8),
  };
}

const initRand = seededRand(42);
const INITIAL_TRANSACTIONS = Array.from({ length: 200 }, (_, i) => genTransaction(i + 1, initRand));

function genTimeSeriesData() {
  const r = seededRand(99);
  return Array.from({ length: 24 }, (_, i) => ({
    hour: `${String(i).padStart(2, "0")}:00`,
    total: Math.floor(r() * 800 + 200),
    fraud: Math.floor(r() * 60 + 5),
    throughput: Math.floor(r() * 2000 + 500),
    latency: Math.floor(r() * 80 + 12),
  }));
}

function genClusterData() {
  const r = seededRand(77);
  return Array.from({ length: 80 }, (_, i) => ({
    x: (r() - 0.5) * 200,
    y: (r() - 0.5) * 200,
    risk: r() * 100,
    cluster: Math.floor(r() * 4),
    size: Math.floor(r() * 20 + 4),
  }));
}

const TIME_SERIES = genTimeSeriesData();
const CLUSTER_DATA = genClusterData();

const CLUSTER_COLORS = ["#00f5d4", "#f72585", "#ffd60a", "#4cc9f0"];
const RISK_GRADIENT = (score) => {
  if (score < 30) return "#00f5d4";
  if (score < 60) return "#ffd60a";
  if (score < 80) return "#f4a261";
  return "#f72585";
};

// ─── ANIMATED COUNTER ────────────────────────────────────────────────────────
function AnimCounter({ value, prefix = "", suffix = "", decimals = 0 }) {
  const [display, setDisplay] = useState(0);
  useEffect(() => {
    let start = display;
    const end = value;
    if (start === end) return;
    const step = (end - start) / 30;
    let frame = 0;
    const timer = setInterval(() => {
      frame++;
      start += step;
      setDisplay(frame >= 30 ? end : start);
      if (frame >= 30) clearInterval(timer);
    }, 20);
    return () => clearInterval(timer);
  }, [value]);
  return <>{prefix}{typeof display === "number" ? display.toFixed(decimals) : display}{suffix}</>;
}

// ─── RISK BADGE ───────────────────────────────────────────────────────────────
function RiskBadge({ score }) {
  const color = score >= 80 ? "#f72585" : score >= 60 ? "#f4a261" : score >= 30 ? "#ffd60a" : "#00f5d4";
  const label = score >= 80 ? "CRITICAL" : score >= 60 ? "HIGH" : score >= 30 ? "MEDIUM" : "LOW";
  return (
    <span style={{
      background: `${color}22`, border: `1px solid ${color}55`, color,
      borderRadius: 4, padding: "2px 8px", fontSize: 10, fontWeight: 700,
      letterSpacing: "0.08em", fontFamily: "monospace"
    }}>{label}</span>
  );
}

// ─── STATUS BADGE ─────────────────────────────────────────────────────────────
function StatusDot({ status }) {
  const colors = { FLAGGED: "#f72585", REVIEWING: "#ffd60a", CONFIRMED: "#f4a261", CLEARED: "#00f5d4", BLOCKED: "#9d4edd" };
  return (
    <span style={{ display: "flex", alignItems: "center", gap: 5 }}>
      <span style={{ width: 7, height: 7, borderRadius: "50%", background: colors[status] || "#888", display: "inline-block", boxShadow: `0 0 6px ${colors[status] || "#888"}` }} />
      <span style={{ color: colors[status] || "#888", fontSize: 11, fontFamily: "monospace", letterSpacing: "0.06em" }}>{status}</span>
    </span>
  );
}

// ─── SPARKLINE ────────────────────────────────────────────────────────────────
function Sparkline({ data, color = "#00f5d4", height = 40 }) {
  const max = Math.max(...data), min = Math.min(...data);
  const pts = data.map((v, i) => {
    const x = (i / (data.length - 1)) * 120;
    const y = height - ((v - min) / (max - min || 1)) * (height - 6) - 3;
    return `${x},${y}`;
  }).join(" ");
  return (
    <svg width={120} height={height} style={{ display: "block" }}>
      <defs>
        <linearGradient id={`sg-${color.replace("#","")}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.3" />
          <stop offset="100%" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      <polygon points={`0,${height} ${pts} 120,${height}`} fill={`url(#sg-${color.replace("#","")})`} />
      <polyline points={pts} fill="none" stroke={color} strokeWidth="1.5" />
    </svg>
  );
}

// ─── STAT CARD ────────────────────────────────────────────────────────────────
function StatCard({ label, value, sub, spark, color = "#00f5d4", prefix = "", suffix = "", decimals = 0, icon }) {
  return (
    <div style={{
      background: "linear-gradient(135deg, #0d1117 0%, #161b22 100%)",
      border: `1px solid ${color}33`,
      borderRadius: 12, padding: "18px 22px",
      display: "flex", flexDirection: "column", gap: 8,
      position: "relative", overflow: "hidden",
      boxShadow: `0 0 30px ${color}11, inset 0 1px 0 ${color}22`
    }}>
      <div style={{ position: "absolute", top: 0, right: 0, width: 80, height: 80, background: `radial-gradient(circle at 80% 20%, ${color}18 0%, transparent 70%)` }} />
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <span style={{ color: "#6e7681", fontSize: 11, letterSpacing: "0.12em", fontWeight: 600, textTransform: "uppercase", fontFamily: "monospace" }}>{label}</span>
        {icon && <span style={{ fontSize: 18 }}>{icon}</span>}
      </div>
      <div style={{ color: "#e6edf3", fontSize: 28, fontWeight: 700, fontFamily: "'Space Mono', monospace", letterSpacing: "-0.02em" }}>
        <AnimCounter value={value} prefix={prefix} suffix={suffix} decimals={decimals} />
      </div>
      {sub && <div style={{ color: color, fontSize: 11, fontFamily: "monospace" }}>{sub}</div>}
      {spark && <Sparkline data={spark} color={color} />}
    </div>
  );
}

// ─── PIPELINE NODE ────────────────────────────────────────────────────────────
function PipelineNode({ label, sub, color, active, pulse }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 6 }}>
      <div style={{
        width: 52, height: 52, borderRadius: 12,
        background: `${color}22`, border: `2px solid ${color}`,
        display: "flex", alignItems: "center", justifyContent: "center",
        fontSize: 22, position: "relative",
        boxShadow: active ? `0 0 20px ${color}66, 0 0 40px ${color}33` : "none",
        animation: pulse ? "nodePulse 1.8s ease-in-out infinite" : "none"
      }}>
        {active && <span style={{
          position: "absolute", inset: -4, borderRadius: 14,
          border: `2px solid ${color}44`,
          animation: "ringPulse 1.8s ease-in-out infinite"
        }} />}
        {sub}
      </div>
      <span style={{ color: "#8b949e", fontSize: 10, fontFamily: "monospace", textAlign: "center", letterSpacing: "0.06em", maxWidth: 70 }}>{label}</span>
    </div>
  );
}

// ─── HEATMAP GRID ─────────────────────────────────────────────────────────────
function HeatmapGrid({ transactions }) {
  const grid = {};
  transactions.forEach(t => {
    const key = `${t.region}-${t.channel}`;
    if (!grid[key]) grid[key] = { total: 0, fraud: 0 };
    grid[key].total++;
    if (t.isFraud) grid[key].fraud++;
  });
  return (
    <div style={{ overflowX: "auto" }}>
      <table style={{ borderCollapse: "collapse", width: "100%", fontSize: 11, fontFamily: "monospace" }}>
        <thead>
          <tr>
            <th style={{ color: "#6e7681", padding: "6px 10px", textAlign: "left" }}>Region\Ch</th>
            {CHANNELS.map(c => <th key={c} style={{ color: "#6e7681", padding: "6px 10px", textAlign: "center", letterSpacing: "0.06em" }}>{c}</th>)}
          </tr>
        </thead>
        <tbody>
          {REGIONS.map(region => (
            <tr key={region}>
              <td style={{ color: "#8b949e", padding: "5px 10px", fontWeight: 600 }}>{region}</td>
              {CHANNELS.map(channel => {
                const key = `${region}-${channel}`;
                const cell = grid[key] || { total: 0, fraud: 0 };
                const rate = cell.total > 0 ? cell.fraud / cell.total : 0;
                const intensity = Math.min(rate * 5, 1);
                const bg = rate > 0.3 ? `rgba(247,37,133,${intensity * 0.7 + 0.05})` : rate > 0.15 ? `rgba(244,162,97,${intensity * 0.7 + 0.05})` : `rgba(0,245,212,${intensity * 0.5 + 0.03})`;
                return (
                  <td key={channel} style={{
                    background: bg, border: "1px solid #21262d",
                    padding: "8px 10px", textAlign: "center", color: "#e6edf3",
                    cursor: "default", transition: "all 0.2s"
                  }} title={`${cell.fraud}/${cell.total} fraud`}>
                    {cell.fraud > 0 ? <span style={{ color: rate > 0.3 ? "#f72585" : rate > 0.15 ? "#ffd60a" : "#00f5d4" }}>{Math.round(rate * 100)}%</span> : <span style={{ color: "#30363d" }}>—</span>}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ─── NETWORK GRAPH ────────────────────────────────────────────────────────────
function NetworkGraph({ transactions }) {
  const canvasRef = useRef(null);
  useEffect(() => {
    const c = canvasRef.current;
    if (!c) return;
    const ctx = c.getContext("2d");
    const W = c.width, H = c.height;
    ctx.clearRect(0, 0, W, H);

    // Build small node set
    const nodes = [], links = [];
    const seen = {};
    transactions.slice(0, 40).forEach(t => {
      if (!seen[t.userId]) {
        seen[t.userId] = { id: t.userId, x: Math.random() * (W - 60) + 30, y: Math.random() * (H - 60) + 30, isFraud: t.isFraud, deg: 0 };
        nodes.push(seen[t.userId]);
      }
      if (!seen[t.merchant]) {
        seen[t.merchant] = { id: t.merchant, x: Math.random() * (W - 60) + 30, y: Math.random() * (H - 60) + 30, isMerchant: true, deg: 0 };
        nodes.push(seen[t.merchant]);
      }
      if (t.isFraud) {
        links.push({ src: seen[t.userId], dst: seen[t.merchant], risk: t.riskScore });
        seen[t.userId].deg++;
        seen[t.merchant].deg++;
      }
    });

    // Draw links
    links.forEach(l => {
      const grd = ctx.createLinearGradient(l.src.x, l.src.y, l.dst.x, l.dst.y);
      grd.addColorStop(0, `rgba(247,37,133,${l.risk / 200})`);
      grd.addColorStop(1, `rgba(156,77,221,${l.risk / 200})`);
      ctx.beginPath(); ctx.moveTo(l.src.x, l.src.y); ctx.lineTo(l.dst.x, l.dst.y);
      ctx.strokeStyle = grd; ctx.lineWidth = 1.2; ctx.stroke();
    });

    // Draw nodes
    nodes.forEach(n => {
      const r = n.isMerchant ? 8 : 5 + Math.min(n.deg * 2, 10);
      const col = n.isFraud ? "#f72585" : n.isMerchant ? "#4cc9f0" : "#00f5d4";
      ctx.beginPath(); ctx.arc(n.x, n.y, r, 0, Math.PI * 2);
      ctx.fillStyle = `${col}33`; ctx.fill();
      ctx.strokeStyle = col; ctx.lineWidth = 1.5; ctx.stroke();
      if (n.deg > 2) {
        ctx.beginPath(); ctx.arc(n.x, n.y, r + 5, 0, Math.PI * 2);
        ctx.strokeStyle = `${col}44`; ctx.lineWidth = 1; ctx.stroke();
      }
    });
  }, [transactions]);
  return <canvas ref={canvasRef} width={520} height={260} style={{ width: "100%", borderRadius: 8 }} />;
}

function apiTxnToLocal(t) {
  return {
    id: t.transaction_id,
    timestamp: t.timestamp,
    amount: t.amount,
    merchant: t.merchant,
    region: t.region,
    channel: t.channel,
    fraudType: t.fraud_type,
    riskScore: t.risk_score,
    status: t.status,
    userId: t.user_id,
    isFraud: t.is_fraud,
  };
}

// ─── MAIN APP ─────────────────────────────────────────────────────────────────
export default function FraudDashboard() {
  const [txns, setTxns] = useState(INITIAL_TRANSACTIONS);
  const [activeTab, setActiveTab] = useState("overview");
  const [filterStatus, setFilterStatus] = useState("ALL");
  const [filterRisk, setFilterRisk] = useState("ALL");
  const [search, setSearch] = useState("");
  const [liveMode, setLiveMode] = useState(true);
  const [alerts, setAlerts] = useState([]);
  const [alertVisible, setAlertVisible] = useState(false);
  const [selectedTxn, setSelectedTxn] = useState(null);
  const [tickCount, setTickCount] = useState(0);
  const [apiMetrics, setApiMetrics] = useState(null);
  const counterRef = useRef(200);
  const randRef = useRef(seededRand(Date.now() % 10000));

  useEffect(() => {
    fetch("/api/v1/transactions?limit=200")
      .then(r => r.json())
      .then(data => {
        if (data && data.length) {
          setTxns(data.map(apiTxnToLocal));
          counterRef.current = data.length + 1;
        }
      })
      .catch(() => {});
    fetch("/api/v1/alerts?limit=8")
      .then(r => r.json())
      .then(data => {
        if (data && data.length) {
          setAlerts(data.map(a => ({
            id: Date.now() + Math.random(),
            txn: apiTxnToLocal(a),
            msg: `HIGH RISK: ${a.fraud_type || "Fraud"} detected on ${a.merchant}`,
          })));
        }
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    const interval = setInterval(() => {
      fetch("/api/v1/metrics")
        .then(r => r.json())
        .then(setApiMetrics)
        .catch(() => {});
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (!liveMode) return;
    const interval = setInterval(() => {
      counterRef.current++;
      const r = randRef.current;
      const newTxn = genTransaction(counterRef.current, r);
      setTxns(prev => [newTxn, ...prev].slice(0, 500));
      setTickCount(c => c + 1);
      if (newTxn.isFraud && newTxn.riskScore > 80) {
        const alert = { id: Date.now(), txn: newTxn, msg: `HIGH RISK: ${newTxn.fraudType} detected on ${newTxn.merchant}` };
        setAlerts(prev => [alert, ...prev].slice(0, 8));
        setAlertVisible(true);
        setTimeout(() => setAlertVisible(false), 4000);
      }
    }, 1800);
    return () => clearInterval(interval);
  }, [liveMode]);

  const filtered = txns.filter(t => {
    if (filterStatus !== "ALL" && t.status !== filterStatus) return false;
    if (filterRisk === "HIGH" && t.riskScore < 72) return false;
    if (filterRisk === "CRITICAL" && t.riskScore < 85) return false;
    if (filterRisk === "LOW" && t.riskScore >= 30) return false;
    if (search && !t.id.includes(search.toUpperCase()) && !t.merchant.toLowerCase().includes(search.toLowerCase()) && !t.userId.includes(search.toUpperCase())) return false;
    return true;
  });

  const m = apiMetrics || {};
  const totalTxns = m.total_transactions || txns.length;
  const totalFraud = m.total_fraud || txns.filter(t => t.isFraud).length;
  const fraudRate = m.fraud_rate != null ? m.fraud_rate.toFixed(1) : (totalFraud / Math.max(txns.length, 1) * 100).toFixed(1);
  const avgRisk = m.avg_risk_score != null ? m.avg_risk_score.toFixed(1) : (txns.reduce((s, t) => s + t.riskScore, 0) / Math.max(txns.length, 1)).toFixed(1);
  const totalVolume = txns.reduce((s, t) => s + t.amount, 0);
  const fraudVolume = txns.filter(t => t.isFraud).reduce((s, t) => s + t.amount, 0);
  const sparkFraud = TIME_SERIES.map(d => d.fraud);
  const sparkTotal = TIME_SERIES.map(d => d.total);
  const sparkLatency = TIME_SERIES.map(d => d.latency);

  const radarData = [
    { metric: "Precision", value: 94 }, { metric: "Recall", value: 87 },
    { metric: "F1-Score", value: 90 }, { metric: "Accuracy", value: 96 },
    { metric: "AUC-ROC", value: 98 }, { metric: "Specificity", value: 97 },
  ];

  const tabs = ["overview", "transactions", "analytics", "pipeline", "models"];

  return (
    <div style={{ minHeight: "100vh", background: "#0d1117", color: "#e6edf3", fontFamily: "'Space Mono', 'Courier New', monospace" }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Syne:wght@400;600;700;800&display=swap');
        * { box-sizing: border-box; margin: 0; padding: 0; }
        ::-webkit-scrollbar { width: 4px; height: 4px; }
        ::-webkit-scrollbar-track { background: #161b22; }
        ::-webkit-scrollbar-thumb { background: #30363d; border-radius: 4px; }
        @keyframes nodePulse { 0%,100%{opacity:1} 50%{opacity:0.6} }
        @keyframes ringPulse { 0%{transform:scale(1);opacity:0.8} 100%{transform:scale(1.6);opacity:0} }
        @keyframes slideIn { from{transform:translateX(120%);opacity:0} to{transform:translateX(0);opacity:1} }
        @keyframes blink { 0%,100%{opacity:1} 50%{opacity:0.3} }
        @keyframes scanline { 0%{transform:translateY(-100%)} 100%{transform:translateY(400%)} }
        .tab-btn { background: none; border: none; cursor: pointer; transition: all 0.2s; }
        .tab-btn:hover { background: #21262d; }
        .row-hover:hover { background: #161b22 !important; cursor: pointer; }
        .ctrl-btn { background: #21262d; border: 1px solid #30363d; color: #8b949e; cursor: pointer; border-radius: 6px; padding: 7px 14px; font-size: 11px; font-family: monospace; letter-spacing: 0.06em; transition: all 0.2s; }
        .ctrl-btn:hover { border-color: #00f5d4; color: #00f5d4; }
        .ctrl-btn.active { background: #00f5d422; border-color: #00f5d4; color: #00f5d4; }
        .live-dot { width: 8px; height: 8px; border-radius: 50%; background: #00f5d4; animation: blink 1.2s ease-in-out infinite; }
      `}</style>

      {/* ALERT BANNER */}
      {alertVisible && alerts[0] && (
        <div style={{
          position: "fixed", top: 16, right: 16, zIndex: 1000, maxWidth: 380,
          background: "#1a0a14", border: "1px solid #f72585", borderRadius: 10,
          padding: "14px 18px", animation: "slideIn 0.3s ease",
          boxShadow: "0 0 40px #f7258544"
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 6 }}>
            <span style={{ color: "#f72585", fontSize: 16 }}>⚠</span>
            <span style={{ color: "#f72585", fontSize: 11, fontWeight: 700, letterSpacing: "0.1em" }}>FRAUD ALERT — REAL-TIME DETECTION</span>
          </div>
          <div style={{ color: "#e6edf3", fontSize: 12 }}>{alerts[0].msg}</div>
          <div style={{ color: "#6e7681", fontSize: 10, marginTop: 6 }}>Risk Score: {alerts[0].txn.riskScore} · {alerts[0].txn.userId} · {alerts[0].txn.region}</div>
        </div>
      )}

      {/* HEADER */}
      <div style={{ background: "#161b22", borderBottom: "1px solid #21262d", padding: "0 28px", display: "flex", alignItems: "center", justifyContent: "space-between", height: 60 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          <div style={{ width: 36, height: 36, background: "linear-gradient(135deg, #f72585, #7209b7)", borderRadius: 8, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 18, boxShadow: "0 0 20px #f7258566" }}>⬡</div>
          <div>
            <div style={{ fontFamily: "'Syne', sans-serif", fontWeight: 800, fontSize: 16, letterSpacing: "0.05em", color: "#e6edf3" }}>SENTINEL</div>
            <div style={{ fontSize: 9, color: "#6e7681", letterSpacing: "0.14em" }}>FRAUD DETECTION PLATFORM · BDA v2.4</div>
          </div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 20 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <div className="live-dot" style={liveMode ? {} : { background: "#6e7681", animation: "none" }} />
            <span style={{ fontSize: 10, color: liveMode ? "#00f5d4" : "#6e7681", letterSpacing: "0.1em" }}>{liveMode ? "STREAMING LIVE" : "PAUSED"}</span>
          </div>
          <button className="ctrl-btn" onClick={() => setLiveMode(v => !v)}>{liveMode ? "⏸ PAUSE" : "▶ RESUME"}</button>
          <div style={{ width: 1, height: 28, background: "#21262d" }} />
          <div style={{ fontSize: 10, color: "#6e7681", fontFamily: "monospace" }}>{new Date().toLocaleTimeString()}</div>
          <div style={{ width: 32, height: 32, borderRadius: "50%", background: "linear-gradient(135deg, #4cc9f0, #7209b7)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 13 }}>👤</div>
        </div>
      </div>

      {/* TABS */}
      <div style={{ background: "#161b22", borderBottom: "1px solid #21262d", padding: "0 28px", display: "flex", gap: 0 }}>
        {tabs.map(t => (
          <button key={t} className="tab-btn" onClick={() => setActiveTab(t)} style={{
            padding: "14px 20px", color: activeTab === t ? "#00f5d4" : "#6e7681",
            fontSize: 11, letterSpacing: "0.1em", textTransform: "uppercase", fontFamily: "monospace",
            borderBottom: activeTab === t ? "2px solid #00f5d4" : "2px solid transparent",
            fontWeight: activeTab === t ? 700 : 400
          }}>{t}</button>
        ))}
      </div>

      <div style={{ padding: "24px 28px", maxWidth: 1600, margin: "0 auto" }}>

        {/* ── OVERVIEW TAB ─────────────────────────────────────────────────── */}
        {activeTab === "overview" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>

            {/* KPI CARDS */}
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(210px, 1fr))", gap: 16 }}>
              <StatCard label="Total Transactions" value={totalTxns} icon="📊" color="#4cc9f0" spark={sparkTotal} sub={apiMetrics ? "from PostgreSQL DB" : `+${tickCount} this session`} />
              <StatCard label="Fraud Detected" value={totalFraud} icon="🚨" color="#f72585" spark={sparkFraud} sub={`${fraudRate}% fraud rate`} />
              <StatCard label="Avg Risk Score" value={parseFloat(avgRisk)} decimals={1} icon="🎯" color="#ffd60a" spark={sparkLatency} suffix="/100" />
              <StatCard label="Fraud Volume" value={fraudVolume} prefix="$" decimals={0} icon="💸" color="#f4a261" sub={`${(fraudVolume / Math.max(totalVolume, 1) * 100).toFixed(1)}% of total`} />
              <StatCard label="Detection Rate" value={94.2} suffix="%" decimals={1} icon="✓" color="#00f5d4" sub="Precision: 96.1%" />
              <StatCard label="Avg Latency" value={38} suffix="ms" icon="⚡" color="#9d4edd" sub="p99: 112ms" spark={sparkLatency.map(v => 100 - v)} />
            </div>

            {/* CHARTS ROW */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
              <div style={{ background: "#161b22", border: "1px solid #21262d", borderRadius: 12, padding: "20px 22px" }}>
                <div style={{ fontSize: 11, color: "#6e7681", letterSpacing: "0.12em", marginBottom: 16, fontWeight: 700 }}>TRANSACTION STREAM — 24H</div>
                <ResponsiveContainer width="100%" height={200}>
                  <AreaChart data={TIME_SERIES}>
                    <defs>
                      <linearGradient id="gradTotal" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#4cc9f0" stopOpacity="0.3" />
                        <stop offset="100%" stopColor="#4cc9f0" stopOpacity="0" />
                      </linearGradient>
                      <linearGradient id="gradFraud" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#f72585" stopOpacity="0.4" />
                        <stop offset="100%" stopColor="#f72585" stopOpacity="0" />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#21262d" />
                    <XAxis dataKey="hour" tick={{ fill: "#6e7681", fontSize: 10 }} interval={3} />
                    <YAxis tick={{ fill: "#6e7681", fontSize: 10 }} />
                    <Tooltip contentStyle={{ background: "#1c2128", border: "1px solid #30363d", borderRadius: 8, fontSize: 11, fontFamily: "monospace" }} />
                    <Area type="monotone" dataKey="total" stroke="#4cc9f0" fill="url(#gradTotal)" strokeWidth={2} dot={false} />
                    <Area type="monotone" dataKey="fraud" stroke="#f72585" fill="url(#gradFraud)" strokeWidth={2} dot={false} />
                  </AreaChart>
                </ResponsiveContainer>
              </div>

              <div style={{ background: "#161b22", border: "1px solid #21262d", borderRadius: 12, padding: "20px 22px" }}>
                <div style={{ fontSize: 11, color: "#6e7681", letterSpacing: "0.12em", marginBottom: 16, fontWeight: 700 }}>MODEL PERFORMANCE METRICS</div>
                <ResponsiveContainer width="100%" height={200}>
                  <RadarChart data={radarData}>
                    <PolarGrid stroke="#21262d" />
                    <PolarAngleAxis dataKey="metric" tick={{ fill: "#8b949e", fontSize: 10 }} />
                    <Radar name="Score" dataKey="value" stroke="#00f5d4" fill="#00f5d4" fillOpacity={0.15} strokeWidth={2} />
                  </RadarChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* HEATMAP + NETWORK */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
              <div style={{ background: "#161b22", border: "1px solid #21262d", borderRadius: 12, padding: "20px 22px" }}>
                <div style={{ fontSize: 11, color: "#6e7681", letterSpacing: "0.12em", marginBottom: 16, fontWeight: 700 }}>FRAUD RATE HEATMAP — REGION × CHANNEL</div>
                <HeatmapGrid transactions={txns} />
              </div>
              <div style={{ background: "#161b22", border: "1px solid #21262d", borderRadius: 12, padding: "20px 22px" }}>
                <div style={{ fontSize: 11, color: "#6e7681", letterSpacing: "0.12em", marginBottom: 16, fontWeight: 700 }}>ENTITY RELATIONSHIP GRAPH</div>
                <div style={{ fontSize: 10, color: "#30363d", marginBottom: 10 }}>
                  <span style={{ color: "#4cc9f0" }}>● Merchant</span>&nbsp;&nbsp;
                  <span style={{ color: "#f72585" }}>● Fraud User</span>&nbsp;&nbsp;
                  <span style={{ color: "#00f5d4" }}>● Clean User</span>&nbsp;&nbsp;
                  <span style={{ color: "#9d4edd" }}>— Fraud link</span>
                </div>
                <NetworkGraph transactions={txns} />
              </div>
            </div>

            {/* RECENT ALERTS */}
            <div style={{ background: "#161b22", border: "1px solid #21262d", borderRadius: 12, padding: "20px 22px" }}>
              <div style={{ fontSize: 11, color: "#6e7681", letterSpacing: "0.12em", marginBottom: 16, fontWeight: 700 }}>RECENT FRAUD ALERTS</div>
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {txns.filter(t => t.isFraud && t.riskScore > 80).slice(0, 5).map(t => (
                  <div key={t.id} style={{ display: "flex", alignItems: "center", gap: 16, padding: "12px 16px", background: "#0d1117", borderRadius: 8, border: "1px solid #f7258522", cursor: "pointer" }} onClick={() => { setSelectedTxn(t); setActiveTab("transactions"); }}>
                    <span style={{ color: "#f72585", fontSize: 18 }}>⚠</span>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontSize: 12, color: "#e6edf3", marginBottom: 2 }}>{t.fraudType} · {t.merchant}</div>
                      <div style={{ fontSize: 10, color: "#6e7681", fontFamily: "monospace" }}>{t.id} · {t.userId} · {t.region}</div>
                    </div>
                    <div style={{ textAlign: "right" }}>
                      <div style={{ color: "#f72585", fontSize: 13, fontWeight: 700 }}>${t.amount.toFixed(2)}</div>
                      <RiskBadge score={t.riskScore} />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* ── TRANSACTIONS TAB ─────────────────────────────────────────────── */}
        {activeTab === "transactions" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            {/* FILTERS */}
            <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center" }}>
              <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search TXN / USR / Merchant..." style={{
                background: "#161b22", border: "1px solid #30363d", borderRadius: 8, padding: "8px 14px",
                color: "#e6edf3", fontSize: 12, fontFamily: "monospace", width: 260, outline: "none"
              }} />
              {["ALL", "FLAGGED", "REVIEWING", "CONFIRMED", "CLEARED", "BLOCKED"].map(s => (
                <button key={s} className={`ctrl-btn ${filterStatus === s ? "active" : ""}`} onClick={() => setFilterStatus(s)}>{s}</button>
              ))}
              <div style={{ width: 1, height: 28, background: "#21262d" }} />
              {["ALL", "CRITICAL", "HIGH", "LOW"].map(r => (
                <button key={r} className={`ctrl-btn ${filterRisk === r ? "active" : ""}`} onClick={() => setFilterRisk(r)}>
                  {r === "ALL" ? "ALL RISK" : `${r} RISK`}
                </button>
              ))}
              <span style={{ fontSize: 10, color: "#6e7681", marginLeft: "auto", fontFamily: "monospace" }}>{filtered.length} records</span>
            </div>

            {/* TABLE */}
            <div style={{ background: "#161b22", border: "1px solid #21262d", borderRadius: 12, overflow: "hidden" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 11, fontFamily: "monospace" }}>
                <thead>
                  <tr style={{ background: "#0d1117", borderBottom: "1px solid #21262d" }}>
                    {["Transaction ID", "Timestamp", "User", "Merchant", "Amount", "Channel", "Region", "Risk Score", "Fraud Type", "Status"].map(h => (
                      <th key={h} style={{ padding: "12px 14px", color: "#6e7681", fontWeight: 600, textAlign: "left", letterSpacing: "0.08em", whiteSpace: "nowrap" }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {filtered.slice(0, 80).map((t, i) => (
                    <tr key={t.id} className="row-hover" onClick={() => setSelectedTxn(t)} style={{
                      borderBottom: "1px solid #21262d",
                      background: selectedTxn?.id === t.id ? "#21262d" : t.isFraud ? "#1a0a14" : "transparent"
                    }}>
                      <td style={{ padding: "10px 14px", color: "#4cc9f0" }}>{t.id}</td>
                      <td style={{ padding: "10px 14px", color: "#6e7681" }}>{new Date(t.timestamp).toLocaleTimeString()}</td>
                      <td style={{ padding: "10px 14px", color: "#8b949e" }}>{t.userId}</td>
                      <td style={{ padding: "10px 14px", color: "#e6edf3" }}>{t.merchant}</td>
                      <td style={{ padding: "10px 14px", color: t.amount > 500 ? "#ffd60a" : "#e6edf3", fontWeight: t.amount > 500 ? 700 : 400 }}>${t.amount.toFixed(2)}</td>
                      <td style={{ padding: "10px 14px", color: "#8b949e" }}>{t.channel}</td>
                      <td style={{ padding: "10px 14px", color: "#8b949e" }}>{t.region}</td>
                      <td style={{ padding: "10px 14px" }}>
                        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                          <div style={{ width: 48, height: 4, background: "#21262d", borderRadius: 2 }}>
                            <div style={{ width: `${t.riskScore}%`, height: "100%", background: RISK_GRADIENT(t.riskScore), borderRadius: 2 }} />
                          </div>
                          <span style={{ color: RISK_GRADIENT(t.riskScore), fontSize: 11 }}>{t.riskScore}</span>
                        </div>
                      </td>
                      <td style={{ padding: "10px 14px", color: t.fraudType ? "#f72585" : "#30363d" }}>{t.fraudType || "—"}</td>
                      <td style={{ padding: "10px 14px" }}><StatusDot status={t.status} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* DETAIL PANEL */}
            {selectedTxn && (
              <div style={{ background: "#161b22", border: "1px solid #00f5d433", borderRadius: 12, padding: "22px 26px", display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
                <div>
                  <div style={{ fontSize: 11, color: "#6e7681", letterSpacing: "0.12em", marginBottom: 14, fontWeight: 700 }}>TRANSACTION DETAIL</div>
                  {[
                    ["ID", selectedTxn.id], ["User", selectedTxn.userId], ["Merchant", selectedTxn.merchant],
                    ["Amount", `$${selectedTxn.amount.toFixed(2)}`], ["Channel", selectedTxn.channel],
                    ["Region", selectedTxn.region], ["Processing", `${selectedTxn.processingMs}ms`],
                    ["Timestamp", new Date(selectedTxn.timestamp).toLocaleString()],
                  ].map(([k, v]) => (
                    <div key={k} style={{ display: "flex", justifyContent: "space-between", padding: "8px 0", borderBottom: "1px solid #21262d" }}>
                      <span style={{ color: "#6e7681", fontSize: 11 }}>{k}</span>
                      <span style={{ color: "#e6edf3", fontSize: 11 }}>{v}</span>
                    </div>
                  ))}
                </div>
                <div>
                  <div style={{ fontSize: 11, color: "#6e7681", letterSpacing: "0.12em", marginBottom: 14, fontWeight: 700 }}>RISK ASSESSMENT</div>
                  <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                    <div style={{ background: "#0d1117", borderRadius: 8, padding: "16px", textAlign: "center" }}>
                      <div style={{ fontSize: 48, fontWeight: 700, color: RISK_GRADIENT(selectedTxn.riskScore), fontFamily: "'Syne', sans-serif" }}>{selectedTxn.riskScore}</div>
                      <div style={{ fontSize: 10, color: "#6e7681", letterSpacing: "0.1em" }}>RISK SCORE</div>
                    </div>
                    <div style={{ display: "flex", gap: 10 }}>
                      <div style={{ flex: 1, background: "#0d1117", borderRadius: 8, padding: "12px", textAlign: "center" }}>
                        <StatusDot status={selectedTxn.status} />
                      </div>
                      <div style={{ flex: 1, background: "#0d1117", borderRadius: 8, padding: "12px", textAlign: "center" }}>
                        <RiskBadge score={selectedTxn.riskScore} />
                      </div>
                    </div>
                    {selectedTxn.fraudType && (
                      <div style={{ background: "#1a0a14", border: "1px solid #f7258533", borderRadius: 8, padding: "14px" }}>
                        <div style={{ color: "#f72585", fontSize: 11, marginBottom: 4, fontWeight: 700 }}>⚠ FRAUD TYPE DETECTED</div>
                        <div style={{ color: "#e6edf3", fontSize: 13 }}>{selectedTxn.fraudType}</div>
                      </div>
                    )}
                    <div style={{ display: "flex", gap: 8 }}>
                      <button className="ctrl-btn" style={{ flex: 1 }}>✓ CONFIRM</button>
                      <button className="ctrl-btn" style={{ flex: 1 }}>✗ CLEAR</button>
                      <button className="ctrl-btn" style={{ flex: 1, borderColor: "#f72585", color: "#f72585" }}>🚫 BLOCK</button>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* ── ANALYTICS TAB ────────────────────────────────────────────────── */}
        {activeTab === "analytics" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
              <div style={{ background: "#161b22", border: "1px solid #21262d", borderRadius: 12, padding: "20px 22px" }}>
                <div style={{ fontSize: 11, color: "#6e7681", letterSpacing: "0.12em", marginBottom: 16, fontWeight: 700 }}>THROUGHPUT & LATENCY — 24H</div>
                <ResponsiveContainer width="100%" height={220}>
                  <LineChart data={TIME_SERIES}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#21262d" />
                    <XAxis dataKey="hour" tick={{ fill: "#6e7681", fontSize: 10 }} interval={3} />
                    <YAxis yAxisId="left" tick={{ fill: "#6e7681", fontSize: 10 }} />
                    <YAxis yAxisId="right" orientation="right" tick={{ fill: "#6e7681", fontSize: 10 }} />
                    <Tooltip contentStyle={{ background: "#1c2128", border: "1px solid #30363d", borderRadius: 8, fontSize: 11, fontFamily: "monospace" }} />
                    <Line yAxisId="left" type="monotone" dataKey="throughput" stroke="#4cc9f0" strokeWidth={2} dot={false} />
                    <Line yAxisId="right" type="monotone" dataKey="latency" stroke="#ffd60a" strokeWidth={2} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>

              <div style={{ background: "#161b22", border: "1px solid #21262d", borderRadius: 12, padding: "20px 22px" }}>
                <div style={{ fontSize: 11, color: "#6e7681", letterSpacing: "0.12em", marginBottom: 16, fontWeight: 700 }}>ISOLATION FOREST — ANOMALY CLUSTERS</div>
                <ResponsiveContainer width="100%" height={220}>
                  <ScatterChart>
                    <CartesianGrid strokeDasharray="3 3" stroke="#21262d" />
                    <XAxis dataKey="x" tick={{ fill: "#6e7681", fontSize: 10 }} name="Feature 1" />
                    <YAxis dataKey="y" tick={{ fill: "#6e7681", fontSize: 10 }} name="Feature 2" />
                    <Tooltip contentStyle={{ background: "#1c2128", border: "1px solid #30363d", borderRadius: 8, fontSize: 11, fontFamily: "monospace" }} cursor={{ strokeDasharray: "3 3" }} />
                    <Scatter data={CLUSTER_DATA}>
                      {CLUSTER_DATA.map((d, i) => (
                        <Cell key={i} fill={CLUSTER_COLORS[d.cluster]} fillOpacity={0.7} />
                      ))}
                    </Scatter>
                  </ScatterChart>
                </ResponsiveContainer>
                <div style={{ display: "flex", gap: 16, marginTop: 10 }}>
                  {["Normal", "Suspicious", "High-Risk", "Outlier"].map((l, i) => (
                    <div key={l} style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 10, color: "#8b949e" }}>
                      <div style={{ width: 8, height: 8, borderRadius: "50%", background: CLUSTER_COLORS[i] }} />
                      {l}
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* FRAUD TYPE BREAKDOWN */}
            <div style={{ background: "#161b22", border: "1px solid #21262d", borderRadius: 12, padding: "20px 22px" }}>
              <div style={{ fontSize: 11, color: "#6e7681", letterSpacing: "0.12em", marginBottom: 20, fontWeight: 700 }}>FRAUD TYPE DISTRIBUTION</div>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12 }}>
                {FRAUD_TYPES.map((ft, i) => {
                  const count = txns.filter(t => t.fraudType === ft).length;
                  const pct = (count / totalFraud * 100).toFixed(1);
                  const colors2 = ["#f72585", "#f4a261", "#ffd60a", "#4cc9f0", "#9d4edd", "#00f5d4"];
                  return (
                    <div key={ft} style={{ background: "#0d1117", borderRadius: 8, padding: "14px 16px", border: `1px solid ${colors2[i]}33` }}>
                      <div style={{ fontSize: 12, color: "#e6edf3", marginBottom: 8 }}>{ft}</div>
                      <div style={{ height: 4, background: "#21262d", borderRadius: 2, marginBottom: 8 }}>
                        <div style={{ width: `${pct}%`, height: "100%", background: colors2[i], borderRadius: 2 }} />
                      </div>
                      <div style={{ display: "flex", justifyContent: "space-between" }}>
                        <span style={{ color: colors2[i], fontSize: 18, fontWeight: 700 }}>{count}</span>
                        <span style={{ color: "#6e7681", fontSize: 11 }}>{pct}%</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* MODEL METRICS TABLE */}
            <div style={{ background: "#161b22", border: "1px solid #21262d", borderRadius: 12, padding: "20px 22px" }}>
              <div style={{ fontSize: 11, color: "#6e7681", letterSpacing: "0.12em", marginBottom: 16, fontWeight: 700 }}>MODEL PERFORMANCE COMPARISON</div>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 11, fontFamily: "monospace" }}>
                <thead>
                  <tr style={{ borderBottom: "1px solid #21262d" }}>
                    {["Model", "Precision", "Recall", "F1", "AUC-ROC", "Latency", "Status"].map(h => (
                      <th key={h} style={{ padding: "10px 14px", color: "#6e7681", textAlign: "left", letterSpacing: "0.08em" }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {[
                    ["Isolation Forest", "91.2%", "88.4%", "89.8%", "0.967", "8ms", "ACTIVE"],
                    ["XGBoost Classifier", "96.1%", "87.3%", "91.5%", "0.982", "12ms", "ACTIVE"],
                    ["LSTM Sequence", "89.7%", "93.2%", "91.4%", "0.978", "45ms", "ACTIVE"],
                    ["DBSCAN Clustering", "84.3%", "79.1%", "81.6%", "0.921", "67ms", "STANDBY"],
                    ["Random Forest", "94.8%", "85.9%", "90.2%", "0.971", "15ms", "STANDBY"],
                  ].map(([name, prec, rec, f1, auc, lat, status]) => (
                    <tr key={name} style={{ borderBottom: "1px solid #21262d" }}>
                      <td style={{ padding: "12px 14px", color: "#4cc9f0", fontWeight: 700 }}>{name}</td>
                      <td style={{ padding: "12px 14px", color: "#e6edf3" }}>{prec}</td>
                      <td style={{ padding: "12px 14px", color: "#e6edf3" }}>{rec}</td>
                      <td style={{ padding: "12px 14px", color: "#00f5d4", fontWeight: 700 }}>{f1}</td>
                      <td style={{ padding: "12px 14px", color: "#ffd60a" }}>{auc}</td>
                      <td style={{ padding: "12px 14px", color: "#8b949e" }}>{lat}</td>
                      <td style={{ padding: "12px 14px" }}>
                        <span style={{ background: status === "ACTIVE" ? "#00f5d422" : "#21262d", color: status === "ACTIVE" ? "#00f5d4" : "#6e7681", border: `1px solid ${status === "ACTIVE" ? "#00f5d4" : "#30363d"}`, borderRadius: 4, padding: "2px 8px", fontSize: 10, letterSpacing: "0.06em" }}>{status}</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* ── PIPELINE TAB ─────────────────────────────────────────────────── */}
        {activeTab === "pipeline" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
            <div style={{ background: "#161b22", border: "1px solid #21262d", borderRadius: 12, padding: "30px 28px" }}>
              <div style={{ fontSize: 11, color: "#6e7681", letterSpacing: "0.12em", marginBottom: 28, fontWeight: 700 }}>BDA PIPELINE ARCHITECTURE — REAL-TIME</div>
              {[
                {
                  label: "INGESTION LAYER",
                  color: "#4cc9f0",
                  nodes: [
                    { label: "Kafka Topics", sub: "📨", color: "#4cc9f0", active: true, pulse: true },
                    { label: "Event Streams", sub: "⚡", color: "#4cc9f0", active: true, pulse: false },
                    { label: "REST APIs", sub: "🔌", color: "#4cc9f0", active: true, pulse: false },
                    { label: "DB CDC", sub: "💾", color: "#4cc9f0", active: false, pulse: false },
                  ]
                },
                {
                  label: "PROCESSING LAYER",
                  color: "#9d4edd",
                  nodes: [
                    { label: "Spark Streaming", sub: "🔥", color: "#9d4edd", active: true, pulse: true },
                    { label: "Flink Jobs", sub: "🌊", color: "#9d4edd", active: true, pulse: false },
                    { label: "Feature Eng.", sub: "⚙️", color: "#9d4edd", active: true, pulse: false },
                    { label: "ETL Pipeline", sub: "🔄", color: "#9d4edd", active: true, pulse: false },
                  ]
                },
                {
                  label: "ML INFERENCE LAYER",
                  color: "#f72585",
                  nodes: [
                    { label: "Isolation Forest", sub: "🌲", color: "#f72585", active: true, pulse: true },
                    { label: "XGBoost", sub: "🎯", color: "#f72585", active: true, pulse: false },
                    { label: "LSTM Network", sub: "🧠", color: "#f72585", active: true, pulse: false },
                    { label: "Feature Store", sub: "📦", color: "#f4a261", active: true, pulse: false },
                  ]
                },
                {
                  label: "STORAGE LAYER",
                  color: "#00f5d4",
                  nodes: [
                    { label: "PostgreSQL", sub: "🐘", color: "#00f5d4", active: true, pulse: false },
                    { label: "Redis Cache", sub: "⚡", color: "#ffd60a", active: true, pulse: true },
                    { label: "MongoDB Logs", sub: "🍃", color: "#00f5d4", active: true, pulse: false },
                    { label: "HDFS/S3", sub: "🗄️", color: "#00f5d4", active: true, pulse: false },
                  ]
                },
              ].map((layer, li) => (
                <div key={layer.label} style={{ marginBottom: li < 3 ? 24 : 0 }}>
                  <div style={{ fontSize: 9, color: layer.color, letterSpacing: "0.16em", marginBottom: 14, fontWeight: 700, paddingLeft: 4, borderLeft: `3px solid ${layer.color}` }}>&nbsp;{layer.label}</div>
                  <div style={{ display: "flex", alignItems: "center", gap: 0 }}>
                    {layer.nodes.map((n, ni) => (
                      <div key={n.label} style={{ display: "flex", alignItems: "center" }}>
                        <PipelineNode {...n} />
                        {ni < layer.nodes.length - 1 && (
                          <div style={{ width: 40, height: 2, background: `linear-gradient(90deg, ${layer.color}88, ${layer.color}22)`, margin: "0 4px", position: "relative", top: -12 }}>
                            <div style={{ position: "absolute", right: -4, top: -4, color: layer.color, fontSize: 10 }}>▶</div>
                          </div>
                        )}
                      </div>
                    ))}
                    <div style={{ flex: 1, height: 1, background: "#21262d", marginLeft: 20, position: "relative", top: -12 }} />
                  </div>
                  {li < 3 && (
                    <div style={{ display: "flex", justifyContent: "center", marginTop: 8, marginBottom: 6 }}>
                      <div style={{ width: 2, height: 20, background: `linear-gradient(180deg, ${layer.color}88, ${["#9d4edd","#f72585","#00f5d4","#21262d"][li]}88)` }} />
                    </div>
                  )}
                </div>
              ))}
            </div>

            {/* PIPELINE STATS */}
            <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12 }}>
              {[
                { label: "Kafka Topics", value: "12 active", color: "#4cc9f0", detail: "3.2M msg/hr" },
                { label: "Spark Jobs", value: "8 running", color: "#9d4edd", detail: "4 batch, 4 stream" },
                { label: "ML Models", value: "3 live", color: "#f72585", detail: "2 warm standby" },
                { label: "Cache Hit Rate", value: "94.7%", color: "#ffd60a", detail: "Redis 12GB used" },
              ].map(s => (
                <div key={s.label} style={{ background: "#161b22", border: `1px solid ${s.color}33`, borderRadius: 10, padding: "16px 18px" }}>
                  <div style={{ fontSize: 10, color: "#6e7681", letterSpacing: "0.1em", marginBottom: 8 }}>{s.label}</div>
                  <div style={{ fontSize: 20, fontWeight: 700, color: s.color, marginBottom: 4 }}>{s.value}</div>
                  <div style={{ fontSize: 10, color: "#6e7681" }}>{s.detail}</div>
                </div>
              ))}
            </div>

            {/* KAFKA TOPICS TABLE */}
            <div style={{ background: "#161b22", border: "1px solid #21262d", borderRadius: 12, padding: "20px 22px" }}>
              <div style={{ fontSize: 11, color: "#6e7681", letterSpacing: "0.12em", marginBottom: 16, fontWeight: 700 }}>KAFKA TOPICS — LIVE STATUS</div>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 11, fontFamily: "monospace" }}>
                <thead><tr style={{ borderBottom: "1px solid #21262d" }}>
                  {["Topic", "Partitions", "Replication", "Msg/sec", "Consumers", "Lag", "Status"].map(h => (
                    <th key={h} style={{ padding: "10px 14px", color: "#6e7681", textAlign: "left" }}>{h}</th>
                  ))}
                </tr></thead>
                <tbody>
                  {[
                    ["txn.raw", 24, 3, "8,240", 4, "120ms", "HEALTHY"],
                    ["txn.enriched", 12, 3, "8,190", 3, "145ms", "HEALTHY"],
                    ["fraud.alerts", 6, 3, "420", 8, "18ms", "HEALTHY"],
                    ["model.predictions", 8, 2, "8,180", 2, "92ms", "HEALTHY"],
                    ["audit.logs", 4, 2, "9,100", 1, "2.1s", "WARNING"],
                    ["dlq.failed", 2, 2, "12", 1, "—", "IDLE"],
                  ].map(([topic, parts, rep, mps, cons, lag, status]) => (
                    <tr key={topic} style={{ borderBottom: "1px solid #21262d" }}>
                      <td style={{ padding: "11px 14px", color: "#4cc9f0" }}>{topic}</td>
                      <td style={{ padding: "11px 14px", color: "#e6edf3" }}>{parts}</td>
                      <td style={{ padding: "11px 14px", color: "#e6edf3" }}>{rep}</td>
                      <td style={{ padding: "11px 14px", color: "#00f5d4" }}>{mps}</td>
                      <td style={{ padding: "11px 14px", color: "#8b949e" }}>{cons}</td>
                      <td style={{ padding: "11px 14px", color: lag === "—" ? "#30363d" : parseFloat(lag) > 1 ? "#ffd60a" : "#8b949e" }}>{lag}</td>
                      <td style={{ padding: "11px 14px" }}>
                        <span style={{ color: status === "HEALTHY" ? "#00f5d4" : status === "WARNING" ? "#ffd60a" : "#6e7681", fontSize: 10 }}>● {status}</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* ── MODELS TAB ───────────────────────────────────────────────────── */}
        {activeTab === "models" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 16 }}>
              {[
                { name: "Isolation Forest", type: "Anomaly Detection", version: "v2.1.4", precision: 91.2, recall: 88.4, f1: 89.8, auc: 0.967, latency: 8, color: "#4cc9f0", trained: "2h ago", samples: "2.4M" },
                { name: "XGBoost", type: "Binary Classification", version: "v3.0.1", precision: 96.1, recall: 87.3, f1: 91.5, auc: 0.982, latency: 12, color: "#f72585", trained: "6h ago", samples: "4.1M" },
                { name: "LSTM Network", type: "Sequence Modeling", version: "v1.8.2", precision: 89.7, recall: 93.2, f1: 91.4, auc: 0.978, latency: 45, color: "#9d4edd", trained: "12h ago", samples: "1.8M" },
              ].map(m => (
                <div key={m.name} style={{ background: "#161b22", border: `1px solid ${m.color}33`, borderRadius: 12, padding: "22px 22px" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 16 }}>
                    <div>
                      <div style={{ fontSize: 14, color: "#e6edf3", fontWeight: 700, fontFamily: "'Syne', sans-serif" }}>{m.name}</div>
                      <div style={{ fontSize: 10, color: "#6e7681", marginTop: 3 }}>{m.type} · {m.version}</div>
                    </div>
                    <span style={{ background: "#00f5d422", color: "#00f5d4", border: "1px solid #00f5d444", borderRadius: 4, padding: "2px 8px", fontSize: 10 }}>ACTIVE</span>
                  </div>
                  {[
                    ["Precision", m.precision, "%"], ["Recall", m.recall, "%"], ["F1-Score", m.f1, "%"]
                  ].map(([label, val, suf]) => (
                    <div key={label} style={{ marginBottom: 12 }}>
                      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 5 }}>
                        <span style={{ fontSize: 10, color: "#6e7681" }}>{label}</span>
                        <span style={{ fontSize: 11, color: m.color, fontWeight: 700 }}>{val}{suf}</span>
                      </div>
                      <div style={{ height: 3, background: "#21262d", borderRadius: 2 }}>
                        <div style={{ width: `${val}%`, height: "100%", background: m.color, borderRadius: 2 }} />
                      </div>
                    </div>
                  ))}
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, marginTop: 16 }}>
                    {[["AUC-ROC", m.auc, "#ffd60a"], ["Latency", `${m.latency}ms`, "#4cc9f0"], ["Trained", m.trained, "#8b949e"], ["Samples", m.samples, "#8b949e"]].map(([k, v, c]) => (
                      <div key={k} style={{ background: "#0d1117", borderRadius: 6, padding: "10px" }}>
                        <div style={{ fontSize: 9, color: "#6e7681", marginBottom: 3, letterSpacing: "0.08em" }}>{k}</div>
                        <div style={{ fontSize: 13, color: c, fontWeight: 700 }}>{v}</div>
                      </div>
                    ))}
                  </div>
                  <div style={{ display: "flex", gap: 8, marginTop: 16 }}>
                    <button className="ctrl-btn" style={{ flex: 1 }}>Retrain</button>
                    <button className="ctrl-btn" style={{ flex: 1 }}>Explain</button>
                  </div>
                </div>
              ))}
            </div>

            {/* FEATURE IMPORTANCE */}
            <div style={{ background: "#161b22", border: "1px solid #21262d", borderRadius: 12, padding: "20px 22px" }}>
              <div style={{ fontSize: 11, color: "#6e7681", letterSpacing: "0.12em", marginBottom: 20, fontWeight: 700 }}>FEATURE IMPORTANCE — XGBOOST</div>
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                {[
                  ["transaction_amount", 0.231, "#f72585"],
                  ["velocity_1h", 0.187, "#f4a261"],
                  ["merchant_risk_score", 0.162, "#ffd60a"],
                  ["geo_anomaly_score", 0.141, "#4cc9f0"],
                  ["device_fingerprint_match", 0.098, "#9d4edd"],
                  ["time_since_last_txn", 0.076, "#00f5d4"],
                  ["amount_vs_avg_30d", 0.062, "#8b949e"],
                  ["channel_frequency_score", 0.043, "#6e7681"],
                ].map(([feat, imp, color]) => (
                  <div key={feat} style={{ display: "flex", alignItems: "center", gap: 14 }}>
                    <span style={{ fontSize: 11, color: "#8b949e", minWidth: 220, fontFamily: "monospace" }}>{feat}</span>
                    <div style={{ flex: 1, height: 12, background: "#21262d", borderRadius: 6 }}>
                      <div style={{ width: `${imp * 400}%`, height: "100%", background: `linear-gradient(90deg, ${color}, ${color}88)`, borderRadius: 6 }} />
                    </div>
                    <span style={{ fontSize: 11, color, minWidth: 46, textAlign: "right", fontWeight: 700 }}>{(imp * 100).toFixed(1)}%</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* FOOTER STATUS BAR */}
      <div style={{ position: "sticky", bottom: 0, background: "#0d1117", borderTop: "1px solid #21262d", padding: "8px 28px", display: "flex", alignItems: "center", gap: 24, fontSize: 10, fontFamily: "monospace", color: "#6e7681" }}>
        <span style={{ color: "#00f5d4" }}>● SYSTEM ONLINE</span>
        <span>Kafka: 12/12 partitions</span>
        <span>Spark: 8 executors</span>
        <span>ML Inference: 3 models active</span>
        <span>Redis: 94.7% hit rate</span>
        <span style={{ marginLeft: "auto", color: "#30363d" }}>SENTINEL BDA v2.4 · Anthropic Demo</span>
      </div>
    </div>
  );
}
