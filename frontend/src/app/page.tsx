import Link from "next/link";

const pillars=[
  ["BIM-connected evidence","Trace every progress KPI to IFC elements, schedule activities, site zones, captures, algorithms, and reviewer decisions."],
  ["Real visual processing","Decode MP4 frames, calculate aligned image change, annotate evidence, and persist processing metrics on CPU."],
  ["Explainable schedule risk","Rank activities with transparent contributions from variance, criticality, delayed predecessors, stale evidence, and operational issues."],
  ["Human-governed automation","Approve, reject, or modify AI observations without silently overwriting accepted project progress."]
];
export default function Home(){return <main className="landing">
  <nav className="landing-nav"><div className="brand"><span className="brand-mark">BT</span><span>BuildTwin <b>Vision</b></span></div><Link className="button ghost" href="/login">Open operations</Link></nav>
  <section className="hero"><div className="eyebrow">AUTONOMOUS 4D CONSTRUCTION INTELLIGENCE</div><h1>Turn site evidence into an auditable construction digital twin.</h1><p>BuildTwin Vision connects IFC elements, project schedules, visual captures, change analysis, progress approvals, safety events, quality candidates, and delay risk in one operational system.</p><div className="hero-actions"><Link className="button primary" href="/login">Launch Northstar demo</Link><a className="button ghost" href="http://localhost:8000/docs">Explore API</a></div><div className="hero-stats"><div><b>12</b><span>IFC entities</span></div><div><b>72</b><span>decoded frames</span></div><div><b>8</b><span>linked activities</span></div><div><b>100%</b><span>evidence traceability</span></div></div></section>
  <section className="pillar-grid">{pillars.map(([t,d])=><article key={t}><span className="card-index">0{pillars.findIndex(x=>x[0]===t)+1}</span><h3>{t}</h3><p>{d}</p></article>)}</section>
  <section className="flow"><div><span className="eyebrow">CONNECTED WORKFLOW</span><h2>Capture → detect → review → approve → forecast</h2></div><div className="flow-line">IFC + schedule <b>›</b> site media <b>›</b> evidence observations <b>›</b> human decision <b>›</b> 4D project control</div></section>
</main>}
