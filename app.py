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

def format_styled_df(df):
    styled = df.copy()
    if 'Organic (%)' in styled.columns:
        styled['Organic (%)'] = styled['Organic (%)'].apply(lambda x: f"{x:.0%}" if isinstance(x, (int, float)) else x)
    if 'Paid (%)' in styled.columns:
        styled['Paid (%)'] = styled['Paid (%)'].apply(lambda x: f"{x:.0%}" if isinstance(x, (int, float)) else x)
    if 'T-ACOS' in styled.columns:
        styled['T-ACOS'] = styled['T-ACOS'].apply(lambda x: f"{x:.1%}" if isinstance(x, (int, float)) else x)
    return styled

st.title("📊 Amazon Master Projections")

# --- SIDEBAR FILTERS ---
st.sidebar.header("🚀 Growth Settings")
roas_uplift = st.sidebar.slider("ROAS Uplift (%)", 0, 100, 20) / 100
organic_lift = st.sidebar.slider("Organic Lift (%)", 0, 50, 5) / 100

st.sidebar.divider()
ads_file = st.sidebar.file_uploader("1. Ads Report", type=["csv", "xlsx"])
biz_file = st.sidebar.file_uploader("2. Business Report", type=["csv", "xlsx"])

if ads_file and biz_file:
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

    for brand in unique_brands:
        b_ads = ads_df[ads_df['Brand'] == brand]
        b_biz_sales = biz_df[biz_df['Brand'] == brand][biz_sales_col].sum() if biz_sales_col else 0
        spend, ad_sales = b_ads['Spend'].sum(), b_ads[ad_sales_col].sum() if ad_sales_col else 0
        clicks, imps = b_ads['Clicks'].sum(), b_ads['Impressions'].sum()
        
        c_roas = ad_sales / spend if spend > 0 else 0
        c_org_pct = (b_biz_sales - ad_sales) / b_biz_sales if b_biz_sales > 0 else 0
        c_cpc = spend / clicks if clicks > 0 else 0
        c_ctr = clicks / imps if imps > 0 else 0
        
        t_roas = c_roas * (1 + roas_uplift)
        t_ad_rev = spend * t_roas
        t_org_pct = min(0.95, c_org_pct + organic_lift)
        t_total_rev = t_ad_rev / (1 - t_org_pct) if t_org_pct < 1 else t_ad_rev
        
        brand_metrics.append({
            'Brand': brand, 'Imp': int((spend/c_cpc)/c_ctr) if c_cpc>0 and c_ctr>0 else 0,
            'Clicks': int(spend/c_cpc) if c_cpc>0 else 0, 'Spends': spend,
            'ROAS': round(t_roas, 2), 'Ad Revenue': round(t_ad_rev, 2),
            'Organic (%)': t_org_pct, 'Paid (%)': 1 - t_org_pct,
            'Organic Revenue': round(t_total_rev - t_ad_rev, 2), 'Overall Revenue': round(t_total_rev, 2),
            'T-ROAS': round(t_total_rev / spend, 2) if spend > 0 else 0,
            'T-ACOS': (spend / t_total_rev) if t_total_rev > 0 else 0
        })

    proj_df = pd.DataFrame(brand_metrics)
    
    # Platform Total Calculation
    ts, tar, tor, tr = proj_df['Spends'].sum(), proj_df['Ad Revenue'].sum(), proj_df['Overall Revenue'].sum(), proj_df['Organic Revenue'].sum()
    platform_total = pd.DataFrame([{
        'Brand': 'TOTAL AMAZON PLATFORM', 'Imp': int(proj_df['Imp'].sum()), 'Clicks': int(proj_df['Clicks'].sum()),
        'Spends': ts, 'ROAS': round(tar/ts, 2) if ts>0 else 0, 'Ad Revenue': tar,
        'Organic (%)': tr/tor if tor>0 else 0, 'Paid (%)': tar/tor if tor>0 else 0,
        'Organic Revenue': tr, 'Overall Revenue': tor, 'T-ROAS': round(tor/ts, 2) if ts>0 else 0, 'T-ACOS': ts/tor if tor>0 else 0
    }])

    tabs = st.tabs(["🌎 Amazon Portfolio"] + unique_brands)

    with tabs[0]:
        st.markdown("### 🏆 Combined Amazon Platform Projections")
        st.table(format_styled_df(platform_total))
        st.write("") # Spacing
        st.divider()
        st.markdown("### 🏢 Brand-Wise Summary")
        st.table(format_styled_df(proj_df))

    weights = [0.30, 0.20, 0.20, 0.20, 0.10] # 30/20/20/20/10
    all_weekly_data = []

    for i, brand in enumerate(unique_brands):
        with tabs[i+1]:
            st.subheader(f"📊 {brand} Projections")
            b_row = proj_df[proj_df['Brand'] == brand].iloc[0]
            st.table(format_styled_df(pd.DataFrame([b_row])))
            st.divider()
            st.markdown("#### 📅 Weekly Segregation")
            weekly_rows = []
            for w, wt in enumerate(weights):
                weekly_rows.append({
                    "Brand": brand, "Week": f"Week {w+1}", "Imp": int(b_row['Imp']*wt), "Clicks": int(b_row['Clicks']*wt),
                    "Spends": b_row['Spends']*wt, "ROAS": b_row['ROAS'], "Ad Revenue": b_row['Ad Revenue']*wt,
                    "Organic (%)": f"{b_row['Organic (%)']:.0%}", "Paid (%)": f"{(1-b_row['Organic (%)']):.0%}",
                    "Organic Revenue": b_row['Organic Revenue']*wt, "Overall Revenue": b_row['Overall Revenue']*wt,
                    "T-ROAS": b_row['T-ROAS'], "T-ACOS": f"{(b_row['Spends']/b_row['Overall Revenue']):.1%}"
                })
            weekly_df = pd.DataFrame(weekly_rows)
            st.table(weekly_df.drop(columns=['Brand']))
            all_weekly_data.append(weekly_df)

    # --- ENHANCED EXCEL EXPORT ---
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        format_styled_df(platform_total).to_excel(writer, sheet_name='Combined_Overview', index=False)
        format_styled_df(proj_df).to_excel(writer, sheet_name='Brand_Total_Summary', index=False)
        if all_weekly_data:
            pd.concat(all_weekly_data).to_excel(writer, sheet_name='Weekly_Overview', index=False)
        for i, brand in enumerate(unique_brands):
            format_styled_df(pd.DataFrame([proj_df[proj_df['Brand'] == brand].iloc[0]])).to_excel(writer, sheet_name=brand[:31], index=False)

    st.sidebar.divider()
    st.sidebar.download_button("📥 Download Master Multi-Tab Report", data=output.getvalue(), file_name="Amazon_Platform_Master_Report.xlsx", use_container_width=True)
else:
    st.info("Please upload Ads and Business reports to generate projections.")
