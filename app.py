import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO

st.set_page_config(page_title="PPC & Organic Projections", page_icon="📊", layout="wide")

# Updated Brand Mapping
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

st.title("Amazon Projections: +20% ROAS & +5% Organic Lift")

ads_file = st.sidebar.file_uploader("Upload Search Term Report", type=["csv", "xlsx"])
biz_file = st.sidebar.file_uploader("Upload Business Report", type=["csv", "xlsx"])

if ads_file and biz_file:
    # Use map instead of applymap for Python 3.13 compatibility
    ads_df = pd.read_csv(ads_file).map(clean_numeric) if ads_file.name.endswith('.csv') else pd.read_excel(ads_file).map(clean_numeric)
    biz_df = pd.read_csv(biz_file).map(clean_numeric) if biz_file.name.endswith('.csv') else pd.read_excel(biz_file).map(clean_numeric)
    
    # Identify Columns Dynamically
    ad_sales_col = next((c for c in ads_df.columns if 'Sales' in c), None)
    biz_sales_col = next((c for c in biz_df.columns if 'Sales' in c), None)
    biz_title_col = next((c for c in biz_df.columns if 'Title' in c), None)

    # 1. Map Brands
    ads_df['Brand'] = ads_df['Campaign Name'].apply(lambda x: BRAND_MAP.get(str(x).split('_')[0].upper(), 'Other Brand'))
    biz_df['Brand'] = biz_df[biz_title_col].apply(identify_brand_from_title)
    
    current_metrics = []
    # Loop through our known brands
    for prefix, full_name in BRAND_MAP.items():
        b_ads = ads_df[ads_df['Brand'] == full_name]
        b_total_sales = biz_df[biz_df['Brand'] == full_name][biz_sales_col].sum()
        
        spend = b_ads['Spend'].sum()
        ad_sales = b_ads[ad_sales_col].sum() if ad_sales_col else 0
        
        # Calculate Base Metrics
        roas = ad_sales / spend if spend > 0 else 0
        org_pct = (b_total_sales - ad_sales) / b_total_sales if b_total_sales > 0 else 0
        
        # Apply Growth Logic: +20% ROAS, +5% Organic Ratio
        t_roas = roas * 1.20
        t_ad_rev = spend * t_roas
        t_org_pct = min(0.95, org_pct + 0.05)
        t_paid_pct = 1 - t_org_pct
        t_overall_rev = t_ad_rev / t_paid_pct if t_paid_pct > 0 else t_ad_rev
        t_org_rev = t_overall_rev - t_ad_rev
        
        current_metrics.append({
            'Brand': full_name,
            'Spends (in ₹)': spend,
            'ROAS': round(t_roas, 2),
            'Ad Revenue (in ₹)': round(t_ad_rev, 2),
            'Organic (%)': f"{t_org_pct:.0%}",
            'Paid (%)': f"{t_paid_pct:.0%}",
            'Organic Revenue (in ₹)': round(t_org_rev, 2),
            'Overall Revenue (in ₹)': round(t_overall_rev, 2),
            'T-ROAS': round(t_overall_rev / spend, 2) if spend > 0 else 0,
            'T-ACOS': f"{(spend / t_overall_rev):.1%}" if t_overall_rev > 0 else "0%"
        })

    # Final DataFrame Construction
    proj_df = pd.DataFrame(current_metrics)

    # 3. Display per Image Format
    st.subheader("Target Projections - Monthly Overview")
    st.table(proj_df)

    # 4. Weekly Breakdown (1 to 5)
    st.divider()
    selected_brand = st.selectbox("Select Brand for Weekly Breakdown", options=proj_df['Brand'].unique())
    
    brand_row = proj_df[proj_df['Brand'] == selected_brand].iloc[0]
    weekly_data = []
    for w in range(1, 6):
        weekly_data.append({
            "Sr. No": w,
            "Week": f"Week {w}",
            "Spends": brand_row['Spends (in ₹)'] / 5,
            "Ad Revenue": brand_row['Ad Revenue (in ₹)'] / 5,
            "Organic Revenue": brand_row['Organic Revenue (in ₹)'] / 5,
            "Overall Revenue": brand_row['Overall Revenue (in ₹)'] / 5
        })
    st.write(f"### {selected_brand} - Weekly Targets")
    st.dataframe(pd.DataFrame(weekly_data), use_container_width=True)

    # 5. Export
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        proj_df.to_excel(writer, sheet_name='Monthly_Targets', index=False)
    st.download_button("📥 Download Projection Report", data=output.getvalue(), file_name="Amazon_Projections.xlsx", use_container_width=True)
else:
    st.info("Please upload both the Search Term and Business reports to generate projections.")
