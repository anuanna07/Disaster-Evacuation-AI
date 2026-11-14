import math
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from evacuation_engine import (
    build_building_graph, apply_scenario, generate_groups, apply_congestion,
    assign_groups, nearest_exit_assignments, multi_source_exit_search, astar_path, NODE_LABELS, NODES,
    EXITS, path_distance
)

st.set_page_config(page_title="Disaster Evacuation AI", page_icon="🚨", layout="wide")

st.markdown("""
<style>
.main {background-color: #f7f9fc;}
.block-container {padding-top: 1.4rem; padding-bottom: 2rem;}
.hero {padding: 1.25rem 1.5rem; border-radius: 16px; background: linear-gradient(115deg,#10233f,#1b5570); color: white; margin-bottom: 1rem;}
.hero h1 {color:white; margin:0; font-size:2.0rem;}
.hero p {color:#dbeafe; margin:.35rem 0 0 0;}
.metric-note {color:#64748b; font-size:.8rem;}
</style>
<div class="hero">
<h1>🚨 Disaster Evacuation Planning System</h1>
<p>Informed search • Capacity-aware assignment • Hazard-aware routing • Dynamic replanning</p>
</div>
""", unsafe_allow_html=True)

with st.sidebar:
    st.header("⚙️ Simulation controls")
    scenario = st.selectbox("Emergency scenario", ["Fire", "Flood", "Earthquake"])
    hazard_node = st.selectbox("Hazard origin", list(NODES), format_func=lambda n: NODE_LABELS[n], index=2)
    severity = st.slider("Hazard severity", 0.1, 1.0, 0.65, 0.05)
    spread = st.slider("Maximum hazard spread (graph steps)", 0, 4, 3)
    time_step = st.slider("Hazard simulation time step", 0, 5, 3)
    total_people = st.slider("Number of evacuees", 10, 300, 100, 10)
    st.divider()
    st.subheader("Dynamic blockage")
    enable_block = st.checkbox("Simulate a corridor becoming blocked", value=False)
    edge_options = [(a,b) for a,b,_,_ in [
        ("junction_1","corridor_1",10,20), ("junction_1","corridor_2",10,20),
        ("corridor_1","exit_1",12,18), ("corridor_2","exit_2",12,18),
        ("junction_2","corridor_3",10,20), ("junction_2","corridor_4",10,20),
        ("corridor_3","exit_3",12,18), ("corridor_4","exit_4",12,18),
        ("junction_1","stair_1",14,16), ("stair_1","stair_2",18,12),
        ("junction_2","stair_2",14,16)
    ]]
    blocked_edge = st.selectbox(
        "Blocked connection",
        edge_options,
        format_func=lambda e: f"{NODE_LABELS[e[0]]} ↔ {NODE_LABELS[e[1]]}",
        disabled=not enable_block
    )
    run = st.button("🚀 Generate evacuation plan", type="primary", use_container_width=True)

if "results" not in st.session_state:
    st.session_state.results = None

if run or st.session_state.results is None:
    graph = build_building_graph()
    apply_scenario(graph, scenario, hazard_node, severity, spread,
                   blocked_edge if enable_block else None, time_step)
    groups = generate_groups(total_people)
    apply_congestion(graph, groups)
    multi_source_map = multi_source_exit_search(graph)
    assignments, exit_load, explored = assign_groups(graph, groups)
    baseline = nearest_exit_assignments(graph, groups)
    st.session_state.results = {
        "graph": graph, "groups": groups, "assignments": assignments,
        "exit_load": exit_load, "explored": explored, "baseline": baseline, "multi_source_map": multi_source_map,
        "scenario": scenario, "hazard_node": hazard_node,
        "severity": severity, "spread": spread, "time_step": time_step, "total_people": total_people,
        "blocked_edge": blocked_edge if enable_block else None
    }

data = st.session_state.results
# Re-run when controls change, not only on button click, to keep display consistent.
current_signature = (scenario, hazard_node, severity, spread, time_step, total_people,
                     blocked_edge if enable_block else None, time_step)
saved_signature = (data["scenario"], data["hazard_node"], data["severity"],
                   data["spread"], data["time_step"], data["total_people"], data["blocked_edge"])
if current_signature != saved_signature:
    graph = build_building_graph()
    apply_scenario(graph, scenario, hazard_node, severity, spread,
                   blocked_edge if enable_block else None, time_step)
    groups = generate_groups(total_people)
    apply_congestion(graph, groups)
    multi_source_map = multi_source_exit_search(graph)
    assignments, exit_load, explored = assign_groups(graph, groups)
    baseline = nearest_exit_assignments(graph, groups)
    data = {"graph": graph, "groups": groups, "assignments": assignments,
            "exit_load": exit_load, "explored": explored, "baseline": baseline, "multi_source_map": multi_source_map,
            "scenario": scenario, "hazard_node": hazard_node,
            "severity": severity, "spread": spread, "time_step": time_step, "total_people": total_people,
            "blocked_edge": blocked_edge if enable_block else None}
    st.session_state.results = data

graph = data["graph"]
assignments = data["assignments"]
baseline = data["baseline"]

def max_evacuation_time(items):
    times = [x["estimated_seconds"] for x in items if x.get("path") and math.isfinite(x.get("estimated_seconds", math.inf))]
    return max(times) if times else math.inf

optimized_time = max_evacuation_time(assignments)
baseline_times = []
for item in baseline:
    if item["path"]:
        # Baseline time uses the same physical speed but does not balance exit queues.
        baseline_times.append(path_distance(graph, item["path"]) / 1.35)
baseline_time = max(baseline_times) if baseline_times else math.inf
successful = sum(x["people"] for x in assignments if x["path"])
unassigned = data["total_people"] - successful

m1,m2,m3,m4 = st.columns(4)
m1.metric("Evacuees with a route", f"{successful}/{data['total_people']}")
m2.metric("Estimated completion time", f"{optimized_time/60:.1f} min" if math.isfinite(optimized_time) else "No safe plan")
m3.metric("Search nodes explored", data["explored"])
m4.metric("Groups needing assistance", sum(1 for g in data["groups"] if g["condition"] != "Mobile"))

st.subheader("🗺️ Building evacuation map")
floor = st.radio("View floor", [1,2], horizontal=True)
fig = go.Figure()
# Draw graph edges, highlighting assigned routes.
route_colors = ["#2563eb", "#16a34a", "#9333ea", "#d97706"]
for a,b in graph.edges:
    na, nb = NODES[a], NODES[b]
    if na["floor"] != floor or nb["floor"] != floor:
        continue
    blocked = graph[a][b]["blocked"]
    fig.add_trace(go.Scatter(x=[na["x"],nb["x"]], y=[na["y"],nb["y"]],
        mode="lines", line=dict(color="#ef4444" if blocked else "#cbd5e1",
                                width=5 if blocked else 3,
                                dash="dash" if blocked else "solid"),
        hoverinfo="text", text=[f"{NODE_LABELS[a]} ↔ {NODE_LABELS[b]}",
                                f"Capacity: {graph[a][b]['capacity']} people/min"],
        showlegend=False))
for i, item in enumerate(assignments):
    if not item["path"]:
        continue
    path = item["path"]
    for a,b in zip(path,path[1:]):
        na,nb=NODES[a],NODES[b]
        if na["floor"] == floor and nb["floor"] == floor:
            fig.add_trace(go.Scatter(x=[na["x"],nb["x"]],y=[na["y"],nb["y"]],
                mode="lines",line=dict(color=route_colors[i%len(route_colors)],width=6),
                name=f"{item['name']} → {NODE_LABELS[item['exit']]}",
                showlegend=False,hoverinfo="skip"))
node_x=[]; node_y=[]; node_text=[]; node_color=[]; node_size=[]
for node, attrs in NODES.items():
    if attrs["floor"] != floor:
        continue
    node_x.append(attrs["x"]); node_y.append(attrs["y"])
    label = attrs["label"]
    if attrs["kind"] == "exit":
        color="#16a34a"
    elif graph.nodes[node].get("unsafe"):
        color="#dc2626"
    elif node == data["hazard_node"]:
        color="#f97316"
    elif attrs["kind"] == "stair":
        color="#8b5cf6"
    else:
        color="#2563eb"
    node_color.append(color); node_size.append(24 if attrs["kind"]=="exit" else 19)
    node_text.append(f"{label}<br>Hazard level: {graph.nodes[node].get('hazard',0):.2f}")
fig.add_trace(go.Scatter(x=node_x,y=node_y,mode="markers+text",
    marker=dict(size=node_size,color=node_color,line=dict(color="white",width=2)),
    text=[NODES[n]["label"] for n in NODES if NODES[n]["floor"]==floor],
    textposition="bottom center",hovertext=node_text,hoverinfo="text",
    showlegend=False))
fig.update_layout(height=430,margin=dict(l=10,r=10,t=10,b=10),
    xaxis=dict(visible=False,range=[0,8]),yaxis=dict(visible=False,range=[-0.5,4.8],
    scaleanchor="x",scaleratio=1),plot_bgcolor="white",paper_bgcolor="white")
st.plotly_chart(fig,use_container_width=True)
st.caption("Illustrative two-floor graph. Green nodes are exits, red nodes are marked unsafe, orange is the hazard origin, and red dashed edges are blocked. Coloured lines show assigned routes.")

left,right=st.columns([1.15,0.85])
with left:
    st.subheader("👥 Group-to-exit assignments")
    rows=[]
    for item in assignments:
        rows.append({"Group":item["name"],"Starting area":NODE_LABELS[item["start"]],
                     "People":item["people"],"Condition":item["condition"],
                     "Assigned exit":NODE_LABELS[item["exit"]] if item["exit"] else "No safe route",
                     "Route":" → ".join(NODE_LABELS[n] for n in item["path"]) if item["path"] else "Unavailable",
                     "Estimated time (min)":round(item["estimated_seconds"]/60,2) if item["path"] else None})
    st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)
with right:
    st.subheader("🚪 Exit utilisation")
    exit_rows=[]
    for ex in EXITS:
        cap = 18 if ex in ("exit_1","exit_2","exit_3","exit_4") else 0
        load=data["exit_load"].get(ex,0)
        exit_rows.append({"Exit":NODE_LABELS[ex],"People assigned":load,
                          "Illustrative flow (people/min)":cap})
    st.dataframe(pd.DataFrame(exit_rows),use_container_width=True,hide_index=True)

st.subheader("📊 Performance comparison")
comparison = pd.DataFrame([
    {"Method":"Nearest-exit baseline","Completion estimate (min)":round(baseline_time/60,2) if math.isfinite(baseline_time) else None,
     "Groups routed":sum(1 for x in baseline if x["path"])},
    {"Method":"A* capacity-aware planner","Completion estimate (min)":round(optimized_time/60,2) if math.isfinite(optimized_time) else None,
     "Groups routed":sum(1 for x in assignments if x["path"])}
])
st.dataframe(comparison,use_container_width=True,hide_index=True)
if math.isfinite(baseline_time) and math.isfinite(optimized_time) and baseline_time > 0:
    delta=(baseline_time-optimized_time)/baseline_time*100
    st.info(f"Illustrative difference from baseline: {delta:.1f}% lower estimated completion time. This is a model estimate, not a real-world guarantee.")
else:
    st.warning("At least one method could not route every group. Review the hazard and blockage settings.")

st.subheader("🔁 Dynamic replanning demonstration")
st.write("Turn on **Simulate a corridor becoming blocked** in the sidebar and regenerate the plan. The planner excludes that connection and searches for alternative safe routes.")
if data["blocked_edge"]:
    st.warning(f"Blocked connection: {NODE_LABELS[data['blocked_edge'][0]]} ↔ {NODE_LABELS[data['blocked_edge'][1]]}")
else:
    st.success("No manually blocked connection is active.")

st.subheader("🧪 Scenario interpretation")
st.write(f"Scenario: **{data['scenario']}** | Hazard origin: **{NODE_LABELS[data['hazard_node']]}** | Severity: **{data['severity']:.2f}** | Spread limit: **{data['spread']} graph steps** | Time step: **{data['time_step']}**.")
if unassigned:
    st.error(f"{unassigned} people are not assigned a safe route in this simulation. Do not interpret this as a safe evacuation plan.")
else:
    st.success("Every simulated group has at least one route in this scenario.")

st.caption("Academic prototype only. Hazard spread, crowd effects, walking speeds and exit flows are simplified assumptions. This tool is not certified for real emergency response or life-safety decisions.")
