document.addEventListener("DOMContentLoaded", function () {
    const chartContainer = document.getElementById('chart-container');
    chartContainer.style.position = 'block'; // Ensure relative positioning

    // Initialize the Lightweight Chart
    const chart = LightweightCharts.createChart(chartContainer, {
        height: 450,
        autoSize: true,
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

    const resizeObserver = new ResizeObserver(entries => {
        if (entries.length === 0 || entries[0].target !== chartContainer) {
            return;
        }
        const { width, height } = entries[0].contentRect;
        chart.resize(width, height);
    });
    resizeObserver.observe(chartContainer);

    // Add candlestick series (price chart)
    const candleSeries = chart.addCandlestickSeries({
        upColor: '#4caf50',
        downColor: '#ff5722',
        borderDownColor: '#ff5722',
        borderUpColor: '#4caf50',
        wickDownColor: '#ff5722',
        wickUpColor: '#4caf50',
        lastValueVisible: false,  // Hide the last value label
        priceLineVisible: false,  // Hide the price line
    });

    // Add portfolio balance series
    const portfolioSeries = chart.addLineSeries({
        color: '#D3D3D3',
        lineWidth: 2,
        priceScaleId: 'left',
        title: 'Portfolio Value',
        lastValueVisible: false,  // Hide the last value label
        priceLineVisible: false,  // Hide the price line
    });

    // Create and configure the tooltip element
    const toolTipElement = document.createElement('div');
    toolTipElement.className = 'floating-tooltip';
    chartContainer.appendChild(toolTipElement);
    toolTipElement.style.position = 'absolute';
    toolTipElement.style.display = 'none';
    toolTipElement.style.padding = '8px';
    toolTipElement.style.backgroundColor = 'rgba(0, 0, 0, 0.8)';
    toolTipElement.style.color = 'white';
    toolTipElement.style.borderRadius = '4px';
    toolTipElement.style.fontSize = '12px';
    toolTipElement.style.pointerEvents = 'none'; // Prevent tooltip from capturing mouse events

    // Subscribe to crosshair move to show/hide tooltip
    chart.subscribeCrosshairMove(param => {
        if (!param.time || param.point === undefined) {
            toolTipElement.style.display = 'none';
            return;
        }

        const markers = candleSeries.markers();
        if (!markers) {
            toolTipElement.style.display = 'none';
            return;
        }

        const currentTime = param.time;
        const marker = markers.find(m => m.time === currentTime);
        
        if (marker) {
            toolTipElement.style.display = 'block';
            toolTipElement.innerHTML = marker.tooltip;
            
            const yPrice = param.seriesPrices.get(candleSeries);
            const coordinate = candleSeries.priceToCoordinate(yPrice);
            const chartRect = chartContainer.getBoundingClientRect();
            const toolTipRect = toolTipElement.getBoundingClientRect();
            
            // Calculate tooltip position relative to chart container
            const tooltipX = param.point.x - toolTipRect.width / 2;
            let tooltipY;
            if (marker.position === 'aboveBar') {
                tooltipY = coordinate - toolTipRect.height - 10;
            } else {
                tooltipY = coordinate + 10;
            }

            // Ensure tooltip stays within the chart container
            const maxX = chartContainer.clientWidth - toolTipRect.width;
            const clampedX = Math.max(0, Math.min(tooltipX, maxX));

            const maxY = chartContainer.clientHeight - toolTipRect.height;
            const clampedY = Math.max(0, Math.min(tooltipY, maxY));

            toolTipElement.style.left = `${clampedX}px`;
            toolTipElement.style.top = `${clampedY}px`;
        } else {
            toolTipElement.style.display = 'none';
        }
    });

    // Fetch price and trade data from the API using the global URL
    fetch(window.BACKTEST_CHART_DATA_URL, {
        method: 'GET',
        headers: {
            'X-CSRFToken': window.CSRF_TOKEN,
            'Content-Type': 'application/json',
        },
        credentials: 'same-origin'  // This is important for including cookies
    })
    .then(response => response.json())
    .then(data => {
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
                text: '',
                tooltip: `${trade.type.toUpperCase()} ${trade.size} @ ${trade.price}`,
                size: 2
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
                text: '',
                tooltip: `${order.type.toUpperCase()} ${order.size} @ ${order.price}`,
                size: 2
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
    .catch(error => console.error('Error:', error));

    // Make the chart responsive
    window.addEventListener('resize', () => {
        const newWidth = chartContainer.getBoundingClientRect().width;
        chart.applyOptions({ width: newWidth });
    });
});