import { useCallback, useEffect, useState } from 'react'
import { api } from './api/client.js'
import { makeThumbnail, store } from './lib/store.js'
import { headline, qualityRejected, readResult } from './lib/analysis.js'
import { Note, Spinner } from './components/Primitives.jsx'
import HomeScreen from './screens/HomeScreen.jsx'
import ScanScreen from './screens/ScanScreen.jsx'
import AnalyzingScreen from './screens/AnalyzingScreen.jsx'
import QualityScreen from './screens/QualityScreen.jsx'
import ResultScreen from './screens/ResultScreen.jsx'
import HistoryScreen from './screens/HistoryScreen.jsx'
import ExplanationScreen from './screens/ExplanationScreen.jsx'
import NextActionScreen from './screens/NextActionScreen.jsx'
import ReferralScreen from './screens/ReferralScreen.jsx'
import ProductsScreen from './screens/ProductsScreen.jsx'
import ReportScreen from './screens/ReportScreen.jsx'

// Shared across effect re-runs (React StrictMode mounts twice in development),
// so a browser never creates two users and saves the wrong one.
let userBootstrap = null

async function bootstrapUser() {
  const saved = store.getUserId()
  if (saved) {
    try {
      const user = await api.getUser(saved)
      return user.user_id
    } catch (error) {
      if (error.status !== 404) throw error
      store.clearUser()
    }
  }
  const created = await api.createUser(true, false)
  store.setUserId(created.user_id)
  return created.user_id
}

function restoreUser() {
  if (!userBootstrap) {
    userBootstrap = bootstrapUser().catch((error) => {
      userBootstrap = null
      throw error
    })
  }
  return userBootstrap
}

/** Test hook: forget the shared bootstrap so each test starts clean. */
export function resetUserBootstrap() {
  userBootstrap = null
}

export default function App() {
  const [userId, setUserId] = useState(null)
  const [booting, setBooting] = useState(true)
  const [bootError, setBootError] = useState(null)

  const [route, setRoute] = useState('home')
  const [scan, setScan] = useState(null)
  const [view, setView] = useState(null)
  const [photo, setPhoto] = useState(null)
  const [analysisError, setAnalysisError] = useState(null)
  const [lastFile, setLastFile] = useState(null)

  // One anonymous user record per browser; the API has no auth layer. A saved
  // id is confirmed with the API first: if the server no longer knows it (for
  // example a fresh storage folder), a new record replaces it instead of
  // every later upload failing with "user not found".
  useEffect(() => {
    let live = true
    restoreUser()
      .then((id) => live && setUserId(id))
      .catch((error) => live && setBootError(error.message))
      .finally(() => live && setBooting(false))
    return () => {
      live = false
    }
  }, [])

  const go = useCallback((next) => {
    setRoute(next)
    window.scrollTo({ top: 0 })
  }, [])

  const runAnalysis = useCallback(
    async (file) => {
      setAnalysisError(null)
      setLastFile(file)
      setPhoto(URL.createObjectURL(file))
      go('analyzing')

      try {
        const { image_reference: imageReference } = await api.uploadImage(userId, file)
        const created = await api.createScan(userId, imageReference)
        const payload = await api.analyze(created.scan_id, userId)
        const parsed = readResult(payload)

        const thumbnail = await makeThumbnail(file)
        store.saveScanEntry(created.scan_id, {
          score: parsed.changeScore,
          statusLabel: headline(parsed).title,
          thumbnail,
        })

        setScan(created)
        setView(parsed)
        go(qualityRejected(parsed) ? 'quality' : 'result')
      } catch (error) {
        setAnalysisError(error)
      }
    },
    [go, userId],
  )

  const openScan = useCallback(
    async (record) => {
      setAnalysisError(null)
      setPhoto(record.thumbnail || null)
      go('analyzing')
      try {
        const payload = await api.analyze(record.scan_id, userId)
        const parsed = readResult(payload)
        store.saveScanEntry(record.scan_id, {
          score: parsed.changeScore,
          statusLabel: headline(parsed).title,
        })
        setScan(record)
        setView(parsed)
        go(qualityRejected(parsed) ? 'quality' : 'result')
      } catch (error) {
        setAnalysisError(error)
      }
    },
    [go, userId],
  )

  if (booting) {
    return (
      <div className="app">
        <main className="main">
          <Spinner label="Preparing your private record" />
        </main>
      </div>
    )
  }

  return (
    <div className="app">
      <header className="masthead">
        <div className="masthead__inner">
          <button type="button" className="wordmark" onClick={() => go('home')}>
            <span className="wordmark__mark" aria-hidden="true" />
            SpectraDerm
          </button>
          <nav className="masthead__nav">
            <button
              type="button"
              className="navlink"
              aria-current={route === 'history'}
              onClick={() => go('history')}
            >
              History
            </button>
            <button
              type="button"
              className="navlink"
              aria-current={route === 'scan'}
              onClick={() => go('scan')}
            >
              Start scan
            </button>
            <button
              type="button"
              className="navlink"
              aria-current={route === 'privacy'}
              onClick={() => go('privacy')}
            >
              Privacy
            </button>
          </nav>
        </div>
      </header>

      <main className="main">
        {bootError ? (
          <Note tone="error">
            Could not reach the SpectraDerm service: {bootError} Start the API, then reload.
          </Note>
        ) : (
          <Screen
            route={route}
            go={go}
            userId={userId}
            scan={scan}
            view={view}
            photo={photo}
            analysisError={analysisError}
            onSubmit={runAnalysis}
            onRetry={() => lastFile && runAnalysis(lastFile)}
            onOpenScan={openScan}
          />
        )}
      </main>

      <footer className="footer">
        <p>
          SpectraDerm supports observation of your skin over time. It is not a medical device and does
          not diagnose skin conditions.
        </p>
      </footer>
    </div>
  )
}

function Screen({
  route,
  go,
  userId,
  scan,
  view,
  photo,
  analysisError,
  onSubmit,
  onRetry,
  onOpenScan,
}) {
  // Screens below the result depend on a completed analysis in memory.
  const needsResult = ['result', 'quality', 'explanation', 'next', 'referral', 'products', 'report']
  if (needsResult.includes(route) && !view) {
    return (
      <Note>
        That observation is no longer loaded. Open it again from your record.{' '}
        <button type="button" className="btn btn--quiet" onClick={() => go('history')}>
          Go to my record
        </button>
      </Note>
    )
  }

  switch (route) {
    case 'scan':
      return <ScanScreen go={go} onSubmit={onSubmit} />
    case 'analyzing':
      return <AnalyzingScreen photo={photo} error={analysisError} onRetry={onRetry} go={go} />
    case 'quality':
      return <QualityScreen view={view} photo={photo} go={go} />
    case 'result':
      return <ResultScreen view={view} scan={scan} photo={photo} go={go} />
    case 'explanation':
      return <ExplanationScreen view={view} go={go} />
    case 'next':
      return <NextActionScreen view={view} go={go} />
    case 'referral':
      return <ReferralScreen scanId={scan.scan_id} userId={userId} go={go} />
    case 'products':
      return <ProductsScreen scanId={scan.scan_id} userId={userId} go={go} />
    case 'report':
      return <ReportScreen scanId={scan.scan_id} userId={userId} go={go} />
    case 'history':
      return <HistoryScreen userId={userId} go={go} onOpenScan={onOpenScan} />
    case 'privacy':
      return <PrivacyScreen />
    default:
      return <HomeScreen userId={userId} go={go} />
  }
}

function PrivacyScreen() {
  return <div className="stack"><section className="report-hero"><p className="eyebrow">Privacy</p><h1>Your observations, your record.</h1><p className="lede">Images are used to create your observation record. Location is requested only when you choose to search for a dermatologist.</p></section><Note>This is a skin-monitoring product, not a diagnostic service.</Note></div>
}
