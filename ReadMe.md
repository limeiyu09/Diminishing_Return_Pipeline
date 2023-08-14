## Purpose

- An automatic model stimulator for any user to run
- To check weekly performance by finding the diminishing return point using sigmoid function
- Result can be in "Country -- Funnel -- Channel" level or in "Country -- Funnel -- Channel -- Partner" level
- To store all results (succesful model outputs and model failed granularities) in the format of table and plot in Excel with separate sheets

## User System Installation

- Anaconda: Jupyter Notebook
- Git

## Files

- aws_creds.py
	+ Users insert personal AWS credentials and do not share this file to others once insert
	+ Do not need to modify once credentials are inserted
- s3_connector.py
	+ Data is generated to S3 on daily basis
	+ This file will call aws_creds.py and pull data from S3
	+ Users do not need to modify this file
- diminishing_return_class.py
	+ This file includes all functions for modelling, graphing, creating output file, and calls s3_connector.py to load data
	+ Users do not need to modify this file
- parameter.py
	+ This file includs code of interactive platform
	+ Once user submit request, this file calls diminishing_return_class.py for modelling
	+ Users do not need to modify this file
- Diminishing_Return_User_platform.ipynb
	+ Users open this file everytime to submit request
	+ Import parameter.py for users to select options and submit request
- .gitignore
	+ List of files or file types that we do not want git to track modifications
	+ Users do not need to modify this file

## Algorithm

- Users select data range with no less than half year
- Any granularity with less than 26 weeks (half year) of valid investment will be skipped from modelling due to a small sample size and result will be shown on final output Excel
- Data Used for modelling:
	+ x_value: weekly investment
	+ y_value: revenue (measurement * cost per)
- Media Response Formulation:
	+ Revenue = a / (1 + b * investment^c)
	where:
		+ a: Media Saturation
		+ b: Steepness of Curve
		+ c: Curve shape (set bound -1 < c < 0)
	+ Fit data to above formula with historical x, y data and return the best a, b and c values
	+ Calculate y_hat (predicted y) and find the diminishing return point where absolute value MROI (slope of the point) is closest to 1
- Graphing:
	+ Scatter Plot historical data
	+ Plot modeling curve line
	+ Bold diminishing return point on the curve line if it exists
