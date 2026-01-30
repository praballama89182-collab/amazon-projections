import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO

st.set_page_config(page_title="PPC & Organic Master Dashboard", page_icon="📊", layout="wide")

# Brand Mapping & Keywords
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

def calculate_all_metrics(spend, ad_sales, imps, clicks, total_sales):
    organic_sales = max(0, total_sales - ad_sales)
    ad_contrib = (ad_sales / total_sales) if total_sales > 0 else 0
    org_contrib = (organic_sales / total_sales) if total_sales > 0 else 0
    roas = (ad_sales / spend) if spend > 0 else 0
    acos = (spend / ad_sales) if ad_sales > 0 else 0
    tacos = (spend / total_sales) if total_sales > 0 else 0
    ctr = (clicks / imps) if imps > 0 else 0
    cpc = (spend / clicks) if clicks > 0 else 0
    
    return {
        "organic_sales": organic_sales, "ad_contrib": ad_contrib, "org_contrib": org_contrib,
        "roas": roas, "acos": acos, "tacos": tacos, "ctr": ctr, "cpc": cpc
    }

def display_metrics_row(spend, ad_sales, imps, clicks, total_sales):
    m = calculate_all_metrics(spend, ad_sales, imps, clicks, total_sales)
    st.markdown("#### 💰 Sales & Efficiency")
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Overall Sales", f"{total_sales:,.2f}")
    c2.metric("Ad Sales", f"{ad_sales:,.2f}")
    c3.metric("Organic Sales", f"{m['organic_sales']:,.2f}")
    c4.metric("Ad Contribution", f"{m['ad_contrib']:.1%}")
    c5.metric("ROAS", f"{m['roas']:.2f}")

st.title("📊 Amazon Master Dashboard: Organic vs. Ads")
st.sidebar.header("Upload Files")
ads_file = st.sidebar.file_uploader("1. Search Term Report (Ads)", type=["csv", "xlsx"])
biz_file = st.sidebar.file_uploader("2. Business Report (Total Sales)", type=["csv", "xlsx"])

if ads_file and biz_file:
    # 1. Load Data
    ads_df = pd.read_csv(ads_file).map(clean_numeric) if ads_file.name.endswith('.csv') else pd.read_excel(ads_file).map(clean_numeric)
    biz_df = pd.read_csv(biz_file).map(clean_numeric) if biz_file.name.endswith('.csv') else pd.read_excel(biz_file).map(clean_numeric)
    
    ads_df.columns = [c.strip() for c in ads_df.columns]
    biz_df.columns = [c.strip() for c in biz_df.columns]
    
    ad_sales_col = next((c for c in ads_df.columns if 'Sales' in c), '7 Day Total Sales')
    biz_sales_col = next((c for c in biz_df.columns if 'Sales' in c), 'Ordered Product Sales')
    biz_title_col = next((c for c in biz_df.columns if 'Title' in c), None)

    ads_df['Brand'] = ads_df['Campaign Name'].apply(get_brand_from_campaign)
    biz_df['Brand'] = biz_df[biz_title_col].apply(identify_brand_from_title) if biz_title_col else "Unmapped"

    # 2. Process All Brands for Summary
    unique_brands = sorted([b for b in ads_df['Brand'].unique() if b != "Unmapped"])
    summary_data = []
    projection_data = []

    for brand in unique_brands:
        b_ads = ads_df[ads_df['Brand'] == brand]
        b_biz = biz_df[biz_df['Brand'] == brand]
        
        spend, ad_sales = b_ads['Spend'].sum(), b_ads[ad_sales_col].sum()
        imps, clicks = b_ads['Impressions'].sum(), b_ads['Clicks'].sum()
        total_sales = b_biz[biz_sales_col].sum()
        
        m = calculate_all_metrics(spend, ad_sales, imps, clicks, total_sales)
        summary_data.append({"Brand": brand, "Total Sales": total_sales, "Ad Sales": ad_sales, "Spend": spend, "ROAS": round(m['roas'], 2), "TACOS": f"{m['tacos']:.2%}"})

        # Growth Logic: +20% ROAS, +5% Organic Lift
        t_roas = m['roas'] * 1.20
        t_ad_rev = spend * t_roas
        t_org_pct = min(0.95, m['org_contrib'] + 0.05)
        t_total_rev = t_ad_rev / (1 - t_org_pct) if t_org_pct < 1 else t_ad_rev
        
        projection_data.append({
            'Brand': brand, 'Imp': int(imps * (t_ad_rev/ad_sales)) if ad_sales > 0 else 0,
            'Clicks': int(clicks * (t_ad_rev/ad_sales)) if ad_sales > 0 else 0,
            'Spends': spend, 'ROAS': round(t_roas, 2), 'Ad Revenue': round(t_ad_rev, 2),
            'Organic (%)': f"{t_org_pct:.0%}", 'Paid (%)': f"{(1-t_org_pct):.0%}",
            'Organic Revenue': round(t_total_rev - t_ad_rev, 2), 'Overall Revenue': round(t_total_rev, 2),
            'T-ROAS': round(t_total_rev / spend, 2) if spend > 0 else 0, 'T-ACOS': f"{(spend / t_total_rev):.1%}" if t_total_rev > 0 else "0%"
        })

    # 3. UI Tabs
    tabs = st.tabs(["🌍 Portfolio Overview", "🔮 Next Month Projections"] + unique_brands)

    with tabs[0]:
        display_metrics_row(ads_df['Spend'].sum(), ads_df[ad_sales_col].sum(), ads_df['Impressions'].sum(), ads_df['Clicks'].sum(), biz_df[biz_sales_col].sum())
        st.divider()
        st.subheader("🏢 Brand-Wise Performance")
        st.table(pd.DataFrame(summary_data))

    with tabs[1]:
        proj_df = pd.DataFrame(projection_data)
        st.subheader("Monthly Target Overview")
        st.table(proj_df)
        st.divider()
        
        selected_brand = st.selectbox("Select Brand for Weekly Breakdown (30/20/20/20/10):", options=unique_brands)
        brand_row = proj_df[proj_df['Brand'] == selected_brand].iloc[0]
        weights = [0.30, 0.20, 0.20, 0.20, 0.10]
        
        weekly_rows = []
        for i, weight in enumerate(weights):
            weekly_rows.append({
                "Week": f"Week {i+1}", "Imp": int(brand_row['Imp'] * weight), "Clicks": int(brand_row['Clicks'] * weight),
                "Spends": brand_row['Spends'] * weight, "ROAS": brand_row['ROAS'], "Ad Revenue": brand_row['Ad Revenue'] * weight,
                "Organic Revenue": brand_row['Organic Revenue'] * weight, "Overall Revenue": brand_row['Overall Revenue'] * weight,
                "T-ROAS": brand_row['T-ROAS'], "T-ACOS": brand_row['T-ACOS']
            })
        st.table(pd.DataFrame(weekly_rows))

    # Individual Tabs logic remains for drilldowns
    for i, brand in enumerate(unique_brands):
        with tabs[i+2]:
            b_ads = ads_df[ads_df['Brand'] == brand]
            display_metrics_row(b_ads['Spend'].sum(), b_ads[ad_sales_col].sum(), b_ads['Impressions'].sum(), b_ads['Clicks'].sum(), biz_df[biz_df['Brand'] == brand][biz_sales_col].sum())

    # 4. Export
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        proj_df.to_excel(writer, sheet_name='Projections', index=False)
        pd.DataFrame(summary_data).to_excel(writer, sheet_name='Current_Summary', index=False)
    st.sidebar.download_button("📥 Download Master Report", data=output.getvalue(), file_name="Amazon_Master_Report.xlsx", use_container_width=True)

else:
    st.info("Please upload both Search Term and Business reports.")
