import { useEffect, useRef, useState } from 'react'
import { Note, PageHead, Section } from '../components/Primitives.jsx'

const ACCEPTED = ['image/jpeg', 'image/png', 'image/webp']
const MAX_BYTES = 10 * 1024 * 1024

export default function ScanScreen({ go, onSubmit }) {
  const [file, setFile] = useState(null)
  const [preview, setPreview] = useState(null)
  const [problem, setProblem] = useState(null)
  const [dragging, setDragging] = useState(false)
  const inputRef = useRef(null)

  useEffect(() => {
    if (!file) {
      setPreview(null)
      return undefined
    }
    const url = URL.createObjectURL(file)
    setPreview(url)
    return () => URL.revokeObjectURL(url)
  }, [file])

  function accept(candidate) {
    if (!candidate) return
    if (!ACCEPTED.includes(candidate.type)) {
      setProblem('Use a JPEG, PNG or WebP image. Other formats cannot be read.')
      return
    }
    if (candidate.size > MAX_BYTES) {
      setProblem('That image is over the 10 MB limit. Export it at a smaller size and try again.')
      return
    }
    setProblem(null)
    setFile(candidate)
  }

  return (
    <div className="stack">
      <PageHead
        back="Home"
        onBack={() => go('home')}
        title="New observation"
        lede="Photograph the same area the same way each time. Consistency is what makes the comparison meaningful."
      />

      {problem ? <Note tone="problem">{problem}</Note> : null}

      <Section>
        {preview ? (
          <div className="stack stack--tight">
            <img className="preview" src={preview} alt="The photograph you selected" />
            <div className="row">
              <button type="button" className="btn btn--primary" onClick={() => onSubmit(file)}>
                Compare this photograph
              </button>
              <button
                type="button"
                className="btn btn--ghost"
                onClick={() => {
                  setFile(null)
                  if (inputRef.current) inputRef.current.value = ''
                }}
              >
                Choose another
              </button>
            </div>
          </div>
        ) : (
          <button
            type="button"
            className={dragging ? 'dropzone dropzone--over' : 'dropzone'}
            onClick={() => inputRef.current?.click()}
            onDragOver={(event) => {
              event.preventDefault()
              setDragging(true)
            }}
            onDragLeave={() => setDragging(false)}
            onDrop={(event) => {
              event.preventDefault()
              setDragging(false)
              accept(event.dataTransfer.files?.[0])
            }}
          >
            <span className="dropzone__aperture" aria-hidden="true" />
            <strong>Photograph or choose an image</strong>
            <span className="muted">Drag one here, or select from your device. Up to 10 MB.</span>
          </button>
        )}

        <input
          ref={inputRef}
          type="file"
          accept="image/jpeg,image/png,image/webp"
          capture="environment"
          className="sr-only"
          onChange={(event) => accept(event.target.files?.[0])}
        />
      </Section>

      <Section title="What makes a photograph comparable">
        <ul className="guidance">
          <li>The same light as your earlier photographs — daylight near a window works well.</li>
          <li>The same distance and angle, with the area filling most of the frame.</li>
          <li>Sharp focus, no flash glare, no filters or beauty modes.</li>
          <li>Skin clean and dry, without makeup or cream over the area.</li>
        </ul>
      </Section>
    </div>
  )
}
