import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './App.css';

const API_URL = 'http://127.0.0.1:8000';

const DEMO_PLAYS = [
  { down: 1, ydstogo: 10, yardline_100: 75, qtr: 1, half_seconds_remaining: 1800, score_differential: 0, goal_to_go: 0, posteam_type: "home", desc: "1st & 10 at own 25 - Opening drive" },
  { down: 3, ydstogo: 8, yardline_100: 45, qtr: 1, half_seconds_remaining: 1500, score_differential: 0, goal_to_go: 0, posteam_type: "home", desc: "3rd & 8 at midfield" },
  { down: 1, ydstogo: 10, yardline_100: 20, qtr: 2, half_seconds_remaining: 900, score_differential: 7, goal_to_go: 0, posteam_type: "home", desc: "1st & 10 - RED ZONE!" },
  { down: 1, ydstogo: 5, yardline_100: 5, qtr: 2, half_seconds_remaining: 600, score_differential: 7, goal_to_go: 1, posteam_type: "home", desc: "1st & Goal at the 5!" },
  { down: 3, ydstogo: 15, yardline_100: 65, qtr: 4, half_seconds_remaining: 120, score_differential: -4, goal_to_go: 0, posteam_type: "away", desc: "3rd & 15 - Trailing, 2 min left!" },
  { down: 1, ydstogo: 2, yardline_100: 2, qtr: 4, half_seconds_remaining: 30, score_differential: -4, goal_to_go: 1, posteam_type: "away", desc: "1st & Goal at 2 - GAME ON THE LINE!" },
];

function App() {
  const [prediction, setPrediction] = useState(null);
  const [loading, setLoading] = useState(false);
  const [apiStatus, setApiStatus] = useState(null);
  const [mode, setMode] = useState('manual');
  const [demoIndex, setDemoIndex] = useState(0);
  const [demoRunning, setDemoRunning] = useState(false);
  
  const [playData, setPlayData] = useState({
    down: 1, ydstogo: 10, yardline_100: 75, qtr: 1,
    half_seconds_remaining: 900, score_differential: 0,
    goal_to_go: 0, posteam_type: 'home',
    defenders_in_box: 6, number_of_pass_rushers: 4
  });

  useEffect(() => {
    checkApiHealth();
  }, []);

  useEffect(() => {
    if (demoRunning && mode === 'demo') {
      const timer = setTimeout(() => {
        const nextIndex = (demoIndex + 1) % DEMO_PLAYS.length;
        setDemoIndex(nextIndex);
        getPrediction(DEMO_PLAYS[nextIndex]);
      }, 4000);
      return () => clearTimeout(timer);
    }
  }, [demoRunning, demoIndex, mode]);

  const checkApiHealth = async () => {
    try {
      const response = await axios.get(`${API_URL}/health`);
      setApiStatus(response.data);
    } catch (error) {
      setApiStatus({ status: 'offline' });
    }
  };

  const getPrediction = async (data) => {
    setLoading(true);
    try {
      const response = await axios.post(`${API_URL}/predict`, data);
      setPrediction(response.data);
    } catch (error) {
      console.error('Prediction error:', error);
    }
    setLoading(false);
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setPlayData(prev => ({
      ...prev,
      [name]: name === 'posteam_type' ? value : parseInt(value) || 0
    }));
  };

  const handlePredict = () => getPrediction(playData);

  const startDemo = () => {
    setMode('demo');
    setDemoIndex(0);
    setDemoRunning(true);
    getPrediction(DEMO_PLAYS[0]);
  };

  const stopDemo = () => setDemoRunning(false);

  const formatPercent = (value) => `${(value * 100).toFixed(1)}%`;

  return (
    <div className="app">
      <header className="header">
        <h1>🏈 NFL Real-Time Analytics</h1>
        <p>Expected Points • Scoring Probability • Play Prediction</p>
        <div>
          {apiStatus?.status === 'healthy' ? (
            <span className="status-badge status-online">
              ✅ API Connected | Models: {Object.values(apiStatus.models).filter(Boolean).length}/4
            </span>
          ) : (
            <span className="status-badge status-offline">
              ❌ API Offline - Start the backend
            </span>
          )}
        </div>
      </header>

      <div className="mode-buttons">
        <button onClick={() => setMode('manual')}
          className={`mode-btn ${mode === 'manual' ? 'mode-btn-active' : 'mode-btn-inactive'}`}>
          ⚙️ Manual Input
        </button>
        <button onClick={startDemo}
          className={`mode-btn ${mode === 'demo' ? 'mode-btn-active' : 'mode-btn-inactive'}`}>
          🎮 Demo Mode
        </button>
        {demoRunning && (
          <button onClick={stopDemo} className="mode-btn mode-btn-stop">
            ⏹️ Stop
          </button>
        )}
      </div>

      <div className="grid-container">
        {/* Input Panel */}
        <div className="card">
          <h2>{mode === 'demo' ? '📍 Current Play' : '📝 Game Situation'}</h2>
          
          {mode === 'demo' ? (
            <div>
              <div className="demo-description">
                <p>{DEMO_PLAYS[demoIndex].desc}</p>
              </div>
              <div className="stats-grid">
                <div className="stat-box">
                  <span>Down</span>
                  <p>{DEMO_PLAYS[demoIndex].down}</p>
                </div>
                <div className="stat-box">
                  <span>Distance</span>
                  <p>{DEMO_PLAYS[demoIndex].ydstogo}</p>
                </div>
                <div className="stat-box">
                  <span>Yard Line</span>
                  <p>{100 - DEMO_PLAYS[demoIndex].yardline_100}</p>
                </div>
                <div className="stat-box">
                  <span>Quarter</span>
                  <p>Q{DEMO_PLAYS[demoIndex].qtr}</p>
                </div>
              </div>
              <p style={{textAlign: 'center', color: '#94a3b8', marginTop: '16px'}}>
                Play {demoIndex + 1} of {DEMO_PLAYS.length}
              </p>
            </div>
          ) : (
            <div>
              <div className="input-grid">
                <div className="input-group">
                  <label>Down</label>
                  <select name="down" value={playData.down} onChange={handleInputChange}>
                    {[1,2,3,4].map(d => <option key={d} value={d}>{d}</option>)}
                  </select>
                </div>
                <div className="input-group">
                  <label>Distance</label>
                  <input type="number" name="ydstogo" value={playData.ydstogo} onChange={handleInputChange} />
                </div>
                <div className="input-group">
                  <label>Yard Line</label>
                  <input type="number" name="yardline_100" value={playData.yardline_100} onChange={handleInputChange} />
                </div>
                <div className="input-group">
                  <label>Quarter</label>
                  <select name="qtr" value={playData.qtr} onChange={handleInputChange}>
                    {[1,2,3,4].map(q => <option key={q} value={q}>{q}</option>)}
                  </select>
                </div>
                <div className="input-group">
                  <label>Score Diff</label>
                  <input type="number" name="score_differential" value={playData.score_differential} onChange={handleInputChange} />
                </div>
                <div className="input-group">
                  <label>Time (sec)</label>
                  <input type="number" name="half_seconds_remaining" value={playData.half_seconds_remaining} onChange={handleInputChange} />
                </div>
              </div>
              <div className="checkbox-group">
                <input type="checkbox" id="goal_to_go"
                  checked={playData.goal_to_go === 1}
                  onChange={(e) => setPlayData(prev => ({...prev, goal_to_go: e.target.checked ? 1 : 0}))} />
                <label htmlFor="goal_to_go">Goal to Go</label>
              </div>
              <button onClick={handlePredict} className="predict-btn">
                {loading ? '⏳ Predicting...' : '🎯 Get Prediction'}
              </button>
            </div>
          )}
        </div>

        {/* Real-Time Predictions */}
        <div className="card">
          <h2>📊 Real-Time Predictions <span className="badge-green">✓ ESPN Ready</span></h2>
          
          {prediction ? (
            <div>
              <div className="ep-box">
                <p>Expected Points</p>
                <p>{prediction.expected_points}</p>
              </div>
              
              <div className="prob-section">
                <h3>Scoring Probability</h3>
                
                <div className="prob-item">
                  <div className="prob-header">
                    <span>🏈 Touchdown</span>
                    <span className="text-green">{formatPercent(prediction.td_prob)}</span>
                  </div>
                  <div className="prob-bar">
                    <div className="prob-fill prob-fill-green" style={{width: `${prediction.td_prob * 100}%`}}></div>
                  </div>
                </div>
                
                <div className="prob-item">
                  <div className="prob-header">
                    <span>🥅 Field Goal</span>
                    <span className="text-yellow">{formatPercent(prediction.fg_prob)}</span>
                  </div>
                  <div className="prob-bar">
                    <div className="prob-fill prob-fill-yellow" style={{width: `${prediction.fg_prob * 100}%`}}></div>
                  </div>
                </div>
                
                <div className="prob-item">
                  <div className="prob-header">
                    <span>❌ No Score</span>
                    <span className="text-red">{formatPercent(prediction.no_score_prob)}</span>
                  </div>
                  <div className="prob-bar">
                    <div className="prob-fill prob-fill-red" style={{width: `${prediction.no_score_prob * 100}%`}}></div>
                  </div>
                </div>
                
                <div className="prob-item">
                  <div className="prob-header">
                    <span>🔄 Opp TD</span>
                    <span className="text-purple">{formatPercent(prediction.opp_td_prob)}</span>
                  </div>
                  <div className="prob-bar">
                    <div className="prob-fill prob-fill-purple" style={{width: `${prediction.opp_td_prob * 100}%`}}></div>
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="empty-state">
              <p>📊</p>
              <p>Enter play data or start demo</p>
            </div>
          )}
        </div>

        {/* Play Type & Pressure */}
        <div className="card">
          <h2>🎯 Play Analysis <span className="badge-yellow">⚠️ Post-snap</span></h2>
          
          {prediction ? (
            <div>
              <p style={{color: '#94a3b8', marginBottom: '8px'}}>Predicted Play Type</p>
              <div className="play-type-box">
                <p>{prediction.predicted_play.replace('_', ' ')}</p>
              </div>
              
              <div className="run-pass-grid">
                <div className="run-pass-box">
                  <p>Run</p>
                  <p className="text-orange">{formatPercent(prediction.run_probability)}</p>
                </div>
                <div className="run-pass-box">
                  <p>Pass</p>
                  <p className="text-blue">{formatPercent(prediction.pass_probability)}</p>
                </div>
              </div>
              
              <p style={{color: '#94a3b8', marginBottom: '8px'}}>Pressure Prediction</p>
              <div className={`pressure-box ${
                prediction.pressure_risk === 'high' ? 'pressure-high' :
                prediction.pressure_risk === 'medium' ? 'pressure-medium' : 'pressure-low'
              }`}>
                <p>{formatPercent(prediction.pressure_probability)}</p>
                <p>{prediction.pressure_risk === 'high' ? '🔴 HIGH RISK' :
                    prediction.pressure_risk === 'medium' ? '🟡 MEDIUM RISK' : '🟢 LOW RISK'}</p>
              </div>
              
              <div className="disclaimer">
                ⚠️ Play type and pressure predictions use post-snap data which may not be available in true real-time.
              </div>
            </div>
          ) : (
            <div className="empty-state">
              <p>🎯</p>
              <p>Waiting for prediction...</p>
            </div>
          )}
        </div>
      </div>

      <footer className="footer">
        <p>Expected Points: R² = 99.5% | Scoring Probability: R² = 94-99% | Play Classifier: 68.8% | Pressure: 61.1% AUC</p>
        <p>Data: 9 NFL Seasons (2016-2024) • ~310K plays</p>
      </footer>
    </div>
  );
}

export default App;
