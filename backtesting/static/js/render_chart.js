document.addEventListener("DOMContentLoaded", function () {
    const chartContainer = document.getElementById('chart-container');

    // Initialize the Lightweight Chart
    const chart = LightweightCharts.createChart(chartContainer, {
        width: chartContainer.clientWidth,
        height: 600,  // Increased height for better visibility
        layout: {
            backgroundColor: '#ffffff',
            textColor: '#000000',
        },
        grid: {
            vertLines: {
                color: '#e1e1e1',
            },
            horzLines: {
                color: '#e1e1e1',
            },
        },
        rightPriceScale: {
            scaleMargins: {
                top: 0.1,
                bottom: 0.1,
            },
            autoScale: true,  // Enable auto-scaling
            borderColor: '#cccccc',
        },
        leftPriceScale: {
            scaleMargins: {
                top: 0.1,
                bottom: 0.1,
            },
            visible: true,
            borderColor: '#cccccc',
            autoScale: true,  // Enable auto-scaling
        },
        timeScale: {
            borderColor: '#cccccc',
            timeVisible: true,
            secondsVisible: false,
        },
        crosshair: {
            mode: LightweightCharts.CrosshairMode.Normal,
        },
        handleScroll: {
            mouseWheel: true,        // Enable mouse wheel scrolling
            pressedMouseMove: true,  // Enable chart panning
            horzTouchDrag: true,     // Enable horizontal touch dragging
            vertTouchDrag: true      // Enable vertical touch dragging
        },
        handleScale: {
            axisPressedMouseMove: {
                time: true,   // Enable time scale zooming
                price: true   // Enable price scale zooming
            },
            mouseWheel: true,        // Enable mouse wheel zooming
            pinch: true,             // Enable pinch zooming
            axisDoubleClickReset: true  // Enable double-click reset
        },
    });

    // Add candlestick series (price chart)
    const candleSeries = chart.addCandlestickSeries({
        upColor: '#4caf50',
        downColor: '#ff5722',
        borderDownColor: '#ff5722',
        borderUpColor: '#4caf50',
        wickDownColor: '#ff5722',
        wickUpColor: '#4caf50',
    });

    // Add portfolio balance series
    const portfolioSeries = chart.addLineSeries({
        color: '#D3D3D3',
        lineWidth: 2,
        priceScaleId: 'left',
        title: 'Portfolio Value',
    });

    // Fetch price and trade data from the API using the global URL
    fetch(window.BACKTEST_CHART_DATA_URL)
        .then((response) => response.json())
        .then((data) => {
            console.log("Raw Chart Data:", data);

            // Format portfolio values for the line series
            if (data.portfolioValues && data.portfolioValues.length > 0) {
                const formattedPortfolioValues = data.portfolioValues.map(d => ({
                    time: Math.floor(new Date(d.time).getTime() / 1000),
                    value: d.portfolio_value
                }));
                console.log("Formatted Portfolio Values:", formattedPortfolioValues);
                portfolioSeries.setData(formattedPortfolioValues);
            }

            // Format price data for candlestick series
            if (data.priceData && data.priceData.length > 0) {
                const formattedPriceData = data.priceData.map(d => ({
                    time: Math.floor(new Date(d.time || d.Date).getTime() / 1000),
                    open: parseFloat(d.open || d.Open),
                    high: parseFloat(d.high || d.High),
                    low: parseFloat(d.low || d.Low),
                    close: parseFloat(d.close || d.Close)
                }));
                console.log("Formatted Price Data:", formattedPriceData);
                candleSeries.setData(formattedPriceData);
            }

            // Initialize arrays for markers
            let allMarkers = [];

            // Add trade markers if they exist
            if (data.tradeData && data.tradeData.length > 0) {
                const tradeMarkers = data.tradeData.map(trade => ({
                    time: Math.floor(new Date(trade.time).getTime() / 1000),
                    position: trade.type === 'buy' ? 'belowBar' : 'aboveBar',
                    color: trade.type === 'buy' ? '#4caf50' : '#ef5350',  // Green for buy, Red for sell
                    shape: trade.type === 'buy' ? 'arrowUp' : 'arrowDown',
                    text: `${trade.type.toUpperCase()} ${trade.size} @ ${trade.price}`,
                    size: 2  // Slightly larger size for better visibility
                }));
                console.log("Trade Markers:", tradeMarkers);
                allMarkers = [...tradeMarkers];
            }

            // Add order markers if they exist
            if (data.orderData && data.orderData.length > 0) {
                const orderMarkers = data.orderData.map(order => ({
                    time: Math.floor(new Date(order.time).getTime() / 1000),
                    position: order.type === 'buy' ? 'belowBar' : 'aboveBar',
                    color: order.type === 'buy' ? '#4caf50' : '#ef5350',  // Green for buy, Red for sell
                    shape: order.type === 'buy' ? 'arrowUp' : 'arrowDown',  // Triangles instead of circles
                    text: `${order.type.toUpperCase()} ${order.size} @ ${order.price}`,
                    size: 2  // Slightly larger size for better visibility
                }));
                console.log("Order Markers:", orderMarkers);
                allMarkers = [...allMarkers, ...orderMarkers];
            }

            // Set all markers if we have any
            if (allMarkers.length > 0) {
                console.log("Setting All Markers:", allMarkers);
                candleSeries.setMarkers(allMarkers);
            }

            // Set the chart to fit the data
            chart.timeScale().fitContent();
        })
        .catch((error) => {
            console.error("Error fetching or processing chart data:", error);
            const chartContainer = document.getElementById('chart-container');
            chartContainer.innerHTML = `
                <div class="text-red-500 p-4">
                    Error loading chart: ${error.message}
                </div>
            `;
        });

    // Make the chart responsive
    window.addEventListener('resize', () => {
        chart.applyOptions({ width: chartContainer.clientWidth });
    });
});