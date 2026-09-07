import { useEffect, useState } from "react";

import {
  Leaf,
  Droplets,
  ThermometerSun,
  MapPin,
  Sprout,
  TreePine,
  CloudSun,
  ArrowRight,
  ShieldCheck,
  Satellite,
  BrainCircuit,
  AlertTriangle,
} from "lucide-react";

import {
  MapContainer,
  TileLayer,
  CircleMarker,
  Popup,
  useMap,
  useMapEvents,
} from "react-leaflet";

import "leaflet/dist/leaflet.css";
import "./App.css";

function MapUpdater({ lat, lon }) {
  const map = useMap();

  useEffect(() => {
    const latitude = Number(lat);
    const longitude = Number(lon);

    if (
      !Number.isNaN(latitude) &&
      !Number.isNaN(longitude)
    ) {
      map.flyTo([latitude, longitude], 8, {
        duration: 1.2,
      });
    }
  }, [lat, lon, map]);

  return null;
}
function MapClickHandler({ setLat, setLon }) {
  useMapEvents({
    click(e) {
      const newLat = e.latlng.lat.toFixed(4);
      const newLon = e.latlng.lng.toFixed(4);

      setLat(newLat);
      setLon(newLon);
    },
  });

  return null;
}

function SpeciesImage({ scientificName, commonName }) {
  const [imageData, setImageData] = useState(null);
  const [imageLoading, setImageLoading] = useState(true);

  useEffect(() => {
    let active = true;

    async function loadImage() {
      setImageLoading(true);
      try {
        const response = await fetch(
          `https://gaia-ai-9gnm.onrender.com/species-image?name=${encodeURIComponent(scientificName)}`
        );
        if (!response.ok) throw new Error("Image lookup failed");
        const result = await response.json();
        if (active) setImageData(result);
      } catch (error) {
        console.warn(`No verified image for ${scientificName}`, error);
        if (active) setImageData(null);
      } finally {
        if (active) setImageLoading(false);
      }
    }

    loadImage();
    return () => {
      active = false;
    };
  }, [scientificName]);

  if (imageLoading) {
    return (
      <div className="species-photo-placeholder loading">
        <Sprout size={34} />
        <span>Finding verified species photo…</span>
      </div>
    );
  }

  if (!imageData?.image_url) {
    return (
      <div className="species-photo-placeholder">
        <Sprout size={34} />
        <strong>{commonName || scientificName}</strong>
        <span>No verified photo found</span>
      </div>
    );
  }

  return (
    <>
      <img
        src={imageData.image_url}
        alt={`${scientificName} plant`}
        loading="lazy"
        onError={(event) => {
          event.currentTarget.style.display = "none";
          const fallback = event.currentTarget.nextElementSibling;
          if (fallback) fallback.style.display = "flex";
        }}
      />
      <div className="species-photo-placeholder image-error-fallback" style={{ display: "none" }}>
        <Sprout size={34} />
        <strong>{commonName || scientificName}</strong>
        <span>Photo unavailable</span>
      </div>

      <div className="species-photo-credit">
        <span>{imageData.source}</span>
        {(imageData.creator || imageData.license) && (
          <small>
            {[imageData.creator, imageData.license].filter(Boolean).join(" · ")}
          </small>
        )}
      </div>
    </>
  );
}

function App() {
  const [lat, setLat] = useState("30.5085");
  const [lon, setLon] = useState("47.7804");

  const [loading, setLoading] = useState(false);

  const [riskData, setRiskData] = useState(null);
  const [speciesData, setSpeciesData] = useState(null);
  const [interventionData, setInterventionData] = useState(null);
  const [ecosystemData, setEcosystemData] = useState(null);
  const [aiData, setAiData] = useState(null);

  const [error, setError] = useState("");

  const analyzeLocation = async () => {
    setLoading(true);
    setError("");
    setRiskData(null);
    setSpeciesData(null);
    setInterventionData(null);
    setEcosystemData(null);
    setAiData(null);

    try {
      // Run the independent data requests together so the UI feels much faster.
      const [riskResponse, speciesResponse, interventionResponse, ecosystemResponse] =
        await Promise.all([
          fetch(`https://gaia-ai-9gnm.onrender.com/risk?lat=${lat}&lon=${lon}`),
          fetch(`https://gaia-ai-9gnm.onrender.com/species?lat=${lat}&lon=${lon}`),
          fetch(`https://gaia-ai-9gnm.onrender.com/intervention?lat=${lat}&lon=${lon}`),
          fetch(`https://gaia-ai-9gnm.onrender.com/ecosystem?lat=${lat}&lon=${lon}`),
        ]);

      if (
        !riskResponse.ok ||
        !speciesResponse.ok ||
        !interventionResponse.ok ||
        !ecosystemResponse.ok
      ) {
        throw new Error("Could not analyze this location.");
      }

      const [riskResult, speciesResult, interventionResult, ecosystemResult] =
        await Promise.all([
          riskResponse.json(),
          speciesResponse.json(),
          interventionResponse.json(),
          ecosystemResponse.json(),
        ]);

      setRiskData(riskResult);
      setSpeciesData(speciesResult);
      setInterventionData(interventionResult);
      setEcosystemData(ecosystemResult);

      // AI is requested after the scientific evidence is visible.
      // If AI fails, the evidence-grounded analysis still remains usable.
      try {
        const aiResponse = await fetch(
          `https://gaia-ai-9gnm.onrender.com/ai-analysis?lat=${lat}&lon=${lon}&limit=5`
        );
        if (aiResponse.ok) {
          setAiData(await aiResponse.json());
        }
      } catch (aiErr) {
        console.warn("GAIA AI reasoning unavailable:", aiErr);
      }
    } catch (err) {
      console.error(err);
      setError(
        "GAIA could not connect to the backend. Make sure FastAPI is running."
      );
    } finally {
      setLoading(false);
    }
  };

  const riskCards = riskData
    ? [
        {
          title: "Heat Stress",
          score: riskData.environmental_risk.heat_stress.score,
          level: riskData.environmental_risk.heat_stress.level,
          icon: <ThermometerSun size={22} />,
        },
        {
          title: "Water Stress",
          score: riskData.environmental_risk.water_stress.score,
          level: riskData.environmental_risk.water_stress.level,
          icon: <Droplets size={22} />,
        },
        {
          title: "Drought Pressure",
          score: riskData.environmental_risk.drought_pressure.score,
          level: riskData.environmental_risk.drought_pressure.level,
          icon: <CloudSun size={22} />,
        },
        {
          title: "Overall Climate Risk",
          score:
            riskData.environmental_risk.overall_climate_risk.score,
          level:
            riskData.environmental_risk.overall_climate_risk.level,
          icon: <ShieldCheck size={22} />,
        },
      ]
    : [];



  return (
    <div className="app-shell">
      {/* ================= NAVBAR ================= */}

      <header className="topbar">
        <div className="brand">
          <div className="brand-icon">
            <Leaf size={27} />
          </div>

          <div>
            <h1>GAIA</h1>
            <p>Environmental Intelligence</p>
          </div>
        </div>

        <nav>
          <a href="#home">Home</a>
          <a href="#analyze">Analyze</a>
          <a href="#intervention">Intervention</a>
           <a href="#ai">AI Verdict</a>
          <a href="#species">Species</a>
          <a href="#about">About</a>
        </nav>

        <button
          className="nav-cta"
          onClick={() => {
            document.getElementById("analyze")?.scrollIntoView({
              behavior: "smooth",
            });
          }}
        >
          Get Started
        </button>
      </header>

      <main>
        {/* ================= HERO ================= */}

        <section className="hero" id="home">
          <div className="hero-overlay"></div>

          <div className="hero-content">
            <span className="eyebrow">
              AI-powered ecosystem restoration
            </span>

            <h2>
              Restore smarter.
              <br />
              <span>Protect what matters.</span>
            </h2>

            <p className="hero-text">
              GAIA analyzes environmental stress, recommends suitable
              restoration species, and helps communities make smarter
              ecosystem decisions using real climate data.
            </p>

            <div className="hero-actions">
              <button
                className="primary-btn"
                onClick={() =>
                  document
                    .getElementById("analyze")
                    ?.scrollIntoView({
                      behavior: "smooth",
                    })
                }
              >
                Analyze a Location
                <ArrowRight size={18} />
              </button>

              <button
                className="secondary-btn"
                onClick={() =>
                  document
                    .getElementById("future")
                    ?.scrollIntoView({
                      behavior: "smooth",
                    })
                }
              >
                Explore the Vision
              </button>
            </div>

            <div className="hero-mini-grid">
              <div>
                <Leaf size={21} />
                <span>Data-driven restoration</span>
              </div>

              <div>
                <Droplets size={21} />
                <span>Water-aware decisions</span>
              </div>

              <div>
                <TreePine size={21} />
                <span>Species intelligence</span>
              </div>
            </div>
          </div>
        </section>

        {/* ================= ANALYSIS ================= */}

        <section
          className="analysis-section"
          id="analyze"
        >
          <div className="section-heading">
            <div>
              <span className="section-kicker">
                Environmental scan
              </span>

              <h3>Analyze any location</h3>
            </div>

            <p>
              Enter coordinates and GAIA will evaluate recent
              climate conditions using NASA POWER data.
            </p>
          </div>

          <div className="analysis-panel">
            <div className="coordinates-card">
              <div className="input-group">
                <label>
                  <MapPin size={17} />
                  Latitude
                </label>

                <input
                  type="number"
                  step="any"
                  value={lat}
                  onChange={(e) =>
                    setLat(e.target.value)
                  }
                />
              </div>

              <div className="input-group">
                <label>
                  <MapPin size={17} />
                  Longitude
                </label>

                <input
                  type="number"
                  step="any"
                  value={lon}
                  onChange={(e) =>
                    setLon(e.target.value)
                  }
                />
              </div>

              <button
                className="analyze-btn"
                onClick={analyzeLocation}
                disabled={loading}
              >
                {loading
                  ? "Analyzing..."
                  : "Analyze Location"}

                {!loading && (
                  <ArrowRight size={18} />
                )}
              </button>
            </div>

           <div className="map-card real-map-card">
  <MapContainer
    center={[Number(lat), Number(lon)]}
    zoom={8}
    scrollWheelZoom={true}
    className="gaia-map"
  >
    <TileLayer
      attribution="&copy; OpenStreetMap contributors"
      url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
    />

    <MapUpdater lat={lat} lon={lon} />

<MapClickHandler
  setLat={setLat}
  setLon={setLon}
/>

    <CircleMarker
      center={[Number(lat), Number(lon)]}
      radius={12}
      pathOptions={{
        color: "#ffffff",
        fillColor: "#2f7654",
        fillOpacity: 1,
        weight: 4,
      }}
    >
      <Popup>
        <strong>GAIA Selected Location</strong>
        <br />
        Latitude: {lat}
        <br />
        Longitude: {lon}
      </Popup>
    </CircleMarker>
  </MapContainer>

  <div className="map-label real-map-label">
    <strong>
      {lat}, {lon}
    </strong>
    <span>Selected location</span>
  </div>
</div>
          </div>

          {error && (
            <div className="error-box">
              {error}
            </div>
          )}

          {/* ================= RISK RESULTS ================= */}

          {riskData && (
            <>
              <div className="results-heading">
                <div>
                  <span className="section-kicker">
                    Environmental risk overview
                  </span>

                  <h3>
                    Current climate pressure
                  </h3>
                </div>

                <p>
                  Period: {riskData.period.start} →{" "}
                  {riskData.period.end}
                </p>
              </div>

              <div className="risk-grid">
                {riskCards.map((card) => (
                  <article
                    className="risk-card"
                    key={card.title}
                  >
                    <div className="risk-icon">
                      {card.icon}
                    </div>

                    <div className="risk-card-top">
                      <span>{card.title}</span>

                      <strong>
                        {card.score}
                      </strong>
                    </div>

                    <div className="risk-bar">
                      <div
                        className="risk-fill"
                        style={{
                          width: `${Math.min(
                            card.score,
                            100
                          )}%`,
                        }}
                      ></div>
                    </div>

                    <div className="risk-footer">
                      <span
                        className={`status ${card.level}`}
                      >
                        {card.level}
                      </span>

                      <small>/ 100</small>
                    </div>
                  </article>
                ))}
              </div>

              {/* ================= CLIMATE SNAPSHOT ================= */}

              <div className="climate-summary">
                <div className="climate-summary-title">
                  <CloudSun size={25} />

                  <div>
                    <span className="section-kicker">
                      NASA POWER inputs
                    </span>

                    <h4>Climate snapshot</h4>
                  </div>
                </div>

                <div className="climate-metrics">
                  <div>
                    <span>
                      Average Temperature
                    </span>

                    <strong>
                      {
                        riskData.inputs
                          .average_temperature_c
                      }{" "}
                      °C
                    </strong>
                  </div>

                  <div>
                    <span>
                      Maximum Temperature
                    </span>

                    <strong>
                      {
                        riskData.inputs
                          .maximum_temperature_c
                      }{" "}
                      °C
                    </strong>
                  </div>

                  <div>
                    <span>
                      Total Rainfall
                    </span>

                    <strong>
                      {
                        riskData.inputs
                          .total_rainfall_mm
                      }{" "}
                      mm
                    </strong>
                  </div>

                  <div>
                    <span>
                      Average Humidity
                    </span>

                    <strong>
                      {
                        riskData.inputs
                          .average_humidity_percent
                      }{" "}
                      %
                    </strong>
                  </div>
                </div>
              </div>
            </>
          )}
        </section>

        {/* ================= ECOSYSTEM ================= */}

        {ecosystemData && (
          <section className="ecosystem-section" id="ecosystem">
            <div className="section-heading">
              <div>
                <span className="section-kicker">ESA WorldCover · 10 m satellite intelligence</span>
                <h3>What kind of landscape is this?</h3>
              </div>
              <span className="source-pill">
                <Satellite size={16} />
                ESA WorldCover 2021
              </span>
            </div>

            <div className="ecosystem-card">
              <div className="ecosystem-identity">
                <div className="ecosystem-icon"><Satellite size={30} /></div>
                <div>
                  <span className="section-kicker">Detected land cover</span>
                  <h4>{ecosystemData.land_cover.class_name}</h4>
                  <p>
                    {ecosystemData.land_cover.ecosystem_interpretation
                      .replaceAll("_", " ")}
                  </p>
                </div>
                <strong className="class-code">
                  Class {ecosystemData.land_cover.class_code}
                </strong>
              </div>

              <div className="ecosystem-guidance">
                <div>
                  <span>GAIA focus</span>
                  <p>{ecosystemData.intervention_guidance.focus}</p>
                </div>
                <div>
                  <span>Do not assume</span>
                  <p>{ecosystemData.intervention_guidance.avoid}</p>
                </div>
              </div>

              <div className="evidence-strip">
                <ShieldCheck size={17} />
                <span>{ecosystemData.confidence_note}</span>
              </div>
            </div>
          </section>
        )}

        {/* ================= INTERVENTION ================= */}

        {interventionData && (
          <section
            className="intervention-section"
            id="intervention"
          >
            <div className="section-heading">
              <div>
                <span className="section-kicker">
                  GAIA Intervention Engine
                </span>

                <h3>
                  Recommended intervention strategy
                </h3>
              </div>

              <span className="intervention-priority">
                {
                  interventionData
                    .recommended_intervention
                    .priority
                }{" "}
                Priority
              </span>
            </div>

            <div className="intervention-card">
              <div className="intervention-main">
                <div className="intervention-icon">
                  <Leaf size={28} />
                </div>

                <div>
                  <span className="section-kicker">
                    Best environmental response
                  </span>

                  <h4>
                    {
                      interventionData
                        .recommended_intervention
                        .title
                    }
                  </h4>

                  <p>
                    {
                      interventionData
                        .recommended_intervention
                        .strategy
                    }
                  </p>
                </div>
              </div>

              <div className="intervention-columns">
                {/* RECOMMENDED ACTIONS */}

                <div className="intervention-actions">
                  <h5>
                    What GAIA recommends
                  </h5>

                  {interventionData.recommended_intervention.actions.map(
                    (action, index) => (
                      <div
                        className="intervention-item"
                        key={index}
                      >
                        <span className="action-dot">
                          ✓
                        </span>

                        <span>{action}</span>
                      </div>
                    )
                  )}
                </div>

                {/* AVOID */}

                <div className="intervention-avoid">
                  <h5>What to avoid</h5>

                  {interventionData.recommended_intervention.avoid.map(
                    (item, index) => (
                      <div
                        className="intervention-item"
                        key={index}
                      >
                        <span className="avoid-dot">
                          ×
                        </span>

                        <span>{item}</span>
                      </div>
                    )
                  )}
                </div>
              </div>

              <div className="intervention-disclaimer">
                <ShieldCheck size={17} />

                <span>
                  {interventionData.disclaimer}
                </span>
              </div>
            </div>
          </section>
        )}

        {/* ================= SPECIES ================= */}

        {speciesData && (
          <section
            className="species-section"
            id="species"
          >
            <div className="section-heading">
              <div>
                <span className="section-kicker">
                  GAIA Species Intelligence
                </span>

                <h3>
                  Climate-matched species candidates
                </h3>
              </div>

              <p>
                Ranked by heat tolerance,
                drought resilience, water
                efficiency, salinity tolerance
                and ecosystem value.
              </p>
            </div>

            <div className="species-grid">
              {speciesData.recommendation.top_species.map(
                (species, index) => (
                  <article
                    className="species-card"
                    key={
                      species.scientific_name
                    }
                  >
                    <div className="species-image-wrap">
                      <SpeciesImage
                        scientificName={species.scientific_name}
                        commonName={species.common_name}
                      />

                      <div className="rank-badge">
                        #{index + 1}
                      </div>

                      <div className="score-badge">
                        {species.gaia_score}
                        /100
                      </div>
                    </div>

                    <div className="species-content">
                      <span className="species-tag">
                        <Sprout size={15} />
                        Climate candidate
                      </span>

                      <h4>
                        {species.common_name}
                      </h4>

                      <p className="scientific-name">
                        {
                          species.scientific_name
                        }
                      </p>

                      <div className="reason-list">
                        {species.reasons
                          .slice(0, 4)
                          .map((reason) => (
                            <div key={reason}>
                              <span className="check-dot">
                                ✓
                              </span>

                              <span>
                                {reason}
                              </span>
                            </div>
                          ))}
                      </div>

                      <div className="tag-row">
                        {species.best_for
                          .slice(0, 3)
                          .map((tag) => (
                            <span key={tag}>
                              {tag}
                            </span>
                          ))}
                      </div>

                      {species.warnings &&
                        species.warnings.length >
                          0 && (
                          <div className="species-warning">
                            <ShieldCheck
                              size={15}
                            />

                            <span>
                              {
                                species
                                  .warnings[0]
                              }
                            </span>
                          </div>
                        )}
                    </div>
                  </article>
                )
              )}
            </div>

            <div className="species-note">
              <Leaf size={20} />

              <p>
                {speciesData.important_note}
              </p>
            </div>
          </section>
        )}

        {/* ================= AI DECISION ================= */}

        {aiData?.ai_analysis && (
          <section className="ai-section" id="ai">
            <div className="section-heading">
              <div>
                <span className="section-kicker">GAIA Hybrid AI Decision Engine</span>
                <h3>Evidence-grounded AI verdict</h3>
              </div>
              <span className={`confidence-pill ${aiData.ai_analysis.confidence}`}>
                {aiData.ai_analysis.confidence} confidence
              </span>
            </div>

            <div className="ai-decision-card">
              <div className="ai-decision-top">
                <div className="ai-icon"><BrainCircuit size={30} /></div>
                <div>
                  <span>Best climate candidate</span>
                  <h4>
                    {aiData.ai_analysis.best_climate_candidate?.scientific_name ||
                      aiData.ai_analysis.scientific_name ||
                      "Candidate under review"}
                  </h4>
                  <p>
                    {aiData.ai_analysis.best_climate_candidate?.why ||
                      aiData.ai_analysis.why}
                  </p>
                </div>
              </div>

              {aiData.ai_analysis.ecosystem_verdict && (
                <div
                  className={`ecosystem-verdict ${
                    aiData.ai_analysis.ecosystem_verdict.recommend_for_ecosystem
                      ? "approved"
                      : "hold"
                  }`}
                >
                  <ShieldCheck size={23} />
                  <div>
                    <span>Ecosystem verdict</span>
                    <h5>{aiData.ai_analysis.ecosystem_verdict.statement}</h5>
                    <p>{aiData.ai_analysis.ecosystem_verdict.reason}</p>
                  </div>
                </div>
              )}

              <div className="ai-detail-grid">
                <div>
                  <h5>Trade-offs GAIA considered</h5>
                  {(aiData.ai_analysis.tradeoffs || []).slice(0, 4).map((item, index) => (
                    <p key={index}>• {item}</p>
                  ))}
                </div>
                <div>
                  <h5>Evidence still needed</h5>
                  {(aiData.ai_analysis.missing_data || []).slice(0, 6).map((item, index) => (
                    <span className="missing-chip" key={index}>{item}</span>
                  ))}
                </div>
              </div>

              <div className="ai-summary">
                <BrainCircuit size={18} />
                <p>{aiData.ai_analysis.decision_summary}</p>
              </div>

              <div className="ai-sources">
                <span>NASA POWER</span>
                <span>ESA WorldCover</span>
                <span>FAO ECOCROP</span>
                <span>GBIF</span>
                <span>OpenAI reasoning</span>
              </div>
            </div>
          </section>
        )}

        {/* ================= FUTURE ================= */}

        <section
          className="future-section"
          id="future"
        >
          <div>
            <span className="section-kicker">
              Next generation restoration
            </span>

            <h3>
              From environmental diagnosis to
              action.
            </h3>

            <p>
              GAIA is being designed to compare
              restoration strategies, simulate
              environmental interventions, and
              recommend the highest-impact path
              for each region.
            </p>
          </div>

          <button
            className="primary-btn"
            onClick={() =>
              document
                .getElementById("intervention")
                ?.scrollIntoView({
                  behavior: "smooth",
                })
            }
          >
            Explore Interventions
            <ArrowRight size={18} />
          </button>
        </section>
      </main>

      {/* ================= FOOTER ================= */}

      <footer id="about">
        <div className="footer-brand">
          <Leaf size={20} />
          <strong>GAIA</strong>
        </div>

        <p>
          Explainable environmental
          intelligence for climate-resilient
          ecosystem restoration.
        </p>
      </footer>
    </div>
  );
}

export default App;
 