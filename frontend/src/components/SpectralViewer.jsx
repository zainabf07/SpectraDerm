import { useState } from 'react'

/**
 * Module K output. The false-colour image and the representative band arrive as
 * PNG data URLs from the API; the ROI spectrum arrives as wavelength/value
 * pairs and is drawn here as a small line plot.
 *
 * The wording stays "AI-estimated" everywhere — this is reconstructed from RGB,
 * not measured with a spectrometer.
 */
export default function SpectralViewer({ spectral, photo, unavailableReason }) {
  const [view, setView] = useState('spectral')

  if (!spectral || spectral.available !== true) {
    return (
      <div>
        <div className="frame frame--empty">
          <p style={{ margin: 0 }}>
            No spectral estimate for this scan.
            <br />
            {unavailableReason || 'The reconstruction model was not available during analysis.'}
          </p>
        </div>
        <p className="caption">
          The rest of the analysis still runs on the RGB image; only the estimated spectral view is
          missing.
        </p>
      </div>
    )
  }

  const bandWavelength = spectral.representative_band?.wavelength_nm
  const range = spectral.wavelength_range_nm || []
  const tabs = [
    { id: 'rgb', label: 'Your photo', enabled: Boolean(photo) },
    { id: 'spectral', label: 'Estimated spectral', enabled: Boolean(spectral.false_color_image) },
    {
      id: 'band',
      label: bandWavelength ? `${bandWavelength} nm band` : 'Single band',
      enabled: Boolean(spectral.representative_band?.image),
    },
  ].filter((tab) => tab.enabled)

  const active = tabs.some((tab) => tab.id === view) ? view : tabs[0]?.id
  const source =
    active === 'rgb'
      ? photo
      : active === 'band'
        ? spectral.representative_band.image
        : spectral.false_color_image

  const captions = {
    rgb: 'The original RGB photo you uploaded, unmodified.',
    spectral:
      'Estimated spectral information rendered in false colour. Colour maps to wavelength, not to what your eye would see.',
    band: `Intensity estimated at ${bandWavelength} nm, shown as brightness.`,
  }

  return (
    <div>
      <div className="tabs" role="tablist" aria-label="Image view">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            type="button"
            role="tab"
            className="tab"
            aria-selected={active === tab.id}
            onClick={() => setView(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className="frame">
        <img src={source} alt={captions[active]} />
      </div>
      <p className="caption">{captions[active]}</p>

      {range.length === 2 ? (
        <div className="wavekey">
          <div className="wavekey__bar" />
          <div className="wavekey__ends">
            <span>{range[0]} nm</span>
            <span>
              {spectral.reconstructed_band_count} estimated bands
            </span>
            <span>{range[1]} nm</span>
          </div>
        </div>
      ) : null}

      {spectral.roi_spectrum ? <RoiSpectrum spectrum={spectral.roi_spectrum} /> : null}

      <p className="caption" style={{ marginTop: '0.9rem' }}>
        {spectral.note ||
          'Reconstructed from the RGB image; this is not measured spectroscopy.'}
      </p>
    </div>
  )
}

function RoiSpectrum({ spectrum }) {
  const wavelengths = spectrum.wavelengths_nm || []
  const values = spectrum.values || []
  if (wavelengths.length < 2 || values.length !== wavelengths.length) return null

  const width = 640
  const height = 180
  const pad = { top: 14, right: 12, bottom: 28, left: 40 }
  const min = Math.min(...values)
  const max = Math.max(...values)
  const span = max - min || 1

  const x = (index) =>
    pad.left + (index / (wavelengths.length - 1)) * (width - pad.left - pad.right)
  const y = (value) =>
    pad.top + (1 - (value - min) / span) * (height - pad.top - pad.bottom)

  const path = values.map((value, index) => `${index ? 'L' : 'M'}${x(index)} ${y(value)}`).join(' ')

  return (
    <div style={{ marginTop: '1.1rem' }}>
      <h3 style={{ fontSize: '1.02rem', marginBottom: '0.3rem' }}>
        Estimated reflectance across the skin region
      </h3>
      <svg
        className="chart"
        viewBox={`0 0 ${width} ${height}`}
        role="img"
        aria-label="Estimated spectral curve across the detected skin region"
      >
        <line
          x1={pad.left}
          y1={height - pad.bottom}
          x2={width - pad.right}
          y2={height - pad.bottom}
          stroke="var(--hairline)"
        />
        <path d={path} fill="none" stroke="var(--clay)" strokeWidth="2" />
        <text x={pad.left} y={height - 8} fontSize="11" fill="var(--slate)">
          {wavelengths[0]} nm
        </text>
        <text
          x={width - pad.right}
          y={height - 8}
          fontSize="11"
          fill="var(--slate)"
          textAnchor="end"
        >
          {wavelengths[wavelengths.length - 1]} nm
        </text>
        <text x={4} y={pad.top + 4} fontSize="11" fill="var(--slate)">
          {max.toFixed(2)}
        </text>
        <text x={4} y={height - pad.bottom} fontSize="11" fill="var(--slate)">
          {min.toFixed(2)}
        </text>
      </svg>
      <p className="caption">
        Averaged over the pixels detected as skin. Relative values from the reconstruction, not
        calibrated units.
      </p>
    </div>
  )
}
