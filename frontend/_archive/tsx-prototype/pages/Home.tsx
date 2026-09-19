import type { Page } from "../layout/Shell";

export function Home({setPage,historyCount}:{setPage:(p:Page)=>void;historyCount:number}) {
  const hasHistory=historyCount>0;
  return <section className="home-page">
    <div className="hero">
      <p className="eyebrow">A personal monitoring practice</p>
      <h1>Understand your skin<br/>over time.</h1>
      <p className="lede">AI-assisted skin monitoring using ordinary RGB photographs. Build a personal reference, then return under similar conditions to understand model-derived observations over time.</p>
      <div className="actions"><button className="button" onClick={()=>setPage("scan")}>Start a scan <span>→</span></button><button className="button text" onClick={()=>setPage("timeline")}>View history</button></div>
    </div>
    <section className="home-status" aria-label="Observation record">
      <p className="eyebrow">Your observation record</p>
      {hasHistory?<><h2>Latest observation recorded</h2><p>You have {historyCount} recorded observation{historyCount===1?"":"s"}. Open your history to revisit the available monitoring context.</p><button className="button secondary" onClick={()=>setPage("timeline")}>View history →</button></>:<><h2>Your first scan starts a personal reference.</h2><p>Use a clear photograph today. Future observations can be compared with this reference when enough history is available.</p><button className="button secondary" onClick={()=>setPage("scan")}>Create your first observation →</button></>}
    </section>
  </section>
}
