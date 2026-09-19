export interface ApiErrorEnvelope { error: { code: string; message: string } }
export interface User { user_id: string; scan_ids: string[]; created_at: string; updated_at: string; general_consent: boolean; location_consent: boolean }
export interface Scan { scan_id: string; user_id: string; timestamp: string; feature_reference: string | null; analysis_reference: string | null; change_reference: string | null; created_at: string }
export interface ImageArtifact { image_reference: string }
export interface ScanList { scans: Scan[] }
export interface History { user_id: string; timeline: Scan[] }
export interface Analysis { status: string; result: Record<string, unknown>; safety: Record<string, unknown> | null; next_action: string | null }
export interface SpectralVisualization { available: true; label: string; note: string; wavelength_range_nm: [number, number]; reconstructed_band_count: number; false_color_image: string; representative_band: { wavelength_nm: number; image: string }; roi_spectrum?: { wavelengths_nm: number[]; values: number[] } }
export interface Action { status: string; items: Record<string, unknown>[] }
export interface ReportSection { title: string; status: string; items: { label: string; value: unknown }[] }
export interface Report { sections: ReportSection[] }
export interface ReferralRequest { city?: string; latitude?: number; longitude?: number; radius_km?: number }
