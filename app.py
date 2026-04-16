import streamlit as st
import json
from auth import login, logout
from gsheets_db import fetch_all_tasks, save_task, update_task_status, delete_task, update_subtasks, cleanup_old_tasks, get_google_sheet
import google.generativeai as genai
import pandas as pd
import plotly.express as px
from datetime import datetime, date, timedelta
from utils import generate_pdf_report, get_advanced_kpis, get_screenshot_kpis, generate_heatmap_data, generate_weekly_bar_data, generate_daily_line_data, calculate_gamification, get_trophies

st.set_page_config(page_title="Task & Analytics Dashboard", page_icon="📈", layout="wide")

st.title("Task Management & Analytics Dashboard")

# CSS Theme Injection Matching the Mockup
st.markdown("""
<style>
/* White cards matching screenshot */
.kpi-card {
    background-color: white;
    border-radius: 12px;
    padding: 20px;
    text-align: center;
    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    border-top: 4px solid #ff4b4b; /* red top border */
    margin-bottom: 5px;
    color: #333 !important;
}
.kpi-card div {
    color: #333 !important;
}
.kpi-icon {
    font-size: 2.5em;
    margin-bottom: 10px;
}
.kpi-val {
    color: #e11d48 !important;
    font-size: 2.2em;
    font-weight: bold;
    margin: 5px 0;
}
.kpi-title {
    font-size: 0.8em;
    font-weight: 800;
    color: #333;
    letter-spacing: 0.5px;
    text-transform: uppercase;
}
.kpi-sub {
    font-size: 0.7em;
    color: #888 !important;
}

/* Chart Title Underlines */
.section-title {
    font-size: 1.5em;
    font-weight: bold;
    margin-bottom: 5px;
    display: inline-block;
}
.section-underline {
    height: 3px;
    background-color: #e11d48;
    width: 100%;
    margin-bottom: 15px;
}

/* White background for visual containers Native */
div[data-testid="stVerticalBlockBorderWrapper"] > div {
    background-color: white !important;
    border-radius: 12px !important;
    border: none !important;
    box-shadow: 0 4px 6px rgba(0,0,0,0.1) !important;
    padding: 20px !important;
    color: #333 !important;
}

</style>
""", unsafe_allow_html=True)

# Authentication Check
user_email = login()

if not user_email:
    st.stop()

# Load tasks
df_tasks = fetch_all_tasks(user_email)

# --- PHASE 4: GAMIFICATION ENGINE ---
if 'previous_level' not in st.session_state:
    st.session_state.previous_level = None

level_info = calculate_gamification(df_tasks)

if st.session_state.previous_level is not None and level_info['level'] > st.session_state.previous_level:
    st.balloons()
st.session_state.previous_level = level_info['level']

# Header: show logged-in user and logout button
col_head1, col_head2, col_head3 = st.columns([5, 4, 1])
with col_head1:
    st.subheader(f"Welcome, {user_email}")
with col_head2:
    st.markdown(f"**🏅 Level {level_info['level']}** | {level_info['current_level_xp']} / {level_info['xp_to_next']} XP to Level {level_info['level'] + 1}")
    st.progress(level_info['progress_percent'])
with col_head3:
    if st.button("Logout"):
        logout()

# Phase 6: Global Notification System and Smart Sorting
today_date = date.today()
def get_dl_status(str_date):
    if not str_date: return "No Due Date", 3
    try:
        d = datetime.strptime(str_date, "%Y-%m-%d").date()
        if d < today_date: return "Overdue", 0
        if d == today_date: return "Due Today", 1
        return "Upcoming", 2
    except:
        return "Unknown", 3

pending_global = df_tasks[df_tasks['status'] == 'Pending'].copy()
if not pending_global.empty:
    pending_global['deadline_status'] = pending_global['deadline'].apply(lambda x: get_dl_status(x)[0])
    pending_global['sort_order'] = pending_global['deadline'].apply(lambda x: get_dl_status(x)[1])
    pr_m = {"High": 0, "Medium": 1, "Low": 2}
    pending_global['priority_order'] = pending_global['priority'].map(pr_m).fillna(3)
    pending_global = pending_global.sort_values(by=['sort_order', 'priority_order'])
    
    overdue_ct = len(pending_global[pending_global['deadline_status'] == 'Overdue'])
    today_ct = len(pending_global[pending_global['deadline_status'] == 'Due Today'])
    if overdue_ct > 0 or today_ct > 0:
        st.error(f"🚨 **ACTION REQUIRED**: You have {overdue_ct} Overdue and {today_ct} task(s) Due Today.")
else:
    pending_global['deadline_status'] = "Upcoming"

# Tab Layout
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📋 Task Manager", "📊 Analytics & Insights", "🏆 Trophy Room", "🤖 AI Coach", "🌐 Leaderboard"])

# --- PHASE 8: DEEP WORK ENGINE ---
with st.sidebar:
    st.header("⏱️ Deep Work Engine")
    if 'focus_start' not in st.session_state:
        st.session_state.focus_start = None
        
    if st.session_state.focus_start is None:
        if st.button("▶️ Start Focus Session"):
            st.session_state.focus_start = datetime.now()
            st.rerun()
    else:
        st.warning(f"Focusing since {st.session_state.focus_start.strftime('%H:%M')}")
        if st.button("⏹️ End Session"):
            elapsed = datetime.now() - st.session_state.focus_start
            minutes = elapsed.total_seconds() / 60
            st.session_state.focus_start = None
            if minutes >= 25:
                import uuid
                sheet = get_google_sheet()
                if sheet:
                    row_data = [str(uuid.uuid4()), user_email, f"Focus Block ({int(minutes)}m)", "Meditation", "High", "Completed", str(date.today()), datetime.now().isoformat(), datetime.now().isoformat(), "[]"]
                    sheet.append_row(row_data)
                st.success("25m+ Focus Completed! +50 XP Awarded!")
            else:
                st.info(f"Session ended ({int(minutes)}m). Need 25m for XP!")
            st.rerun()
            
    st.divider()
    st.info("Work for 25+ minutes strictly uninterrupted to earn a 50 XP Focus Bounty.")

with tab1:
    st.header("Task Manager")
    
    # Task Input Form
    with st.form("new_task_form", clear_on_submit=True):
        st.subheader("Add a New Task")
        col1, col2 = st.columns(2)
        
        with col1:
            title = st.text_input("Task Title", placeholder="Enter task name...")
            
        with col2:
            template = st.selectbox("Quick Templates (Optional)", ["None", "Study", "Exercise", "Meditation", "Work", "Reading"])
            
        col3, col4, col5 = st.columns([2, 2, 1])
        with col3:
            priority = st.selectbox("Priority", ["High", "Medium", "Low"])
        with col4:
            deadline = st.date_input("Deadline", min_value=date.today())
        with col5:
            st.markdown("<br>", unsafe_allow_html=True)
            is_habit = st.checkbox("🔁 Daily Habit")
            
        submit = st.form_submit_button("Add Task")
        
        if submit:
            final_title = template if template != "None" and not title else title
            final_category = template if template != "None" else "General"
            if is_habit:
                final_category += " [HABIT]"
                
            if final_title:
                success = save_task(user_email, final_title, final_category, priority, str(deadline))
                if success:
                    st.success("Task Added successfully!")
                    st.rerun()
            else:
                st.error("Please provide a task title or select a template.")
                
    st.divider()
    
    # --- PHASE 2: SEARCH & FILTER ENGINE ---
    search_col, filter_col = st.columns([2, 1])
    with search_col:
        search_term = st.text_input("🔍 Search tasks by title...", "")
    with filter_col:
        available_categories = ["Study", "Exercise", "Meditation", "Work", "Reading", "General"]
        if not df_tasks.empty:
            available_categories = list(df_tasks['category'].unique())
        category_filter = st.multiselect("Filter by Category", available_categories)
        
    st.subheader("Your Tasks")
    
    if not df_tasks.empty:
        filtered_df = df_tasks.copy()
        
        # Apply Search Filter (Case Insensitive)
        if search_term:
            filtered_df = filtered_df[filtered_df['title'].str.contains(search_term, case=False, na=False)]
        
        # Apply Category Filter
        if category_filter:
            filtered_df = filtered_df[filtered_df['category'].isin(category_filter)]
            
        completed_tasks = filtered_df[filtered_df['status'] == 'Completed']
        
        # Merge global sorting attributes back into pending_tasks
        pending_tasks = filtered_df[filtered_df['status'] == 'Pending'].copy()
        if not pending_tasks.empty:
            pending_tasks['deadline_status'] = pending_tasks['deadline'].apply(lambda x: get_dl_status(x)[0])
            pending_tasks['sort_order'] = pending_tasks['deadline'].apply(lambda x: get_dl_status(x)[1])
            pr_m = {"High": 0, "Medium": 1, "Low": 2}
            pending_tasks['priority_order'] = pending_tasks['priority'].map(pr_m).fillna(3)
            pending_tasks = pending_tasks.sort_values(by=['sort_order', 'priority_order'])
        else:
            pending_tasks['deadline_status'] = "Upcoming"
            
        st.write(f"**Pending Tasks:** {len(pending_tasks)}")
        
        for index, row in pending_tasks.iterrows():
            dl_status = row.get('deadline_status', "Upcoming")
            if dl_status == "Overdue":
                dl_emoji = "🚨"
                dl_text = f"**<span style='color:#e11d48'>[OVERDUE] {row['deadline']}</span>**"
            elif dl_status == "Due Today":
                dl_emoji = "⚠️"
                dl_text = f"**<span style='color:#ff8c00'>[DUE TODAY] {row['deadline']}</span>**"
            else:
                dl_emoji = "📌"
                dl_text = f"📅 {row['deadline']}"

            with st.expander(f"{dl_emoji} {row['title']} - {dl_status}"):
                col_a, col_b, col_c = st.columns([1, 6, 2])
                with col_a:
                    do_complete = st.checkbox("Done", key=f"check_{row['id']}")
                with col_b:
                    priority_emoji = "🔴" if row['priority'] == "High" else "🟡" if row['priority'] == "Medium" else "🟢"
                    xp_val = 50 if row['priority'] == "High" else 20 if row['priority'] == "Medium" else 10
                    habit_badge = " **🔁 HABIT** " if "[HABIT]" in str(row.get('category','')) else ""
                    st.markdown(f"**Main Task** <span style='font-size:0.8em; color:gray'>[+{xp_val} XP]</span> | {priority_emoji} {row['priority']} | {dl_text}{habit_badge}", unsafe_allow_html=True)
                with col_c:
                    if st.button("Delete", key=f"del_{row['id']}", help="Delete Task"):
                        delete_task(row['id'])
                        st.rerun()
                        
                # --- SUBTASKS UI ---
                st.markdown("---")
                try:
                    subtasks = json.loads(row['subtasks']) if isinstance(row['subtasks'], str) else []
                except:
                    subtasks = []
                
                if subtasks:
                    for s_idx, stask in enumerate(subtasks):
                        s_col1, s_col2 = st.columns([6, 1])
                        with s_col1:
                            sub_done = st.checkbox(stask['title'], value=stask['done'], key=f"sub_{row['id']}_{s_idx}")
                            if sub_done != stask['done']:
                                subtasks[s_idx]['done'] = sub_done
                                update_subtasks(row['id'], json.dumps(subtasks))
                                st.rerun()
                        with s_col2:
                            if st.button("x", key=f"subdel_{row['id']}_{s_idx}"):
                                subtasks.pop(s_idx)
                                update_subtasks(row['id'], json.dumps(subtasks))
                                st.rerun()
                                
                    d_count = sum(1 for s in subtasks if s['done'])
                    st.progress(d_count / len(subtasks), text=f"Subtask Progress: {d_count}/{len(subtasks)}")
                
                with st.form(f"form_sub_{row['id']}", clear_on_submit=True):
                    col_sa, col_sb = st.columns([4,1])
                    with col_sa:
                        new_sub = st.text_input("Add Subtask", placeholder="Type a step...", label_visibility="collapsed")
                    with col_sb:
                        add_sub = st.form_submit_button("Add")
                    if add_sub and new_sub:
                        subtasks.append({"title": new_sub, "done": False})
                        update_subtasks(row['id'], json.dumps(subtasks))
                        st.rerun()
            
                if do_complete:
                    update_task_status(row['id'], "Completed")
                    if "[HABIT]" in str(row.get('category','')):
                        tmrw = str(date.today() + timedelta(days=1))
                        save_task(user_email, row['title'], row['category'], row['priority'], tmrw)
                    st.rerun()
                
        if not completed_tasks.empty:
            with st.expander("Show Completed Tasks"):
                for index, row in completed_tasks.iterrows():
                    st.markdown(f"~~{row['title']}~~ (Completed on {row['completed_at'][:10]})")
                    if st.button("Delete Completed", key=f"del_c_{row['id']}"):
                         delete_task(row['id'])
                         st.rerun()
    else:
        st.info("No tasks found. Add a new task above!")

with tab2:
    if df_tasks.empty:
        st.warning("Not enough data to calculate insights. Start adding and completing tasks!")
    else:
        st.markdown("<div class='section-title' style='color: inherit;'>📊 Filters & Timeline</div><div class='section-underline'></div>", unsafe_allow_html=True)
        
        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1:
            time_filter = st.selectbox("DATE RANGE", ["Last 30 Days", "Today", "Last 7 Days", "All Time"], key="time_filter")
        with col_f2:
            available_categories = ["All Categories"] + list(df_tasks['category'].unique()) if not df_tasks.empty else ["All Categories"]
            category_filter_tab2 = st.selectbox("CATEGORY FILTER", available_categories, key="cat_filter_tab2")
        with col_f3:
            status_filter_tab2 = st.selectbox("STATUS FILTER", ["All Status", "Pending", "Completed"], key="stat_filter_tab2")
            
        viz_df = df_tasks.copy()
        days_back = 0
        if time_filter == "Today":
            days_back = 1
        elif time_filter == "Last 7 Days":
            days_back = 7
        elif time_filter == "Last 30 Days":
            days_back = 30
            
        if days_back > 0:
            cutoff_date = pd.to_datetime(date.today() - timedelta(days=days_back-1))
            created_dt = pd.to_datetime(viz_df['created_at'])
            completed_dt = pd.to_datetime(viz_df['completed_at'], errors='coerce')
            filter_date = completed_dt.fillna(created_dt)
            viz_df = viz_df[filter_date >= cutoff_date]
            
        if category_filter_tab2 != "All Categories":
            viz_df = viz_df[viz_df['category'] == category_filter_tab2]
        if status_filter_tab2 != "All Status":
            viz_df = viz_df[viz_df['status'] == status_filter_tab2]

        kpis = get_screenshot_kpis(viz_df, days_back=days_back)
        
        c1, c2, c3, c4, c5 = st.columns(5)
        
        html_card1 = f"""<div class='kpi-card'><div class='kpi-icon'>🎯</div>
        <div class='kpi-val'>{kpis['consistency']}</div>
        <div class='kpi-title'>TASK CONSISTENCY</div>
        <div class='kpi-sub'>Days with task sessions</div></div>"""
        c1.markdown(html_card1, unsafe_allow_html=True)
        
        html_card2 = f"""<div class='kpi-card'><div class='kpi-icon'>📈</div>
        <div class='kpi-val'>{kpis['growth_trend']}</div>
        <div class='kpi-title'>GROWTH TREND</div>
        <div class='kpi-sub'>vs. previous period</div></div>"""
        c2.markdown(html_card2, unsafe_allow_html=True)
        
        html_card3 = f"""<div class='kpi-card'><div class='kpi-icon'>⚡</div>
        <div class='kpi-val'>{kpis['streak']}</div>
        <div class='kpi-title'>CURRENT STREAK</div>
        <div class='kpi-sub'>Consecutive task days</div></div>"""
        c3.markdown(html_card3, unsafe_allow_html=True)

        html_card4 = f"""<div class='kpi-card'><div class='kpi-icon'>🏆</div>
        <div class='kpi-val'>{kpis['top_focus']}</div>
        <div class='kpi-title'>FOCUS CATEGORY</div>
        <div class='kpi-sub'>Most focused category</div></div>"""
        c4.markdown(html_card4, unsafe_allow_html=True)

        html_card5 = f"""<div class='kpi-card'><div class='kpi-icon'>⏱️</div>
        <div class='kpi-val'>{kpis['avg_length']}</div>
        <div class='kpi-title'>AVG TASKS DONE</div>
        <div class='kpi-sub'>Per active session</div></div>"""
        c5.markdown(html_card5, unsafe_allow_html=True)

        st.write("") 
        
        v_col1, v_col2 = st.columns(2)
        with v_col1:
            with st.container(border=True):
                 st.markdown("<div class='section-title' style='color:#333 !important;'>📉 Daily Task Trend</div><div class='section-underline'></div>", unsafe_allow_html=True)
                 line_df = generate_daily_line_data(viz_df, days_back=days_back)
                 fig_line = px.line(line_df, x='Date', y='Tasks Completed', template="plotly_white", color_discrete_sequence=['#e11d48'])
                 fig_line.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(t=0, b=0, l=0, r=0))
                 st.plotly_chart(fig_line, width='stretch')
                 
            st.write("")
            with st.container(border=True):
                 st.markdown("<div class='section-title' style='color:#333 !important;'>📊 Weekly Comparison</div><div class='section-underline'></div>", unsafe_allow_html=True)
                 bar_df = generate_weekly_bar_data(viz_df, days_back=days_back)
                 fig_bar = px.bar(bar_df, x='Day Label', y='Tasks Completed', template="plotly_white", color_discrete_sequence=['#e11d48'])
                 fig_bar.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(t=0, b=0, l=0, r=0))
                 st.plotly_chart(fig_bar, width='stretch')

        with v_col2:
            with st.container(border=True):
                 st.markdown("<div class='section-title' style='color:#333 !important;'>🥯 Category Distribution</div><div class='section-underline'></div>", unsafe_allow_html=True)
                 if not viz_df.empty:
                    pie_chart = px.pie(viz_df, names='category', hole=0.3, template="plotly_white", color_discrete_sequence=px.colors.qualitative.Pastel)
                    pie_chart.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(t=0, b=0, l=0, r=0))
                    st.plotly_chart(pie_chart, width='stretch')
                 else:
                    st.info("No data available.")
                 
            st.write("")
            with st.container(border=True):
                 st.markdown("<div class='section-title' style='color:#333 !important;'>🔥 Task Heatmap</div><div class='section-underline'></div>", unsafe_allow_html=True)
                 heat_df = generate_heatmap_data(viz_df, days_back=days_back)
                 fig_heat = px.imshow(heat_df, color_continuous_scale="Reds", aspect="auto")
                 fig_heat.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(t=0, b=0, l=0, r=0))
                 st.plotly_chart(fig_heat, width='stretch')
                 
        with st.container(border=True):
            st.markdown("<div class='section-title' style='color:#333 !important;'>🗓️ Task Calendar & Patterns</div><div class='section-underline'></div>", unsafe_allow_html=True)
            st.dataframe(viz_df[['title', 'category', 'status', 'deadline', 'completed_at']].reset_index(drop=True), use_container_width=True)

with tab3:
    st.header("Trophies & Utilities 🏆")
    
    st.markdown("### Your Badges")
    trophies = get_trophies(df_tasks)
    if not trophies:
        st.info("Complete tasks to unlock trophies!")
    else:
        cols = st.columns(4)
        for i, trophy in enumerate(trophies):
            with cols[i % 4]:
                st.markdown(f"""
                <div style='background-color:#ffffff; padding:15px; border-radius:10px; text-align:center; box-shadow:0 2px 4px rgba(0,0,0,0.1); margin-bottom:10px; border: 1px solid #ccc;'>
                    <div style='font-size:3em; margin-bottom:5px;'>{trophy['icon']}</div>
                    <div style='font-weight:bold; color:#333'>{trophy['name']}</div>
                    <div style='font-size:0.8em; color:#666'>{trophy['desc']}</div>
                </div>
                """, unsafe_allow_html=True)
                
    st.divider()
    
    st.subheader("Data Export")
    st.write("Generate a detailed summary of your KPIs and pending items.")
    if st.button("Generate Weekly PDF Report"):
        with st.spinner("Generating PDF..."):
            pdf_bytes = generate_pdf_report(df_tasks, user_email)
            st.download_button(
                label="📥 Download Report",
                data=bytes(pdf_bytes),
                file_name=f"Task_Report_{date.today()}.pdf",
                mime="application/pdf"
            )
        
    st.subheader("Reminders & Maintenance")
    today = str(date.today())
    high_priority_pending = df_tasks[(df_tasks['status'] == 'Pending') & (df_tasks['priority'] == 'High') & (df_tasks['deadline'] <= today)]
    
    if not high_priority_pending.empty:
        st.warning(f"⚠️ You have {len(high_priority_pending)} High Priority tasks pending for today!")
        for _, row in high_priority_pending.iterrows():
            st.markdown(f"- **{row['title']}**")
    else:
        st.success("No urgent high-priority tasks pending! Great job.")
        
    st.divider()
    if st.button("Run Automated Cleanup (>30 days old)", help="Click to clean up old completed tasks."):
        with st.spinner("Deleting dead tasks..."):
            count = cleanup_old_tasks(user_email, 30)
            st.success(f"Archived and destroyed {count} old tasks!")
            st.rerun()

with tab4:
    st.header("🤖 AI Productivity Coach")
    st.markdown("Your personal AI assistant, powered by Google Gemini.")
    
    gemini_key = st.secrets.get("GEMINI_API_KEY", "")
    
    if not gemini_key:
        st.error("⚠️ **Gemini API Key missing!** Please add `GEMINI_API_KEY = \"your-key\"` to your Streamlit Secrets.")
    else:
        genai.configure(api_key=gemini_key)
        
        if st.button("🔮 Analyze My Day & Generate Strategy"):
            with st.spinner("The AI is analyzing your XP and tasks..."):
                try:
                    model = genai.GenerativeModel('gemini-2.5-flash')
                    pending_bounties = df_tasks[df_tasks['status'] == 'Pending']
                    task_titles = pending_bounties['title'].tolist()
                    
                    urgent = []
                    overdue = []
                    for index, row in pending_bounties.iterrows():
                        dl_status = get_dl_status(row['deadline'])[0]
                        if dl_status == "Due Today": urgent.append(row['title'])
                        elif dl_status == "Overdue": overdue.append(row['title'])
                    
                    prompt = f"""
                    You are an intense, encouraging RPG video game coach speaking directly to me. 
                    I am currently Level {level_info['level']} with {level_info['current_level_xp']} XP.
                    
                    Here are my currently pending quests (tasks): {task_titles}.
                    URGENT (Due Today): {urgent}
                    OVERDUE (Penalty): {overdue}
                    
                    Give me a highly motivating 3-paragraph strategy on how I should tackle my day. Do not use markdown headers, just bold the important actions. End with a war cry. Keep it strictly focused on my tasks.
                    """
                    
                    response = model.generate_content(prompt)
                    st.info(response.text)
                    
                except Exception as e:
                    st.error(f"AI Engine failed to initialize: {e}")

with tab5:
    st.header("🌐 Global Leaderboard")
    st.markdown("Compete against every player using this dashboard.")
    if st.button("Refresh Ranks"):
        st.rerun()
        
    global_tasks = fetch_all_tasks(email=None)
    if not global_tasks.empty:
        leaderboard = []
        unique_users = [u for u in global_tasks['user_email'].unique() if pd.notna(u)]
        
        for u in unique_users:
            if not u: continue
            u_tasks = global_tasks[global_tasks['user_email'] == u]
            u_gam = calculate_gamification(u_tasks)
            c_count = len(u_tasks[u_tasks['status'] == 'Completed'])
            obfuscated = u[:3] + "***" + u[u.find("@"):] if "@" in u else "Unknown Hero"
            if u == user_email: obfuscated = "⭐ YOU (" + obfuscated + ")"
            
            leaderboard.append({
                "Player": obfuscated,
                "Level": u_gam['level'],
                "Total XP": u_gam['total_xp'],
                "Quests Done": c_count
            })
            
        ldf = pd.DataFrame(leaderboard).sort_values(by=["Level", "Total XP"], ascending=[False, False]).reset_index(drop=True)
        ldf.index = ldf.index + 1
        
        st.dataframe(ldf, use_container_width=True)
        
        if len(ldf) > 0:
             top_player = ldf.iloc[0]['Player']
             st.success(f"🏆 Current World Rank #1 is **{top_player}**!")
    else:
        st.info("No players found on the server.")
