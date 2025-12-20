function loadTyreStrategy(year, event) {
    console.log('Загрузка стратегии по шинам:', event, year);
    
    fetch('/tyre_strategy', {
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
        console.log('Стратегия получена:', data);
        if (data.error) {
            displayStrategyError(data.error);
        } else {
            renderTyreStrategyChart(data);
        }
    })
    .catch(error => {
        console.error('Ошибка загрузки стратегии:', error);
        displayStrategyError('Не удалось загрузить данные стратегии');
    });
}

function renderTyreStrategyChart(strategyData) {
    const container = document.getElementById('tyre-strategy-chart');
    if (!container) {
        console.error('Контейнер tyre-strategy-chart не найден');
        return;
    }
    
    if (!strategyData || strategyData.length === 0) {
        container.innerHTML = '<p style="text-align: center; color: #666;">Нет данных по стратегии</p>';
        return;
    }
    
    // Определяем максимальное количество кругов для масштабирования
    let maxLaps = 0;
    strategyData.forEach(driver => {
        let driverLaps = 0;
        driver.stints.forEach(stint => {
            driverLaps += stint.stint_length;
        });
        maxLaps = Math.max(maxLaps, driverLaps);
    });
    
    // Пока просто сортируем по имени, потом можно будет по позиции
    strategyData.sort((a, b) => a.driver.localeCompare(b.driver));
    
    let html = '<div class="tyre-strategy-container">';
    
    strategyData.forEach(driver => {
        html += `<div class="tyre-bar">`;
        html += `<div class="tyre-driver">${driver.driver}</div>`;
        html += `<div class="tyre-stints">`;
        
        let currentLap = 0;
        driver.stints.forEach((stint, index) => {
            const widthPercent = (stint.stint_length / maxLaps) * 100;
            const compoundClass = `tyre-${stint.compound.toLowerCase()}`;
            const stintLabel = `${stint.stint_length}L (${stint.compound})`;
            
            html += `<div class="tyre-stint ${compoundClass}" 
                         style="width: ${widthPercent}%"
                         title="${stintLabel}">
                         ${stint.stint_length}
                    </div>`;
        });
        
        html += `</div></div>`;
    });
    
    html += createTyreLegend();
    html += '</div>';
    
    container.innerHTML = html;
}

function createTyreLegend() {
    return `
        <div class="tyre-legend">
            <div class="tyre-legend-item">
                <div class="tyre-legend-color tyre-soft"></div>
                <span class="tyre-legend-label">SOFT</span>
            </div>
            <div class="tyre-legend-item">
                <div class="tyre-legend-color tyre-medium"></div>
                <span class="tyre-legend-label">MEDIUM</span>
            </div>
            <div class="tyre-legend-item">
                <div class="tyre-legend-color tyre-hard"></div>
                <span class="tyre-legend-label">HARD</span>
            </div>
            <div class="tyre-legend-item">
                <div class="tyre-legend-color tyre-intermediate"></div>
                <span class="tyre-legend-label">INTER</span>
            </div>
            <div class="tyre-legend-item">
                <div class="tyre-legend-color tyre-wet"></div>
                <span class="tyre-legend-label">WET</span>
            </div>
            <div class="tyre-legend-item">
                <div class="tyre-legend-color tyre-unknown"></div>
                <span class="tyre-legend-label">UNKNOWN</span>
            </div>
        </div>
    `;
}

function displayStrategyError(message) {
    const container = document.getElementById('tyre-strategy-chart');
    if (!container) return;
    
    container.innerHTML = `
        <div style="text-align: center; padding: 40px;">
            <p style="color: #e10600;">${message}</p>
            <p style="color: #666; font-size: 14px;">Попробуйте выбрать другую гонку</p>
        </div>
    `;
}


// Экспортируем функции
if (typeof window !== 'undefined') {
    window.loadTyreStrategy = loadTyreStrategy;
    window.renderTyreStrategyChart = renderTyreStrategyChart;
}

function loadPitstopAnalysis(year, event) {
    console.log('Загрузка анализа пит-стопов:', event, year);
    
    fetch('/pitstop_analysis', {
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
        console.log('Анализ пит-стопов получен:', data);
        if (data.error) {
            displayPitstopChartError(data.error);
        } else {
            renderPitstopAnalysisChart(data);
        }
    })
    .catch(error => {
        console.error('Ошибка загрузки анализа пит-стопов:', error);
        displayPitstopChartError('Не удалось загрузить данные пит-стопов');
    });
}

function renderPitstopAnalysisChart(data) {
    const container = document.getElementById('pitstop-chart');
    if (!container) {
        console.error('Контейнер pitstop-chart не найден');
        return;
    }
    
    if (!data || !data.teams || Object.keys(data.teams).length === 0) {
        container.innerHTML = '<p style="text-align: center; color: #666;">Нет данных по пит-стопам</p>';
        return;
    }
    
    // Создаем график для команд
    let html = `
        <div class="pitstop-analysis-container">
            <div class="pitstop-summary">
                <div class="summary-item">
                    <div class="summary-label">Всего пит-стопов</div>
                    <div class="summary-value">${data.total_pitstops}</div>
                </div>
            </div>
    `;
    
    // Сортируем команды по среднему времени пит-стопа
    const teams = Object.entries(data.teams)
        .sort(([, a], [, b]) => a.avg_time - b.avg_time);
    
    // Отображаем топ-5 команд
    const topTeams = teams.slice(0, 5);
    
    html += '<div class="team-analysis">';
    html += '<h5>Лучшие по времени (тут считается время нахождения на питлейне в целом, включая пит-стоп)</h5>';
    
    topTeams.forEach(([teamName, teamData]) => {
        const avgTime = teamData.avg_time.toFixed(2);
        
        html += `
            <div class="team-row">
                <div class="team-name">${teamName}</div>
                <div class="team-stats">
                    <span class="pitstop-count">${teamData.total_stops} стопов</span>
                    <span class="avg-time">${avgTime} сек</span>
                </div>
                <div class="time-bar-container">
                    <div class="time-bar" style="width: ${(avgTime / 50) * 100}%"></div>
                </div>
            </div>
        `;
    });
    
    html += '</div>';
    
    // Анализ по напарникам
    if (data.teams && Object.keys(data.teams).length > 0) {
        html += '<div class="teammate-comparison">';
        html += '<h5>Сравнение напарников</h5>';
        
        // Группируем гонщиков по командам
        const teamDrivers = {};
        Object.entries(data.teams).forEach(([teamName, teamData]) => {
            if (teamData.stops && teamData.stops.length > 0) {
                // Группируем остановки по гонщикам
                const driverTimes = {};
                teamData.stops.forEach(stop => {
                    if (!driverTimes[stop.driver]) {
                        driverTimes[stop.driver] = [];
                    }
                    driverTimes[stop.driver].push(stop.time);
                });
                
                const drivers = Object.keys(driverTimes);
                if (drivers.length === 2) {
                    const avgTime1 = driverTimes[drivers[0]].reduce((a, b) => a + b, 0) / driverTimes[drivers[0]].length;
                    const avgTime2 = driverTimes[drivers[1]].reduce((a, b) => a + b, 0) / driverTimes[drivers[1]].length;
                    
                    const fasterDriver = avgTime1 < avgTime2 ? drivers[0] : drivers[1];
                    const timeDiff = Math.abs(avgTime1 - avgTime2).toFixed(2);
                    
                    html += `
                        <div class="teammate-row">
                            <div class="team-name-small">${teamName}</div>
                            <div class="teammate-info">
                                <span class="driver-faster">${fasterDriver}</span>
                                <span class="time-diff">быстрее на ${timeDiff}с</span>
                            </div>
                        </div>
                    `;
                }
            }
        });
        
        html += '</div>';
    }
    
    html += '</div>';
    container.innerHTML = html;
}

function displayPitstopChartError(message) {
    const container = document.getElementById('pitstop-chart');
    if (!container) return;
    
    container.innerHTML = `
        <div style="text-align: center; padding: 60px 20px;">
            <h4 style="color: #666; margin-bottom: 10px;">Анализ пит-стопов</h4>
            <p style="color: #999; font-size: 14px;">
                ${message}<br>
                Попробуйте выбрать другую гонку
            </p>
        </div>
    `;
}