'use client'

import { useRef, useState, useCallback } from 'react'

interface CameraCaptureProps {
  onCapture: (file: File) => void
}

export default function CameraCapture({ onCapture }: CameraCaptureProps) {
  const videoRef = useRef<HTMLVideoElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const [streaming, setStreaming] = useState(false)
  const [captured, setCaptured] = useState(false)
  const [facingMode, setFacingMode] = useState<'environment' | 'user'>('environment')
  const [cameraError, setCameraError] = useState<string | null>(null)

  const stopCamera = useCallback(() => {
    if (videoRef.current?.srcObject) {
      const stream = videoRef.current.srcObject as MediaStream
      stream.getTracks().forEach(track => track.stop())
      videoRef.current.srcObject = null
    }
    setStreaming(false)
  }, [])

  const startCamera = useCallback(async (mode: 'environment' | 'user') => {
    try {
      setCameraError(null)
      stopCamera()

      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: mode,
          width: { ideal: 1280 },
          height: { ideal: 720 }
        },
        audio: false
      })

      if (videoRef.current) {
        videoRef.current.srcObject = stream
        await videoRef.current.play()
        setStreaming(true)
        setCaptured(false)
      }
    } catch (err) {
      setCameraError('카메라를 시작할 수 없습니다. 권한을 확인하거나 갤러리 업로드를 이용해주세요.')
      setStreaming(false)
    }
  }, [stopCamera])

  const switchCamera = useCallback(async () => {
    const newMode = facingMode === 'environment' ? 'user' : 'environment'
    setFacingMode(newMode)
    await startCamera(newMode)
  }, [facingMode, startCamera])

  const capture = useCallback(() => {
    if (!videoRef.current || !canvasRef.current) return

    const canvas = canvasRef.current
    const video = videoRef.current

    canvas.width = video.videoWidth
    canvas.height = video.videoHeight

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    ctx.drawImage(video, 0, 0)

    canvas.toBlob((blob) => {
      if (!blob) return

      const file = new File(
        [blob],
        `road_insight_${Date.now()}.jpg`,
        { type: 'image/jpeg' }
      )

      onCapture(file)
      setCaptured(true)
      stopCamera()
    }, 'image/jpeg', 0.9)
  }, [onCapture, stopCamera])

  const handleUploadClick = () => {
    fileInputRef.current?.click()
  }

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return

    if (!file.type.startsWith('image/')) {
      setCameraError('이미지 파일만 업로드할 수 있습니다.')
      return
    }

    stopCamera()
    setCaptured(true)
    setCameraError(null)
    onCapture(file)

    // Allow selecting the same file again.
    event.target.value = ''
  }

  const handleRetake = () => {
    setCaptured(false)
    setCameraError(null)
    startCamera(facingMode)
  }

  return (
    <div style={{ width: '100%' }}>
      {!streaming && !captured && (
        <div style={{ display: 'grid', gap: '8px' }}>
          <button
            onClick={() => startCamera(facingMode)}
            style={{
              width: '100%',
              padding: '16px',
              background: '#1D9E75',
              color: 'white',
              border: 'none',
              borderRadius: '8px',
              fontSize: '16px',
              fontWeight: 600,
              cursor: 'pointer'
            }}
          >
            카메라 시작
          </button>

          <button
            onClick={handleUploadClick}
            style={{
              width: '100%',
              padding: '14px',
              background: '#F1F1F1',
              color: '#333',
              border: 'none',
              borderRadius: '8px',
              fontSize: '15px',
              fontWeight: 600,
              cursor: 'pointer'
            }}
          >
            갤러리에서 이미지 선택
          </button>
        </div>
      )}

      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        onChange={handleFileChange}
        style={{ display: 'none' }}
      />

      {cameraError && (
        <div style={{
          marginTop: '12px',
          padding: '12px',
          background: '#FCEBEB',
          color: '#A32D2D',
          borderRadius: '8px',
          fontSize: '13px',
          lineHeight: 1.5
        }}>
          {cameraError}
        </div>
      )}

      <div style={{ display: streaming ? 'block' : 'none' }}>
        <div style={{ position: 'relative' }}>
          <video
            ref={videoRef}
            style={{ width: '100%', borderRadius: '8px', display: 'block' }}
            playsInline
            autoPlay
            muted
          />
          <div style={{
            position: 'absolute',
            inset: 0,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
          }}>
            <div style={{
              width: '60%',
              height: '40%',
              border: '2px solid #00ff00',
              borderRadius: '8px'
            }} />
          </div>
          <p style={{
            position: 'absolute',
            bottom: '16px',
            width: '100%',
            textAlign: 'center',
            color: 'white',
            fontSize: '14px',
            margin: 0,
            textShadow: '0 1px 4px rgba(0,0,0,0.8)'
          }}>
            도로 위험 요소를 녹색 박스 안에 맞춰주세요
          </p>
        </div>

        <div style={{
          display: 'flex',
          gap: '8px',
          marginTop: '12px'
        }}>
          <button
            onClick={capture}
            style={{
              flex: 1,
              padding: '14px',
              background: '#1D9E75',
              color: 'white',
              border: 'none',
              borderRadius: '8px',
              fontSize: '16px',
              fontWeight: 600,
              cursor: 'pointer'
            }}
          >
            촬영
          </button>

          <button
            onClick={switchCamera}
            style={{
              padding: '14px 20px',
              background: '#333',
              color: 'white',
              border: 'none',
              borderRadius: '8px',
              fontSize: '14px',
              cursor: 'pointer'
            }}
          >
            {facingMode === 'environment' ? '전면' : '후면'}
          </button>

          <button
            onClick={stopCamera}
            style={{
              padding: '14px 16px',
              background: '#F1F1F1',
              color: '#333',
              border: 'none',
              borderRadius: '8px',
              fontSize: '14px',
              cursor: 'pointer'
            }}
          >
            종료
          </button>
        </div>
      </div>

      <canvas ref={canvasRef} style={{ display: 'none' }} />

      {captured && (
        <div style={{
          marginTop: '12px',
          textAlign: 'center'
        }}>
          <p style={{ color: '#1D9E75', fontWeight: 600, marginBottom: '8px' }}>
            이미지 준비 완료! 분석 중...
          </p>
          <button
            onClick={handleRetake}
            style={{
              padding: '10px 14px',
              background: '#F1F1F1',
              color: '#333',
              border: 'none',
              borderRadius: '8px',
              fontSize: '13px',
              fontWeight: 600,
              cursor: 'pointer'
            }}
          >
            다시 촬영하기
          </button>
        </div>
      )}
    </div>
  )
}
