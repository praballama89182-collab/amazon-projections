import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO

st.set_page_config(page_title="PPC & Organic Projections", page_icon="📊", layout="wide")

# Brand Configuration
BRAND_MAP = {
    'MA': 'Maison de l’Avenir',
    'CL': 'Creation Lamis',
    'JPD': 'Jean Paul Dupont',
    'PC': 'Paris Collection',
    'DC': 'Dorall Collection',
    'CPT': 'CP Trendies'
}

BRAND_KEYWORDS = {
    'Maison de l’Avenir': ['MAISON DE L’AVENIR', 'MAISON DE LAVENIR', 'MAISON'],
    'Creation Lamis': ['CREATION LAMIS', 'CREATION DELUXE', 'CREATION'],
    'Jean Paul Dupont': ['JEAN PAUL DUPONT', 'JPD'],
    'Paris Collection': ['PARIS COLLECTION'],
    'Dorall Collection': ['DORALL COLLECTION'],
    'CP Trendies': ['CP TRENDIES', 'CPT']
}

def clean_numeric(val):
    if isinstance(val, str):
        cleaned = val.replace('AED', '').replace('₹', '').replace('\xa0', '').replace(',', '').strip()
        try: return pd.to_numeric(cleaned)
        except: return val
    return val

def identify_brand_from_title(title):
    title_upper = str(title).upper()
    for brand, keywords in BRAND_KEYWORDS.items():
        if any(kw in title_upper for kw in keywords):
            return brand
    return 'Other'

def get_brand_from_campaign(campaign_name):
    name = str(campaign_name).upper().strip()
    for prefix, full_name in BRAND_MAP.items():
        if name.startswith(prefix + "_") or name.startswith(prefix + " ") or name.startswith(prefix + "-"):
            return full_name
    return "Unmapped"

def format_df(df):
    styled = df.copy()
    if 'Organic (%)' in styled.columns:
        styled['Organic (%)'] = styled['Organic (%)'].apply(lambda x: f"{x:.0%}")
    if 'Paid (%)' in styled.columns:
        styled['Paid (%)'] = styled['Paid (%)'].apply(lambda x: f"{x:.0%}")
    if 'T-ACOS' in styled.columns:
        styled['T-ACOS'] = styled['T-ACOS'].apply(lambda x: f"{x:.1%}")
    return styled

st.title("📊 Amazon Master Projections")

# --- SIDEBAR FILTERS ---
st.sidebar.header("🚀 Growth Projections")
roas_uplift = st.sidebar.slider("ROAS Uplift (%)", 0, 100, 20) / 100
organic_lift = st.sidebar.slider("Organic Contribution Lift (%)", 0, 50, 5) / 100

st.sidebar.divider()
ads_file = st.sidebar.file_uploader("1. Search Term Report (Ads)", type=["csv", "xlsx"])
biz_file = st.sidebar.file_uploader("2. Business Report (Total Sales)", type=["csv", "xlsx"])

if ads_file and biz_file:
    # 1. Load Data
    ads_df = pd.read_csv(ads_file).map(clean_numeric) if ads_file.name.endswith('.csv') else pd.read_excel(ads_file).map(clean_numeric)
    biz_df = pd.read_csv(biz_file).map(clean_numeric) if biz_file.name.endswith('.csv') else pd.read_excel(biz_file).map(clean_numeric)
    
    ads_df.columns = [c.strip() for c in ads_df.columns]
    biz_df.columns = [c.strip() for c in biz_df.columns]

    ad_sales_col = next((c for c in ads_df.columns if 'Sales' in c), None)
    biz_sales_col = next((c for c in biz_df.columns if 'Sales' in c), None)
    biz_title_col = next((c for c in biz_df.columns if 'Title' in c), None)

    ads_df['Brand'] = ads_df['Campaign Name'].apply(get_brand_from_campaign)
    biz_df['Brand'] = biz_df[biz_title_col].apply(identify_brand_from_title) if biz_title_col else "Unmapped"

    unique_brands = [b for b in BRAND_MAP.values() if b in ads_df['Brand'].unique()]
    brand_metrics = []

    # 2. Projection Logic for Each Brand
    for brand in unique_brands:
        b_ads = ads_df[ads_df['Brand'] == brand]
        b_biz_sales = biz_df[biz_df['Brand'] == brand][biz_sales_col].sum() if biz_sales_col else 0
        
        spend = b_ads['Spend'].sum()
        ad_sales = b_ads[ad_sales_col].sum() if ad_sales_col else 0
        clicks = b_ads['Clicks'].sum()
        imps = b_ads['Impressions'].sum()
        
        curr_roas = ad_sales / spend if spend > 0 else 0
        curr_org_pct = (b_biz_sales - ad_sales) / b_biz_sales if b_biz_sales > 0 else 0
        curr_cpc = spend / clicks if clicks > 0 else 0
        curr_ctr = clicks / imps if imps > 0 else 0
        
        # Apply Growth
        target_roas = curr_roas * (1 + roas_uplift)
        target_ad_rev = spend * target_roas
        target_org_pct = min(0.95, curr_org_pct + organic_lift)
        target_total_rev = target_ad_rev / (1 - target_org_pct) if target_org_pct < 1 else target_ad_rev
        
        target_clicks = spend / curr_cpc if curr_cpc > 0 else 0
        target_imps = target_clicks / curr_ctr if curr_ctr > 0 else 0

        brand_metrics.append({
            'Brand': brand, 'Imp': int(target_imps), 'Clicks': int(target_clicks),
            'Spends': spend, 'ROAS': round(target_roas, 2), 'Ad Revenue': round(target_ad_rev, 2),
            'Organic (%)': target_org_pct, 'Paid (%)': 1 - target_org_pct,
            'Organic Revenue': round(target_total_rev - target_ad_rev, 2),
            'Overall Revenue': round(target_total_rev, 2),
            'T-ROAS': round(target_total_rev / spend, 2) if spend > 0 else 0,
            'T-ACOS': (spend / target_total_rev) if target_total_rev > 0 else 0
        })

    proj_df = pd.DataFrame(brand_metrics)

    # 3. Create Tabs
    tabs = st.tabs(["🌎 Amazon Portfolio"] + unique_brands)

    # Tab 1: Overall Platform Overview
    with tabs[0]:
        st.subheader("Combined Amazon Platform Projections")
        t_spends = proj_df['Spends'].sum()
        t_ad_rev = proj_df['Ad Revenue'].sum()
        t_overall_rev = proj_df['Overall Revenue'].sum()
        t_org_rev = proj_df['Organic Revenue'].sum()
        
        overall_total = {
            'Brand': 'TOTAL AMAZON PLATFORM',
            'Imp': int(proj_df['Imp'].sum()), 'Clicks': int(proj_df['Clicks'].sum()),
            'Spends': t_spends, 'ROAS': round(t_ad_rev / t_spends, 2) if t_spends > 0 else 0,
            'Ad Revenue': t_ad_rev, 
            'Organic (%)': t_org_rev / t_overall_rev if t_overall_rev > 0 else 0,
            'Paid (%)': t_ad_rev / t_overall_rev if t_overall_rev > 0 else 0,
            'Organic Revenue': t_org_rev, 'Overall Revenue': t_overall_rev,
            'T-ROAS': round(t_overall_rev / t_spends, 2) if t_spends > 0 else 0,
            'T-ACOS': (t_spends / t_overall_rev) if t_overall_rev > 0 else 0
        }
        st.table(format_df(pd.DataFrame([overall_total])))

    # Individual Brand Tabs
    weights = [0.30, 0.20, 0.20, 0.20, 0.10] # 30/20/20/20/10 Split
    for i, brand in enumerate(unique_brands):
        with tabs[i+1]:
            st.subheader(f"{brand} - Next Month Projections")
            b_row = proj_df[proj_df['Brand'] == brand].iloc[0]
            st.markdown("#### Monthly Target")
            st.table(format_df(pd.DataFrame([b_row])))
            
            st.divider()
            st.markdown("#### Weekly Breakdown")
            weekly_rows = []
            for w, weight in enumerate(weights):
                weekly_rows.append({
                    "Week": f"Week {w+1}", "Imp": int(b_row['Imp'] * weight),
                    "Clicks": int(b_row['Clicks'] * weight), "Spends": b_row['Spends'] * weight,
                    "ROAS": b_row['ROAS'], "Ad Revenue": b_row['Ad Revenue'] * weight,
                    "Organic Revenue": b_row['Organic Revenue'] * weight,
                    "Overall Revenue": b_row['Overall Revenue'] * weight,
                    "T-ROAS": b_row['T-ROAS'], "T-ACOS": b_row['T-ACOS']
                })
            st.table(format_df(pd.DataFrame(weekly_rows)))

    # 4. Export Report
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        proj_df.to_excel(writer, sheet_name='Brand_Summary', index=False)
        pd.DataFrame([overall_total]).to_excel(writer, sheet_name='Platform_Total', index=False)
    st.sidebar.download_button("📥 Download Projection Report", data=output.getvalue(), file_name="Amazon_Platform_Projections.xlsx", use_container_width=True)

else:
    st.info("Upload your reports to see the Amazon Platform Overview and Brand-Specific Projections.")
