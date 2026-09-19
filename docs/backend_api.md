# SpectraDerm FastAPI backend

AK–AO is a thin HTTP/JSON layer around existing AF–AJ services. It does not implement a frontend, PostgreSQL, a new analysis pipeline, or live Google testing.

Start locally after installing project dependencies:

```powershell
uvicorn spectraderm.api.app:app --reload
```

`GET /health` returns `{"status":"ok"}`. Versioned routes are under `/api/v1`: users, scans, analysis, history/timeline, reports, and actions. OpenAPI documentation is at `/docs`.

Configuration uses `SPECTRADERM_ENV`, `SPECTRADERM_STORAGE_ROOT`, `SPECTRADERM_CORS_ORIGINS`, optional server-side `GOOGLE_MAPS_API_KEY`, and optional `SPECTRADERM_MSTPP_CHECKPOINT` / `SPECTRADERM_MSTPP_DEVICE`. Services are contained in the app and are replaceable through `create_app(settings, container)` or FastAPI dependency overrides. Google/provider integration is mocked in tests.

`POST /users/{user_id}/image-artifacts` accepts one multipart field named `file`, verifies JPEG, PNG, or WebP content, and enforces a 10 MB limit. It stores the image under the existing AG storage root and returns an opaque relative `image_reference`; browser filenames and local paths are never stored. Pass that returned reference to `POST /users/{user_id}/scans` before calling `POST /scans/{scan_id}/analyze`. An absent or undecodable artifact returns `422 IMAGE_ARTIFACT_UNAVAILABLE`; analysis never substitutes a result for it.

```powershell
py -m pytest tests/test_api_app.py tests/test_api_users.py tests/test_api_scans.py tests/test_api_analysis.py tests/test_api_history.py tests/test_api_reports.py tests/test_api_actions.py -q
```
