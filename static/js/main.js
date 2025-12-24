function showLoading(containerId, size = 'normal') {
    const container = document.getElementById(containerId);
    if (!container) return null;
    
    // Проверяем, есть ли уже лоадер
    let loader = container.querySelector('.loading-overlay');
    if (!loader) {
        loader = document.createElement('div');
        loader.className = `loading-overlay ${size === 'small' ? 'loading-inline' : ''}`;
        const wheel = document.createElement('div');
        wheel.className = `loader-wheel ${size}`;
        loader.appendChild(wheel);
        container.style.position = 'relative';
        container.appendChild(loader);
    }
    loader.classList.remove('hidden');
    
    return loader;
}

function hideLoading(containerId) {
    const container = document.getElementById(containerId);
    if (!container) return;
    
    const loader = container.querySelector('.loading-overlay');
    if (loader) {
        loader.classList.add('hidden');
    }
}

function updateEvents() {
    const year = document.getElementById('year-select').value;
    const loader = showLoading('event-select', 'small');

    fetch('/events?year=' + year)
    .then(response => response.json())
    .then(data => {
        const select = document.getElementById('event-select');
        select.innerHTML = '';
        data.forEach(event => {
            const option = document.createElement('option');
            option.value = event;
            option.textContent = event;
            select.appendChild(option);
        });
        if (loader) loader.remove();
        loadResults();
    })
    .catch(error => {
        if (loader) loader.remove();
        console.error('Ошибка загрузки событий:', error);
    });
}

function loadResults() {
    const year = document.getElementById('year-select').value;
    const event = document.getElementById('event-select').value;

    // Показываем лоадеры для всех секций
    showLoading('results', 'normal');
    showLoading('track-stats', 'normal');
    showLoading('position-chart', 'normal');
    showLoading('tyre-strategy-chart', 'normal');
    showLoading('pitstop-chart', 'normal');
    showLoading('track-visualization', 'normal'); 

    fetch('/results', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: 'year=' + encodeURIComponent(year) + '&event=' + encodeURIComponent(event)
    })
    .then(response => response.text())
    .then(data => {
        document.getElementById('results').innerHTML = data;
        hideLoading('results');
        
        loadPositionChart(year, event);
        
        // Загружаем статистику трассы
        if (typeof loadTrackStats === 'function') {
            loadTrackStats(year, event);
        } else {
            console.warn('loadTrackStats не определена');
            if (typeof displayFallbackStats === 'function') {
                displayFallbackStats(event);
            }
            hideLoading('track-stats');
            hideLoading('track-visualization'); 
        }

        // Загружаем стратегию по шинам
        if (typeof loadTyreStrategy === 'function') {
            loadTyreStrategy(year, event);
        } else {
            hideLoading('tyre-strategy-chart');
        }
        
        // Загружаем анализ пит-стопов
        if (typeof loadPitstopAnalysis === 'function') {
            loadPitstopAnalysis(year, event);
        } else {
            hideLoading('pitstop-chart');
        }
    })
    .catch(error => {
        console.error('Ошибка загрузки результатов:', error);
        // Скрываем все лоадеры в случае ошибки
        hideLoading('results');
        hideLoading('track-stats');
        hideLoading('position-chart');
        hideLoading('tyre-strategy-chart');
        hideLoading('pitstop-chart');
        hideLoading('track-visualization'); 
    });
}

function loadPositionChart(year, event) {
    const loader = showLoading('position-chart', 'normal');

    fetch('/positions', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: 'year=' + encodeURIComponent(year) + '&event=' + encodeURIComponent(event)
    })
    .then(response => response.json())
    .then(data => {
        plotPositions(data);
        hideLoading('position-chart');
    })
    .catch(error => {
        console.error('Ошибка загрузки позиций:', error);
        hideLoading('position-chart');
        
        const container = document.getElementById('position-chart');
        if (container) {
            container.innerHTML = '<p style="text-align: center; color: #666; padding: 40px;">Не удалось загрузить график позиций</p>';
        }
    });
}

function plotPositions(data) {
    if (!data || data.length === 0) {
        console.warn("Нет данных для графика");
        return;
    }

    const traces = data.map(driver => ({
        x: driver.laps,
        y: driver.positions,
        mode: 'lines',
        name: driver.name,
        line: {
            color: driver.color,
            dash: driver.dash || 'solid',
            width: 2
        },
        type: 'scatter',
        hovertemplate: 
            '<b>%{fullData.name}</b><br>' +
            'Круг: %{x}<br>' +
            'Позиция: %{y}<br>' +
            '<extra></extra>'
    }));

    const layout = {
        title: {
            font: {
                size: 18,
                color: '#e10600'
            }
        },
        xaxis: {
            title: {
                text: 'Круг',
                font: { size: 14 }
            },
            gridcolor: '#f0f0f0',
            showgrid: true
        },
        yaxis: {
            title: {
                text: 'Позиция',
                font: { size: 14 }
            },
            range: [20.5, 0.5],
            dtick: 1,
            autorange: false,
            gridcolor: '#f0f0f0',
            zeroline: false
        },
        hovermode: 'closest',
        hoverlabel: {
            bgcolor: '#1a1a1a',
            font: {
                size: 12,
                color: 'white'
            }
        },
        height: 500,
        margin: { l: 60, r: 30, t: 60, b: 60 },
        plot_bgcolor: 'white',
        paper_bgcolor: 'white',
        showlegend: true,
        legend: {
            x: 1.02,
            xanchor: 'left',
            y: 1,
            bgcolor: 'rgba(255, 255, 255, 0.8)',
            bordercolor: '#ddd',
            borderwidth: 1
        }
    };

    // Настройки для отображения
    const config = {
        responsive: true,
        displayModeBar: true,
        displaylogo: false,
        modeBarButtonsToRemove: ['pan2d', 'lasso2d', 'select2d'],
        modeBarButtonsToAdd: ['hoverClosestGl2d'],
        scrollZoom: false
    };

    Plotly.newPlot('position-chart', traces, layout, config)
    .catch(error => console.error('Ошибка отрисовки графика:', error));
}

// Функция для загрузки логотипов команд 
function loadTeamLogos() {
    const logosContainer = document.getElementById('team-logos');
    if (!logosContainer) return;
    
    // Очищаем контейнер
    logosContainer.innerHTML = '';
    
    // Добавляем логотипы
    teams2024.forEach(team => {
        const logoImg = document.createElement('img');
        logoImg.src = team.logo;
        logoImg.alt = team.name;
        logoImg.title = team.name; 
        logoImg.className = 'team-logo-simple';
        logosContainer.appendChild(logoImg);
    });
}

// Загружаем данные при запуске
document.addEventListener('DOMContentLoaded', function() {
    // Показываем лоадеры при первой загрузке
    showLoading('results', 'normal');
    showLoading('track-stats', 'normal');
    showLoading('position-chart', 'normal');
    showLoading('tyre-strategy-chart', 'normal');
    showLoading('pitstop-chart', 'normal');
    showLoading('track-visualization', 'large'); 
    loadTeamLogos();
    
    // Затем загружаем данные
    setTimeout(() => {
        loadResults();
    }, 100);
});