function loadTrackInfo(year, event) {
    console.log('loadTrackInfo вызвана для:', year, event);
    
    fetch('/track_info', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: 'year=' + encodeURIComponent(year) + '&event=' + encodeURIComponent(event)
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        return response.json();
    })
    .then(data => {
        console.log('Данные трассы получены:', data);
        drawSimpleTrack(data);
        updateTrackStats(data);
    })
    .catch(error => {
        console.error('Ошибка загрузки трассы:', error);
        drawFallbackTrack();
    });
}

function drawSimpleTrack(trackData) {
    const svg = document.getElementById('track-svg');
    if (!svg) {
        console.error('SVG элемент не найден!');
        return;
    }
    
    svg.innerHTML = '';
    
    // Просто рисуем линию если есть координаты
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

function updateTrackStats(trackData) {
    const statsContainer = document.getElementById('track-stats');
    if (!statsContainer) {
        console.error('Элемент track-stats не найден!');
        return;
    }
    
    let html = `
        <div class="track-info-card">
            <h4>${trackData.name || 'Трасса'}</h4>
            <p><strong>Страна:</strong> ${trackData.country || 'Нет данных'}</p>
            <p><strong>Место:</strong> ${trackData.location || 'Нет данных'}</p>
    `;
    
    if (trackData.lap_record) {
        html += `<p><strong>Рекорд круга:</strong> ${trackData.lap_record.time || 'Нет данных'} (${trackData.lap_record.driver || '?'})</p>`;
    }
    
    html += '</div>';
    statsContainer.innerHTML = html;
}

// Экспортируем функцию для использования в main.js
window.loadTrackInfo = loadTrackInfo;
window.drawFallbackTrack = drawFallbackTrack;