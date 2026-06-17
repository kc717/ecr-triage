import os
import json
import streamlit as st
from pathlib import Path

# Set streamlit page config with custom title and styling
st.set_page_config(
    page_title="eCR-Triage Queue Dashboard",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for modern styling and tier color badges
st.markdown("""
<style>
    .tier-badge {
        padding: 5px 12px;
        border-radius: 12px;
        font-weight: bold;
        color: white;
        display: inline-block;
        font-size: 14px;
        text-align: center;
    }
    .tier-4-hour { background-color: #dc3545; }
    .tier-24-hour { background-color: #fd7e14; }
    .tier-7-day { background-color: #ffc107; color: black; }
    .tier-non-notifiable { background-color: #6c757d; }
    
    .val-badge {
        padding: 3px 8px;
        border-radius: 4px;
        font-weight: bold;
        font-size: 12px;
    }
    .val-pass { background-color: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
    .val-fail { background-color: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
    
    .card {
        padding: 20px;
        border-radius: 10px;
        border: 1px solid #e0e0e0;
        margin-bottom: 15px;
        background-color: #fcfcfc;
    }
</style>
""", unsafe_allow_html=True)

# Imports from project
from src.bundle_parser import BundleParser
from src.triage_engine import TriageEngine
from src.validator import validate_triage_result

@st.cache_data
def load_and_triage_cases():
    base_dir = Path(__file__).resolve().parent / "data" / "test_bundles"
    expected_path = base_dir / "EXPECTED_TIERS.json"
    
    if not expected_path.exists():
        st.error(f"EXPECTED_TIERS.json not found in {base_dir}")
        return []
        
    with open(expected_path, "r") as f:
        expected_list = json.load(f)
        
    parser = BundleParser()
    engine = TriageEngine()
    results = []
    
    for item in expected_list:
        filename = item["file"]
        filepath = base_dir / filename
        
        if not filepath.exists():
            continue
            
        with open(filepath, "r") as f:
            bundle = json.load(f)
            
        parsed = parser.parse_bundle(bundle)
        prompt = parser.to_triage_prompt(parsed)
        
        # Run triage
        triage_res = engine.triage(prompt)
        
        # Run validation
        validation_report = validate_triage_result(triage_res, parsed)
        
        # Determine condition name
        active_conds = [c["display"] for c in parsed.get("Conditions", []) if c.get("clinical_status") == "active"]
        condition = active_conds[0] if active_conds else "Unknown Condition"
        
        results.append({
            "filename": filename,
            "patient_name": parsed.get("Patient", {}).get("name", "Unknown"),
            "patient_id": parsed.get("Patient", {}).get("id", "Unknown"),
            "condition": condition,
            "triage_result": triage_res,
            "validation_report": validation_report
        })
        
    # Sort: 4-hour (0) -> 24-hour (1) -> 7-day (2) -> non-notifiable (3), then score desc
    tier_order = {"4-hour": 0, "24-hour": 1, "7-day": 2, "non-notifiable": 3}
    results.sort(key=lambda x: (
        tier_order.get(x["triage_result"].get("tier", "non-notifiable"), 99),
        -x["triage_result"].get("urgency_score", 0)
    ))
    
    return results

def main():
    st.title("🏥 eCR-Triage Public Health Queue Dashboard")
    st.markdown("Real-time clinical prioritization of electronic Initial Case Reports (eICRs) using CSTE 2025 guidelines.")
    
    with st.spinner("Processing test bundles through triage engine and validator..."):
        try:
            cases = load_and_triage_cases()
        except Exception as e:
            st.error(f"Error loading or triaging cases: {e}")
            return
            
    # Sidebar stats
    st.sidebar.header("Triage Statistics")
    total_cases = len(cases)
    st.sidebar.metric("Total Cases in Queue", total_cases)
    
    t4 = sum(1 for c in cases if c["triage_result"].get("tier") == "4-hour")
    t24 = sum(1 for c in cases if c["triage_result"].get("tier") == "24-hour")
    t7 = sum(1 for c in cases if c["triage_result"].get("tier") == "7-day")
    tnn = sum(1 for c in cases if c["triage_result"].get("tier") == "non-notifiable")
    
    st.sidebar.markdown(f"🔴 **4-hour (Extremely Urgent):** {t4}")
    st.sidebar.markdown(f"🟠 **24-hour (Urgent):** {t24}")
    st.sidebar.markdown(f"🟡 **7-day (Routine):** {t7}")
    st.sidebar.markdown(f"⚪ **Non-Notifiable:** {tnn}")
    
    st.sidebar.markdown("---")
    
    valid_passes = sum(1 for c in cases if c["validation_report"]["passed"])
    st.sidebar.metric("Validator Status (Pass rate)", f"{valid_passes}/{total_cases}")

    # Main Queue List
    st.subheader("📋 Ranked Triage Investigation Queue")
    
    for idx, case in enumerate(cases, 1):
        t_res = case["triage_result"]
        v_rep = case["validation_report"]
        tier = t_res.get("tier", "non-notifiable")
        score = t_res.get("urgency_score", 1)
        
        # Badge classes
        badge_class = f"tier-{tier}"
        val_class = "val-pass" if v_rep["passed"] else "val-fail"
        val_text = "PASSED" if v_rep["passed"] else "FLAGGED"
        
        # HTML formatting
        st.markdown(f"""
        <div class="card">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                <div>
                    <span style="font-size: 18px; font-weight: bold; margin-right: 15px;">#{idx} | {case['patient_name']}</span>
                    <span style="color: #6c757d; font-size: 14px;">(Patient ID: {case['patient_id']})</span>
                </div>
                <div>
                    <span class="tier-badge {badge_class}">{tier.upper()}</span>
                    <span style="font-size: 18px; font-weight: bold; margin-left: 10px; margin-right: 15px;">Score: {score}/10</span>
                    <span class="val-badge {val_class}">{val_text}</span>
                </div>
            </div>
            <div style="font-size: 15px; margin-bottom: 8px;">
                <strong>Active Condition:</strong> <code style="background-color: #f1f3f5; padding: 2px 6px; border-radius: 4px;">{case['condition']}</code>
            </div>
        """, unsafe_allow_html=True)
        
        # Recommendation
        actions = t_res.get("recommended_actions", [])
        if actions:
            st.markdown("**Recommended Actions:**")
            for action in actions:
                st.markdown(f"- {action}")
                
        # Rationale Expander
        with st.expander("Show Triage Rationale & Validator Report"):
            col1, col2 = st.columns([2, 1])
            with col1:
                st.markdown("**LLM Reasoning:**")
                st.write(t_res.get("reasoning"))
                if t_res.get("key_findings"):
                    st.markdown("**Key Findings:**")
                    st.write(", ".join(t_res.get("key_findings")))
            with col2:
                st.markdown("**Validator Report:**")
                for name, res in v_rep["results"].items():
                    status_icon = "🟢" if res["passed"] else "🔴"
                    st.markdown(f"{status_icon} **{name.replace('_', ' ').title()}**")
                    if not res["passed"]:
                        st.caption(f"Reason: {res['reason']}")
                        
        st.markdown("</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
