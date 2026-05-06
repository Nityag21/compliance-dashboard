import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

st.set_page_config(page_title="Compliance Mail Tracker", layout="wide", page_icon="📧")

st.markdown("""
<style>
[data-testid="stMetricValue"] { font-size: 2rem; }
.section-title { font-size: 14px; font-weight: 600; color: #444; margin-bottom: 8px; }
</style>
""", unsafe_allow_html=True)


# ── Priority rules based on Query Type & Partner ───────────────────────────────
def get_priority(query_type, partner=""):
    q = str(query_type).upper()
    p = str(partner).upper()
    if any(x in q for x in ["KYC", "VKYC", "SEBI", "MARGIN", "COMPLIANCE", "PENALTY"]):
        return "HIGH"
    if any(x in p for x in ["NSE", "BSE", "SEBI", "CDSL", "NSDL", "RBI"]):
        return "HIGH"
    if any(x in q for x in ["TRADE", "DISPUTE", "ACCOUNT", "BANK", "OPENING"]):
        return "NORMAL"
    return "LOW"

def get_category(query_type, partner=""):
    q = str(query_type).upper()
    p = str(partner).upper()
    if any(x in p for x in ["NSE", "BSE"]):
        return "Exchange"
    if any(x in q for x in ["KYC", "VKYC", "VERIFICATION", "ONBOARDING"]):
        return "KYC"
    if any(x in q for x in ["SEBI", "CIRCULAR", "COMPLIANCE", "REGULATORY"]):
        return "SEBI / Regulatory"
    if any(x in q for x in ["TRADE", "DISPUTE", "MARGIN"]):
        return "Trade"
    if any(x in q for x in ["ACCOUNT", "DIVIDEND", "NOMINATION", "CLIENT", "BANK", "PAN"]):
        return "Client Query"
    if any(x in p for x in ["INTERNAL"]):
        return "Internal"
    return query_type  # keep original if nothing matches

def get_conv_type(type_col):
    t = str(type_col).upper()
    if "IN" in t:
        return "Inbound (External)"
    if "OUT" in t:
        return "Outbound (Internal)"
    return type_col

def calc_tat(time_in, time_out):
    try:
        fmt = "%I:%M %p"
        t1 = datetime.strptime(str(time_in).strip(), fmt)
        t2 = datetime.strptime(str(time_out).strip(), fmt)
        diff = (t2 - t1).seconds // 60
        return diff if diff > 0 else (diff + 1440)
    except:
        return 0


# ── Load data ──────────────────────────────────────────────────────────────────
@st.cache_data
def load_data():
    try:
        df = pd.read_excel("company_data.xlsx")
        df.columns = df.columns.str.strip()

        # Add derived columns
        df["Category"] = df.apply(
            lambda r: get_category(r.get("Query Type",""), r.get("Partner","")), axis=1)
        df["Priority"] = df.apply(
            lambda r: get_priority(r.get("Query Type",""), r.get("Partner","")), axis=1)
        df["Conv Type"] = df["Type"].apply(get_conv_type) if "Type" in df.columns else "Unknown"
        df["TAT (mins)"] = df.apply(
            lambda r: calc_tat(r.get("Time",""), r.get("Response Time","")), axis=1)
        df["Forwarded To"] = "—"

        # Clean date
        if "Date" in df.columns:
            df["Date"] = pd.to_datetime(df["Date"], errors="coerce").dt.strftime("%d-%b-%Y")

        return df, None
    except FileNotFoundError:
        return None, "company_data.xlsx not found in the project folder!"
    except Exception as e:
        return None, str(e)

df, error = load_data()

# ── Header ─────────────────────────────────────────────────────────────────────
st.title("📧 Compliance Mail Tracker")
st.caption("Bonanza Portfolio Ltd  |  Compliance Department")
st.markdown("---")

if error:
    st.error(f"❌ Error loading file: {error}")
    st.info("Make sure **company_data.xlsx** is in the same folder as app.py")
    st.stop()

st.success(f"✅ Loaded {len(df)} records from company_data.xlsx")


# ── Sidebar filters ────────────────────────────────────────────────────────────
st.sidebar.title("🔽 Filters")

all_agents   = sorted(df["Agent"].dropna().unique().tolist())   if "Agent"    in df.columns else []
all_branches = sorted(df["Branch"].dropna().unique().tolist())  if "Branch"   in df.columns else []
all_cats     = sorted(df["Category"].dropna().unique().tolist())
all_pris     = ["HIGH","NORMAL","LOW"]
all_convs    = sorted(df["Conv Type"].dropna().unique().tolist())

sel_agent  = st.sidebar.multiselect("Agent",    all_agents,   default=all_agents)
sel_branch = st.sidebar.multiselect("Branch",   all_branches, default=all_branches)
sel_cat    = st.sidebar.multiselect("Category", all_cats,     default=all_cats)
sel_pri    = st.sidebar.multiselect("Priority", all_pris,     default=all_pris)
sel_conv   = st.sidebar.multiselect("Conv Type",all_convs,    default=all_convs)

fdf = df.copy()
if sel_agent  and "Agent"    in df.columns: fdf = fdf[fdf["Agent"].isin(sel_agent)]
if sel_branch and "Branch"   in df.columns: fdf = fdf[fdf["Branch"].isin(sel_branch)]
if sel_cat:    fdf = fdf[fdf["Category"].isin(sel_cat)]
if sel_pri:    fdf = fdf[fdf["Priority"].isin(sel_pri)]
if sel_conv:   fdf = fdf[fdf["Conv Type"].isin(sel_conv)]

st.sidebar.markdown("---")
st.sidebar.markdown(f"**Showing {len(fdf)} of {len(df)} records**")


# ── Tabs ───────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Overview",
    "🔍 Keyword Detector",
    "📋 Mail Register",
    "👥 Agent Tracker",
    "🏢 Branch Tracker"
])

cat_colors = {
    "Exchange":          "#E24B4A",
    "KYC":               "#378ADD",
    "SEBI / Regulatory": "#7F77DD",
    "Trade":             "#EF9F27",
    "Client Query":      "#1D9E75",
    "Internal":          "#888780",
}
def get_color(cat):
    return cat_colors.get(cat, "#AAAAAA")


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 — OVERVIEW
# ═══════════════════════════════════════════════════════════════════════════════
with tab1:

    c1,c2,c3,c4,c5 = st.columns(5)
    c1.metric("Total Records",   len(fdf))
    c2.metric("HIGH Priority",   len(fdf[fdf["Priority"]=="HIGH"]))
    c3.metric("Inbound Mails",   len(fdf[fdf["Conv Type"].str.contains("Inbound", na=False)]))
    c4.metric("Unique Agents",   fdf["Agent"].nunique() if "Agent" in fdf.columns else 0)
    c5.metric("Avg TAT (mins)",  int(fdf["TAT (mins)"].mean()) if len(fdf) else 0)

    st.markdown("")
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Mails by Category**")
        cat_df = fdf["Category"].value_counts().reset_index()
        cat_df.columns = ["Category","Count"]
        cat_df["Color"] = cat_df["Category"].apply(get_color)
        fig1 = px.bar(cat_df, x="Count", y="Category", orientation="h",
                      color="Category",
                      color_discrete_map={r["Category"]: r["Color"] for _,r in cat_df.iterrows()},
                      height=320)
        fig1.update_layout(showlegend=False, margin=dict(l=0,r=10,t=10,b=0),
                           plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
        fig1.update_xaxes(showgrid=False)
        st.plotly_chart(fig1, use_container_width=True)

    with col2:
        st.markdown("**Inbound vs Outbound**")
        conv_df = fdf["Conv Type"].value_counts()
        fig2 = go.Figure(go.Pie(
            labels=conv_df.index, values=conv_df.values,
            hole=0.6, marker_colors=["#378ADD","#7F77DD","#EF9F27"],
            textinfo="label+percent"
        ))
        fig2.update_layout(height=320, margin=dict(l=0,r=0,t=10,b=0),
                           paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig2, use_container_width=True)

    col3, col4 = st.columns(2)

    with col3:
        st.markdown("**Priority Breakdown**")
        pri_df = fdf["Priority"].value_counts().reset_index()
        pri_df.columns = ["Priority","Count"]
        fig3 = px.bar(pri_df, x="Priority", y="Count",
                      color="Priority",
                      color_discrete_map={"HIGH":"#E24B4A","NORMAL":"#EF9F27","LOW":"#1D9E75"},
                      height=280, text="Count")
        fig3.update_traces(textposition="outside")
        fig3.update_layout(showlegend=False, margin=dict(l=0,r=0,t=10,b=0),
                           plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig3, use_container_width=True)

    with col4:
        st.markdown("**Avg Reply Time by Category (mins)**")
        tat_df = fdf[fdf["TAT (mins)"]>0].groupby("Category")["TAT (mins)"].mean().round().reset_index()
        tat_df.columns = ["Category","Avg TAT"]
        tat_df = tat_df.sort_values("Avg TAT", ascending=False)
        tat_df["Color"] = tat_df["Category"].apply(get_color)
        fig4 = px.bar(tat_df, x="Category", y="Avg TAT",
                      color="Category",
                      color_discrete_map={r["Category"]: r["Color"] for _,r in tat_df.iterrows()},
                      height=280, text="Avg TAT")
        fig4.update_traces(textposition="outside")
        fig4.update_layout(showlegend=False, margin=dict(l=0,r=0,t=10,b=0),
                           plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                           xaxis_tickangle=-30)
        st.plotly_chart(fig4, use_container_width=True)

    if "Partner" in fdf.columns:
        st.markdown("**Mails by Partner**")
        partner_df = fdf["Partner"].value_counts().reset_index()
        partner_df.columns = ["Partner","Count"]
        fig5 = px.bar(partner_df, x="Partner", y="Count",
                      color_discrete_sequence=["#378ADD"], height=280, text="Count")
        fig5.update_traces(textposition="outside")
        fig5.update_layout(margin=dict(l=0,r=0,t=10,b=0),
                           plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig5, use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2 — KEYWORD DETECTOR
# ═══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.subheader("🔍 Type any mail subject to detect category & priority")
    st.caption("This shows how the system will auto-categorise real emails.")

    samples = [
        "NSE circular on revised margin requirements",
        "KYC verification pending for client 4821",
        "Pune branch compliance checklist not submitted",
        "SEBI inspection scheduled for next week",
        "Client complaint — dividend not received",
        "VKYC session failed — PwD client",
        "BSE trade dispute escalation",
        "Team meeting 3pm Friday",
    ]

    col_i, col_b = st.columns([4,1])
    with col_i:
        user_text = st.text_input("Mail subject:", placeholder="Type subject here...")
    with col_b:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Try sample ▶"):
            if "sidx" not in st.session_state: st.session_state.sidx = 0
            st.session_state.kw_text = samples[st.session_state.sidx % len(samples)]
            st.session_state.sidx += 1

    if "kw_text" in st.session_state and not user_text:
        user_text = st.session_state.kw_text
        st.text_input("Mail subject (sample):", value=user_text, key="disp", disabled=True)

    if user_text:
        cat  = get_category(user_text)
        pri  = get_priority(user_text)
        c1,c2,c3 = st.columns(3)
        c1.success (f"**Category:** {cat}")
        if pri=="HIGH":   c2.error  (f"**Priority:** {pri}")
        elif pri=="NORMAL": c2.warning(f"**Priority:** {pri}")
        else:             c2.info   (f"**Priority:** {pri}")
        c3.info(f"**Conv Type:** Based on sender domain")

    st.markdown("---")
    st.markdown("**Keyword Rules**")
    rules = {
        "Exchange (HIGH)":          "NSE, BSE in Partner column",
        "KYC (HIGH)":               "KYC, VKYC, Verification, Onboarding",
        "SEBI / Regulatory (HIGH)": "SEBI, Circular, Compliance, Regulatory, Penalty",
        "Trade (NORMAL)":           "Trade, Dispute, Margin",
        "Client Query (NORMAL)":    "Account, Dividend, Nomination, Client, Bank, PAN",
        "Internal (LOW)":           "Partner = Internal",
    }
    for rule, words in rules.items():
        with st.expander(rule):
            st.code(words)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3 — MAIL REGISTER
# ═══════════════════════════════════════════════════════════════════════════════
with tab3:
    st.subheader("📋 Full Mail Register")
    st.caption(f"Showing {len(fdf)} records")

    def color_pri(val):
        if val=="HIGH":   return "background-color:#FCEBEB;color:#A32D2D;font-weight:bold"
        if val=="NORMAL": return "background-color:#FAEEDA;color:#633806;font-weight:bold"
        return "background-color:#EAF3DE;color:#3B6D11;font-weight:bold"

    def color_conv(val):
        if "Inbound"  in str(val): return "background-color:#E6F1FB;color:#0C447C;font-weight:bold"
        if "Outbound" in str(val): return "background-color:#EEEDFE;color:#3C3489;font-weight:bold"
        return ""

    def color_tat(val):
        try:
            v = int(val)
            if v > 200: return "color:#A32D2D;font-weight:bold"
            if v > 100: return "color:#633806;font-weight:bold"
            if v > 0:   return "color:#3B6D11;font-weight:bold"
        except: pass
        return ""

    show_cols = [c for c in ["Ticket ID","Date","Time","Agent","Branch",
                              "Client Code","Query Type","Category","Priority",
                              "Partner","Conv Type","Response Time","TAT (mins)"]
                 if c in fdf.columns]

    styled = fdf[show_cols].style\
        .applymap(color_pri,  subset=["Priority"])\
        .applymap(color_conv, subset=["Conv Type"])\
        .applymap(color_tat,  subset=["TAT (mins)"] if "TAT (mins)" in show_cols else [])

    st.dataframe(styled, use_container_width=True, height=480)

    csv = fdf[show_cols].to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Download filtered data as CSV",
                       csv, "filtered_compliance_data.csv", "text/csv")


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 4 — AGENT TRACKER
# ═══════════════════════════════════════════════════════════════════════════════
with tab4:
    if "Agent" not in fdf.columns:
        st.warning("No 'Agent' column found in your Excel file.")
    else:
        st.subheader("👥 Agent Performance")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Queries handled per agent**")
            ag = fdf.groupby("Agent")["Ticket ID"].count().reset_index() if "Ticket ID" in fdf.columns \
                 else fdf["Agent"].value_counts().reset_index()
            ag.columns = ["Agent","Count"]
            ag = ag.sort_values("Count", ascending=True)
            fig_a1 = px.bar(ag, x="Count", y="Agent", orientation="h",
                            color_discrete_sequence=["#378ADD"], height=350, text="Count")
            fig_a1.update_traces(textposition="outside")
            fig_a1.update_layout(showlegend=False, margin=dict(l=0,r=30,t=10,b=0),
                                 plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_a1, use_container_width=True)

        with col2:
            st.markdown("**Avg TAT per agent (mins)**")
            tat_ag = fdf[fdf["TAT (mins)"]>0].groupby("Agent")["TAT (mins)"].mean().round().reset_index()
            tat_ag.columns = ["Agent","Avg TAT"]
            tat_ag = tat_ag.sort_values("Avg TAT", ascending=True)
            fig_a2 = px.bar(tat_ag, x="Avg TAT", y="Agent", orientation="h",
                            color_discrete_sequence=["#EF9F27"], height=350, text="Avg TAT")
            fig_a2.update_traces(textposition="outside")
            fig_a2.update_layout(showlegend=False, margin=dict(l=0,r=30,t=10,b=0),
                                 plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_a2, use_container_width=True)

        st.markdown("---")
        st.markdown("**Category breakdown per agent**")
        ag_cat = fdf.groupby(["Agent","Category"])["Ticket ID"].count().reset_index() \
                 if "Ticket ID" in fdf.columns \
                 else fdf.groupby(["Agent","Category"]).size().reset_index(name="Count")
        ag_cat.columns = ["Agent","Category","Count"]
        fig_a3 = px.bar(ag_cat, x="Agent", y="Count", color="Category",
                        barmode="stack",
                        color_discrete_map=cat_colors,
                        height=380)
        fig_a3.update_layout(margin=dict(l=0,r=0,t=10,b=0),
                             plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                             xaxis_tickangle=-20)
        st.plotly_chart(fig_a3, use_container_width=True)

        st.markdown("**Priority breakdown per agent**")
        ag_pri = fdf.groupby(["Agent","Priority"]).size().reset_index(name="Count")
        fig_a4 = px.bar(ag_pri, x="Agent", y="Count", color="Priority",
                        barmode="group",
                        color_discrete_map={"HIGH":"#E24B4A","NORMAL":"#EF9F27","LOW":"#1D9E75"},
                        height=320)
        fig_a4.update_layout(margin=dict(l=0,r=0,t=10,b=0),
                             plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                             xaxis_tickangle=-20)
        st.plotly_chart(fig_a4, use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 5 — BRANCH TRACKER
# ═══════════════════════════════════════════════════════════════════════════════
with tab5:
    if "Branch" not in fdf.columns:
        st.warning("No 'Branch' column found in your Excel file.")
    else:
        st.subheader("🏢 Branch-wise Analysis")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Tickets per branch**")
            br = fdf["Branch"].value_counts().reset_index()
            br.columns = ["Branch","Count"]
            fig_b1 = px.bar(br, x="Count", y="Branch", orientation="h",
                            color_discrete_sequence=["#7F77DD"], height=320, text="Count")
            fig_b1.update_traces(textposition="outside")
            fig_b1.update_layout(showlegend=False, margin=dict(l=0,r=30,t=10,b=0),
                                 plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_b1, use_container_width=True)

        with col2:
            st.markdown("**HIGH priority tickets per branch**")
            br_hi = fdf[fdf["Priority"]=="HIGH"]["Branch"].value_counts().reset_index()
            br_hi.columns = ["Branch","HIGH Priority Count"]
            fig_b2 = px.bar(br_hi, x="HIGH Priority Count", y="Branch", orientation="h",
                            color_discrete_sequence=["#E24B4A"], height=320, text="HIGH Priority Count")
            fig_b2.update_traces(textposition="outside")
            fig_b2.update_layout(showlegend=False, margin=dict(l=0,r=30,t=10,b=0),
                                 plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_b2, use_container_width=True)

        st.markdown("**Category breakdown per branch**")
        br_cat = fdf.groupby(["Branch","Category"]).size().reset_index(name="Count")
        fig_b3 = px.bar(br_cat, x="Branch", y="Count", color="Category",
                        barmode="stack", color_discrete_map=cat_colors, height=380)
        fig_b3.update_layout(margin=dict(l=0,r=0,t=10,b=0),
                             plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                             xaxis_tickangle=-20)
        st.plotly_chart(fig_b3, use_container_width=True)


st.markdown("---")
st.caption("Built by Rutuja Bhosale | Compliance Analyst Intern | Bonanza Portfolio Ltd | 2025")
