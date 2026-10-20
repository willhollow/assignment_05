"""
payroll_report_app.py — the quarter at a glance, for someone who never opens a terminal.

Every Friday since September the office manager at Salt City Coffee has downloaded
a payroll export from the Assignment 04 app; before that she typed the same file
by hand. The owner now wants to know where the hours went this quarter, the
accountant wants pay by month and department, and the manager wants to see who
has been missing shifts. This page answers all three from the pile of exports.

Same shape as Assignment 04: the page *assembles* the pipeline — one call to
`build_history` does the cleaning — and then shows the reports, filtered by the
department and dates the user picks.

Run it:  Run and Debug -> "Streamlit Run: Current File"
Test it: pytest tests/test_pipeline.py -k app
"""
import streamlit as st

from payroll import (
    build_history,
    hours_grid,
    load_employees,
    load_export,
    missed_weeks,
    pay_by_month,
    summarize_employees,
)


st.title("Salt City Coffee — Quarterly Payroll Report")
st.write(
    "Upload the weekly payroll exports for the period you want to review — "
    "old spreadsheet weeks and new app weeks can be mixed. The roster is loaded "
    "automatically."
)

roster = load_employees()
uploads = st.file_uploader(
    "Upload weekly payroll exports (CSV)",
    type="csv",
    accept_multiple_files=True,
    key="exports",
)

if uploads:
    history = build_history([load_export(upload) for upload in uploads], roster)
    unmatched = sorted(
        history.loc[history["department"].isna(), "employeeid"].dropna().unique()
    )
    if unmatched:
        st.warning(
            "These employee IDs were not found on the roster: "
            f"{', '.join(unmatched)}"
        )

    matched = history.loc[history["department"].notna()].copy()
    departments = ["All"] + sorted(matched["department"].unique())
    department = st.selectbox("Department", departments, key="department")

    first_date = matched["pay_date"].min().date()
    last_date = matched["pay_date"].max().date()
    dates = st.date_input(
        "Pay dates",
        value=(first_date, last_date),
        min_value=first_date,
        max_value=last_date,
        key="dates",
    )
    if isinstance(dates, (tuple, list)) and len(dates) == 2:
        start_date, end_date = dates
    else:
        start_date = end_date = dates

    selected = matched.loc[
        matched["pay_date"].dt.date.between(start_date, end_date)
    ]
    if department != "All":
        selected = selected.loc[selected["department"] == department]

    st.subheader(f"{department} · {start_date} to {end_date}")
    metrics = st.columns(4)
    metrics[0].metric("Weeks", selected["week_ending"].nunique())
    metrics[1].metric("Employees", selected["employee_id"].nunique())
    metrics[2].metric("Total hours", f"{selected['hours_worked'].sum():,.2f}")
    metrics[3].metric("Total gross pay", f"${selected['gross_pay'].sum():,.2f}")

    monthly = pay_by_month(selected)
    st.subheader("Gross pay by month")
    st.bar_chart(monthly.set_index("month"))

    st.subheader("Employees")
    st.dataframe(summarize_employees(selected), use_container_width=True)

    grid = hours_grid(selected)
    st.subheader("Hours by week")
    st.dataframe(grid, use_container_width=True)

    st.subheader("Missed weeks")
    st.dataframe(missed_weeks(grid), use_container_width=True)

    st.download_button(
        "Download pay by month for the accountant (CSV)",
        monthly.to_csv(index=False),
        file_name="pay_by_month.csv",
        mime="text/csv",
        key="download",
    )
