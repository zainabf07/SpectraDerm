# Archived TypeScript prototype

An earlier TypeScript UI (`App.tsx`, `pages/`, `layout/`, `client.ts`) that was
left next to the live app but never wired in: `index.html` loads
`src/main.jsx`, which renders the JSX app in `src/App.jsx` + `src/screens/`.

It is kept here for reference only. It is excluded from the build and from
`npm test`. Its one unique behaviour — replacing a stale browser user id after
the API forgets it — has been ported into `src/App.jsx`.
