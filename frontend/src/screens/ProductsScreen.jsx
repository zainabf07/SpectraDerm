import { useEffect, useState } from 'react'
import { api } from '../api/client.js'
import { Note, PageHead, Section, Spinner } from '../components/Primitives.jsx'

export default function ProductsScreen({ scanId, userId, go }) {
  const [state, setState] = useState({ phase: 'loading' })

  useEffect(() => {
    let live = true
    api
      .products(scanId, userId)
      .then((data) => live && setState({ phase: 'done', status: data.status, items: data.items || [] }))
      .catch((error) => live && setState({ phase: 'error', message: error.message }))
    return () => {
      live = false
    }
  }, [scanId, userId])

  return (
    <div className="stack">
      <PageHead
        back="Next step"
        onBack={() => go('next')}
        title="General skincare"
        lede="Everyday categories, not treatments. Nothing here is directed at a condition, because none has been identified."
      />

      {state.phase === 'loading' ? <Spinner label="Loading" /> : null}
      {state.phase === 'error' ? <Note tone="problem">{state.message}</Note> : null}

      {state.phase === 'done' ? (
        state.items.length ? (
          state.items.map((item) => (
            <Section key={item.category_id} title={item.category_name}>
              <p>{item.neutral_description}</p>
              {item.reason ? <p className="muted">{item.reason}</p> : null}
            </Section>
          ))
        ) : (
          <Note>
            General skincare categories are not available for this observation.
          </Note>
        )
      ) : null}

      <Section>
        <Note>
          These are general categories, never brands, and never treatment for a diagnosed
          condition. A pharmacist or clinician can help you choose within a category.
        </Note>
      </Section>
    </div>
  )
}
