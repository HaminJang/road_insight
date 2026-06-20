const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000'

export type DetectionItem = {
  class_id: number
  class_name: string
  confidence: number
  bbox: number[]
  area_ratio: number
  risk_score: number
}

export type LegacyDetection = {
  detected: boolean
  confidence: number
  area_ratio: number
  damage_score: number
  bbox: number[] | null
}

export type AnalysisResult = {
  success: boolean
  hash: string
  timestamp: string

  latitude: number | null
  longitude: number | null
  gps_accuracy_m?: number | null

  detection: LegacyDetection

  detections?: DetectionItem[]
  detection_count?: number

  model_version?: string
  threshold?: number

  message: string
}

function appendNumberIfExists(
  formData: FormData,
  key: string,
  value: number | null | undefined
) {
  if (value !== null && value !== undefined && Number.isFinite(value)) {
    formData.append(key, value.toString())
  }
}

function buildRoadAnalysisFormData(
  file: File,
  latitude: number | null,
  longitude: number | null,
  gpsAccuracyM?: number | null
) {
  const formData = new FormData()

  formData.append('file', file)

  appendNumberIfExists(formData, 'latitude', latitude)
  appendNumberIfExists(formData, 'longitude', longitude)
  appendNumberIfExists(formData, 'gps_accuracy_m', gpsAccuracyM)

  return formData
}

async function readErrorMessage(response: Response, fallback: string) {
  try {
    const contentType = response.headers.get('content-type') || ''

    if (contentType.includes('application/json')) {
      const data = await response.json()

      if (typeof data.detail === 'string') {
        return data.detail
      }

      if (Array.isArray(data.detail)) {
        return data.detail
          .map((item: any) => item?.msg || JSON.stringify(item))
          .join(', ')
      }

      if (typeof data.message === 'string') {
        return data.message
      }
    }

    const text = await response.text()

    if (text) {
      return text
    }

    return fallback
  } catch {
    return fallback
  }
}

function getPdfFileName(response: Response) {
  const contentDisposition = response.headers.get('content-disposition')

  if (!contentDisposition) {
    return `road_insight_${new Date().toISOString().slice(0, 10)}.pdf`
  }

  const utf8Match = contentDisposition.match(/filename\*=UTF-8''([^;]+)/i)

  if (utf8Match?.[1]) {
    return decodeURIComponent(utf8Match[1])
  }

  const normalMatch = contentDisposition.match(/filename="?([^";]+)"?/i)

  if (normalMatch?.[1]) {
    return normalMatch[1]
  }

  return `road_insight_${new Date().toISOString().slice(0, 10)}.pdf`
}

export async function analyzeRoad(
  file: File,
  latitude: number | null,
  longitude: number | null,
  gpsAccuracyM?: number | null
): Promise<AnalysisResult> {
  const formData = buildRoadAnalysisFormData(
    file,
    latitude,
    longitude,
    gpsAccuracyM
  )

  const response = await fetch(`${API_URL}/analyze`, {
    method: 'POST',
    body: formData
  })

  if (!response.ok) {
    const message = await readErrorMessage(response, '분석 요청 실패')
    throw new Error(message)
  }

  return response.json()
}

export async function downloadPDF(
  file: File,
  latitude: number | null,
  longitude: number | null,
  gpsAccuracyM?: number | null
) {
  const formData = buildRoadAnalysisFormData(
    file,
    latitude,
    longitude,
    gpsAccuracyM
  )

  const response = await fetch(`${API_URL}/generate-pdf`, {
    method: 'POST',
    body: formData
  })

  if (!response.ok) {
    const message = await readErrorMessage(response, 'PDF 생성 실패')
    throw new Error(message)
  }

  const blob = await response.blob()
  const url = window.URL.createObjectURL(blob)

  try {
    const a = document.createElement('a')
    a.href = url
    a.download = getPdfFileName(response)
    document.body.appendChild(a)
    a.click()
    a.remove()
  } finally {
    window.URL.revokeObjectURL(url)
  }
}
