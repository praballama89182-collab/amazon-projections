def generate_projections(current_data_list):
    projections = []
    for brand_data in current_data_list:
        # 1. Apply 20% ROAS improvement
        current_roas = brand_data['ROAS']
        target_roas = current_roas * 1.20
        
        # 2. Calculate New Ad Revenue (at constant spend)
        target_ad_spend = brand_data['Ad Spend']
        projected_ad_revenue = target_ad_spend * target_roas
        
        # 3. Adjust Organic Ratio: Increase by 5% (e.g., 50% becomes 55%)
        # This reduces the Paid % share
        current_org_ratio = brand_data['org_contrib']
        target_org_ratio = min(0.95, current_org_ratio + 0.05) # Cap at 95%
        target_paid_ratio = 1 - target_org_ratio
        
        # 4. Calculate Total Revenue based on the new Paid Ratio
        # Total Revenue = Ad Revenue / Paid Ratio
        if target_paid_ratio > 0:
            projected_total_revenue = projected_ad_revenue / target_paid_ratio
        else:
            projected_total_revenue = projected_ad_revenue
            
        projected_organic_revenue = projected_total_revenue - projected_ad_revenue
        
        # Monthly Row
        monthly = {
            "Brand": brand_data['Brand'],
            "Period": "Monthly Projection",
            "Spends": target_ad_spend,
            "ROAS": target_roas,
            "Ad Revenue": projected_ad_revenue,
            "Organic (%)": target_org_ratio,
            "Paid (%)": target_paid_ratio,
            "Organic Revenue": projected_organic_revenue,
            "Overall Revenue": projected_total_revenue,
            "T-ACOS": (target_ad_spend / projected_total_revenue) if projected_total_revenue > 0 else 0
        }
        projections.append(monthly)
        
        # 5. Weekly Breakdown (Weeks 1-5)
        # Week 1-4 (7 days each), Week 5 (remaining 2-3 days or split evenly)
        for w in range(1, 6):
            projections.append({
                "Brand": brand_data['Brand'],
                "Period": f"Week {w}",
                "Spends": target_ad_spend / 5,
                "Ad Revenue": projected_ad_revenue / 5,
                "Organic Revenue": projected_organic_revenue / 5,
                "Overall Revenue": projected_total_revenue / 5,
                "ROAS": target_roas # Efficiency remains constant weekly
            })
            
    return pd.DataFrame(projections)
