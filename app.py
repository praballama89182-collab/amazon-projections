import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO

st.set_page_config(page_title="PPC & Organic Projections", page_icon="📊", layout="wide")

# Brand Mapping Updated
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

def calculate_projections(row):
    """Applies +20% ROAS and +5% Organic Ratio logic."""
    target_roas = row['Current ROAS'] * 1.20
    target_ad_rev = row['Current Spend'] * target_roas
    
    # Organic % improves by 5% (0.05)
    target_org_pct = min(0.95, row['Current Org %'] + 0.05)
    target_paid_pct = 1 - target_org_pct
    
    # Recalculate Total Revenue based on new Paid Share
    target_overall_rev = target_ad_rev / target_paid_pct if target_paid_pct > 0 else target_ad_rev
    target_org_rev = target_overall_rev - target_ad_rev
    
    t_roas = target_overall_rev / row['Current Spend'] if row['Current Spend'] > 0 else 0
    t_acos = (row['Current Spend'] / target_overall_rev) if target_overall_rev > 0 else 0
    
    return pd.Series({
        'Spends': row['Current Spend'],
        'ROAS': round(target_roas, 2),
        'Ad Revenue': round(target_ad_rev, 2),
        'Organic (%)': f"{target_org_pct:.0%}",
        'Paid (%)': f"{target_paid_pct:.0%}",
        'Organic Revenue': round(target_org_rev, 2),
        'Overall Revenue': round(target_overall_rev, 2),
        'T-ROAS': round(t_roas, 2),
        'T-ACOS': f"{t_acos:.1%}"
    })

st.title("Amazon Projections: +20% ROAS & +5% Organic Lift")

ads_file = st.sidebar.file_uploader("Upload Search Term Report", type=["csv", "xlsx"])
biz_file = st.sidebar.file_uploader("Upload Business Report", type=["csv", "xlsx"])

if ads_file and biz_file:
    # Processing logic
    ads_df = pd.read_csv(ads_file).map(clean_numeric) if ads_file.name.endswith('.csv') else pd.read_excel(ads_file).map(clean_numeric)
    biz_df = pd.read_csv(biz_file).map(clean_numeric) if biz_file.name.endswith('.csv') else pd.read_excel(biz_file).map(clean_numeric)
    
    # 1. Prepare Current State
    ads_df['Brand'] = ads_df['Campaign Name'].apply(lambda x: BRAND_MAP.get(str(x).split('_')[0].upper(), 'Other'))
    biz_df['Brand'] = biz_df[next(c for c in biz_df.columns if 'Title' in c)].apply(identify_brand_from_title)
    
    current_metrics = []
    unique_brands = [b for b in BRAND_MAP.values() if b in ads_df['Brand'].unique()]

    for brand in unique_brands:
        b_ads = ads_df[ads_df['Brand'] == brand]
        b_total_sales = biz_df[biz_df['Brand'] == brand][next(c for c in biz_df.columns if 'Sales' in c)].sum()
        
        spend = b_ads['Spend'].sum()
        ad_sales = b_ads[next(c for c in ads_df.columns if 'Sales' in c)].sum()
        
        current_metrics.append({
            'Brand': brand,
            'Current Spend': spend,
            'Current ROAS': ad_sales / spend if spend > 0 else 0,
            'Current Org %': (b_total_sales - ad_sales) / b_total_sales if b_total_sales > 0 else 0
        })

    # 2. Generate Projection Table
    base_df = pd.DataFrame(current_metrics)
    proj_df = base_df.apply(calculate_projections, axis=1)
    proj_df.insert(0, 'Brand', base_df['Brand'])

    # 3. Display per Image Format
    st.subheader("Target Projections - Monthly Overview")
    st.table(proj_df)

    # 4. Weekly Breakdown Tabs
    tabs = st.tabs(unique_brands)
    for i, brand in enumerate(unique_brands):
        with tabs[i]:
            st.write(f"### {brand} Weekly Projection")
            brand_row = proj_df[proj_df['Brand'] == brand].iloc[0]
            
            weekly_data = []
            for w in range(1, 6):
                weekly_data.append({
                    "Week": f"Week {w}",
                    "Spends": brand_row['Spends'] / 5,
                    "Ad Revenue": brand_row['Ad Revenue'] / 5,
                    "Organic Revenue": brand_row['Organic Revenue'] / 5,
                    "Overall Revenue": brand_row['Overall Revenue'] / 5
                })
            st.dataframe(pd.DataFrame(weekly_data), use_container_width=True)

    # 5. Export
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        proj_df.to_excel(writer, sheet_name='Monthly_Targets', index=False)
    st.download_button("📥 Download Projection Report", data=output.getvalue(), file_name="Amazon_Projections.xlsx")
