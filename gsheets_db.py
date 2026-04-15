import gspread
import streamlit as st
import pandas as pd
from datetime import datetime
import uuid

# Define the scope for Google Sheets
SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive"
]

@st.cache_resource
def get_google_sheet():
    try:
        # Streamlit secrets will hold the loaded dictionary of the JSON
        credentials_dict = dict(st.secrets["gcp_service_account"])
        client = gspread.service_account_from_dict(credentials_dict)
        # Open the specific Google Sheet by Name (must be shared with service account)
        sheet = client.open("Task Dashboard DB").sheet1
        
        # Initialize headers if sheet is empty
        if len(sheet.get_all_values()) == 0:
            headers = ["id", "user_email", "title", "category", "priority", "status", "deadline", "completed_at", "created_at", "subtasks"]
            sheet.append_row(headers)
        return sheet
    except Exception as e:
        st.error(f"Error connecting to Google Sheets: {e}")
        return None

def fetch_all_tasks(email=None):
    sheet = get_google_sheet()
    if not sheet:
        return pd.DataFrame()
        
    data = sheet.get_all_values()
    default_headers = ["id", "user_email", "title", "category", "priority", "status", "deadline", "completed_at", "created_at", "subtasks"]
    
    if not data:
        return pd.DataFrame(columns=default_headers)
        
    # Auto-repair if the user accidentally overwrote the header row with a task!
    if "id" not in data[0]:
        sheet.insert_row(default_headers, 1)
        data = sheet.get_all_values()
        
    headers = data[0]
    records = data[1:]
    
    # Pad rows to match header length just in case Google Sheets truncates trailing empty cells
    padded_records = [row + [""] * (len(headers) - len(row)) for row in records]
    
    df = pd.DataFrame(padded_records, columns=headers)
    
    if 'subtasks' not in df.columns:
        df['subtasks'] = "[]"
    else:
        df['subtasks'] = df['subtasks'].replace("", "[]").fillna("[]")
        
    if not df.empty and email is not None:
        if 'user_email' in df.columns:
            df = df[df['user_email'] == email]
    return df

def save_task(email, title, category, priority, deadline):
    sheet = get_google_sheet()
    if not sheet:
        return False
    
    task_id = str(uuid.uuid4())
    created_at = datetime.now().isoformat()
    new_row = [
        task_id,
        email,
        title,
        category,
        priority,
        "Pending",
        deadline,
        "",
        created_at,
        "[]"
    ]
    try:
        # appending requires lists
        sheet.append_row(new_row)
        return True
    except Exception as e:
        st.error(f"Failed to add task: {e}")
        return False

def update_task_status(task_id, new_status):
    sheet = get_google_sheet()
    if not sheet:
        return False
    
    try:
        # Find the row with the matching task_id
        cell = sheet.find(task_id)
        if cell:
            row_idx = cell.row
            sheet.update_cell(row_idx, 6, new_status) # 6 corresponds to status column (1-indexed)
            
            if new_status == "Completed":
                sheet.update_cell(row_idx, 8, datetime.now().isoformat()) # 8 corresponds to completed_at
            else:
                sheet.update_cell(row_idx, 8, "")
            return True
        return False
    except gspread.exceptions.CellNotFound:
         st.error("Task not found to update.")
         return False
    except Exception as e:
        st.error(f"Error updating task: {e}")
        return False

def update_subtasks(task_id, json_str):
    sheet = get_google_sheet()
    if not sheet:
        return False
    try:
        cell = sheet.find(task_id)
        if cell:
            sheet.update_cell(cell.row, 10, json_str)
            return True
        return False
    except Exception as e:
        st.error(f"Error updating subtasks: {e}")
        return False

def delete_task(task_id):
    sheet = get_google_sheet()
    if not sheet:
        return False
        
    try:
        cell = sheet.find(task_id)
        if cell:
            sheet.delete_rows(cell.row)
            return True
        return False
    except Exception as e:
        st.error(f"Error deleting task: {e}")
        return False

def archive_old_tasks():
    # Placeholder for the automated cleanup feature to be implemented later
    pass
