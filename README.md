# MongoDB-Car-Sales-Analytics-Dashboard

# Car Sales Analytics Dashboard
Interactive Data Exploration Platform using MongoDB Atlas and Streamlit

---

## Overview

This project is a fully interactive analytics dashboard built using Streamlit, MongoDB Atlas, Pandas, Plotly, and Altair.  
It visualizes insights from a UK car sales dataset and enables dynamic filtering, trend analysis, and full vehicle history inspection.

The dashboard supports real-time MongoDB aggregation pipelines and is optimized for deployment on Streamlit Cloud.

---

## Features

### Interactive Filters
- Manufacturer  
- Fuel type  
- Dealer  
- Price range  
- Year range  

### Six Analytical Visualizations
- Manufacturer distribution  
- Average price by manufacturer  
- Fuel type distribution  
- Accident severity distribution  
- Service frequency (last 5 years)  
- Price vs mileage scatter  

### Full Vehicle History Viewer
For any selected vehicle:
- Overview panel  
- Engine size  
- Year of manufacture  
- Dealer name  
- Feature list  
- Service history  
- Accident history  

---

## Tech Stack

| Component | Technology |
|----------|------------|
| Web Framework | Streamlit |
| Database | MongoDB Atlas |
| Visualizations | Plotly, Altair |
| Data Processing | Pandas |
| Deployment | Streamlit Cloud |

---

## Project Structure
│
├── app.py
├── requirements.txt
├── config.toml
└── README.md

