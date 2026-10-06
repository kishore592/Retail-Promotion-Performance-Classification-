'use client';
import {useState} from 'react';
const API=process.env.NEXT_PUBLIC_API_URL||'http://localhost:8000';
export default function Home(){
 const [q,setQ]=useState('Classify promotion P-1003 for merchant approval'); const [result,setResult]=useState<any>(null); const [loading,setLoading]=useState(false);
 async function run(){setLoading(true); const r=await fetch(`${API}/api/chat`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({session_id:'demo-ui',user_id:'merchant-001',query:q})}); setResult(await r.json()); setLoading(false)}
 return <main><header><div><span className="eyebrow">AGENTIC RETAIL AI</span><h1>Promotion Risk Studio</h1><p>Classify planned promotions before merchant approval using multi-agent reasoning, policy RAG and human review.</p></div><span className="pill">LangGraph · RAG · HITL</span></header>
 <section className="grid"><div className="card chat"><h2>Promotion request</h2><textarea value={q} onChange={e=>setQ(e.target.value)}/><button onClick={run} disabled={loading}>{loading?'Running agents…':'Run classification'}</button>{result&&<div className="response"><div className={`risk ${result.risk_classification?.risk_band?.toLowerCase()}`}>{result.risk_classification?.risk_band||'NEEDS INPUT'}</div><div dangerouslySetInnerHTML={{__html:(result.response||'').replaceAll('\n','<br/>')}}/></div>}</div>
 <div className="card"><h2>Workflow</h2>{['Triage','Promotion Data','Policy RAG','Investigation','Risk Classification','Validation','Human Approval','Response'].map((x,i)=><div className="stage" key={x}><span>{String(i+1).padStart(2,'0')}</span>{x}<b>{result?'✓':'•'}</b></div>)}</div>
 <div className="card sources"><h2>Policy sources</h2>{(result?.sources||[]).map((s:any)=><div className="source" key={s.document_id}><b>{s.document_id} · {s.title}</b><small>{s.section}</small><p>{s.text}</p></div>)}</div></section></main>
}
