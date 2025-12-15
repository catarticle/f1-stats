function updateEvents() {
    const year = document.getElementById('year-select').value;

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
        loadResults();
    });
}

function loadResults() {
    const year = document.getElementById('year-select').value;
    const event = document.getElementById('event-select').value;

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
        loadPositionChart(year, event);
        
        // Загружаем статистику трассы
        if (typeof loadTrackStats === 'function') {
            loadTrackStats(year, event);
        } else {
            console.warn('loadTrackStats не определена');
            // Показываем заглушку
            if (typeof displayFallbackStats === 'function') {
                displayFallbackStats(event);
            }
        }
    });
}


function loadPositionChart(year, event) {
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
            dash: driver.dash || 'solid'
        },
        type: 'scatter'
    }));

    const layout = {
        title: 'Изменение позиций в гонке',
        xaxis: { title: 'Круг' },
        yaxis: {
            title: 'Позиция',
            range: [20.5, 0.5],
            dtick: 1,
            autorange: false
        },
        height: 400,
        margin: { l: 50, r: 30, t: 40, b: 50 }
    };

    Plotly.newPlot('position-chart', traces, layout)
    .catch(error => console.error('Ошибка отрисовки графика:', error));
}

// Загружаем данные при запуске
document.addEventListener('DOMContentLoaded', function() {
    loadResults();
});