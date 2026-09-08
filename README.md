# 🌍 GAIA — AI Environmental Intervention Engine

> **Don't just predict Earth's future. Find the best way to change it.**

GAIA is an AI-powered environmental decision-support platform that transforms real-world climate and ecosystem data into actionable restoration strategies.

Instead of only asking **“What environmental risks exist here?”**, GAIA asks a more useful question:

> **“Given the conditions of this location, what intervention should we actually make — and why?”**

🌐 **Live Demo:** https://gaia-ai-frontend.onrender.com  
💻 **GitHub:** https://github.com/hawraa078/gaia-ai

---

## 🌱 The Problem

Climate change, drought, extreme heat, water scarcity, soil degradation, and ecosystem loss are interconnected problems.

Environmental data is increasingly available, but turning that data into a practical decision remains difficult.

For example:

- Should a degraded area actually be planted with trees?
- Which species could tolerate the local climate?
- Could planting the wrong species consume scarce water?
- Is the real problem vegetation loss — or water flow, salinity, agriculture, or urban heat?
- How can environmental interventions be explained instead of blindly generated?

GAIA was built to bridge the gap between **environmental data and environmental action**.

---

## 💡 What GAIA Does

A user selects a location using coordinates or the interactive map.

GAIA then:

1. 🌡️ Retrieves real climate observations.
2. ⚠️ Calculates interpretable environmental risk indicators.
3. 🛰️ Identifies the local land-cover context.
4. 🌿 Searches thousands of plant species for environmental compatibility.
5. 📍 Looks for geographic occurrence evidence.
6. 🧠 Evaluates whether climate suitability actually means ecological suitability.
7. 🛠️ Generates an ecosystem-aware intervention strategy.
8. 🤖 Uses AI to explain the decision, trade-offs, uncertainties, and missing evidence.
9. 📸 Retrieves verified species imagery with source and licensing information.

The result is not simply a prediction.

It is an **explainable environmental intervention recommendation**.

---

## ✨ Core Features

### 🌡️ Real Climate Intelligence

GAIA retrieves recent environmental observations using **NASA POWER**, including:

- Average temperature
- Maximum temperature
- Minimum temperature
- Rainfall
- Relative humidity

These measurements feed GAIA's environmental risk engine.

---

### ⚠️ Environmental Risk Engine

GAIA estimates:

- Heat stress
- Water stress
- Drought risk
- Overall environmental risk

The current MVP uses transparent heuristic scoring so users can understand how a result was produced.

It is intentionally presented as a decision-support indicator rather than a validated climate forecasting model.

---

### 🛰️ Ecosystem Intelligence

GAIA uses **ESA WorldCover** land-cover information to understand what kind of environment exists at the selected location.

Examples include:

- Tree cover
- Shrubland
- Grassland
- Cropland
- Built-up areas
- Bare / sparse vegetation
- Permanent water
- Herbaceous wetlands
- Mangroves

This prevents GAIA from treating every location as a tree-planting problem.

---

### 🌿 Species Intelligence

GAIA uses a processed **FAO ECOCROP** knowledge base containing more than **2,500 plant species**.

Candidates are evaluated using environmental requirements such as:

- Temperature range
- Rainfall range
- Soil pH
- Plant uses
- Restoration relevance

GAIA can then use **GBIF occurrence evidence** to strengthen geographic context.

Species that appear environmentally compatible are treated as **climate candidates**, not automatically as ecological recommendations.

---

### 🧠 Ecological Recommendation Gate

One of GAIA's key principles is:

> **A species being able to survive somewhere does not automatically mean it should be introduced there.**

GAIA separates:

**Climate suitability**  
from  
**Ecological recommendation**

The system considers evidence gaps involving:

- Local/native status
- Invasive risk
- Hydrology
- Salinity
- Ecosystem appropriateness

When evidence is insufficient, GAIA can explicitly warn:

> **“This species may be able to survive here, but GAIA does not recommend it for this ecosystem yet.”**

This prevents the AI layer from turning uncertain evidence into an unjustified recommendation.

---

### 🛠️ Ecosystem-Aware Interventions

GAIA does not recommend the same intervention everywhere.

Examples include:

- **Built-up areas:** Urban Heat & Water Resilience
- **Bare / sparse land:** Arid Land Stabilization & Sparse Vegetation Recovery
- **Cropland:** Water-Smart Agricultural Resilience
- **Wetlands:** Wetland Hydrology & Habitat Recovery
- **Permanent water:** Aquatic & Riparian System Protection

The engine can also identify actions that should be avoided.

For example, in naturally arid environments, dense high-water-demand tree planting may cause more harm than benefit.

---

### 🤖 AI Decision Explanation

AI is used as an **explanation and reasoning layer**, not as the source of environmental facts.

The deterministic environmental engine first gathers and evaluates evidence.

The AI layer then explains:

- The strongest candidate
- Ecosystem compatibility
- Trade-offs
- Alternatives
- Confidence
- Missing evidence
- Why an intervention may or may not be appropriate

This architecture reduces unsupported AI recommendations and makes GAIA more transparent.

---

### 📸 Verified Species Images

Species images are dynamically resolved from biodiversity/media sources such as:

- GBIF
- iNaturalist-hosted observations
- Wikimedia Commons fallback

When possible, GAIA also displays attribution and licensing information.

If a verified image cannot be found, GAIA avoids substituting an unrelated generic plant photo.

---

## 🧩 How GAIA Works

```text
                     User selects location
                              │
                              ▼
                       Climate Data
                        NASA POWER
                              │
                              ▼
                  Environmental Risk Engine
                              │
                 ┌────────────┴────────────┐
                 ▼                         ▼
          ESA WorldCover              FAO ECOCROP
          Land-Cover Data            Species Database
                 │                         │
                 │                         ▼
                 │                  Environmental Filter
                 │                         │
                 │                         ▼
                 │                    GBIF Evidence
                 │                         │
                 └────────────┬────────────┘
                              ▼
                  Ecological Decision Gate
                              │
                              ▼
                 Intervention Recommendation
                              │
                              ▼
                    AI Explanation Layer
                              │
                              ▼
                    GAIA Decision Interface
```

---

## 🧪 Example: Southern Iraq

Southern Iraq provides a challenging case study because environmental decisions can involve:

- Extreme heat
- Very low rainfall
- Water scarcity
- Salinity
- Agricultural pressure
- Arid landscapes
- Wetland and riparian ecosystems

A simplistic system might respond:

> “Plant more trees.”

GAIA instead asks:

> What ecosystem exists here?  
> What is actually causing environmental stress?  
> Does vegetation restoration make sense?  
> Which species match the climate?  
> Is there enough ecological evidence to recommend them?  
> Would water management or habitat restoration be more appropriate?

This distinction is central to GAIA.

---

## 🛠️ Technology Stack

### Frontend
- React
- Vite
- JavaScript
- Leaflet
- React Leaflet
- Lucide React

### Backend
- Python
- FastAPI
- Uvicorn
- Pandas
- NumPy
- Requests

### AI
- OpenAI API

### Environmental & Biodiversity Data
- NASA POWER
- ESA WorldCover
- FAO ECOCROP
- GBIF
- Wikimedia Commons

### Deployment
- Render
- GitHub

---

## 📊 Data Sources

GAIA combines multiple independent environmental datasets instead of relying on a single AI prompt.

| Source | Purpose |
|---|---|
| NASA POWER | Climate observations |
| ESA WorldCover | Global land-cover classification |
| FAO ECOCROP | Plant environmental requirements |
| GBIF | Biodiversity occurrence evidence and media |
| Wikimedia Commons | Species image fallback |
| OpenAI | Decision explanation and comparison |

---

## 🔬 Scientific Responsibility

GAIA is currently a **hackathon MVP and decision-support prototype**, not a replacement for professional ecological assessment.

Important limitations include:

- Environmental risk scores are interpretable heuristics, not validated climate forecasts.
- Land-cover classification does not fully describe ecosystem health.
- Species climate compatibility does not prove ecological suitability.
- Local soil, salinity, hydrology, invasive-species risk, and native-range evidence may require additional validation.
- Restoration decisions should ultimately involve local environmental experts and field measurements.

GAIA is designed to expose uncertainty rather than hide it.

---

## 🚀 Running GAIA Locally

### 1. Clone the repository

```bash
git clone https://github.com/hawraa078/gaia-ai.git
cd gaia-ai
```

### 2. Create a Python environment

```bash
python -m venv venv
```

### 3. Install backend dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file:

```env
OPENAI_API_KEY=your_api_key_here
```

Never commit this file to GitHub.

### 5. Start the backend

```bash
uvicorn main:app --reload
```

### 6. Start the frontend

```bash
cd frontend
npm install
npm run dev
```

---

## 🛣️ What's Next

Future versions of GAIA could include:

- 🧪 Real-time soil data integration
- 💧 Salinity and hydrology models
- 🛰️ NDVI and satellite vegetation monitoring
- 💰 Intervention budget optimization
- 📈 Before/after environmental simulation
- ⏳ Future climate scenarios
- 🌎 Expanded native and invasive species databases
- 📍 Higher-resolution ecosystem classification
- 🧑‍🔬 Expert-reviewed restoration rules

The long-term goal is to evolve GAIA from a hackathon prototype into an environmental decision-support system capable of comparing interventions before resources are committed.

---

## 🌍 Vision

Environmental intelligence should not stop at predicting damage.

It should help us determine **what to do next**.

**GAIA — Don't just predict Earth's future. Optimize it.**