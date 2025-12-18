// 🧭 기상 데이터 기반 경로 최적화 시스템
// A* 알고리즘 + 바람/파도 고려

class WeatherAwareRouter {
    constructor(weatherLayer) {
        this.weatherLayer = weatherLayer;
        this.gridSize = 0.005; // 약 550m 간격 (더 정밀하게)
        
        // 가중치 설정
        this.weights = {
            distance: 1.0,      // 거리
            windFactor: 0.3,    // 바람 영향
            waveFactor: 0.4,    // 파도 영향
            wasteValue: 0.8     // 쓰레기 가치
        };
        
        // 안전 한계
        this.limits = {
            maxWindSpeed: 20,   // m/s
            maxWaveHeight: 3.0  // m
        };
        
        // 해역 범위 (부산 앞바다 - 바다만 허용)
        this.seaBounds = {
            minLat: 34.70,  // 남쪽 한계
            maxLat: 35.08,  // 북쪽 한계 (육지 시작)
            minLon: 128.80, // 서쪽 한계
            maxLon: 129.40  // 동쪽 한계
        };
        
        console.log('🧭 기상 기반 경로 시스템 초기화 (해상 전용)');
    }

    // 🎯 최적 경로 계산 (A* + 기상 + 왕복)
    async calculateOptimalRoute(start, hotspots, currentPosition, returnToStart = true) {
        console.log('🔍 최적 경로 계산 시작... (왕복: ' + (returnToStart ? 'YES' : 'NO') + ')');
        console.log('📍 실제 출발지:', start);
        
        // 1. 핫스팟 우선순위 정렬
        const prioritizedHotspots = this.prioritizeHotspots(hotspots, currentPosition);
        
        // 2. 각 핫스팟까지의 경로 계산 (가는 길)
        const routes = [];
        let currentPos = start; // ✅ 실제 선박 위치에서 시작
        
        console.log('🛫 가는 길: 출발지 → 핫스팟 ' + prioritizedHotspots.length + '개');
        
        for (let i = 0; i < prioritizedHotspots.length; i++) {
            const hotspot = prioritizedHotspots[i];
            let targetPos = [hotspot.lat, hotspot.lon];
            
            // 핫스팟이 육지 근처면 바다쪽으로 (핫스팟만)
            if (targetPos[0] > 35.08) {
                targetPos = [35.07, targetPos[1]];
                console.log(`⚠️ 핫스팟 ${i+1}이 육지 근처임, 바다로 이동:`, targetPos);
            }
            
            // A* 알고리즘으로 경로 찾기
            const path = await this.aStarWithWeather(currentPos, targetPos);
            
            if (path) {
                routes.push({
                    from: currentPos,
                    to: targetPos,
                    path: path,
                    hotspot: hotspot,
                    cost: this.calculatePathCost(path)
                });
                
                currentPos = targetPos;
            }
        }
        
        // 3. 돌아오는 경로 추가
        if (returnToStart && routes.length > 0) {
            console.log('🛬 돌아오는 길: 마지막 핫스팟 → 출발지');
            
            const lastPos = routes[routes.length - 1].to;
            const returnPath = await this.aStarWithWeather(lastPos, start); // ✅ 실제 출발지로 귀환
            
            if (returnPath) {
                routes.push({
                    from: lastPos,
                    to: start,
                    path: returnPath,
                    hotspot: { name: '출발지 귀환', lat: start[0], lon: start[1], density: 0, priority: 'return' },
                    cost: this.calculatePathCost(returnPath)
                });
                
                console.log('✅ 귀환 경로 추가 완료');
            }
        }
        
        // 4. 전체 경로 병합
        const fullRoute = this.mergeRoutes(routes);
        fullRoute.isRoundTrip = returnToStart;
        
        console.log('✅ 경로 계산 완료:', fullRoute);
        return fullRoute;
    }

    // 🌟 A* 알고리즘 (기상 고려)
    async aStarWithWeather(start, goal) {
        const openSet = [{ pos: start, g: 0, h: this.heuristic(start, goal), f: 0, parent: null }];
        const closedSet = new Set();
        const cameFrom = new Map();
        
        while (openSet.length > 0) {
            // f값이 가장 낮은 노드 선택
            openSet.sort((a, b) => a.f - b.f);
            const current = openSet.shift();
            
            // 목표 도달
            if (this.distance(current.pos, goal) < 0.01) {
                return this.reconstructPath(cameFrom, current.pos);
            }
            
            const key = `${current.pos[0].toFixed(3)},${current.pos[1].toFixed(3)}`;
            closedSet.add(key);
            
            // 이웃 노드 탐색
            const neighbors = this.getNeighbors(current.pos);
            
            for (const neighbor of neighbors) {
                const nKey = `${neighbor[0].toFixed(3)},${neighbor[1].toFixed(3)}`;
                
                if (closedSet.has(nKey)) continue;
                
                // 기상 비용 계산
                const weatherCost = await this.getWeatherCost(neighbor);
                const moveCost = this.distance(current.pos, neighbor);
                const tentativeG = current.g + moveCost + weatherCost;
                
                const existingNode = openSet.find(n => 
                    Math.abs(n.pos[0] - neighbor[0]) < 0.001 && 
                    Math.abs(n.pos[1] - neighbor[1]) < 0.001
                );
                
                if (!existingNode || tentativeG < existingNode.g) {
                    const h = this.heuristic(neighbor, goal);
                    const f = tentativeG + h;
                    
                    if (existingNode) {
                        existingNode.g = tentativeG;
                        existingNode.f = f;
                        existingNode.parent = current;
                    } else {
                        openSet.push({
                            pos: neighbor,
                            g: tentativeG,
                            h: h,
                            f: f,
                            parent: current
                        });
                    }
                    
                    cameFrom.set(nKey, current.pos);
                }
            }
            
            // 너무 많이 탐색하면 중단 (성능)
            if (closedSet.size > 500) {
                console.warn('⚠️ A* 탐색 제한 도달, 직선 경로 반환');
                return this.straightPath(start, goal);
            }
        }
        
        // 경로 못 찾으면 직선
        console.warn('⚠️ 경로를 찾을 수 없음, 직선 경로 반환');
        return this.straightPath(start, goal);
    }

    // 📍 이웃 노드 생성
    getNeighbors(pos) {
        const [lat, lon] = pos;
        const step = this.gridSize;
        
        return [
            [lat + step, lon],       // 북
            [lat + step, lon + step], // 북동
            [lat, lon + step],       // 동
            [lat - step, lon + step], // 남동
            [lat - step, lon],       // 남
            [lat - step, lon - step], // 남서
            [lat, lon - step],       // 서
            [lat + step, lon - step]  // 북서
        ];
    }

    // 🏝️ 육지 체크 (정밀 버전 - 부산/김해/거제 해역)
    isLand(lat, lon) {
        // 포괄적인 육지 체크 - 보수적으로
        
        // 부산항 북쪽 육지 (안전 마진을 크게)
        if (lat > 35.09) {
            return true; // 북위 35.09도 이상은 모두 육지
        }
        
        // 서쪽 김해/거제 육지
        if (lon < 128.85) {
            return true; // 동경 128.85도 서쪽은 육지
        }
        
        // 영도구 방향 (동쪽 해안)
        if (lat > 35.05 && lon > 129.05 && lon < 129.12) {
            return true; // 해운대/광안리 해변 그 너머
        }
        
        return false;
    }

    // 🌊 기상 비용 계산 (육지 회피 포함)
    async getWeatherCost(position) {
        const [lat, lon] = position;
        
        // 🚨 1순위: 해역 밖으로 나가면 차단
        if (lat < this.seaBounds.minLat || lat > this.seaBounds.maxLat ||
            lon < this.seaBounds.minLon || lon > this.seaBounds.maxLon) {
            return 99999;
        }
        
        // 🚨 2순위: 육지 체크
        if (this.isLand(lat, lon)) {
            return 99999; // 절대 통과 불가
        }
        
        const weather = await this.weatherLayer.getWeatherAt(lat, lon);
        
        if (!weather) return 0;
        
        let cost = 0;
        
        // 풍속 비용
        const windCost = Math.pow(weather.wind.speed / 10, 2) * this.weights.windFactor;
        cost += windCost;
        
        // 파고 비용
        const waveCost = Math.pow(weather.waves.height / 2, 2) * this.weights.waveFactor;
        cost += waveCost;
        
        // 위험 구역 (운항 불가능)
        if (weather.wind.speed > this.limits.maxWindSpeed || 
            weather.waves.height > this.limits.maxWaveHeight) {
            cost += 9999; // 거의 통과 불가
        }
        
        return cost;
    }

    // 📏 휴리스틱 (추정 거리)
    heuristic(from, to) {
        return this.distance(from, to) * this.weights.distance;
    }

    // 📏 거리 계산
    distance(pos1, pos2) {
        const R = 6371; // km
        const lat1 = pos1[0] * Math.PI / 180;
        const lat2 = pos2[0] * Math.PI / 180;
        const deltaLat = (pos2[0] - pos1[0]) * Math.PI / 180;
        const deltaLon = (pos2[1] - pos1[1]) * Math.PI / 180;

        const a = Math.sin(deltaLat / 2) * Math.sin(deltaLat / 2) +
                  Math.cos(lat1) * Math.cos(lat2) *
                  Math.sin(deltaLon / 2) * Math.sin(deltaLon / 2);
        
        const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
        return R * c;
    }

    // 🎯 핫스팟 우선순위 정렬
    prioritizeHotspots(hotspots, currentPosition) {
        return hotspots
            .map(hotspot => {
                const distance = this.distance(
                    currentPosition, 
                    [hotspot.lat, hotspot.lon]
                );
                
                // 우선순위 점수 계산
                let score = 0;
                
                // 우선순위
                if (hotspot.priority === 'high') score += 100;
                else if (hotspot.priority === 'medium') score += 50;
                else score += 20;
                
                // 거리 패널티 (가까울수록 좋음)
                score -= distance * 2;
                
                return { ...hotspot, score, distance };
            })
            .sort((a, b) => b.score - a.score);
    }

    // 🛤️ 경로 재구성
    reconstructPath(cameFrom, current) {
        const path = [current];
        let curr = current;
        const key = (pos) => `${pos[0].toFixed(3)},${pos[1].toFixed(3)}`;
        
        while (cameFrom.has(key(curr))) {
            curr = cameFrom.get(key(curr));
            path.unshift(curr);
        }
        
        return path;
    }

    // 📊 경로 비용 계산
    calculatePathCost(path) {
        let totalCost = 0;
        
        for (let i = 1; i < path.length; i++) {
            totalCost += this.distance(path[i-1], path[i]);
        }
        
        return totalCost;
    }

    // 🔗 경로 병합
    mergeRoutes(routes) {
        const allPoints = [];
        let totalDistance = 0;
        let totalTime = 0;
        const avgSpeed = 12 * 1.852; // knots to km/h
        
        routes.forEach(route => {
            allPoints.push(...route.path);
            totalDistance += route.cost;
        });
        
        totalTime = totalDistance / avgSpeed;
        
        return {
            path: allPoints,
            totalDistance: totalDistance,
            totalTime: totalTime,
            waypoints: routes.map(r => r.hotspot),
            segments: routes
        };
    }

    // 📏 직선 경로 (fallback)
    straightPath(start, end, segments = 10) {
        const path = [];
        
        for (let i = 0; i <= segments; i++) {
            const t = i / segments;
            const lat = start[0] + (end[0] - start[0]) * t;
            const lon = start[1] + (end[1] - start[1]) * t;
            path.push([lat, lon]);
        }
        
        return path;
    }

    // 🎨 경로를 지도에 그리기
    drawRoute(map, route, color = '#2196f3') {
        // 기존 경로 제거
        if (this.routeLayer) {
            map.removeLayer(this.routeLayer);
        }
        
        // 새 경로 그리기
        this.routeLayer = L.polyline(route.path, {
            color: color,
            weight: 4,
            opacity: 0.7,
            smoothFactor: 1
        }).addTo(map);
        
        // 웨이포인트 마커
        route.waypoints.forEach((hotspot, idx) => {
            L.marker([hotspot.lat, hotspot.lon], {
                icon: L.divIcon({
                    className: 'route-waypoint',
                    html: `<div style="
                        background: ${color};
                        color: white;
                        border-radius: 50%;
                        width: 30px;
                        height: 30px;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        font-weight: bold;
                        border: 2px solid white;
                        box-shadow: 0 2px 8px rgba(0,0,0,0.3);
                    ">${idx + 1}</div>`,
                    iconSize: [30, 30],
                    iconAnchor: [15, 15]
                })
            }).addTo(map).bindPopup(`
                <b>경유지 ${idx + 1}</b><br>
                ${hotspot.name}
            `);
        });
        
        return this.routeLayer;
    }

    // 📊 경로 정보 요약
    getRouteSummary(route) {
        const hours = Math.floor(route.totalTime);
        const minutes = Math.round((route.totalTime - hours) * 60);
        
        return {
            distance: `${route.totalDistance.toFixed(1)} km`,
            time: `${hours}시간 ${minutes}분`,
            waypoints: route.waypoints.length,
            segments: route.segments.length
        };
    }
}

// 전역으로 export
if (typeof window !== 'undefined') {
    window.WeatherAwareRouter = WeatherAwareRouter;
}
