/**
 * Turns the orchestrator payload into the handful of values the screens show.
 *
 * The backend speaks in engineering terms. The product speaks to a person
 * looking at their own skin. All of that translation lives here so the wording
 * stays consistent and the non-diagnostic framing cannot drift screen by screen.
 */

export function readResult(payload) {
  const result = payload?.result || {}
  const pipeline = result.metadata?.pipeline || {}
  const vision = result.vision_result || null
  const monitoring = result.monitoring_result || null
  const evidence = result.evidence_result || null
  const safety = result.safety_result || payload?.safety || null
  const progress = pipeline.progress || null

  return {
    status: payload?.status || result.status || 'unknown',
    errors: result.errors || [],
    vision,
    monitoring,
    evidence,
    safety,
    pipeline,
    progress,
    visuals: pipeline.visuals || null,
    stage: progress?.stage || null,
    scanNumber: progress?.scan_number ?? null,
    statusLabel: progress?.status_label || 'Observation recorded',
    changePercent: numberOrNull(progress?.change_percent),
    changeScore: numberOrNull(progress?.change_score),
    direction: progress?.direction_vs_previous || null,
    trend: progress?.trend || null,
    trendText: progress?.trend_text || null,
    parameters: progress?.parameters || [],
    history: progress?.history || [],
    spectral: pipeline.spectral_visualization || null,
    spectralUnavailableReason: pipeline.spectral_reconstruction_unavailable_reason || null,
    quality: pipeline.quality || vision?.image_quality_summary?.supplied_output || null,
    explanation: evidence?.explanation || null,
    sources: evidence?.retrieved_evidence || [],
    referralRecommended: safety?.professional_assessment_recommended === true,
  }
}

function numberOrNull(value) {
  return typeof value === 'number' && Number.isFinite(value) ? value : null
}

/**
 * Is the photo unusable? The quality gate runs before anything else is shown.
 * Only a REJECT stops the comparison; a borderline REVIEW continues with the
 * quality caveat shown on the result, matching the backend Vision Agent.
 */
export function qualityRejected(view) {
  if (view.vision?.overall_status === 'insufficient_quality') return true
  return String(view.quality?.status || '').toUpperCase().includes('REJECT')
}

export function qualityReasons(view) {
  const quality = view.quality
  if (!quality) return []
  if (Array.isArray(quality.reasons) && quality.reasons.length) return quality.reasons
  return Object.values(quality.metrics || {})
    .filter((metric) => metric && String(metric.status || '').toUpperCase() !== 'GOOD')
    .map((metric) => metric.message)
    .filter(Boolean)
}

/** Tone for tags and verdict borders: steady (olive), observed/notice (clay). */
export const TONE = {
  'Baseline established': 'steady',
  Stable: 'steady',
  'Slight change': 'observed',
  'Change detected': 'notice',
}

export function headline(view) {
  if (view.stage === 'baseline') {
    return {
      tone: 'steady',
      title: 'Baseline established',
      body: 'This first scan is your personal baseline. Your next scans will be compared with it.',
    }
  }
  if (view.changePercent === null) {
    return { tone: 'steady', title: 'Observation recorded', body: 'Change information is not available for this scan.' }
  }
  const pct = view.changePercent.toFixed(0)
  if (view.statusLabel === 'Stable') {
    return {
      tone: 'steady',
      title: 'Stable — no meaningful change',
      body: `The monitored skin region is close to your personal baseline (overall change ${pct}%).`,
    }
  }
  if (view.statusLabel === 'Slight change' && !view.referralRecommended) {
    return {
      tone: 'observed',
      title: 'Slight change — keep monitoring',
      body: `A small change of ${pct}% was detected in the monitored skin region compared with your personal baseline.`,
    }
  }
  return {
    tone: 'notice',
    title: view.referralRecommended ? 'Change detected — consider a professional assessment' : 'Change detected — monitoring recommended',
    body: `A measurable change of ${pct}% was detected in the monitored skin region compared with your personal baseline.`,
  }
}

export const DIRECTION_TEXT = {
  increased: '↑ Increased',
  decreased: '↓ Decreased',
  unchanged: '→ No change',
  similar: '→ Similar',
  unavailable: '—',
}

export const TREND_TEXT = {
  increasing: 'Increasing',
  decreasing: 'Decreasing',
  stable: 'Stable',
}

/** "+18%" style change magnitude. */
export function formatChange(value) {
  if (value === null || value === undefined) return '—'
  return `${value > 0 ? '+' : ''}${value.toFixed(1)}%`
}

export function formatValue(value) {
  if (value === null || value === undefined) return '—'
  return Math.abs(value) >= 10 ? value.toFixed(1) : value.toFixed(2)
}

export function scoreBand(score) {
  if (score === null || score === undefined) return { label: 'No score', tone: 'steady' }
  if (score <= 39) return { label: 'Stable', tone: 'steady' }
  if (score <= 69) return { label: 'Slight change', tone: 'observed' }
  return { label: 'Change detected', tone: 'notice' }
}

/** Human date, e.g. 14 Sep 2026. */
export function formatDate(value) {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '—'
  return date.toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' })
}

export function formatShortDate(value) {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '—'
  return date.toLocaleDateString(undefined, { day: 'numeric', month: 'short' })
}
