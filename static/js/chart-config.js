/**
 * Chart.js configurations for the NiceHash Order Manager
 */

// Order performance chart configuration
function initOrderPerformanceChart(labels, data) {
    const ctx = document.getElementById('orderPerformanceChart');
    
    if (!ctx) return;
    
    // If no data, show a message instead
    if (!labels.length || !data.length) {
        ctx.style.display = 'none';
        const parent = ctx.parentElement;
        const message = document.createElement('div');
        message.className = 'alert alert-info text-center my-5';
        message.innerHTML = '<i class="fas fa-chart-line me-2"></i> No active orders to display in chart.';
        parent.appendChild(message);
        return;
    }
    
    // Generate colors
    const backgroundColors = generateColors(labels.length, 0.7);
    const borderColors = generateColors(labels.length, 1);
    
    const orderChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Speed Limit',
                data: data,
                backgroundColor: backgroundColors,
                borderColor: borderColors,
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: 'Hashpower Order Distribution',
                    color: '#adb5bd',
                    font: {
                        size: 16
                    }
                },
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return `Speed Limit: ${context.raw}`;
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    },
                    ticks: {
                        color: '#adb5bd'
                    },
                    title: {
                        display: true,
                        text: 'Speed Limit',
                        color: '#adb5bd'
                    }
                },
                x: {
                    grid: {
                        display: false
                    },
                    ticks: {
                        color: '#adb5bd'
                    }
                }
            }
        }
    });
}

// Order history chart (for individual order pages)
function initOrderHistoryChart(timestamps, prices, limits) {
    const ctx = document.getElementById('orderHistoryChart');
    
    if (!ctx) return;
    
    // Format timestamps for display
    const formattedDates = timestamps.map(timestamp => {
        const date = new Date(timestamp);
        return date.toLocaleTimeString();
    });
    
    const chart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: formattedDates,
            datasets: [
                {
                    label: 'Price',
                    data: prices,
                    borderColor: 'rgba(54, 162, 235, 1)',
                    backgroundColor: 'rgba(54, 162, 235, 0.1)',
                    borderWidth: 2,
                    pointRadius: 3,
                    tension: 0.3,
                    yAxisID: 'y'
                },
                {
                    label: 'Speed Limit',
                    data: limits,
                    borderColor: 'rgba(255, 99, 132, 1)',
                    backgroundColor: 'rgba(255, 99, 132, 0.1)',
                    borderWidth: 2,
                    pointRadius: 3,
                    tension: 0.3,
                    yAxisID: 'y1'
                }
            ]
        },
        options: {
            responsive: true,
            interaction: {
                mode: 'index',
                intersect: false,
            },
            plugins: {
                title: {
                    display: true,
                    text: 'Order Price and Limit History',
                    color: '#adb5bd',
                    font: {
                        size: 16
                    }
                },
                tooltip: {
                    enabled: true
                }
            },
            scales: {
                x: {
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    },
                    ticks: {
                        color: '#adb5bd'
                    }
                },
                y: {
                    type: 'linear',
                    display: true,
                    position: 'left',
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    },
                    ticks: {
                        color: '#adb5bd'
                    },
                    title: {
                        display: true,
                        text: 'Price (BTC)',
                        color: '#adb5bd'
                    }
                },
                y1: {
                    type: 'linear',
                    display: true,
                    position: 'right',
                    grid: {
                        drawOnChartArea: false,
                    },
                    ticks: {
                        color: '#adb5bd'
                    },
                    title: {
                        display: true,
                        text: 'Speed Limit',
                        color: '#adb5bd'
                    }
                }
            }
        }
    });
}

// Market data chart (price trends)
function initMarketDataChart(timestamps, prices, algorithm) {
    const ctx = document.getElementById('marketDataChart');
    
    if (!ctx) return;
    
    // Format timestamps for display
    const formattedDates = timestamps.map(timestamp => {
        const date = new Date(timestamp);
        return date.toLocaleDateString();
    });
    
    const chart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: formattedDates,
            datasets: [{
                label: `${algorithm} Price Trend`,
                data: prices,
                borderColor: 'rgba(75, 192, 192, 1)',
                backgroundColor: 'rgba(75, 192, 192, 0.1)',
                fill: true,
                borderWidth: 2,
                pointRadius: 2,
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: `${algorithm} Price Trend`,
                    color: '#adb5bd',
                    font: {
                        size: 16
                    }
                },
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return `Price: ${context.raw} BTC`;
                        }
                    }
                }
            },
            scales: {
                y: {
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    },
                    ticks: {
                        color: '#adb5bd'
                    },
                    title: {
                        display: true,
                        text: 'Price (BTC)',
                        color: '#adb5bd'
                    }
                },
                x: {
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    },
                    ticks: {
                        color: '#adb5bd'
                    }
                }
            }
        }
    });
}

// Generate colors for charts
function generateColors(count, opacity) {
    const colors = [];
    for (let i = 0; i < count; i++) {
        const hue = (i * 137) % 360; // Use golden angle approximation for evenly distributed colors
        colors.push(`hsla(${hue}, 70%, 60%, ${opacity})`);
    }
    return colors;
}
