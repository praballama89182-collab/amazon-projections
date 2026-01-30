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

st.title("📊 Amazon Master Dashboard")
st.markdown("### Next Month Projections (+20% ROAS | +5% Organic Lift)")

st.sidebar.header("Upload Files")
ads_file = st.sidebar.file_uploader("1. Search Term Report (Ads)", type=["csv", "xlsx"])
biz_file = st.sidebar.file_uploader("2. Business Report (Total Sales)", type=["csv", "xlsx"])

if ads_file and biz_file:
    # 1. Load & Clean
    ads_df = pd.read_csv(ads_file).map(clean_numeric) if ads_file.name.endswith('.csv') else pd.read_excel(ads_file).map(clean_numeric)
    biz_df = pd.read_csv(biz_file).map(clean_numeric) if biz_file.name.endswith('.csv') else pd.read_excel(biz_file).map(clean_numeric)
    
    ads_df.columns = [c.strip() for c in ads_df.columns]
    biz_df.columns = [c.strip() for c in biz_df.columns]

    ad_sales_col = next((c for c in ads_df.columns if 'Sales' in c), None)
    biz_sales_col = next((c for c in biz_df.columns if 'Sales' in c), None)
    biz_title_col = next((c for c in biz_df.columns if 'Title' in c), None)

    ads_df['Brand'] = ads_df['Campaign Name'].apply(get_brand_from_campaign)
    biz_df['Brand'] = biz_df[biz_title_col].apply(identify_brand_from_title) if biz_title_col else "Unmapped"

    current_metrics = []
    
    # Study current month and project next
    for prefix, full_name in BRAND_MAP.items():
        b_ads = ads_df[ads_df['Brand'] == full_name]
        b_biz_sales = biz_df[biz_df['Brand'] == full_name][biz_sales_col].sum() if biz_sales_col else 0
        
        spend = b_ads['Spend'].sum()
        ad_sales = b_ads[ad_sales_col].sum() if ad_sales_col else 0
        clicks = b_ads['Clicks'].sum()
        imps = b_ads['Impressions'].sum()
        
        # Current Ratios
        curr_roas = ad_sales / spend if spend > 0 else 0
        curr_org_pct = (b_biz_sales - ad_sales) / b_biz_sales if b_biz_sales > 0 else 0
        curr_cpc = spend / clicks if clicks > 0 else 0
        curr_ctr = clicks / imps if imps > 0 else 0
        
        # IMPROVEMENT LOGIC: +20% ROAS, +5% Organic
        target_roas = curr_roas * 1.20
        target_ad_rev = spend * target_roas
        target_org_pct = min(0.95, curr_org_pct + 0.05)
        target_total_rev = target_ad_rev / (1 - target_org_pct) if target_org_pct < 1 else target_ad_rev
        target_org_rev = target_total_rev - target_ad_rev
        
        # Projections
        target_clicks = spend / curr_cpc if curr_cpc > 0 else 0
        target_imps = target_clicks / curr_ctr if curr_ctr > 0 else 0

        current_metrics.append({
            'Brand': full_name,
            'Imp': int(target_imps),
            'Clicks': int(target_clicks),
            'Spends': spend,
            'ROAS': round(target_roas, 2),
            'Ad Revenue': round(target_ad_rev, 2),
            'Organic (%)': target_org_pct,
            'Paid (%)': 1 - target_org_pct,
            'Organic Revenue': round(target_org_rev, 2),
            'Overall Revenue': round(target_total_rev, 2),
            'T-ROAS': round(target_total_rev / spend, 2) if spend > 0 else 0,
            'T-ACOS': (spend / target_total_rev) if target_total_rev > 0 else 0
        })

    proj_df = pd.DataFrame(current_metrics)

    # CALCULATE GLOBAL TOTALS (The Combined Overview)
    total_spends = proj_df['Spends'].sum()
    total_ad_rev = proj_df['Ad Revenue'].sum()
    total_overall_rev = proj_df['Overall Revenue'].sum()
    total_org_rev = proj_df['Organic Revenue'].sum()
    
    global_total = {
        'Brand': '🌎 TOTAL PORTFOLIO',
        'Imp': int(proj_df['Imp'].sum()),
        'Clicks': int(proj_df['Clicks'].sum()),
        'Spends': total_spends,
        'ROAS': round(total_ad_rev / total_spends, 2) if total_spends > 0 else 0,
        'Ad Revenue': total_ad_rev,
        'Organic (%)': total_org_rev / total_overall_rev if total_overall_rev > 0 else 0,
        'Paid (%)': total_ad_rev / total_overall_rev if total_overall_rev > 0 else 0,
        'Organic Revenue': total_org_rev,
        'Overall Revenue': total_overall_rev,
        'T-ROAS': round(total_overall_rev / total_spends, 2) if total_spends > 0 else 0,
        'T-ACOS': (total_spends / total_overall_rev) if total_overall_rev > 0 else 0
    }
    
    # Formatting for display
    def format_df(df):
        styled = df.copy()
        styled['Organic (%)'] = styled['Organic (%)'].apply(lambda x: f"{x:.0%}")
        styled['Paid (%)'] = styled['Paid (%)'].apply(lambda x: f"{x:.0%}")
        styled['T-ACOS'] = styled['T-ACOS'].apply(lambda x: f"{x:.1%}")
        return styled

    # 1. Display Overview Section
    st.subheader("🌍 1. Combined Portfolio Overview")
    st.table(format_df(pd.DataFrame([global_total])))
    
    st.divider()
    
    st.subheader("🏢 2. Brand-Wise Performance Summary")
    st.table(format_df(proj_df))

    # 2. Weekly Projections
    st.divider()
    selected_brand = st.selectbox("Select Brand for Weekly Breakdown (30/20/20/20/10):", options=proj_df['Brand'].unique())
    
    brand_row = proj_df[proj_df['Brand'] == selected_brand].iloc[0]
    weights = [0.30, 0.20, 0.20, 0.20, 0.10]
    
    weekly_rows = []
    for i, weight in enumerate(weights):
        w_num = i + 1
        weekly_rows.append({
            "Sr. No": w_num,
            "Week": f"Week {w_num}",
            "Imp": int(brand_row['Imp'] * weight),
            "Clicks": int(brand_row['Clicks'] * weight),
            "Spends": brand_row['Spends'] * weight,
            "ROAS": brand_row['ROAS'],
            "Ad Revenue": brand_row['Ad Revenue'] * weight,
            "Organic (%)": f"{brand_row['Organic (%)']:.0%}",
            "Paid (%)": f"{(1-brand_row['Organic (%)']):.0%}",
            "Organic Revenue": brand_row['Organic Revenue'] * weight,
            "Overall Revenue": brand_row['Overall Revenue'] * weight,
            "T-ROAS": brand_row['T-ROAS'],
            "T-ACOS": f"{(brand_row['Spends']/brand_row['Overall Revenue']):.1%}"
        })
    
    st.write(f"### {selected_brand} - Weekly Targets")
    
    st.table(pd.DataFrame(weekly_rows))

    # 3. Export
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        proj_df.to_excel(writer, sheet_name='Monthly_Targets', index=False)
        pd.DataFrame([global_total]).to_excel(writer, sheet_name='Combined_Overview', index=False)
    st.download_button("📥 Download Master Multi-Tab Report", data=output.getvalue(), file_name="Amazon_Growth_Projections.xlsx", use_container_width=True)

else:
    st.info("Upload reports to generate the dashboard. Ensure campaign names start with brand prefixes (MA_, CL_, etc.).")
