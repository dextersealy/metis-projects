# Clustering New York Rental Listings

This repository contains the presentation, Jupyter workbooks, and
D3/Flask application I created for the fourth project in Metis' Data
Science program. It was an unsupervised learning task aimed at
revealing patterns in New York City apartment rental listings.

[Web app screenshot](ClusterNYC.png)

I applied several **scikit-learn** modules to cluster approximately
50,000 rental listings, using only the text descriptions written by
listing agents. Of the methods I tried, Non-negative Matrix Factoring
(NMF) proved to be the most effective and revealed non-traditional
ways to group listings.

The **app** folder contains the code and data for an interactive
d3/Flask application. Using a random sample of 1000 listings, it
displays the clusters created by three different algorithms (KMeans,
NMF and Ward) and allows you inspect the specific listings in each
cluster.
