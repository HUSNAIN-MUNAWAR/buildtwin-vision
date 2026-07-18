"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

const nav=[
 ["Command Center","/command-center","⌂"],["Digital Twin","/digital-twin","◇"],["4D Schedule","/schedule","▤"],["Site Captures","/captures","▣"],["Progress Review","/progress","✓"],["Change Analysis","/changes","◫"],["Safety","/safety","△"],["Quality","/quality","✦"],["Risk Forecast","/risk","↗"],["Reports","/reports","▧"],["Cameras","/cameras","◉"],["Alerts","/alerts","!"],["Audit Log","/audit","≡"]
];
export default function AppShell({children,title,subtitle}:{children:React.ReactNode,title:string,subtitle:string}){
 const path=usePathname(); const router=useRouter(); const [user,setUser]=useState<{full_name:string;role:string}|null>(null); const [open,setOpen]=useState(false);
 useEffect(()=>{const raw=localStorage.getItem("buildtwin_user");const auth=localStorage.getItem("buildtwin_token");if(!auth){router.replace("/login");return}if(raw)setUser(JSON.parse(raw));},[router]);
 function logout(){localStorage.removeItem("buildtwin_token");localStorage.removeItem("buildtwin_user");router.push("/login")}
 return <div className="app-shell"><aside className={open?"sidebar open":"sidebar"}><div className="brand side-brand"><span className="brand-mark">BT</span><span>BuildTwin <b>Vision</b></span></div><div className="project-chip"><span>ACTIVE PROJECT</span><b>Northstar Medical Center</b><small>NSMC-26 · Islamabad</small></div><nav>{nav.map(([name,href,icon])=><Link key={href} href={href} className={path===href?"nav-link active":"nav-link"}><i>{icon}</i><span>{name}</span></Link>)}</nav><div className="sidebar-foot"><div className="avatar">{user?.full_name?.split(" ").map(x=>x[0]).join("").slice(0,2)??"BT"}</div><div><b>{user?.full_name??"Loading…"}</b><small>{user?.role?.replaceAll("_"," ")}</small></div><button onClick={logout} title="Sign out">↪</button></div></aside><main className="workspace"><header className="workspace-head"><button className="menu" onClick={()=>setOpen(!open)}>☰</button><div><div className="eyebrow">NORTHSTAR / LIVE OPERATIONS</div><h1>{title}</h1><p>{subtitle}</p></div><div className="system-status"><span className="pulse"/> API connected</div></header><div className="workspace-body">{children}</div></main></div>
}
