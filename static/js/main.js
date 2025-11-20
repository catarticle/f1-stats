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
        // Загружаем данные для реплеера
        loadReplayData(year, event);
        loadPositionChart(year, event); // <-- вызываем график с позициями
    });
}

function loadReplayData(year, event) {
    fetch('/replay', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: 'year=' + encodeURIComponent(year) + '&event=' + encodeURIComponent(event)
    })
    .then(response => response.json())
    .then(data => {
        drawTrack(data);
    });
}

function drawTrack(data) {
    const svg = document.getElementById('track');
    svg.innerHTML = '';

    // Рисуем трассу (круг)
    const track = document.createElementNS("http://www.w3.org/2000/svg", "circle");
    track.setAttribute("cx", 250);
    track.setAttribute("cy", 250);
    track.setAttribute("r", 200);
    track.setAttribute("stroke", "black");
    track.setAttribute("fill", "none");
    svg.appendChild(track);

    // Рисуем пилотов
    data.forEach(driver => {
        const x = 250 + 200 * Math.cos(driver.angle);
        const y = 250 + 200 * Math.sin(driver.angle);

        const car = document.createElementNS("http://www.w3.org/2000/svg", "circle");
        car.setAttribute("cx", x);
        car.setAttribute("cy", y);
        car.setAttribute("r", 6);
        car.setAttribute("fill", driver.color);
        svg.appendChild(car);

        const label = document.createElementNS("http://www.w3.org/2000/svg", "text");
        label.setAttribute("x", x + 10);
        label.setAttribute("y", y);
        label.textContent = driver.name.substring(0, 3);
        svg.appendChild(label);
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
            dash: driver.dash || 'solid'  // стиль линии: solid или dash
        },
        type: 'scatter'
    }));

    const layout = {
        title: 'Изменение позиций в гонке',
        xaxis: { title: 'Круг' },
        yaxis: {
            title: 'Позиция',
            range: [20.5, 0.5], // явно задаём диапазон: от 20.5 до 0.5
            dtick: 1,           // шаг сетки
            autorange: false    // отключаем авто-диапазон
        },
        height: 400
    };

    Plotly.newPlot('position-chart', traces, layout)
    .catch(error => console.error('Ошибка отрисовки графика:', error));
}

// Загружаем данные для текущей гонки при запуске
document.addEventListener('DOMContentLoaded', function() {
    const year = document.getElementById('year-select').value;
    const event = document.getElementById('event-select').value;
    loadReplayData(year, event);
});