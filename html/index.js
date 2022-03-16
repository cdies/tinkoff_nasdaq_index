// https://www.youtube.com/watch?v=3KPW9VMyBHA
// https://codesandbox.io/examples/package/lightweight-charts
const log = console.log;

const chartProperties = {
  width: 1450,
  height: 600,
  layout: {
    backgroundColor: '#25313C',
    textColor: '#D8E1E8',
  },
  grid: {
    vertLines: {
      color: '#394B59',
    },
    horzLines: {
      color: '#394B59',
    },
  },
  priceScale: {
    borderColor: '#8A9BA8',
  },
  crosshair: {
    mode: 1,
  },
  timeScale: {
    borderColor: '#8A9BA8',
    timeVisible: true,
    secondsVisible: false,
  }
};

const domElement = document.getElementById('nasdaq_chart');
const chart = LightweightCharts.createChart(domElement, chartProperties);
const candleSeries = chart.addCandlestickSeries(
  {
    upColor: '#14835C',
    borderUpColor: '#0BB06D',
    wickUpColor: '#0BB06D',

    downColor: '#9D2B38',
    borderDownColor: '#D32836',
    wickDownColor: '#D32836',
  }
);


let markers = [];
function get_marker(time, text) {
  return [
    {
      time: time,
      position: 'belowBar',
      color: 'yellow',
      shape: 'arrowUp',
    },
    {
      time: time,
      position: 'aboveBar',
      color: 'yellow',
      shape: 'arrowDown',
      text: text,
    }
  ]
}


// History
fetch(`http://127.0.0.1:8000/api/historical_candles/2`)
  .then(res => res.json())
  .then(json_str => JSON.parse(json_str))
  .then(data => {

    for (let i = 0; i < data.length; ++i) {
      orig_time = new Date(data[i].time);
      data[i].time = data[i].time / 1000 + 10800; // localize to Moscow time 60*60*3 = 10800 

      minutes = orig_time.getMinutes();
      hours = orig_time.getHours();

      if (hours == 10 && minutes == 0) {
        marker = get_marker(data[i].time, 'O') // 10:00
        markers.push(...marker)
      }
      else if (hours == 18 && minutes == 45) {
        marker = get_marker(data[i].time, 'C') // 18:45
        markers.push(...marker)
      }

    };

    // log(data);
    candleSeries.setData(data);

    candleSeries.setMarkers(markers);

  })
  .catch(err => log(err))


// Dynamic Chart
setInterval(function () {
  fetch(`http://127.0.0.1:8000/api/currient_candle`)
    .then(res => res.json())
    .then(json_str => JSON.parse(json_str))
    .then(data => {
      log(data);

      orig_time = new Date(data.time);
      data.time = data.time / 1000 + 10800 // localize to Moscow time 60*60*3 = 10800

      minutes = orig_time.getMinutes();
      hours = orig_time.getHours();


      if (hours == 10 && minutes == 0) {
        if (markers[markers.length - 1].time != data.time) {
          marker = get_marker(data.time, 'O') // 10:00
          markers.push(...marker)
          candleSeries.setMarkers(markers);
        }
      }

      else if (hours == 18 && minutes == 45) {
        if (markers[markers.length - 1].time != data.time) {
          marker = get_marker(data.time, 'C') // 18:45
          markers.push(...marker)
          candleSeries.setMarkers(markers);
        }
      }


      candleSeries.update(data);
    })
    .catch(err => log(err))
}, 1000); // <-- Увеличивай интервал здесь!
/*

Если задержку не поставить, будет очень много ошибок.
Подробнее про ограничения см здесь: https://tinkoff.github.io/investAPI/limits/
1000 - это 1 секунда

С этим параметром можно играть, увеличивая или уменьшая его.

*/