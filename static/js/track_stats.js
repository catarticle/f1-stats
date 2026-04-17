function loadTrackStats(year, event) {
    console.log('Загрузка статистики трассы:', event, year);
    const loaderTrackStats = showLoading('track-stats', 'normal');
    const loaderTrackVis = showLoading('track-visualization', 'large'); // Большой лоадер для трассы

    fetch('/track_stats', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: 'year=' + encodeURIComponent(year) + '&event=' + encodeURIComponent(event)
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Ошибка сети');
        }
        return response.json();
    })
    .then(data => {
        console.log('Статистика получена:', data);
        displayTrackStats(data);
        hideLoading('track-stats');
        hideLoading('track-visualization');
    })
    .catch(error => {
        console.error('Ошибка загрузки статистики:', error);
        displayFallbackStats(event);
        hideLoading('track-stats');
        hideLoading('track-visualization');
    });
}

function displayTrackStats(statsData) {
    const statsContainer = document.getElementById('track-stats');
    if (!statsContainer) {
        console.error('Контейнер track-stats не найден');
        hideLoading('track-visualization');
        return;
    }
    
    const trackInfo = statsData.track_info || {};
    const lapRecord = statsData.lap_record || {};
    const successfulPilot = statsData.successful_pilot || {};
    
    const html = `
        <div class="track-stats-card">
            <div class="track-header">
                <h3>${trackInfo.name || 'Трасса'}</h3>
                <div class="track-location">
                    <span class="country-flag">📍</span>
                    <span>${trackInfo.location || 'Нет данных'}, ${trackInfo.country || 'Нет данных'}</span>
                </div>
            </div>
            
            <div class="stats-grid">
                <div class="stat-item">
                    <div class="stat-icon">📏</div>
                    <div class="stat-content">
                        <div class="stat-label">Длина трассы</div>
                        <div class="stat-value">${statsData.circuit_length || 'Нет данных'}</div>
                    </div>
                </div>
                
                <div class="stat-item">
                    <div class="stat-icon">↩️</div>
                    <div class="stat-content">
                        <div class="stat-label">Повороты</div>
                        <div class="stat-value">${statsData.turns_count || 'Нет данных'}</div>
                    </div>
                </div>
            </div>
    `;
    
    statsContainer.innerHTML = html;

    // Отрисовываем трассу
    if (statsData.coordinates && statsData.coordinates.length > 0) {
        drawSimpleTrack(statsData);
    } else {
        console.log('Нет координат для отрисовки трассы');
        drawFallbackTrack();
    }
}

function displayFallbackStats(eventName) {
    const statsContainer = document.getElementById('track-stats');
    if (!statsContainer) return;
    
    const html = `
        <div class="track-stats-card">
            <div class="track-header">
                <h3>${eventName}</h3>
                <div class="track-location">
                    <span>Данные не загружены</span>
                </div>
            </div>
            <div class="stats-error">
                <p>Не удалось загрузить статистику трассы.</p>
                <p>Попробуйте выбрать другую гонку.</p>
            </div>
        </div>
    `;
    
    statsContainer.innerHTML = html;
}

function drawSimpleTrack(trackData) {
    const container = document.getElementById('track-visualization');
    const svg = document.getElementById('track-svg');
    if (!container || !svg) {
        console.error('Элементы трассы не найдены!');
        return;
    }
    
    // Очищаем SVG
    svg.innerHTML = '';
    
    // Рисуем линию если есть координаты
    if (trackData.coordinates && trackData.coordinates.length > 1) {
        const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
        let d = `M ${trackData.coordinates[0].x} ${trackData.coordinates[0].y}`;
        for (let i = 1; i < trackData.coordinates.length; i++) {
            d += ` L ${trackData.coordinates[i].x} ${trackData.coordinates[i].y}`;
        }
        path.setAttribute("d", d);
        path.setAttribute("stroke", "#e10600");
        path.setAttribute("stroke-width", "3");
        path.setAttribute("fill", "none");
        svg.appendChild(path);
    } else {
        drawFallbackTrack();
    }
}

function drawFallbackTrack() {
    const svg = document.getElementById('track-svg');
    if (!svg) return;
    
    svg.innerHTML = '';
    
    // Простой овал
    const circle = document.createElementNS("http://www.w3.org/2000/svg", "ellipse");
    circle.setAttribute("cx", "250");
    circle.setAttribute("cy", "250");
    circle.setAttribute("rx", "180");
    circle.setAttribute("ry", "80");
    circle.setAttribute("stroke", "#e10600");
    circle.setAttribute("stroke-width", "3");
    circle.setAttribute("fill", "none");
    svg.appendChild(circle);
    
    // Стартовая линия
    const startLine = document.createElementNS("http://www.w3.org/2000/svg", "line");
    startLine.setAttribute("x1", "250");
    startLine.setAttribute("y1", "170");
    startLine.setAttribute("x2", "250");
    startLine.setAttribute("y2", "190");
    startLine.setAttribute("stroke", "#fff");
    startLine.setAttribute("stroke-width", "3");
    svg.appendChild(startLine);
}

if (typeof window !== 'undefined') {
    window.loadTrackStats = loadTrackStats;
    window.displayTrackStats = displayTrackStats;
}