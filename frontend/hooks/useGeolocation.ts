'use client'

import { useEffect, useState } from 'react'

export interface Location {
  latitude: number | null
  longitude: number | null
  accuracy: number | null
  error: string | null
}

export const useGeolocation = () => {
  const [location, setLocation] = useState<Location>({
    latitude: null,
    longitude: null,
    accuracy: null,
    error: null
  })

  useEffect(() => {
    if (typeof window === 'undefined') {
      return
    }

    if (!navigator.geolocation) {
      setLocation({
        latitude: null,
        longitude: null,
        accuracy: null,
        error: 'GPS를 지원하지 않는 기기입니다'
      })
      return
    }

    const watchId = navigator.geolocation.watchPosition(
      (position) => {
        setLocation({
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
          accuracy: position.coords.accuracy,
          error: null
        })
      },
      (error) => {
        let message = 'GPS 정보를 가져올 수 없습니다'

        if (error.code === error.PERMISSION_DENIED) {
          message = 'GPS 권한이 거부되었습니다. 브라우저 설정에서 위치 권한을 허용해주세요'
        }

        if (error.code === error.POSITION_UNAVAILABLE) {
          message = '현재 위치 정보를 사용할 수 없습니다'
        }

        if (error.code === error.TIMEOUT) {
          message = 'GPS 수신 시간이 초과되었습니다'
        }

        setLocation((prev) => ({
          ...prev,
          error: message
        }))
      },
      {
        enableHighAccuracy: true,
        maximumAge: 0,
        timeout: 10000
      }
    )

    return () => {
      navigator.geolocation.clearWatch(watchId)
    }
  }, [])

  return location
}
