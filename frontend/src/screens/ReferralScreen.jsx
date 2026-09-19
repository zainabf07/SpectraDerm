import { useState } from 'react'
import { api } from '../api/client.js'
import { Note, PageHead, Section, Spinner } from '../components/Primitives.jsx'

const EMPTY_MESSAGES = {
  no_results: 'No practices came back for that area. Try a larger radius or a nearby city.',
  provider_error:
    'The dermatologist directory could not be reached. The server may not have a GOOGLE_MAPS_API_KEY configured, or the directory may be temporarily unavailable.',
  location_required: 'Enter a city or allow location access to search.',
  not_applicable: 'A dermatologist search was not suggested for this observation.',
}

export default function ReferralScreen({ scanId, userId, go }) {
  const [city, setCity] = useState('')
  const [radius, setRadius] = useState(25)
  const [state, setState] = useState({ phase: 'idle' })

  async function search(location) {
    setState({ phase: 'loading' })
    try {
      const data = await api.referrals(scanId, userId, { ...location, radiusKm: Number(radius) || 25 })
      setState({ phase: 'done', status: data.status, items: data.items || [] })
    } catch (error) {
      setState({ phase: 'error', message: error.message })
    }
  }

  function useMyLocation() {
    if (!navigator.geolocation) {
      setState({ phase: 'error', message: 'This browser does not offer location access. Enter a city instead.' })
      return
    }
    setState({ phase: 'loading' })
    navigator.geolocation.getCurrentPosition(
      (position) => search({ latitude: position.coords.latitude, longitude: position.coords.longitude }),
      () => setState({ phase: 'error', message: 'Location access was declined. Enter a city instead.' }),
    )
  }

  return (
    <div className="stack">
      <PageHead
        back="Next step"
        onBack={() => go('next')}
        title="Find a dermatologist"
        lede="Your location is used for this search only. It is not stored with your observations."
      />

      <Section>
        <div className="stack stack--tight">
          <label className="field">
            <span>City or area</span>
            <input
              type="text"
              value={city}
              placeholder="e.g. Lahore"
              onChange={(event) => setCity(event.target.value)}
            />
          </label>
          <label className="field">
            <span>Search radius in kilometres</span>
            <input
              type="number"
              min="1"
              max="200"
              value={radius}
              onChange={(event) => setRadius(event.target.value)}
            />
          </label>
          <div className="row">
            <button
              type="button"
              className="btn btn--primary"
              disabled={!city.trim() || state.phase === 'loading'}
              onClick={() => search({ city: city.trim() })}
            >
              Search this area
            </button>
            <button
              type="button"
              className="btn btn--ghost"
              disabled={state.phase === 'loading'}
              onClick={useMyLocation}
            >
              Use my location
            </button>
          </div>
        </div>
      </Section>

      {state.phase === 'loading' ? <Spinner label="Searching" /> : null}
      {state.phase === 'error' ? <Note tone="problem">{state.message}</Note> : null}

      {state.phase === 'done' ? (
        state.items.length ? (
          <Section title={`${state.items.length} ${state.items.length === 1 ? 'practice' : 'practices'}`}>
            {state.items.map((item, index) => (
              <article className="provider" key={`${item.name || 'clinic'}-${index}`}>
                <h3>{item.name || 'Dermatology practice'}</h3>
                <p className="muted">
                  {[item.specialty, item.address].filter(Boolean).join(' — ') || 'Address not listed'}
                </p>
                <p className="muted">
                  {[
                    typeof item.distance_km === 'number' ? `${item.distance_km.toFixed(1)} km away` : null,
                    item.opening_hours,
                    item.phone,
                  ]
                    .filter(Boolean)
                    .join(' · ')}
                </p>
                {item.website ? (
                  <p style={{ marginTop: 'var(--s-3)' }}>
                    <a href={item.website} target="_blank" rel="noreferrer">
                      Visit website
                    </a>
                  </p>
                ) : null}
              </article>
            ))}
          </Section>
        ) : (
          <Note tone={state.status === 'provider_error' ? 'problem' : 'plain'}>
            {EMPTY_MESSAGES[state.status] || 'No practices came back for that search.'}
          </Note>
        )
      ) : null}

      <Section>
        <Note>
          Listings come from a third-party directory. SpectraDerm does not review, rank or endorse
          any practice.
        </Note>
      </Section>
    </div>
  )
}
