import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { Analysis, SpectralVisualization } from "../types/api";
import type { Page } from "../layout/Shell";
import { ErrorState, Loading } from "../ui/State";

const obj = (value: unknown): Record<string, unknown> => value && typeof value === "object" ? value as Record<string, unknown> : {};
const pipelineFor = (analysis: Analysis | null) => obj(obj(analysis?.result).metadata).pipeline as Record<string, unknown> | undefined;
const viewFor = (analysis: Analysis | null): SpectralVisualization | null => { const view = obj(pipelineFor(analysis)).spectral_visualization as SpectralVisualization | undefined; return view?.available === true ? view : null; };
function SpectrumCurve({ spectrum }: { spectrum: NonNullable<SpectralVisualization["roi_spectrum"]> }) { const low = Math.min(...spectrum.values), span = Math.max(...spectrum.values) - low || 1, points = spectrum.values.map((item, index) => `${index / (spectrum.values.length - 1) * 100},${42 - ((item - low) / span) * 36}`).join(" "); return <figure className="spectrum-curve"><figcaption>Regional spectral response</figcaption><svg viewBox="0 0 100 48" role="img" aria-label="Regional spectral response from 400 to 700 nanometres"><line x1="0" y1="42" x2="100" y2="42"/><polyline points={points}/></svg><div><span>400 nm</span><span>700 nm</span></div></figure>; }

function SpectralPanel({ analysis }: { analysis: Analysis }) {
  const view = viewFor(analysis);
  if (!view) return <section className="spectral-panel unavailable"><p className="eyebrow">Spectral view</p><h2>AI-estimated spectral representation</h2><p>Spectral reconstruction isn't available for this observation.</p></section>;
  return <section className="spectral-panel"><header><div><p className="eyebrow">Spectral view</p><h2>{view.label}</h2></div><p className="spectral-meta">{view.wavelength_range_nm[0]}–{view.wavelength_range_nm[1]} nm · {view.reconstructed_band_count} visible bands</p></header><div className="spectral-images"><figure><img src={view.false_color_image} alt="AI-estimated spectral false-color representation"/><figcaption>False-color spectral view</figcaption></figure><figure><img src={view.representative_band.image} alt={`AI-estimated ${view.representative_band.wavelength_nm} nanometre spectral band`}/><figcaption>Representative band · {view.representative_band.wavelength_nm} nm</figcaption></figure>{view.roi_spectrum && <SpectrumCurve spectrum={view.roi_spectrum}/>}</div><p className="spectral-note">{view.note}</p></section>;
}

const stages = ["Image quality", "Skin region analysis", "Spectral reconstruction", "Feature analysis", "Monitoring analysis", "Evidence retrieval", "Safety assessment"];
function Stages({ analysis, running }: { analysis: Analysis | null; running: boolean }) {
  const metadata = obj(obj(analysis?.result).metadata), pipeline = obj(metadata.pipeline), completed = new Set(Array.isArray(metadata.completed_steps) ? metadata.completed_steps.map(String) : []), rejected = analysis?.status === "quality_rejected";
  const status = (stage: string) => {
    if (!analysis) return running ? "running" : "waiting";
    if (rejected) return stage === "Image quality" ? "complete" : "not run";
    if (stage === "Image quality") return "complete";
    if (stage === "Skin region analysis") return pipeline.segmentation_method ? "complete" : "unavailable";
    if (stage === "Spectral reconstruction") return pipeline.spectral_reconstruction_available === true ? "complete" : "unavailable";
    if (stage === "Feature analysis") return typeof pipeline.rgb_feature_count === "number" ? "complete" : "unavailable";
    if (stage === "Monitoring analysis") return obj(analysis.result).monitoring_result ? "complete" : "unavailable";
    return completed.has(stage === "Evidence retrieval" ? "evidence" : "safety") ? "complete" : "unavailable";
  };
  return <section className="workflow" aria-label="Analysis stages"><p className="eyebrow">{running ? "Processing" : "Processing status"}</p>{stages.map(stage => { const current = status(stage); return <p key={stage}><span>{current === "complete" ? "✓" : current === "running" ? "•" : current === "not run" ? "—" : "○"}</span>{stage}<small> · {current}</small></p>; })}</section>;
}

function Rejected({ analysis, setPage }: { analysis: Analysis; setPage: (page: Page) => void }) {
  const reasons = obj(pipelineFor(analysis)).quality_reasons;
  return <section className="report-section"><p className="eyebrow">Image quality check</p><h2>Please retake or re-upload this image.</h2><p>The image did not pass the quality check, so no downstream analysis was run.</p>{Array.isArray(reasons) && <ul>{reasons.map(reason => <li key={String(reason)}>{String(reason)}</li>)}</ul>}<div className="actions"><button className="button" onClick={() => setPage("scan")}>Retake or re-upload</button></div></section>;
}

export function AnalysisPage({ scanId, userId, preview, onDone, setPage }: { scanId: string | null; userId: string | null; preview: string; onDone: (value: Analysis) => void; setPage: (page: Page) => void }) {
  const [error, setError] = useState(""), [running, setRunning] = useState(false), [analysis, setAnalysis] = useState<Analysis | null>(null);
  const run = async () => { if (!scanId || !userId) return; setRunning(true); setError(""); setAnalysis(null); try { const result = await api.analyze(scanId, userId); setAnalysis(result); onDone(result); } catch (cause) { setError(cause instanceof Error ? cause.message : "Something went wrong while preparing this observation."); } finally { setRunning(false); } };
  useEffect(() => { void run(); }, [scanId]);
  if (!scanId) return <ErrorState message="Select or create a scan before analysis."/>;
  const rejected = analysis?.status === "quality_rejected";
  return <section className="page analysis-page"><p className="eyebrow">Analysis</p><h1>{rejected ? "This image needs another try." : "Looking at this observation."}</h1><p className="lede">Processing states reflect the backend response. SpectraDerm is a monitoring prototype, not a medical diagnosis.</p><div className="analysis-grid"><div>{preview ? <img className="preview" src={preview} alt="Current RGB observation"/> : <div className="image-fallback">Your RGB observation is stored privately.</div>}<p className="caption">Original RGB image</p></div><Stages analysis={analysis} running={running}/></div>{running && <Loading>Your scan is being prepared…</Loading>}{error && <ErrorState message={error} retry={run}/>} {rejected && <Rejected analysis={analysis} setPage={setPage}/>} {analysis && !rejected && <><SpectralPanel analysis={analysis}/><section className="what-analyzed"><p className="eyebrow">What we analyzed</p><h2>Built for a consistent record.</h2><div><p><b>Visible color characteristics</b><span>Appearance information from the uploaded RGB image.</span></p><p><b>Regional appearance characteristics</b><span>Information from the available skin region.</span></p><p><b>Estimated spectral response</b><span>Only when reconstruction is available from the RGB image.</span></p><p><b>Comparison-ready features</b><span>Structured for future model-derived monitoring.</span></p></div></section><div className="actions"><button className="button" onClick={() => setPage("result")}>View your observation →</button></div></>}</section>;
}
