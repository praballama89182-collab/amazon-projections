import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO

st.set_page_config(page_title="PPC & Organic Master Dashboard", page_icon="📊", layout="wide")

# Brand Mapping & Configuration
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
        # Cleans AED, INR, commas, and non-breaking spaces
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
        # Handles prefixes followed by underscore, space, or hyphen
        if name.startswith(prefix + "_") or name.startswith(prefix + " ") or name.startswith(prefix + "-") or name == prefix:
            return full_name
    return "Unmapped"

st.title("📊 Amazon Master Dashboard: Organic vs. Ads")
st.markdown("### Next Month Projections (+20% ROAS | +5% Organic Lift)")

# Sidebar for Uploads
st.sidebar.header("Upload Reports")
ads_file = st.sidebar.file_uploader("1. Search Term Report (Ads)", type=["csv", "xlsx"])
biz_file = st.sidebar.file_uploader("2. Business Report (Total Sales)", type=["csv", "xlsx"])

if ads_file and biz_file:
    # Load and Clean Data
    ads_df = pd.read_csv(ads_file).map(clean_numeric) if ads_file.name.endswith('.csv') else pd.read_excel(ads_file).map(clean_numeric)
    biz_df = pd.read_csv(biz_file).map(clean_numeric) if biz_file.name.endswith('.csv') else pd.read_excel(biz_file).map(clean_numeric)
    
    # Clean column headers (removes leading/trailing spaces)
    ads_df.columns = [c.strip() for c in ads_df.columns]
    biz_df.columns = [c.strip() for c in biz_df.columns]

    # Dynamically find essential columns
    ad_sales_col = next((c for c in ads_df.columns if 'Sales' in c), None)
    biz_sales_col = next((c for c in biz_df.columns if 'Sales' in c), None)
    biz_title_col = next((c for c in biz_df.columns if 'Title' in c), None)

    # Apply Brand Mapping
    ads_df['Brand'] = ads_df['Campaign Name'].apply(get_brand_from_campaign)
    biz_df['Brand'] = biz_df[biz_title_col].apply(identify_brand_from_title) if biz_title_col else "Unmapped"

    # DATA DEBUGGER (Check this if metrics are 0)
    with st.sidebar.expander("🛠 Data Mapping Debugger"):
        st.write("Campaign Brands Found:", ads_df['Brand'].unique())
        if "Unmapped" in ads_df['Brand'].values:
            st.warning("Found unmapped campaigns! Check naming conventions.")

    current_metrics = []
    
    for prefix, full_name in BRAND_MAP.items():
        # Filter data for this specific brand
        b_ads = ads_df[ads_df['Brand'] == full_name]
        b_biz_sales = biz_df[biz_df['Brand'] == full_name][biz_sales_col].sum() if biz_sales_col else 0
        
        spend = b_ads['Spend'].sum()
        ad_sales = b_ads[ad_sales_col].sum() if ad_sales_col else 0
        
        # Calculate Current Efficiency
        curr_roas = ad_sales / spend if spend > 0 else 0
        curr_org_pct = (b_biz_sales - ad_sales) / b_biz_sales if b_biz_sales > 0 else 0
        
        # PROJECTION LOGIC
        target_roas = curr_roas * 1.20
        target_ad_rev = spend * target_roas
        
        # Organic % improves by 5%
        target_org_pct = min(0.95, curr_org_pct + 0.05)
        target_paid_pct = 1 - target_org_pct
        
        # Recalculate Total Revenue based on new Paid Share
        target_total_rev = target_ad_rev / target_paid_pct if target_paid_pct > 0 else target_ad_rev
        target_org_rev = target_total_rev - target_ad_rev
        
        current_metrics.append({
            'Brand': full_name,
            'Spends (in ₹)': spend,
            'ROAS': round(target_roas, 2),
            'Ad Revenue (in ₹)': round(target_ad_rev, 2),
            'Organic (%)': f"{target_org_pct:.0%}",
            'Paid (%)': f"{target_paid_pct:.0%}",
            'Organic Revenue (in ₹)': round(target_org_rev, 2),
            'Overall Revenue (in ₹)': round(target_total_rev, 2),
            'T-ROAS': round(target_total_rev / spend, 2) if spend > 0 else 0,
            'T-ACOS': f"{(spend / target_total_rev):.1%}" if target_total_rev > 0 else "0%"
        })

    # Convert to Display DataFrame
    proj_df = pd.DataFrame(current_metrics)
    
    # 1. Main Table (Matching your reference image)
    st.subheader("Target Projections - Monthly Overview")
    st.table(proj_df)

    # 2. Weekly Projections (Weeks 1-5)
    st.divider()
    selected_brand = st.selectbox("Select Brand for Weekly Breakdown", options=proj_df['Brand'].unique())
    
    brand_row = proj_df[proj_df['Brand'] == selected_brand].iloc[0]
    weekly_rows = []
    for w in range(1, 6):
        weekly_rows.append({
            "Sr. No": w,
            "Week": f"Week {w}",
            "Spends": brand_row['Spends (in ₹)'] / 5,
            "Ad Revenue": brand_row['Ad Revenue (in ₹)'] / 5,
            "Organic Revenue": brand_row['Organic Revenue (in ₹)'] / 5,
            "Overall Revenue": brand_row['Overall Revenue (in ₹)'] / 5
        })
    
    st.write(f"### {selected_brand} - Weekly Targets")
    st.table(pd.DataFrame(weekly_rows))

    # 3. Multi-Tab Export
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        proj_df.to_excel(writer, sheet_name='Monthly_Targets', index=False)
        # Create a tab for each brand with weekly breakdown
        for b in BRAND_MAP.values():
            b_row = proj_df[proj_df['Brand'] == b]
            if not b_row.empty:
                b_row.to_excel(writer, sheet_name=b[:31], index=False)
                
    st.download_button(
        label="📥 Download Master Multi-Tab Report",
        data=output.getvalue(),
        file_name="Amazon_Growth_Projections.xlsx",
        use_container_width=True
    )

else:
    st.warning("Please upload both reports to activate the dashboard.")
    st.info("Ensure your campaign names start with: MA_, CL_, JPD_, PC_, DC_, or CPT_")
