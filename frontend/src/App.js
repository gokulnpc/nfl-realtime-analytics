import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import './App.css';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

function App() {
  const [mode, setMode] = useState('manual');
  const [apiStatus, setApiStatus] = useState({ connected: false, models: 0 });
  const [predictions, setPredictions] = useState(null);
  const [kinesisStatus, setKinesisStatus] = useState(null);
  const [pysparkPlays, setPysparkPlays] = useState([]);
  const [dataSource, setDataSource] = useState('pyspark'); // 'pyspark' or 'kinesis'
  const [isPolling, setIsPolling] = useState(false);
  
  const [playInput, setPlayInput] = useState({
    down: 1,
    ydstogo: 10,
    yardline_100: 75,
    qtr: 1,
    half_seconds_remaining: 900,
    score_differential: 0,
    posteam: 'KC',
    defteam: 'SF'
  });

  // Demo plays
  const demoPlays = [
    { down: 1, ydstogo: 10, yardline_100: 75, qtr: 1, half_seconds_remaining: 900, score_differential: 0, posteam: 'KC', defteam: 'SF', description: 'Opening drive' },
    { down: 3, ydstogo: 2, yardline_100: 45, qtr: 2, half_seconds_remaining: 600, score_differential: -7, posteam: 'BUF', defteam: 'MIA', description: 'Short yardage situation' },
    { down: 1, ydstogo: 10, yardline_100: 15, qtr: 3, half_seconds_remaining: 450, score_differential: 3, posteam: 'PHI', defteam: 'DAL', description: 'Red zone opportunity' },
    { down: 4, ydstogo: 1, yardline_100: 35, qtr: 4, half_seconds_remaining: 180, score_differential: -4, posteam: 'SF', defteam: 'KC', description: 'Go for it on 4th!' },
    { down: 2, ydstogo: 8, yardline_100: 98, qtr: 4, half_seconds_remaining: 45, score_differential: -6, posteam: 'KC', defteam: 'SF', description: 'Goal line, game on the line!' },
    { down: 3, ydstogo: 15, yardline_100: 35, qtr: 4, half_seconds_remaining: 120, score_differential: -7, posteam: 'DAL', defteam: 'PHI', description: '3rd and long, trailing' }
  ];

  // Check API health
  useEffect(() => {
    const checkHealth = async () => {
      try {
        const response = await axios.get(`${API_URL}/health`);
        setApiStatus({
          connected: true,
          models: response.data.models_loaded,
          pysparkAvailable: response.data.pyspark_output_available
        });
      } catch (error) {
        setApiStatus({ connected: false, models: 0 });
      }
    };
    checkHealth();
    const interval = setInterval(checkHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  // Get predictions
  const getPredictions = useCallback(async (play) => {
    try {
      const response = await axios.post(`${API_URL}/predict`, {
        ...play,
        shotgun: 1,
        no_huddle: 0,
        defenders_in_box: 6,
        number_of_pass_rushers: 4,
        posteam_type: 'home',
        goal_to_go: play.yardline_100 <= play.ydstogo ? 1 : 0
      });
      setPredictions({ ...response.data, ...play });
    } catch (error) {
      console.error('Prediction error:', error);
    }
  }, []);

  // Fetch from PySpark or Kinesis
  const fetchLiveData = useCallback(async () => {
    try {
      const endpoint = dataSource === 'pyspark' 
        ? `${API_URL}/pyspark/predictions`
        : `${API_URL}/kinesis/fetch`;
      
      const response = await axios.get(endpoint);
      
      if (response.data.plays && response.data.plays.length > 0) {
        setPysparkPlays(response.data.plays);
        const latest = response.data.plays[response.data.plays.length - 1];
        setPredictions(latest);
        setKinesisStatus({
          connected: true,
          source: response.data.source,
          playCount: response.data.play_count
        });
      }
    } catch (error) {
      console.error('Fetch error:', error);
    }
  }, [dataSource]);

  // Polling for live mode
  useEffect(() => {
    let interval;
    if (mode === 'live' && isPolling) {
      fetchLiveData();
      interval = setInterval(fetchLiveData, 3000);
    }
    return () => clearInterval(interval);
  }, [mode, isPolling, fetchLiveData]);

  // Demo mode
  const [demoIndex, setDemoIndex] = useState(0);
  useEffect(() => {
    let interval;
    if (mode === 'demo') {
      getPredictions(demoPlays[demoIndex]);
      interval = setInterval(() => {
        setDemoIndex(prev => {
          const next = (prev + 1) % demoPlays.length;
          getPredictions(demoPlays[next]);
          return next;
        });
      }, 4000);
    }
    return () => clearInterval(interval);
  }, [mode, demoIndex, getPredictions]);

  // Manual mode handler
  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setPlayInput(prev => ({ ...prev, [name]: parseInt(value) || value }));
  };

  const handleManualPredict = () => {
    getPredictions(playInput);
  };

  return (
    <div className="app">
      <header className="header">
        <h1>🏈 NFL Real-Time Analytics</h1>
        <p>Expected Points • Scoring Probability • Play Prediction</p>
        <div className={`api-status ${apiStatus.connected ? 'connected' : 'disconnected'}`}>
          {apiStatus.connected ? `✅ API Connected | Models: ${apiStatus.models}/4` : '❌ API Disconnected'}
          {apiStatus.pysparkAvailable && ' | PySpark ✓'}
        </div>
      </header>

      <nav className="mode-selector">
        <button className={mode === 'manual' ? 'active' : ''} onClick={() => setMode('manual')}>
          ⚙️ Manual Input
        </button>
        <button className={mode === 'demo' ? 'active' : ''} onClick={() => setMode('demo')}>
          🎬 Demo Mode
        </button>
        <button 
          className={mode === 'live' ? 'active live' : ''} 
          onClick={() => { setMode('live'); setIsPolling(true); }}
        >
          🔴 Live Stream
        </button>
        {mode === 'live' && (
          <button className="stop-btn" onClick={() => setIsPolling(false)}>
            ⏹ Stop
          </button>
        )}
      </nav>

      {mode === 'live' && (
        <div className="live-banner">
          <div className="source-toggle">
            <button 
              className={dataSource === 'pyspark' ? 'active' : ''} 
              onClick={() => setDataSource('pyspark')}
            >
              🔥 PySpark
            </button>
            <button 
              className={dataSource === 'kinesis' ? 'active' : ''} 
              onClick={() => setDataSource('kinesis')}
            >
              📡 Kinesis Direct
            </button>
          </div>
          {kinesisStatus?.connected && (
            <span>
              🟢 Source: {kinesisStatus.source} | 📊 {kinesisStatus.playCount} plays | Polling every 3s...
            </span>
          )}
        </div>
      )}

      <main className="dashboard">
        {/* Left Panel - Input/Live Feed */}
        <section className="panel input-panel">
          <h2>📍 {mode === 'live' ? 'Live Feed' : mode === 'demo' ? 'Demo Play' : 'Current Play'}</h2>
          
          {mode === 'manual' ? (
            <div className="manual-inputs">
              <div className="input-grid">
                <div className="input-group">
                  <label>Down</label>
                  <select name="down" value={playInput.down} onChange={handleInputChange}>
                    {[1,2,3,4].map(d => <option key={d} value={d}>{d}</option>)}
                  </select>
                </div>
                <div className="input-group">
                  <label>Distance</label>
                  <input type="number" name="ydstogo" value={playInput.ydstogo} onChange={handleInputChange} min="1" max="99" />
                </div>
                <div className="input-group">
                  <label>Yard Line</label>
                  <input type="number" name="yardline_100" value={playInput.yardline_100} onChange={handleInputChange} min="1" max="99" />
                </div>
                <div className="input-group">
                  <label>Quarter</label>
                  <select name="qtr" value={playInput.qtr} onChange={handleInputChange}>
                    {[1,2,3,4].map(q => <option key={q} value={q}>Q{q}</option>)}
                  </select>
                </div>
              </div>
              <button className="predict-btn" onClick={handleManualPredict}>Get Predictions</button>
            </div>
          ) : (
            <div className="play-display">
              {predictions && (
                <>
                  <div className="matchup">
                    <span className="team">{predictions.posteam || 'OFF'}</span>
                    <span className="vs">vs</span>
                    <span className="team">{predictions.defteam || 'DEF'}</span>
                  </div>
                  <div className="situation">
                    {predictions.description && <p className="description">{predictions.description}</p>}
                  </div>
                  <div className="play-info-grid">
                    <div className="info-box"><label>Down</label><span>{predictions.down}</span></div>
                    <div className="info-box"><label>Distance</label><span>{predictions.ydstogo}</span></div>
                    <div className="info-box"><label>Yard Line</label><span>{100 - predictions.yardline_100}</span></div>
                    <div className="info-box"><label>Quarter</label><span>Q{predictions.qtr}</span></div>
                  </div>
                </>
              )}
            </div>
          )}
          
          {mode === 'live' && pysparkPlays.length > 0 && (
            <div className="recent-plays">
              <h3>Recent Plays ({dataSource === 'pyspark' ? 'PySpark' : 'Kinesis'})</h3>
              <ul>
                {pysparkPlays.slice(-5).reverse().map((play, idx) => (
                  <li key={idx}>{play.down}&{play.ydstogo} at {100-(play.yardline_100 || 0)} - Q{play.qtr}</li>
                ))}
              </ul>
            </div>
          )}
        </section>

        {/* Center Panel - Predictions */}
        <section className="panel predictions-panel">
          <h2>📊 Real-Time Predictions 
            <span className="badge">{dataSource === 'pyspark' ? '🔥 PySpark' : '✓ ML Models'}</span>
          </h2>
          
          {predictions ? (
            <>
              <div className="ep-display">
                <label>Expected Points</label>
                <span className="ep-value">{predictions.expected_points?.toFixed(2) || '0.00'}</span>
              </div>
              
              <div className="scoring-probs">
                <h3>Scoring Probability</h3>
                <div className="prob-bar">
                  <span>🏈 Touchdown</span>
                  <div className="bar-container">
                    <div className="bar td" style={{width: `${(predictions.td_prob || 0) * 100}%`}}></div>
                  </div>
                  <span>{((predictions.td_prob || 0) * 100).toFixed(1)}%</span>
                </div>
                <div className="prob-bar">
                  <span>🥅 Field Goal</span>
                  <div className="bar-container">
                    <div className="bar fg" style={{width: `${(predictions.fg_prob || 0) * 100}%`}}></div>
                  </div>
                  <span>{((predictions.fg_prob || 0) * 100).toFixed(1)}%</span>
                </div>
                <div className="prob-bar">
                  <span>❌ No Score</span>
                  <div className="bar-container">
                    <div className="bar ns" style={{width: `${(predictions.no_score_prob || 0) * 100}%`}}></div>
                  </div>
                  <span>{((predictions.no_score_prob || 0) * 100).toFixed(1)}%</span>
                </div>
              </div>
            </>
          ) : (
            <p className="no-data">Select a mode or enter play data</p>
          )}
        </section>

        {/* Right Panel - Analysis */}
        <section className="panel analysis-panel">
          <h2>🎯 Play Analysis</h2>
          
          {predictions ? (
            <>
              <div className="play-type">
                <label>Predicted Play Type</label>
                <span className="play-type-value">{predictions.predicted_play || 'Pass'}</span>
                <div className="run-pass-split">
                  <div className="split-item">
                    <span>Run</span>
                    <span className="pct">{((predictions.run_probability || 0.3) * 100).toFixed(1)}%</span>
                  </div>
                  <div className="split-item">
                    <span>Pass</span>
                    <span className="pct pass">{((predictions.pass_probability || 0.7) * 100).toFixed(1)}%</span>
                  </div>
                </div>
              </div>
              
              <div className="pressure">
                <label>Pressure Prediction</label>
                <div className={`pressure-indicator ${predictions.pressure_risk || 'medium'}`}>
                  <span className="pressure-value">{((predictions.pressure_probability || 0.4) * 100).toFixed(1)}%</span>
                  <span className="risk-label">{(predictions.pressure_risk || 'MEDIUM').toUpperCase()} RISK</span>
                </div>
              </div>
              
              {dataSource === 'pyspark' && mode === 'live' && (
                <div className="pyspark-badge">
                  <span>🔥 Processed by PySpark</span>
                </div>
              )}
            </>
          ) : (
            <p className="no-data">Waiting for data...</p>
          )}
        </section>
      </main>

      <footer className="footer">
        <p>Expected Points: R² = 99.5% | Scoring Probability: R² = 94-99% | Play Classifier: 68.8% | Pressure: 61.1% AUC</p>
        <p>Data: 9 NFL Seasons (2016-2024) • ~310K plays • PySpark + Kinesis + XGBoost</p>
      </footer>
    </div>
  );
}

export default App;
