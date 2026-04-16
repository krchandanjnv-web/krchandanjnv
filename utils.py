import pandas as pd
from fpdf import FPDF
from datetime import date, timedelta
import numpy as np

def get_advanced_kpis(df: pd.DataFrame):
    if df.empty:
        return {"streak": 0, "days_since_start": 0, "days_missed": 0, "top_focus": "N/A"}
        
    today = date.today()
    df['created_date'] = pd.to_datetime(df['created_at']).dt.date
    df['completed_date'] = pd.to_datetime(df['completed_at'], errors='coerce').dt.date
    
    start_date = df['created_date'].min()
    if pd.isna(start_date): start_date = today
    
    days_since_start = (today - start_date).days
    
    completed_df = df[df['status'] == 'Completed'].copy()
    if completed_df.empty:
        return {"streak": 0, "days_since_start": days_since_start, "days_missed": days_since_start, "top_focus": "N/A"}
        
    top_focus = completed_df['category'].mode()[0] if not completed_df.empty else "N/A"
    
    active_days = set(completed_df['completed_date'].dropna())
    
    total_possible_days = days_since_start + 1
    days_missed = total_possible_days - len(active_days)
    if days_missed < 0: days_missed = 0
    
    streak = 0
    check_date = today
    if check_date not in active_days:
        check_date -= timedelta(days=1)
        
    while check_date in active_days:
        streak += 1
        check_date -= timedelta(days=1)
            
    return {
        "streak": streak,
        "days_since_start": days_since_start,
        "days_missed": days_missed,
        "top_focus": top_focus
    }

def generate_heatmap_data(df: pd.DataFrame, days_back=30):
    today = date.today()
    if days_back == 0:
        min_date = pd.to_datetime(df['completed_at']).dt.date.min() if not df.empty else today
        if pd.isna(min_date): min_date = today
        days_back = (today - min_date).days + 1
        
    date_range = pd.date_range(end=today, periods=max(1, days_back)).date
    
    completed_df = df[df['status'] == 'Completed'].copy()
    if not completed_df.empty:
        completed_df['completed_date'] = pd.to_datetime(completed_df['completed_at'], errors='coerce').dt.date
        date_counts = completed_df['completed_date'].value_counts().to_dict()
    else:
        date_counts = {}
         
    heat_df = pd.DataFrame({'Date': date_range})
    heat_df['Work Done'] = heat_df['Date'].map(date_counts).fillna(0)
    
    heat_df['Day'] = pd.to_datetime(heat_df['Date']).dt.day_name()
    heat_df['Week'] = pd.to_datetime(heat_df['Date']).dt.strftime('Week %U (%b)') # Week number with month
    
    pivot = heat_df.pivot(index='Day', columns='Week', values='Work Done').fillna(0)
    days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    pivot = pivot.reindex(days_order)
    return pivot

def generate_weekly_bar_data(df: pd.DataFrame, days_back=7):
    today = date.today()
    if days_back == 0:
        min_date = pd.to_datetime(df['completed_at']).dt.date.min() if not df.empty else today
        if pd.isna(min_date): min_date = today
        days_back = (today - min_date).days + 1
        
    date_range = pd.date_range(end=today, periods=max(1, days_back)).date
    
    completed_df = df[df['status'] == 'Completed'].copy()
    if not completed_df.empty:
        completed_df['completed_date'] = pd.to_datetime(completed_df['completed_at'], errors='coerce').dt.date
        date_counts = completed_df['completed_date'].value_counts().to_dict()
    else:
        date_counts = {}
        
    bar_df = pd.DataFrame({'Date': date_range})
    bar_df['Tasks Completed'] = bar_df['Date'].map(date_counts).fillna(0)
    bar_df['Day Label'] = pd.to_datetime(bar_df['Date']).dt.strftime('%A (%m/%d)')
    return bar_df

def get_screenshot_kpis(df: pd.DataFrame, days_back: int):
    today = date.today()
    if days_back == 0:
        valid_dates = pd.to_datetime(df['completed_at'], errors='coerce').dropna()
        min_date = valid_dates.dt.date.min() if not valid_dates.empty else today
        if pd.isna(min_date): min_date = today
        days_back = (today - min_date).days + 1
    days_back = max(1, days_back)
    cutoff = today - timedelta(days=days_back-1)
    
    df['completed_date'] = pd.to_datetime(df['completed_at'], errors='coerce').dt.date
    current_df = df[(df['status'] == 'Completed') & (df['completed_date'] >= cutoff)]
    
    active_days = set(current_df['completed_date'].dropna())
    consistency = (len(active_days) / days_back) * 100 if days_back > 0 else 0
    
    prev_cutoff = cutoff - timedelta(days=days_back)
    prev_df = df[(df['status'] == 'Completed') & (df['completed_date'] >= prev_cutoff) & (df['completed_date'] < cutoff)]
    curr_count = len(current_df)
    prev_count = len(prev_df)
    if prev_count == 0:
        growth_trend = 100.0 if curr_count > 0 else 0.0
    else:
        growth_trend = ((curr_count - prev_count) / prev_count) * 100
        
    global_active = set(df[df['status'] == 'Completed']['completed_date'].dropna())
    streak = 0
    check_date = today
    if check_date not in global_active:
        check_date -= timedelta(days=1)
    while check_date in global_active:
        streak += 1
        check_date -= timedelta(days=1)
        
    top_focus = current_df['category'].mode()[0] if not current_df.empty else "-"
    
    avg_len = curr_count / len(active_days) if len(active_days) > 0 else 0.0
    
    return {
        "consistency": f"{int(consistency)}%",
        "growth_trend": f"{int(growth_trend)}%",
        "streak": str(streak),
        "top_focus": top_focus,
        "avg_length": f"{avg_len:.1f}t"
    }

def generate_daily_line_data(df: pd.DataFrame, days_back=7):
    today = date.today()
    if days_back == 0:
        min_date = pd.to_datetime(df['completed_at']).dt.date.min() if not df.empty else today
        if pd.isna(min_date): min_date = today
        days_back = (today - min_date).days + 1
        
    date_range = pd.date_range(end=today, periods=max(1, days_back)).date
    
    completed_df = df[df['status'] == 'Completed'].copy()
    if not completed_df.empty:
        completed_df['completed_date'] = pd.to_datetime(completed_df['completed_at'], errors='coerce').dt.date
        date_counts = completed_df['completed_date'].value_counts().to_dict()
    else:
        date_counts = {}
        
    line_df = pd.DataFrame({'Date': date_range})
    line_df['Tasks Completed'] = line_df['Date'].map(date_counts).fillna(0)
    return line_df

def get_level_info(total_xp: int):
    level = 1
    xp_required = 0
    next_level_xp = 100
    
    while total_xp >= next_level_xp:
        level += 1
        xp_required = next_level_xp
        cost_for_next = 100 + (level * 50)
        next_level_xp += cost_for_next
        
    current_level_progress = total_xp - xp_required
    xp_to_next = next_level_xp - xp_required
    percent = current_level_progress / xp_to_next
    
    return {
        "level": level,
        "total_xp": total_xp,
        "progress_percent": percent,
        "current_level_xp": current_level_progress,
        "xp_to_next": xp_to_next,
        "next_level_xp": next_level_xp,
        "base_xp": xp_required
    }

def calculate_gamification(df: pd.DataFrame):
    if df.empty:
        return get_level_info(0)
    completed_df = df[df['status'] == 'Completed']
    xp_map = {"High": 50, "Medium": 20, "Low": 10}
    total_xp = completed_df['priority'].map(xp_map).fillna(0).sum()
    return get_level_info(int(total_xp))

def get_trophies(df: pd.DataFrame):
    trophies = []
    if df.empty: return trophies
    
    completed_df = df[df['status'] == 'Completed']
    total_completed = len(completed_df)
    
    if total_completed >= 1:
        trophies.append({"name": "Novice Tracker", "icon": "🥉", "desc": "Completed your first task."})
    
    high_count = len(completed_df[completed_df['priority'] == 'High'])
    if high_count >= 5:
        trophies.append({"name": "High Roller", "icon": "💎", "desc": "Completed 5 High-Priority tasks."})
    elif high_count >= 1:
        trophies.append({"name": "Taste of Danger", "icon": "🎲", "desc": "Completed your first High-Priority task."})
        
    kpis = get_screenshot_kpis(df, days_back=30)
    streak = int(kpis["streak"])
    if streak >= 3:
        trophies.append({"name": "Momentum", "icon": "🔥", "desc": "Achieved a 3-Day task streak."})
    if streak >= 7:
        trophies.append({"name": "Unstoppable", "icon": "🚀", "desc": "Achieved a 7-Day task streak."})
        
    if total_completed >= 50:
        trophies.append({"name": "Half-Century", "icon": "🛡️", "desc": "Completed 50 tasks."})
    if total_completed >= 100:
        trophies.append({"name": "Centurion", "icon": "👑", "desc": "Completed 100 tasks."})
        
    return trophies

def generate_pdf_report(df_tasks: pd.DataFrame, user_email: str) -> bytearray:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("helvetica", "B", 16)
    pdf.cell(0, 10, "Weekly Task & Analytics Summary", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.set_font("helvetica", "I", 10)
    pdf.cell(0, 10, f"Generated for: {user_email} on {date.today()}", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(10)
    
    if df_tasks.empty:
        pdf.set_font("helvetica", "", 12)
        pdf.cell(0, 10, "No tasks found for this period.", new_x="LMARGIN", new_y="NEXT")
        return pdf.output()
        
    total_tasks = len(df_tasks)
    completed_df = df_tasks[df_tasks['status'] == 'Completed']
    completed_count = len(completed_df)
    pending_count = total_tasks - completed_count
    completion_rate = (completed_count / total_tasks * 100) if total_tasks > 0 else 0
    kpis = get_advanced_kpis(df_tasks)
    
    pdf.set_font("helvetica", "B", 12)
    pdf.cell(0, 10, "Key Performance Indicators:", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("helvetica", "", 12)
    pdf.cell(0, 10, f"- Total Tasks: {total_tasks}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 10, f"- Completed Tasks: {completed_count}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 10, f"- Completion Rate: {completion_rate:.1f}%", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 10, f"- Active Streak: {kpis['streak']} days", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 10, f"- Top Focus Area: {kpis['top_focus']}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(10)
    
    pdf.set_font("helvetica", "B", 12)
    pdf.cell(0, 10, "Pending Tasks:", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("helvetica", "", 11)
    
    pending_df = df_tasks[df_tasks['status'] == 'Pending']
    if pending_df.empty:
        pdf.cell(0, 10, "None! All caught up.", new_x="LMARGIN", new_y="NEXT")
    else:
        for _, row in pending_df.iterrows():
            txt = f"[ ] {row['title']} (Priority: {row['priority']}, Due: {row['deadline']})"
            clean_txt = txt.encode('latin-1', 'replace').decode('latin-1')
            pdf.cell(0, 8, clean_txt, new_x="LMARGIN", new_y="NEXT")
            
    return pdf.output()
