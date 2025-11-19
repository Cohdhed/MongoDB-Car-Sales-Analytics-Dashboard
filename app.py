# app.py
# Streamlit dashboard for car_sales_db (MongoDB Atlas)
# Requirements: streamlit, pymongo, pandas, altair, plotly

import os
from datetime import datetime
import streamlit as st
from pymongo import MongoClient
import pandas as pd
import altair as alt
import plotly.express as px

st.set_page_config(layout="wide", page_title="Car Sales Analytics", initial_sidebar_state="expanded")

# ------------------------
# DB CONNECTION
# ------------------------
@st.cache_resource(ttl=3600)
def get_db():
    try:
        uri = st.secrets["mongo_uri"]
    except:
        uri = os.environ.get("MONGO_URI")

    if not uri:
        st.error("MongoDB URI not found.")
        st.stop()

    client = MongoClient(uri)
    return client["car_sales_db"]

db = get_db()
cars_coll = db.cars
dealers_coll = db.dealers

# ------------------------
# SIDEBAR FILTERS
# ------------------------
st.sidebar.header("Filters")

@st.cache_data(ttl=600)
def load_filter_options():
    manufacturers = cars_coll.distinct("manufacturer")
    fuel_types = cars_coll.distinct("fuel_type")
    dealer_docs = list(dealers_coll.find({}, {"_id":0, "DealerID":1, "DealerName":1}))
    dealers_map = {str(d["DealerID"]): d["DealerName"] for d in dealer_docs}

    min_price = cars_coll.find_one(sort=[("price",1)])["price"]
    max_price = cars_coll.find_one(sort=[("price",-1)])["price"]
    min_year = cars_coll.find_one(sort=[("year_of_manufacturing",1)])["year_of_manufacturing"]
    max_year = cars_coll.find_one(sort=[("year_of_manufacturing",-1)])["year_of_manufacturing"]

    return manufacturers, fuel_types, dealers_map, min_price, max_price, min_year, max_year

manufacturers, fuel_types, dealers_map, MIN_PRICE, MAX_PRICE, MIN_YEAR, MAX_YEAR = load_filter_options()

sel_manufacturer = st.sidebar.selectbox("Manufacturer", ["All"] + sorted([m for m in manufacturers if m]))
sel_fuel = st.sidebar.multiselect("Fuel type", sorted([f for f in fuel_types if f]), default=sorted([f for f in fuel_types if f]))
sel_dealer = st.sidebar.selectbox("Dealer", ["All"] + [f"{k} | {v}" for k,v in dealers_map.items()])
price_range = st.sidebar.slider("Price range", int(MIN_PRICE), int(MAX_PRICE), (int(MIN_PRICE), int(MAX_PRICE)))
year_range = st.sidebar.slider("Year range", int(MIN_YEAR), int(MAX_YEAR), (int(MIN_YEAR), int(MAX_YEAR)))
apply_filters = st.sidebar.button("Apply filters")

def parse_dealer(value):
    if value == "All": return None
    return int(value.split("|")[0])

dealer_id_filter = parse_dealer(sel_dealer)

# ------------------------
# BUILD MONGODB MATCH FILTER
# ------------------------
def build_match():
    match = {}
    if sel_manufacturer != "All":
        match["manufacturer"] = sel_manufacturer
    if sel_fuel:
        match["fuel_type"] = {"$in": sel_fuel}
    if dealer_id_filter:
        match["dealer_id"] = dealer_id_filter

    match["price"] = {"$gte": price_range[0], "$lte": price_range[1]}
    match["year_of_manufacturing"] = {"$gte": year_range[0], "$lte": year_range[1]}
    return match

match = build_match()
if apply_filters:
    st.rerun()

# ------------------------
# AGGREGATION PIPELINES
# ------------------------
@st.cache_data(ttl=300)
def manufacturer_distribution_pipeline(match):
    pipeline = []
    if match: pipeline.append({"$match": match})
    pipeline.extend([
        {"$group": {"_id": "$manufacturer", "count": {"$sum": 1}}},
        {"$project": {"manufacturer": "$_id", "count": 1, "_id": 0}},
        {"$sort": {"count": -1}}
    ])
    return list(cars_coll.aggregate(pipeline))

@st.cache_data(ttl=300)
def avg_price_by_manufacturer_pipeline(match):
    pipeline = []
    if match: pipeline.append({"$match": match})
    pipeline.extend([
        {"$group": {"_id": "$manufacturer", "avg_price": {"$avg": "$price"}}},
        {"$project": {"manufacturer": "$_id", "avg_price": 1, "_id": 0}},
        {"$sort": {"avg_price": -1}}
    ])
    return list(cars_coll.aggregate(pipeline))

@st.cache_data(ttl=300)
def accident_severity_pipeline(match):
    pipeline = []
    if match: pipeline.append({"$match": match})
    pipeline.extend([
        {"$unwind": "$accidents"},
        {"$group": {"_id": "$accidents.Severity", "count": {"$sum": 1}}},
        {"$project": {"severity": "$_id", "count": 1, "_id": 0}},
        {"$sort": {"count": -1}}
    ])
    return list(cars_coll.aggregate(pipeline))

@st.cache_data(ttl=300)
def fuel_distribution_pipeline(match):
    pipeline = []
    if match: pipeline.append({"$match": match})
    pipeline.extend([
        {"$group": {"_id": "$fuel_type", "count": {"$sum": 1}}},
        {"$project": {"fuel_type": "$_id", "count": 1, "_id": 0}},
        {"$sort": {"count": -1}}
    ])
    return list(cars_coll.aggregate(pipeline))

@st.cache_data(ttl=300)
def service_frequency_pipeline(match):
    cutoff = datetime(datetime.now().year - 5, datetime.now().month, datetime.now().day)
    pipeline = []
    if match: pipeline.append({"$match": match})
    pipeline.extend([
        {"$unwind": "$services"},
        {"$match": {"services.Date_of_Service": {"$gte": cutoff}}},
        {"$group": {"_id": {"year": {"$year": "$services.Date_of_Service"}}, "services_count": {"$sum": 1}}},
        {"$project": {"year": "$_id.year", "services_count": 1, "_id": 0}},
        {"$sort": {"year": 1}}
    ])
    return list(cars_coll.aggregate(pipeline))

@st.cache_data(ttl=300)
def fetch_price_mileage(match, limit=2000):
    query = match.copy() if match else {}
    cursor = cars_coll.find(query, {"price":1, "mileage":1, "manufacturer":1, "model":1, "fuel_type":1}).limit(limit)
    df = pd.DataFrame(list(cursor))
    if df.empty: return pd.DataFrame()
    df["price"] = pd.to_numeric(df["price"], errors="coerce")
    df["mileage"] = pd.to_numeric(df["mileage"], errors="coerce")
    return df.dropna()

# ------------------------
# PAGE TITLE
# ------------------------
st.markdown(
"""
<div style="color:#FF4B4B; text-align:center; padding-bottom:25px;">
    <p style="font-size:35px; font-weight:bold; margin:0;">
        Car Sales Analytics Dashboard
    </p>
</div>
""",
unsafe_allow_html=True
)

# ============================================================
# ROW 1 → Manufacturer Distribution + Avg Price by Manufacturer
# ============================================================
row1_left, row1_right = st.columns([1,1])

with row1_left:
    #st.subheader("Distribution of Manufacturers")
    data = manufacturer_distribution_pipeline(match)
    if data:
        df = pd.DataFrame(data)
        fig = px.bar(df, x="manufacturer", y="count", title="Manufacturer Distribution")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No data available.")

with row1_right:
    #st.subheader("Average Price by Manufacturer")
    data = avg_price_by_manufacturer_pipeline(match)
    if data:
        df = pd.DataFrame(data)
        fig = px.bar(df, x="manufacturer", y="avg_price", title="Average Car Price by Manufacturer", color_discrete_sequence=["#87CEEB"])
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No data available.")

# ============================================================
# ROW 2 → Fuel Distribution + Accident Severity
# ============================================================
row2_left, row2_right = st.columns([1,1])

with row2_left:
    #st.subheader("Fuel Type Distribution")
    data = fuel_distribution_pipeline(match)
    if data:
        df = pd.DataFrame(data)
        fig = px.pie(df, names="fuel_type", values="count", title="Fuel Type Distribution")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No data available.")

with row2_right:
    #st.subheader("Accident Severity Distribution")
    data = accident_severity_pipeline(match)
    if data:
        df = pd.DataFrame(data)
        fig = px.bar(df, x="severity", y="count", title="Accident Severity Distribution", color_discrete_sequence=["#FF4B4B"])
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No accident data.")

# ============================================================
# ROW 3 → Service Frequency + Price vs Mileage
# ============================================================
row3_left, row3_right = st.columns([1,1])

with row3_left:
    st.markdown(
        "<h3 style='font-size:16px; font-weight:700;'>Service Frequency (Last 5 Years)</h3>",
        unsafe_allow_html=True
    )
    #st.subheader("Service Frequency (Last 5 Years)")
    data = service_frequency_pipeline(match)
    if data:
        df = pd.DataFrame(data)
        df["year"] = df["year"].astype(int)
        chart = alt.Chart(df).mark_line(point=True).encode(
            x="year:O", y="services_count:Q", tooltip=["year", "services_count"]
        )
        st.altair_chart(chart, use_container_width=True)
    else:
        st.info("No data available.")

with row3_right:
    st.markdown(
        "<h3 style='font-size:16px; font-weight:700;'>Price vs Mileage</h3>",
        unsafe_allow_html=True
    )
    #st.subheader("Price vs Mileage")
    df = fetch_price_mileage(match)
    if not df.empty:
        chart = alt.Chart(df).mark_circle(size=60).encode(
            x="mileage:Q",
            y="price:Q",
            color="fuel_type:N",
            tooltip=["manufacturer", "model", "price", "mileage", "fuel_type"]
        ).interactive()
        st.altair_chart(chart, use_container_width=True)
    else:
        st.info("No data available.")

# ============================================================
# FULL-WIDTH CAR HISTORY VIEWER
# ============================================================
st.markdown("---")
st.markdown(
"""
<div style="color:#FF4B4B; padding-bottom:20px;">
    <p style="font-size:25px; font-weight:bold; margin:0;">
        Select a Car to View Full History
    </p>
</div>
""",
unsafe_allow_html=True
)

@st.cache_data(ttl=300)
def fetch_cars_list(match, limit=500):
    query = match.copy() if match else {}
    cursor = cars_coll.find(query, {"_id":1, "manufacturer":1, "model":1, "price":1}).limit(limit)
    return [{"_id": d["_id"], "label": f"{d['manufacturer']} {d['model']} | £{d['price']}"} for d in cursor]

@st.cache_data(ttl=300)
def get_car_detail(car_id):
    return cars_coll.find_one({"_id": car_id})

cars = fetch_cars_list(match)

if cars:
    options = {str(c["_id"]): c["label"] for c in cars}

    selected_key = st.selectbox("Pick a car", options=list(options.keys()), format_func=lambda k: options[k])

    try: car_id = int(selected_key)
    except: car_id = selected_key

    car = get_car_detail(car_id)

    if car:
        st.markdown("### Vehicle Summary")

        col1, col2 = st.columns(2)

        with col1:
            st.write("**Manufacturer:**", car.get("manufacturer"))
            st.write("**Model:**", car.get("model"))
            st.write("**Price (£):**", car.get("price"))
            st.write("**Mileage:**", car.get("mileage"))
            st.write("**Fuel Type:**", car.get("fuel_type"))

        with col2:
            st.write("**Engine Size (L):**", car.get("engine_size"))
            st.write("**Year of Manufacturing:**", car.get("year_of_manufacturing"))

            dealer = dealers_coll.find_one({"DealerID": car.get("dealer_id")})
            dealer_name = dealer["DealerName"] if dealer else "Unknown"
            st.write("**Dealer:**", dealer_name)

            features = car.get("features", [])
            st.write("**Features:**")
            if features:
                for f in features: st.markdown(f"- {f}")
            else:
                st.write("None listed")

        st.markdown("---")
        st.markdown("### Service History")

        services = car.get("services", [])
        if services:
            df = pd.DataFrame(services)
            df["Date_of_Service"] = pd.to_datetime(df["Date_of_Service"])
            st.dataframe(df.sort_values("Date_of_Service", ascending=False), use_container_width=True)
        else:
            st.info("No services recorded.")

        st.markdown("---")
        st.markdown("### Accident History")

        accidents = car.get("accidents", [])
        if accidents:
            df = pd.DataFrame(accidents)
            df["Date_of_Accident"] = pd.to_datetime(df["Date_of_Accident"])
            st.dataframe(df.sort_values("Date_of_Accident", ascending=False), use_container_width=True)
        else:
            st.info("No accidents recorded.")

else:
    st.info("No cars available with current filters.")

st.markdown("---")
st.write("Notes: All queries run directly in MongoDB Atlas.")
