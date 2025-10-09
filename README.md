# Market Reactions to Company News —  Stock Analysis Dashboard

Power BI app link: https://app.powerbi.com/Redirect?action=OpenApp&appId=b5a34214-82e2-4c5f-9ca5-2bc3c50c5231&ctid=6230e860-bfc5-4095-a6bc-104721add6e6&experience=power-bi




<img width="1486" height="828" alt="imagem" src="https://github.com/user-attachments/assets/c1e6c522-7823-42be-9e96-4fad28b4fd42" />

# Overview
This interactive dashboard provides comprehensive analysis of stock market reactions to earnings reports for major technology companies (AAPL, MSFT, GOOGL, AMZN, META). The dashboard visualizes how stock prices respond to earnings announcements.

# Main Metrics

Median Percentage Change: Displays the median percentage change in stock prices of all reactions following earnings reports (currently showing 1.07%)
Success Rate: Shows the percentage of earnings reports that resulted in stock price increases (currently 63% of the 8 latest earnings reports)

# Interactive Visualizations

Stock Selection Panel: Choose from five major tech stocks (AAPL, AMZN, GOOGL, META, MSFT) to analyze their specific performance

<img width="1480" height="828" alt="imagem" src="https://github.com/user-attachments/assets/0d3601d9-d308-430d-8ec7-0b3375ecb7fa" />

Earnings Date Filter: It's possible to select sepecific earnings report realease dates and analyse the percentage change in stock prices (3 days before and after the release of the earning report) and the stock prices in that interval.


<img width="1480" height="828" alt="imagem" src="https://github.com/user-attachments/assets/f1a2b898-5d12-4afd-bdb6-54a7aef24c99" />

# Technical Implementation

Built using data from FMP_Script.py which fetches data from Financial Modeling Prep API and Yahoo Finance. Database in mysql
