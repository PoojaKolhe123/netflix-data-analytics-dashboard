from datetime import date
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st


# Keep the data file beside this app.py file so the app works from any folder.
DATA_PATH = Path(__file__).resolve().parent / "Netflix.csv.csv"

st.set_page_config(
    page_title="Netflix Data Analytics Dashboard",
    page_icon=":material/analytics:",
    layout="wide",
)


# A restrained dark palette keeps charts readable without copying a streaming brand.
st.markdown(
    """
    <style>
    :root {
        --canvas: #111419;
        --surface: #191e25;
        --surface-raised: #202630;
        --ink: #f3f4f6;
        --muted: #9aa3af;
        --accent: #ff765f;
        --mint: #75d7c4;
        --line: rgba(255, 255, 255, 0.09);
    }
    .stApp { background: var(--canvas); color: var(--ink); }
    [data-testid="stHeader"] { background: rgba(17, 20, 25, 0.92); }
    [data-testid="stSidebar"] { background: #171b21; border-right: 1px solid var(--line); }
    [data-testid="stSidebar"] h2 { color: var(--ink); }
    .eyebrow {
        color: var(--mint); font-size: 0.76rem; font-weight: 700;
        letter-spacing: 0.12em; text-transform: uppercase; margin-bottom: 0.35rem;
    }
    .page-title { font-size: 2.15rem; line-height: 1.15; font-weight: 750; margin: 0; }
    .page-subtitle { color: var(--muted); margin: 0.45rem 0 1.35rem; }
    [data-testid="stMetric"] {
        background: var(--surface); border: 1px solid var(--line);
        border-radius: 8px; padding: 1rem 1.05rem; min-height: 112px;
    }
    [data-testid="stMetricLabel"] { color: var(--muted); }
    [data-testid="stMetricValue"] { color: var(--ink); font-size: 1.65rem; }
    .chart-title { font-size: 1rem; font-weight: 650; margin: 0.4rem 0 0.1rem; }
    .section-label {
        color: var(--muted); font-size: 0.8rem; font-weight: 650;
        letter-spacing: 0.08em; text-transform: uppercase; margin: 1.25rem 0 0.4rem;
    }
    div[data-testid="stDataFrame"] { border: 1px solid var(--line); border-radius: 8px; }
    .stDownloadButton button { border-color: var(--mint); color: var(--mint); }
    @media (max-width: 700px) {
        .page-title { font-size: 1.75rem; }
        [data-testid="stMetric"] { min-height: 98px; padding: 0.8rem; }
        [data-testid="stMetricValue"] { font-size: 1.35rem; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data
def load_data(csv_path: str) -> pd.DataFrame:
    """Load the CSV and prepare columns used by filters and charts."""
    data = pd.read_csv(csv_path)

    required_columns = {
        "Customer_ID", "Region", "Subscription_Plan", "Movie_ID", "Title",
        "Category", "Type", "Rating", "Watch_Count", "Watch_Date",
        "Watch_Time_Minutes", "Language", "Device", "Payment_Method",
        "Monthly_Revenue",
    }
    missing_columns = required_columns.difference(data.columns)
    if missing_columns:
        raise ValueError("Missing required CSV columns: " + ", ".join(sorted(missing_columns)))

    # Replace blank labels so filters and groupings have a consistent Unknown option.
    text_columns = [
        "Customer_ID", "Region", "Subscription_Plan", "Movie_ID", "Title",
        "Category", "Type", "Rating", "Language", "Device", "Payment_Method",
    ]
    for column in text_columns:
        data[column] = data[column].astype("string").str.strip().replace("", pd.NA).fillna("Unknown")

    data["Watch_Date"] = pd.to_datetime(data["Watch_Date"], errors="coerce")
    for column in ["Watch_Count", "Watch_Time_Minutes", "Monthly_Revenue"]:
        data[column] = pd.to_numeric(data[column], errors="coerce").fillna(0)

    return data


if not DATA_PATH.exists():
    st.error(f"Could not find the dataset at `{DATA_PATH}`. Put Netflix.csv.csv beside app.py and reload.")
    st.stop()

try:
    netflix = load_data(str(DATA_PATH))
except (OSError, pd.errors.ParserError, ValueError) as error:
    st.error(f"The dataset could not be loaded: {error}")
    st.stop()


# Put title search first so it is immediately available in the sidebar.
search_text = st.sidebar.text_input(
    "Search Title",
    placeholder="Search movies or TV shows...",
    help="Search titles using a case-insensitive partial match.",
    key="search_title",
)
st.sidebar.markdown("### Filters")

filter_columns = {
    "Region": "Region",
    "Subscription_Plan": "Subscription_Plan",
    "Category": "Category",
    "Type": "Type",
    "Rating": "Rating",
    "Language": "Language",
    "Device": "Device",
    "Payment_Method": "Payment_Method",
}
selected_values = {}
filter_choices = {}
for label, column in filter_columns.items():
    choices = sorted(netflix[column].astype(str).unique().tolist())
    widget_key = f"filter_{column}"
    filter_choices[widget_key] = choices
    if widget_key not in st.session_state:
        st.session_state[widget_key] = choices.copy()
    selected_values[column] = st.sidebar.multiselect(
        label, choices, key=widget_key
    )

valid_dates = netflix["Watch_Date"].dropna()
if not valid_dates.empty:
    minimum_date = valid_dates.min().date()
    maximum_date = valid_dates.max().date()
else:
    minimum_date = maximum_date = date.today()


def reset_filters() -> None:
    """Restore every sidebar control to its initial, unfiltered value."""
    st.session_state["search_title"] = ""
    for widget_key, choices in filter_choices.items():
        st.session_state[widget_key] = choices.copy()
    st.session_state["watch_date_filter"] = (minimum_date, maximum_date)


if "watch_date_filter" not in st.session_state:
    st.session_state["watch_date_filter"] = (minimum_date, maximum_date)

date_range = st.sidebar.date_input(
    "Watch_Date",
    min_value=minimum_date,
    max_value=maximum_date,
    disabled=valid_dates.empty,
    key="watch_date_filter",
)
st.sidebar.button(
    "Reset Filters",
    width="stretch",
    on_click=reset_filters,
)


# Apply every selected filter to a copy, leaving the loaded data unchanged.
filtered = netflix.copy()
for column, choices in selected_values.items():
    filtered = filtered[filtered[column].astype(str).isin(choices)]

if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = date_range
    filtered = filtered[filtered["Watch_Date"].dt.date.between(start_date, end_date)]
elif isinstance(date_range, date):
    filtered = filtered[filtered["Watch_Date"].dt.date == date_range]

if search_text:
    filtered = filtered[
        filtered["Title"].str.contains(search_text, case=False, na=False, regex=False)
    ]

st.markdown('<div class="eyebrow">Viewing intelligence</div>', unsafe_allow_html=True)
st.markdown('<h1 class="page-title">Netflix Data Analytics Dashboard</h1>', unsafe_allow_html=True)
st.markdown(
    '<p class="page-subtitle">Interactive dashboard to analyze Netflix content, customer behavior, watch patterns and revenue.</p>',
    unsafe_allow_html=True,
)


# Calculate headline metrics from the currently filtered rows.
total_customers = filtered["Customer_ID"].nunique()
total_titles = filtered["Movie_ID"].nunique()
total_watches = filtered["Watch_Count"].sum()
total_watch_minutes = filtered["Watch_Time_Minutes"].sum()
total_revenue = filtered["Monthly_Revenue"].sum()

st.markdown('<div class="section-label">At a glance</div>', unsafe_allow_html=True)
kpi_columns = st.columns(5)
kpi_columns[0].metric("Total Customers", f"{total_customers:,}")
kpi_columns[1].metric("Total Movies/Shows", f"{total_titles:,}")
kpi_columns[2].metric("Total Watch Count", f"{total_watches:,.0f}")
kpi_columns[3].metric("Total Watch Time", f"{total_watch_minutes:,.0f} min")
kpi_columns[4].metric("Total Monthly Revenue", f"{total_revenue:,.0f}")


def plot_bar_chart(values: pd.Series, color: str, horizontal: bool = False, axis_label: str = "") -> None:
    """Draw a consistently styled bar chart from a grouped Pandas series."""
    labels = values.index.astype(str)
    figure, axis = plt.subplots(figsize=(7.4, 3.1), facecolor="#191e25")
    axis.set_facecolor("#191e25")

    if horizontal:
        axis.barh(labels, values.values, color=color, height=0.62)
        axis.invert_yaxis()
        axis.set_xlabel(axis_label, color="#9aa3af")
        axis.tick_params(axis="y", colors="#e8eaed", labelsize=9)
        axis.tick_params(axis="x", colors="#9aa3af", labelsize=8)
        axis.xaxis.grid(True, color="#ffffff", alpha=0.08)
    else:
        axis.bar(labels, values.values, color=color, width=0.66)
        axis.set_ylabel(axis_label, color="#9aa3af")
        axis.tick_params(axis="x", colors="#e8eaed", labelsize=8, rotation=25)
        axis.tick_params(axis="y", colors="#9aa3af", labelsize=8)
        axis.yaxis.grid(True, color="#ffffff", alpha=0.08)

    axis.set_axisbelow(True)
    for spine in axis.spines.values():
        spine.set_visible(False)
    figure.tight_layout()
    st.pyplot(figure, width="stretch")
    plt.close(figure)


if filtered.empty:
    st.info("No matching records found. Please try another title or change the filters.")
else:
    st.markdown('<div class="section-label">Audience & content</div>', unsafe_allow_html=True)
    left_chart, right_chart = st.columns(2)

    with left_chart:
        st.markdown('<div class="chart-title">Movie vs TV Show Distribution</div>', unsafe_allow_html=True)
        type_counts = filtered["Type"].value_counts()
        figure, axis = plt.subplots(figsize=(7.4, 3.1), facecolor="#191e25")
        axis.set_facecolor("#191e25")
        axis.pie(
            type_counts.values,
            labels=type_counts.index,
            autopct="%1.0f%%",
            startangle=90,
            colors=["#ff765f", "#75d7c4", "#e6b566", "#8ba8ff"],
            textprops={"color": "#f3f4f6", "fontsize": 9},
            wedgeprops={"width": 0.42, "edgecolor": "#191e25", "linewidth": 2},
        )
        axis.axis("equal")
        figure.tight_layout()
        st.pyplot(figure, width="stretch")
        plt.close(figure)

    with right_chart:
        st.markdown('<div class="chart-title">Customers by Region</div>', unsafe_allow_html=True)
        region_customers = filtered.groupby("Region")["Customer_ID"].nunique().sort_values(ascending=False)
        plot_bar_chart(region_customers, "#75d7c4", horizontal=True, axis_label="Unique customers")

    st.markdown('<div class="section-label">Viewing patterns</div>', unsafe_allow_html=True)
    left_chart, right_chart = st.columns(2)

    with left_chart:
        st.markdown('<div class="chart-title">Subscription_Plan Distribution</div>', unsafe_allow_html=True)
        plan_customers = filtered.groupby("Subscription_Plan")["Customer_ID"].nunique().sort_values(ascending=False)
        plot_bar_chart(plan_customers, "#e6b566", horizontal=True, axis_label="Unique customers")

    with right_chart:
        st.markdown('<div class="chart-title">Top 10 Most Watched Titles</div>', unsafe_allow_html=True)
        top_titles = filtered.groupby("Title")["Watch_Count"].sum().nlargest(10).sort_values()
        plot_bar_chart(top_titles, "#ff765f", horizontal=True, axis_label="Watch count")

    left_chart, right_chart = st.columns(2)
    with left_chart:
        st.markdown('<div class="chart-title">Watch Count by Device</div>', unsafe_allow_html=True)
        device_watches = filtered.groupby("Device")["Watch_Count"].sum().sort_values(ascending=False)
        plot_bar_chart(device_watches, "#8ba8ff", horizontal=True, axis_label="Watch count")

    with right_chart:
        st.markdown('<div class="chart-title">Content Distribution by Language</div>', unsafe_allow_html=True)
        language_titles = filtered.groupby("Language")["Movie_ID"].nunique().sort_values(ascending=False)
        plot_bar_chart(language_titles, "#75d7c4", horizontal=True, axis_label="Unique titles")

    st.markdown('<div class="section-label">Revenue & engagement</div>', unsafe_allow_html=True)
    left_chart, right_chart = st.columns(2)

    with left_chart:
        st.markdown('<div class="chart-title">Monthly Revenue Trend</div>', unsafe_allow_html=True)
        dated_rows = filtered.dropna(subset=["Watch_Date"]).copy()
        if dated_rows.empty:
            st.caption("No valid watch dates are available for the selected rows.")
        else:
            dated_rows["Month"] = dated_rows["Watch_Date"].dt.to_period("M").dt.to_timestamp()
            monthly_revenue = dated_rows.groupby("Month")["Monthly_Revenue"].sum().sort_index()
            figure, axis = plt.subplots(figsize=(7.4, 3.1), facecolor="#191e25")
            axis.set_facecolor("#191e25")
            axis.plot(monthly_revenue.index, monthly_revenue.values, color="#ff765f", linewidth=2.5, marker="o", markersize=5)
            axis.fill_between(monthly_revenue.index, monthly_revenue.values, color="#ff765f", alpha=0.13)
            axis.tick_params(colors="#9aa3af", labelsize=8)
            axis.yaxis.grid(True, color="#ffffff", alpha=0.08)
            for spine in axis.spines.values():
                spine.set_visible(False)
            figure.autofmt_xdate()
            figure.tight_layout()
            st.pyplot(figure, width="stretch")
            plt.close(figure)

    with right_chart:
        st.markdown('<div class="chart-title">Watch Time by Category</div>', unsafe_allow_html=True)
        category_minutes = filtered.groupby("Category")["Watch_Time_Minutes"].sum().sort_values(ascending=False)
        plot_bar_chart(category_minutes, "#e6b566", horizontal=True, axis_label="Minutes watched")


st.markdown("## Filtered Netflix Data")
st.caption(f"Showing {len(filtered):,} rows from {DATA_PATH.name}.")
st.download_button(
    label="Download Filtered Data",
    data=filtered.to_csv(index=False).encode("utf-8"),
    file_name="netflix_filtered.csv",
    mime="text/csv",
    disabled=filtered.empty,
)
st.dataframe(
    filtered,
    width="stretch",
    hide_index=True,
    column_config={"Watch_Date": st.column_config.DateColumn("Watch Date", format="YYYY-MM-DD")},
)