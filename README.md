# Disaster Evacuation Planning System using Informed Search

A Streamlit-based academic prototype for planning evacuation routes in a two-floor example building. It demonstrates A* informed search, a BFS implementation in the engine, hazard-aware route costs, group-to-exit assignment, congestion/capacity considerations, dynamic blockage replanning, and a nearest-exit baseline comparison.

## Features

- Two-floor building represented as a NetworkX graph.
- Fire, flood and earthquake scenario controls.
- Time-stepped hazard intensity and graph-step spread simulation.
- Edge capacity and illustrative congestion values.
- A* search with a distance heuristic and hazard/congestion-aware edge costs.
- Multi-source Dijkstra search seeded from all safe exits to compute a shared nearest-safe-exit field.
- BFS pathfinding baseline function.
- Capacity-aware greedy group-to-exit assignment.
- Different walking-speed assumptions for occupant mobility conditions.
- Dynamic blocked-edge simulation and replanning.
- Plotly floor map and evacuation analytics.
- Nearest-exit baseline comparison.

## Requirements

- Python 3.10 or newer recommended.
- Windows, macOS or Linux.

## Run locally (Windows PowerShell)

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
streamlit run app.py
```

If PowerShell blocks activation, use the environment's Python directly:

```powershell
py -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m streamlit run app.py
```

## Run locally (macOS/Linux)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## GitHub upload

Create an empty repository on GitHub, then from this project folder:

```bash
git init
git add .
git commit -m "Initial disaster evacuation planning prototype"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/YOUR-REPOSITORY.git
git push -u origin main
```

Replace the URL with your own repository URL.

## Project structure

```text
Disaster-Evacuation-AI/
├── app.py
├── evacuation_engine.py
├── requirements.txt
├── README.md
├── .gitignore
└── tests/
    └── test_engine.py
```

## Model assumptions and limitations

This is an educational simulation, not a certified evacuation or life-safety system. It does not connect to fire alarms, sensors, live building-management systems, maps, or emergency services. The floor plan, hazard propagation, travel speeds, capacities, and congestion are illustrative assumptions. The group assignment is a greedy heuristic, not a proof of globally optimal multi-group scheduling. The displayed evacuation times are estimates for comparing scenarios within this model only. Real deployments require validated building plans, local fire codes, accessibility review, domain experts, live data, and professional safety validation.

## Suggested extensions

- Import real floor plans and validate dimensions.
- Use time-expanded states to model hazard spread over time.
- Add a more rigorous multi-source assignment optimizer.
- Model queueing and corridor flow with SimPy.
- Add automated tests and scenario benchmark exports.
- Deploy on Streamlit Community Cloud after testing.
