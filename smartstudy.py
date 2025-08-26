import streamlit as st
import pandas as pd
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

st.set_page_config(page_title="Study Schedule Generator", page_icon="📅", layout="centered")
st.markdown("""
    <style>
    .main {
        background-color: #f0f5f9;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("📅 Easy Study Schedule Generator")

# Input subjects and hours
subjects_input = st.text_area("Enter subjects (separate by commas)", "Math, Physics, Chemistry")
available_hours = st.slider("Total study hours per week", 1, 70, 20)

# Select study days
days_of_week = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
selected_days = st.multiselect("Select study days", days_of_week, default=days_of_week[:5])

if st.button("Generate Schedule"):
    subjects = [s.strip() for s in subjects_input.split(",") if s.strip()]
    if not subjects:
        st.error("Please enter at least one subject.")
        st.stop()
    if not selected_days:
        st.error("Please select at least one study day.")
        st.stop()

    # Assign equal difficulty for all (simple)
    difficulty = [3] * len(subjects)
    total_difficulty = sum(difficulty)
    # Allocate hours
    allocated_hours = [(d / total_difficulty) * available_hours for d in difficulty]

    # Distribute hours per day
    num_days = len(selected_days)
    daily_hours = [round(h / num_days, 2) for h in allocated_hours]

    # Build schedule DataFrame
    df_weekly = pd.DataFrame({
        "Subject": subjects,
        "Allocated Hours (Week)": allocated_hours,
        "Daily Hours": daily_hours
    })

    def highlight_hours(row):
        if row["Allocated Hours (Week)"] >= 10:
            return ['background-color: #FFB6B9'] * len(row)
        elif row["Allocated Hours (Week)"] >= 5:
            return ['background-color: #FAE3D9'] * len(row)
        else:
            return ['background-color: #BBDED6'] * len(row)

    st.subheader("Your Weekly Study Schedule")
    st.dataframe(df_weekly.style.apply(highlight_hours, axis=1))

    st.subheader("Daily Distribution")
    df_daily = pd.DataFrame({
        day: daily_hours for day in selected_days
    }, index=subjects)
    st.table(df_daily)

    # Visualization chart
    st.subheader("Weekly Hours per Subject")
    st.bar_chart(df_weekly.set_index("Subject")["Allocated Hours (Week)"])

    # PDF Export
    def generate_pdf(df_weekly, df_daily):
        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter
        c.setFont("Helvetica-Bold", 20)
        c.drawString(72, height - 72, "Study Schedule")

        c.setFont("Helvetica", 14)
        y = height - 110
        for i, row in df_weekly.iterrows():
            c.drawString(72, y, f"{row['Subject']}: {round(row['Allocated Hours (Week)'], 1)} hrs/week")
            y -= 20
            if y < 72:
                c.showPage()
                y = height - 72

        y -= 30
        c.setFont("Helvetica-Bold", 16)
        c.drawString(72, y, "Daily Hours Distribution")
        y -= 20
        c.setFont("Helvetica", 12)
        for day in df_daily.columns:
            c.drawString(72, y, f"{day}:")
            y -= 15
            for subject in df_daily.index:
                hours = df_daily.loc[subject, day]
                c.drawString(90, y, f"{subject}: {hours} hrs")
                y -= 15
                if y < 72:
                    c.showPage()
                    y = height - 72

        c.save()
        buffer.seek(0)
        return buffer

    pdf_buffer = generate_pdf(df_weekly, df_daily)
    st.download_button("Download Schedule as PDF", pdf_buffer, "study_schedule.pdf", "application/pdf")
