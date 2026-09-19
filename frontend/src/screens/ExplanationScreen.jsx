import { Note, PageHead, Section } from '../components/Primitives.jsx'

/** Renders "What was observed:" / "Why it can matter:" paragraphs and bullet lists. */
export function ExplanationText({ text }) {
  if (!text) return null
  const blocks = text.split(/\n\s*\n/).map((block) => block.trim()).filter(Boolean)
  return (
    <div className="explanation">
      {blocks.map((block, index) => {
        const lines = block.split('\n').map((line) => line.trim()).filter(Boolean)
        const heading = lines[0].match(/^(What was observed|Why it can matter):\s*(.*)$/i)
        const bullets = lines.filter((line) => line.startsWith('- '))
        return (
          <div key={index}>
            {heading ? <h3 className="subhead">{heading[1]}</h3> : null}
            {heading && heading[2] ? <p>{heading[2]}</p> : null}
            {!heading ? lines.filter((line) => !line.startsWith('- ')).map((line) => <p key={line}>{line}</p>) : null}
            {heading ? lines.slice(1).filter((line) => !line.startsWith('- ')).map((line) => <p key={line}>{line}</p>) : null}
            {bullets.length ? <ul className="guidance">{bullets.map((line) => <li key={line}>{line.slice(2)}</li>)}</ul> : null}
          </div>
        )
      })}
    </div>
  )
}

export const ORIGIN_TEXT = {
  language_model: 'Written by AI using only the sources listed below.',
  retrieved_sources: 'Summarised directly from the sources listed below.',
}

export function explanationOrigin(text) {
  if (!text) return null
  return text.includes('these sources give general context only') ? 'retrieved_sources' : 'language_model'
}

export default function ExplanationScreen({ view, go }) {
  const passages = view.sources || view.evidence?.retrieved_evidence || []
  const text = view.explanation ?? view.evidence?.explanation ?? null
  const origin = explanationOrigin(text)
  return (
    <div className="stack">
      <PageHead
        back="Result"
        onBack={() => go('result')}
        title="Why was this flagged?"
        lede="What SpectraDerm observed, and what trusted dermatology sources say about changes like it."
      />
      <Section title="Explanation">
        {text ? (
          <>
            <ExplanationText text={text} />
            {origin ? <p className="caption">{ORIGIN_TEXT[origin]}</p> : null}
          </>
        ) : (
          <p>Evidence is not available for this observation yet.</p>
        )}
      </Section>
      {passages.length ? (
        <Section title={`Sources (${passages.length})`}>
          <div className="evidence-list">
            {passages.map((item, index) => (
              <article className="evidence" key={item.source?.url || `${item.source?.title || 'source'}-${index}`}>
                <h3>{item.source?.title || 'Source'}</h3>
                {item.source?.organization ? <p className="caption">{item.source.organization}</p> : null}
                <p>{item.text}</p>
                {item.source?.url ? <a href={item.source.url} target="_blank" rel="noreferrer">View source</a> : null}
              </article>
            ))}
          </div>
        </Section>
      ) : null}
      <Note>This is general information from trusted sources. It does not identify a condition or explain the cause of a change.</Note>
      <div className="row">
        <button type="button" className="btn btn--primary" onClick={() => go('report')}>View full report</button>
        <button type="button" className="btn btn--ghost" onClick={() => go('next')}>What you can do next</button>
      </div>
    </div>
  )
}
