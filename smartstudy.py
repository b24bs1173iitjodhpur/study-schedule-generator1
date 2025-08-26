import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

st.title("Advanced Smart Study Schedule Generator")

# Input subjects with difficulty, goals, and progress
num_subjects = st.number_input("How many subjects?", 1, 20, 3)
subjects_data = []
for i in range(num_subjects):
    subj = st.text_input(f"Subject #{i + 1} Name", key=f"subj_{i}")
    diff = st.slider(f"Difficulty (1=easy to 5=hard) for {subj if subj else 'Subject'}", 1, 5, 3, key=f"diff_{i}")
    goal = st.number_input(f"Goal hours for {subj if subj else 'Subject'} this week", min_value=0.0, max_value=100.0, value=10.0, step=0.5, key=f"goal_{i}")
    progress = st.number_input(f"Progress hours completed for {subj if subj else 'Subject'}", min_value=0.0, max_value=goal, value=0.0, step=0.5, key=f"progress_{i}")
    subjects_data.append({"subject": subj, "difficulty": diff, "goal": goal, "progress": progress})

available_hours = st.number_input("Available study hours per week", 1, 100, 15)
days_of_week = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
selected_days = [day for day in days_of_week if st.checkbox(day, True, key=f"day_{day}")]

if st.button("Generate Schedule"):
    subjects_data = [s for s in subjects_data if s["subject"].strip() != ""]
    if not subjects_data:
        st.error("Please enter at least one subject.")
        st.stop()
    if not selected_days:
        st.error("Please select at least one study day.")
        st.stop()

    total_difficulty = sum(s["difficulty"] for s in subjects_data) or 1
    # Weigh hours by difficulty but capped by user goals
    for s in subjects_data:
        raw_allocated = (s["difficulty"] / total_difficulty) * available_hours
        s["allocated_hours"] = min(raw_allocated, s["goal"])

    num_days = len(selected_days)
    for s in subjects_data:
        s["daily_hours"] = round(s["allocated_hours"] / num_days, 2)

    df = pd.DataFrame(subjects_data).set_index("subject")

    st.subheader("Adjust Daily Hours Manually")
    for subj in df.index:
        df.loc[subj, "daily_hours"] = st.number_input(
            f"Daily hours for {subj}",
            min_value=0.0,
            max_value=24.0,
            value=float(df.loc[subj, "daily_hours"]),
            step=0.25,
            key=f"manual_{subj}"
        )

    df["weekly_hours"] = df["daily_hours"] * num_days
    df["remaining_hours"] = df["goal"] - df["progress"]
    df["remaining_hours"] = df["remaining_hours"].apply(lambda x: max(x, 0))

    # Color coding by difficulty
    def color_row(row):
        if row["difficulty"] >= 4:
            return ["background-color: #ff9999"] * len(row)  # Red for hard
        elif row["difficulty"] == 3:
            return ["background-color: #ffcc99"] * len(row)  # Orange for medium
        else:
            return ["background-color: #ccffcc"] * len(row)  # Green for easy

    st.subheader("Final Study Schedule with Color Coding")
    styled = df.style.apply(color_row, axis=1)
    st.dataframe(styled)

    # Break reminders for daily study over 2 hours
    for subj, row in df.iterrows():
        if row["daily_hours"] > 2:
            st.warning(f"Consider taking breaks when studying {subj} for more than 2 hours daily.")

    # Alerts for intense study days based on total daily hours
    total_daily_hours = df["daily_hours"].sum()
    if total_daily_hours > 6 * num_days:
        st.error(f"Warning: Your total weekly planned study hours ({total_daily_hours*num_days}) might be too high. Consider reducing workload.")

    # Excel export
    excel_bytes = BytesIO()
    with pd.ExcelWriter(excel_bytes, engine="xlsxwriter") as writer:
        df.to_excel(writer, sheet_name="Schedule")
    excel_bytes.seek(0)
    st.download_button(
        "Download Schedule as Excel",
        data=excel_bytes,
        file_name="study_schedule.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    # PDF export including weekly and daily schedule, progress, goals
    def generate_pdf(df):
        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter
        c.setFont("Helvetica-Bold", 16)
        c.drawString(72, height - 72, "Smart Study Schedule")
        c.setFont("Helvetica", 12)
        y = height - 100

        c.drawString(72, y, "Weekly Summary:")
        y -= 20
        for i, (subj, row) in enumerate(df.iterrows()):
            line = (
                f"{subj}: Difficulty {row['difficulty']}, "
                f"Weekly Hours: {row['weekly_hours']}, "
                f"Goal: {row['goal']}, Progress: {row['progress']}, Remaining: {row['remaining_hours']}"
            )
            c.drawString(72, y, line)
            y -= 15
            if y < 72:
                c.showPage()
                y = height - 72

        y -= 10
        c.drawString(72, y, "Daily Schedule (Hours per day):")
        y -= 20

        # Draw table header
        header = f"{'Subject':<15}" + "".join(f"{day[:3]:>8}" for day in selected_days)
        c.drawString(72, y, header)
        y -= 15

        for subj, row in df.iterrows():
            line = f"{subj:<15}" + "".join(f"{row['daily_hours']:>8.2f}" for _ in selected_days)
            c.drawString(72, y, line)
            y -= 15
            if y < 72:
                c.showPage()
                y = height - 72

        c.save()
        buffer.seek(0)
        return buffer

    pdf_buffer = generate_pdf(df)
    st.download_button(
        "Download Schedule as PDF",
        data=pdf_buffer,
        file_name="study_schedule.pdf",
        mime="application/pdf",
    )

    # Visualization
    st.subheader("Weekly Study Hours by Subject")
    st.bar_chart(df["weekly_hours"])

    st.subheader("Progress towards Goals")
    progress_percent = ((df["progress"] / df["goal"]) * 100).fillna(0).clip(0, 100)
    st.bar_chart(progress_percent)

