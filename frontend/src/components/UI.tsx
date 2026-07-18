import { mediaUrl } from "@/lib/api";
export function Status({value}:{value:string|number}){const s=String(value).toLowerCase();return <span className={`status ${s.replaceAll(" ","-")}`}>{String(value).replaceAll("_"," ")}</span>}
export function Kpi({label,value,detail,tone=""}:{label:string,value:string|number,detail:string,tone?:string}){return <article className={`kpi ${tone}`}><span>{label}</span><strong>{value}</strong><small>{detail}</small></article>}
export function ProgressBar({value,planned}:{value:number,planned?:number}){return <div className="progress-track"><span style={{width:`${Math.max(0,Math.min(100,value))}%`}}/>{planned!==undefined&&<i style={{left:`${Math.max(0,Math.min(100,planned))}%`}} title={`Planned ${planned}%`}/>}</div>}
export function Empty({text}:{text:string}){return <div className="empty"><b>No records</b><p>{text}</p></div>}
export function Loading(){return <div className="loading-grid">{Array.from({length:6}).map((_,i)=><span key={i}/>)}</div>}
export function Evidence({src,alt}:{src?:string,alt:string}){return src?<img className="evidence" src={mediaUrl(src)} alt={alt}/>:<div className="evidence missing">No evidence</div>}
export function RiskMeter({score}:{score:number}){return <div className="risk-meter"><div style={{"--score":score} as React.CSSProperties}/><b>{score}</b></div>}
