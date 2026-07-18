"use client";
import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { API } from "@/lib/api";

export default function Login(){
 const router=useRouter(); const [email,setEmail]=useState("admin@buildtwin.local"); const [password,setPassword]=useState("BuildTwin123!"); const [error,setError]=useState(""); const [busy,setBusy]=useState(false);
 async function submit(e:FormEvent){e.preventDefault();setBusy(true);setError("");try{const r=await fetch(`${API}/auth/login`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({email,password})});const body=await r.json();if(!r.ok)throw new Error(body.detail??"Login failed");localStorage.setItem("buildtwin_token",body.access_token);localStorage.setItem("buildtwin_user",JSON.stringify(body.user));router.push("/command-center");}catch(e){setError(e instanceof Error?e.message:"Login failed");}finally{setBusy(false)}}
 return <main className="login-page"><Link href="/" className="brand"><span className="brand-mark">BT</span><span>BuildTwin <b>Vision</b></span></Link><form className="login-card" onSubmit={submit}><div className="eyebrow">NORTHSTAR OPERATIONS</div><h1>Enter the 4D command center</h1><p>Use the deterministic local demo account. Authentication and organization scoping are enforced by the API.</p><label>Email<input value={email} onChange={e=>setEmail(e.target.value)} type="email" /></label><label>Password<input value={password} onChange={e=>setPassword(e.target.value)} type="password" /></label>{error&&<div className="error-box">{error}</div>}<button className="button primary full" disabled={busy}>{busy?"Authenticating…":"Sign in securely"}</button><div className="demo-note"><b>Local demo</b><span>admin@buildtwin.local</span><span>BuildTwin123!</span></div></form></main>
}
