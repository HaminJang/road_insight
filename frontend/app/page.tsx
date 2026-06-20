'use client'

import { useEffect, useMemo, useState } from 'react'
import CameraCapture from '@/components/CameraCapture'
import { useGeolocation } from '@/hooks/useGeolocation'
import { analyzeRoad, downloadPDF } from '@/lib/api'

type DetectionItem = {
  class_id: number
  class_name: string
  confidence: number
  bbox: number[]
  area_ratio: number
  risk_score: number
}

type LegacyDetection = {
  detected: boolean
  confidence: number
  area_ratio: number
  damage_score: number
  bbox: number[] | null
}

type AnalysisResult = {
  success: boolean
  hash: string
  timestamp: string
  latitude: number | null
  longitude: number | null
  gps_accuracy_m?: number | null
  detection?: LegacyDetection
  detections?: DetectionItem[]
  detection_count?: number
  model_version?: string
  threshold?: number
  message: string
}

function getRiskLabel(score: number) {
  if (score >= 80) return { label: '긴급', color: '#A32D2D', bg: '#FCEBEB' }
  if (score >= 60) return { label: '높음', color: '#D85A30', bg: '#FFF0E8' }
  if (score >= 30) return { label: '주의', color: '#B7791F', bg: '#FFF8DB' }
  return { label: '낮음', color: '#085041', bg: '#E1F5EE' }
}

function toPercent(value: number, total: number) {
  if (!total || total <= 0) return 0
  return Math.max(0, Math.min(100, (value / total) * 100))
}

function hasGps(latitude: number | null | undefined, longitude: number | null | undefined) {
  return latitude !== null && latitude !== undefined && longitude !== null && longitude !== undefined
}

function DetectionPreview({
  imageUrl,
  detections
}: {
  imageUrl: string
  detections: DetectionItem[]
}) {
  const [imageSize, setImageSize] = useState({
    width: 0,
    height: 0
  })

  return (
    <div style={{ marginTop: '16px' }}>
      <div style={{
        fontSize: '14px',
        fontWeight: 600,
        marginBottom: '8px',
        color: '#333'
      }}>
        AI 탐지 위치
      </div>

      <div style={{
        position: 'relative',
        width: '100%',
        overflow: 'hidden',
        borderRadius: '12px',
        border: '1px solid #e5e5e5',
        background: '#f7f7f7'
      }}>
        <img
          src={imageUrl}
          alt="촬영 이미지"
          onLoad={(event) => {
            setImageSize({
              width: event.currentTarget.naturalWidth,
              height: event.currentTarget.naturalHeight
            })
          }}
          style={{
            width: '100%',
            display: 'block'
          }}
        />

        {imageSize.width > 0 && imageSize.height > 0 && detections.map((item, index) => {
          if (!item.bbox || item.bbox.length < 4) return null

          const [x1, y1, x2, y2] = item.bbox
          const left = toPercent(x1, imageSize.width)
          const top = toPercent(y1, imageSize.height)
          const width = toPercent(x2 - x1, imageSize.width)
          const height = toPercent(y2 - y1, imageSize.height)

          return (
            <div
              key={`${item.class_name}-${index}`}
              style={{
                position: 'absolute',
                left: `${left}%`,
                top: `${top}%`,
                width: `${width}%`,
                height: `${height}%`,
                border: '2px solid #FF3B30',
                borderRadius: '6px',
                boxSizing: 'border-box',
                pointerEvents: 'none'
              }}
            >
              <div style={{
                position: 'absolute',
                left: '-2px',
                top: '-26px',
                background: '#FF3B30',
                color: 'white',
                fontSize: '11px',
                fontWeight: 600,
                padding: '4px 6px',
                borderRadius: '4px',
                whiteSpace: 'nowrap'
              }}>
                #{index + 1} {item.class_name} {(item.confidence * 100).toFixed(1)}%
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

export default function Home() {
  const location = useGeolocation()

  const [result, setResult] = useState<AnalysisResult | null>(null)
  const [capturedFile, setCapturedFile] = useState<File | null>(null)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)

  const [loading, setLoading] = useState(false)
  const [pdfLoading, setPdfLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [cameraKey, setCameraKey] = useState(0)

  useEffect(() => {
    return () => {
      if (previewUrl) {
        URL.revokeObjectURL(previewUrl)
      }
    }
  }, [previewUrl])

  const detections = useMemo<DetectionItem[]>(() => {
    if (!result) return []

    if (result.detections && result.detections.length > 0) {
      return result.detections
    }

    // Temporary compatibility with the previous backend response shape.
    if (result.detection?.detected && result.detection.bbox) {
      return [
        {
          class_id: 0,
          class_name: 'pothole',
          confidence: result.detection.confidence,
          bbox: result.detection.bbox,
          area_ratio: result.detection.area_ratio,
          risk_score: result.detection.damage_score
        }
      ]
    }

    return []
  }, [result])

  const primaryRiskScore = detections.length > 0
    ? detections[0].risk_score
    : (result?.detection?.damage_score ?? 0)

  const risk = getRiskLabel(primaryRiskScore)

  const handleCapture = async (file: File) => {
    setCapturedFile(file)
    setResult(null)
    setLoading(true)
    setError(null)

    setPreviewUrl((prev) => {
      if (prev) URL.revokeObjectURL(prev)
      return URL.createObjectURL(file)
    })

    try {
      const data = await analyzeRoad(
        file,
        location.latitude,
        location.longitude,
        location.accuracy
      )

      setResult(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : '분석 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.')
    } finally {
      setLoading(false)
    }
  }

  const handleDownloadPDF = async () => {
    if (!capturedFile) return

    setPdfLoading(true)
    setError(null)

    try {
      await downloadPDF(
        capturedFile,
        location.latitude,
        location.longitude,
        location.accuracy
      )
    } catch (err) {
      setError(err instanceof Error ? err.message : 'PDF 생성 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.')
    } finally {
      setPdfLoading(false)
    }
  }

  const handleReset = () => {
    setResult(null)
    setCapturedFile(null)
    setError(null)
    setLoading(false)
    setPdfLoading(false)

    setPreviewUrl((prev) => {
      if (prev) URL.revokeObjectURL(prev)
      return null
    })

    // Remount CameraCapture to reset its internal captured state.
    setCameraKey((prev) => prev + 1)
  }

  return (
    <main style={{
      maxWidth: '480px',
      margin: '0 auto',
      padding: '24px 16px 40px',
      fontFamily: 'sans-serif'
    }}>
      <header style={{ marginBottom: '24px' }}>
        <h1 style={{
          fontSize: '26px',
          fontWeight: 700,
          color: '#1D9E75',
          marginBottom: '8px',
          letterSpacing: '-0.5px'
        }}>
          Road-Insight
        </h1>

        <p style={{
          fontSize: '14px',
          color: '#666',
          lineHeight: 1.5,
          margin: 0
        }}>
          스마트폰으로 도로 파손을 촬영하고 AI 분석 리포트를 생성합니다.
        </p>
      </header>

      <section style={{
        padding: '12px',
        borderRadius: '12px',
        background: '#F7FAF9',
        border: '1px solid #E1F0EC',
        marginBottom: '16px',
        fontSize: '12px',
        color: '#42635A',
        lineHeight: 1.5
      }}>
        <div>
          GPS 상태:{' '}
          {hasGps(location.latitude, location.longitude)
            ? `수신 완료 (${location.latitude!.toFixed(4)}, ${location.longitude!.toFixed(4)})`
            : '수신 대기 중'}
        </div>

        {location.accuracy !== null && location.accuracy !== undefined && (
          <div>
            GPS 정확도: ±{Math.round(location.accuracy)}m
          </div>
        )}

        {location.error && (
          <div style={{ color: '#A32D2D', marginTop: '4px' }}>
            {location.error}
          </div>
        )}
      </section>

      <CameraCapture
        key={cameraKey}
        onCapture={handleCapture}
      />

      {previewUrl && detections.length === 0 && (
        <div style={{
          marginTop: '16px',
          borderRadius: '12px',
          overflow: 'hidden',
          border: '1px solid #e5e5e5'
        }}>
          <img
            src={previewUrl}
            alt="촬영 이미지 미리보기"
            style={{
              width: '100%',
              display: 'block'
            }}
          />
        </div>
      )}

      {loading && (
        <div style={{
          textAlign: 'center',
          padding: '24px',
          color: '#666',
          fontSize: '14px'
        }}>
          AI가 도로 위험 요소를 분석 중입니다...
        </div>
      )}

      {error && (
        <div style={{
          padding: '12px',
          background: '#FCEBEB',
          borderRadius: '8px',
          color: '#A32D2D',
          marginTop: '16px',
          fontSize: '14px',
          lineHeight: 1.5
        }}>
          {error}
        </div>
      )}

      {result && (
        <section style={{
          marginTop: '24px',
          padding: '16px',
          border: '1px solid #e0e0e0',
          borderRadius: '14px',
          background: '#fff'
        }}>
          <div style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: '12px'
          }}>
            <h2 style={{
              fontSize: '17px',
              fontWeight: 700,
              margin: 0,
              color: '#222'
            }}>
              분석 결과
            </h2>

            <span style={{
              fontSize: '12px',
              padding: '4px 8px',
              borderRadius: '999px',
              background: risk.bg,
              color: risk.color,
              fontWeight: 700
            }}>
              {risk.label}
            </span>
          </div>

          <div style={{
            padding: '14px',
            background: detections.length > 0 ? '#FCEBEB' : '#E1F5EE',
            borderRadius: '10px',
            marginBottom: '14px',
            textAlign: 'center',
            fontWeight: 700,
            color: detections.length > 0 ? '#A32D2D' : '#085041',
            lineHeight: 1.5
          }}>
            {result.message}
          </div>

          {previewUrl && detections.length > 0 && (
            <DetectionPreview
              imageUrl={previewUrl}
              detections={detections}
            />
          )}

          <div style={{
            marginTop: '16px',
            fontSize: '14px',
            color: '#444'
          }}>
            <InfoRow
              label="탐지 객체 수"
              value={`${detections.length}건`}
            />

            {detections.length > 0 && (
              <>
                <InfoRow
                  label="대표 신뢰도"
                  value={`${(detections[0].confidence * 100).toFixed(1)}%`}
                />

                <InfoRow
                  label="대표 위험도"
                  value={`${detections[0].risk_score.toFixed(1)} / 100`}
                  valueColor={risk.color}
                />

                <InfoRow
                  label="대표 면적 비율"
                  value={`${(detections[0].area_ratio * 100).toFixed(2)}%`}
                />
              </>
            )}

            <InfoRow
              label="모델 버전"
              value={result.model_version || '미표시'}
            />

            <InfoRow
              label="신뢰도 기준"
              value={result.threshold !== undefined
                ? `${(result.threshold * 100).toFixed(0)}% 이상`
                : '미표시'}
            />

            <InfoRow
              label="GPS"
              value={
                hasGps(result.latitude, result.longitude)
                  ? `${result.latitude!.toFixed(5)}, ${result.longitude!.toFixed(5)}`
                  : '없음'
              }
            />

            <InfoRow
              label="GPS 정확도"
              value={
                result.gps_accuracy_m !== null && result.gps_accuracy_m !== undefined
                  ? `±${Math.round(result.gps_accuracy_m)}m`
                  : location.accuracy !== null && location.accuracy !== undefined
                    ? `±${Math.round(location.accuracy)}m`
                    : '없음'
              }
            />

            <InfoRow
              label="분석 시각"
              value={result.timestamp}
            />

            <div style={{
              padding: '10px 0',
              fontSize: '11px',
              color: '#999',
              wordBreak: 'break-all',
              borderBottom: '1px solid #f0f0f0'
            }}>
              <div style={{ marginBottom: '4px', color: '#777' }}>
                SHA-256
              </div>
              {result.hash}
            </div>
          </div>

          {detections.length > 0 && (
            <div style={{ marginTop: '18px' }}>
              <h3 style={{
                fontSize: '15px',
                fontWeight: 700,
                color: '#333',
                marginBottom: '10px'
              }}>
                탐지 객체 목록
              </h3>

              {detections.map((item, index) => {
                const itemRisk = getRiskLabel(item.risk_score)

                return (
                  <div
                    key={`${item.class_name}-${index}`}
                    style={{
                      padding: '12px',
                      border: '1px solid #eeeeee',
                      borderRadius: '10px',
                      marginBottom: '8px',
                      background: '#FAFAFA'
                    }}
                  >
                    <div style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      marginBottom: '8px'
                    }}>
                      <div style={{
                        fontSize: '14px',
                        fontWeight: 700,
                        color: '#222'
                      }}>
                        #{index + 1} {item.class_name}
                      </div>

                      <span style={{
                        fontSize: '11px',
                        padding: '3px 7px',
                        borderRadius: '999px',
                        background: itemRisk.bg,
                        color: itemRisk.color,
                        fontWeight: 700
                      }}>
                        {itemRisk.label}
                      </span>
                    </div>

                    <div style={{
                      display: 'grid',
                      gridTemplateColumns: '1fr 1fr',
                      gap: '6px',
                      fontSize: '12px',
                      color: '#555'
                    }}>
                      <div>신뢰도: {(item.confidence * 100).toFixed(1)}%</div>
                      <div>위험도: {item.risk_score.toFixed(1)}</div>
                      <div>면적: {(item.area_ratio * 100).toFixed(2)}%</div>
                      <div>Class ID: {item.class_id}</div>
                    </div>
                  </div>
                )
              })}
            </div>
          )}

          <div style={{
            display: 'flex',
            gap: '8px',
            marginTop: '18px'
          }}>
            <button
              onClick={handleReset}
              style={{
                flex: 1,
                padding: '12px',
                background: '#F1F1F1',
                color: '#333',
                border: 'none',
                borderRadius: '8px',
                fontSize: '14px',
                fontWeight: 600,
                cursor: 'pointer'
              }}
            >
              다시 촬영
            </button>

            <button
              onClick={handleDownloadPDF}
              disabled={pdfLoading}
              style={{
                flex: 2,
                padding: '12px',
                background: pdfLoading ? '#888' : '#1D9E75',
                color: 'white',
                border: 'none',
                borderRadius: '8px',
                fontSize: '14px',
                fontWeight: 700,
                cursor: pdfLoading ? 'not-allowed' : 'pointer'
              }}
            >
              {pdfLoading ? 'PDF 생성 중...' : '분석 PDF 다운로드'}
            </button>
          </div>
        </section>
      )}
    </main>
  )
}

function InfoRow({
  label,
  value,
  valueColor = '#333'
}: {
  label: string
  value: string
  valueColor?: string
}) {
  return (
    <div style={{
      display: 'flex',
      justifyContent: 'space-between',
      gap: '12px',
      padding: '9px 0',
      borderBottom: '1px solid #f0f0f0'
    }}>
      <span style={{
        color: '#888',
        flexShrink: 0
      }}>
        {label}
      </span>

      <span style={{
        fontWeight: 600,
        color: valueColor,
        textAlign: 'right',
        wordBreak: 'break-word'
      }}>
        {value}
      </span>
    </div>
  )
}
