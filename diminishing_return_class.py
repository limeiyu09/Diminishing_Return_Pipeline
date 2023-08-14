import os
import sys
import pandas as pd 
import numpy as np 
import glob
import s3_connector

import matplotlib.pyplot as plt 
import datetime
from numpy import cov
from scipy.optimize import curve_fit
from sklearn.metrics import mean_squared_error
from scipy import stats
import openpyxl

# Set init parameters
class diminishing_return:

	def __init__(self):
		# init bound of value C (curve): between -1 and 0
		self.bound = [(0,0,-1), (np.inf, np.inf, 0)]
		self.yesterday = str(datetime.date.today()-datetime.timedelta(1))
		# by default / first-time run: set df=None so it will load df from S3 or local drive
		self.df=None
		self.image_num = 0
		self.image_num_fail = 0

	def run(self, countries, funnels, channels, partner, measure, start_date, end_date, cost_per):

		# set init parameters from Jupyter Notebook
		self.countries = countries
		self.funnels = funnels
		self.channels = channels
		self.partner = partner
		self.measure = measure
		# set start date to be the Monday before input start_date
		self.start_date = pd.to_datetime(start_date) - datetime.timedelta(pd.to_datetime(start_date).weekday())
		# set end date to be the Sunday after input end_date
		self.end_date = pd.to_datetime(end_date) + datetime.timedelta(6-pd.to_datetime(end_date).weekday())
		self.cost_per = cost_per

		# call all functions in class
		# Load data from S3 or local drive for first-time run only
		if (type(self.df) == type(None)) is True:
			self.load_df()
		# filter df with parameter inputs and sum up by week
		self.temp_df()
		self.create_file()
		self.find_diminishing_points()


# Load df from S3 or local drive for the first time runner
	def load_df(self):
		conn = s3_connector.s3_connector()
		df = conn.get_placement_report_export(self.yesterday, report = "") # fill in s3 bucket name

		df = pd.read_csv("")
		print("\n")

# Creat temp df with parameters filtered
	def temp_df(self):
		# Check if values of parameters are valid before filtering. If not, raise an error
		assert len([ct for ct in self.countries if ct not in list(self.df.Country.unique())])==0, "Please insert a valid country list!"
		assert len([f for f in self.funnels if f not in list(self.df.Funnel.unique())])==0, "Please insert a valid funnel list!"
		assert len([ch for ch in self.channels if ch not in list(self.df.Channel.unique())])==0, "Please insert a valid channel list!"
		assert self.partner in ['No', 'Yes'], "Please insert Yes or No!"
		measurement_list = ['Impressions', 'Clicks', 'Page Views', 'ESV', 'Free Signups', 'Paid Signups']
		assert self.measure in measurement_list, "Please insert a valid measurement!"

		temp = self.df[(self.df.Day >= self.start_date)
					& (self.df.Day <= self.end_date)
					& (self.df.Country.isin(self.countries))
					& (self.df.Funnel.isin(self.funnels))
					& (self.df.Channel.isin(self.channels))
					]
		# Sum up data by week by metrics
		if self.partner == "Yes":
			self.temp = temp.groupby([pd.Grouper(key='Day', freq='W'), 'Country', 'Funnel', 'Channel', 'Partner'])[
						'Media Cost', self.measure].sum().reset_index()
		else:
			self.temp = temp.groupby([pd.Grouper(key='Day', freq='W'), 'Country', 'Funnel', 'Channel'])[
						'Media Cost', self.measure].sum().reset_index()

# Create output Excel file with first sheet "parameters"
	def create_file(self):
		# Convert parameters to table
		temp = []
		parameters = [self.start_date, self.end_date, self.countries, self.funnels, self.channels, self.partner,
						self.measure, self.cost_per]
		names = ['Start Date', 'End Date', 'Country', 'Funnel', 'Channel', 'Partner', 'Measure', 'Cost Per']
		for n, i in enumerate(parameters):
			try:
				a = i.copy()
			except:
				try:
					a = list(i.split("."))
				except:
					try:
						a = list(str(i.strftime("%Y-%m-%d")).split("."))
					except:
						a = list(str(i).split("."))
			a.insert(0, names[n])
			temp.append(a)
		# Create file name
		parameter_sheet = pd.DataFrame(temp)
		if self.partner == "Yes":
			self.file_name = "Diminishing Return {} by Partner - Generated {}.xlsx".format(self.measure, datetime.datetime.now().strftime("%Y-%m-%d %H-%M"))
		else:
			self.file_name = "Diminishing Return {} by Channel - Generated {}.xlsx".format(self.measure, datetime.datetime.now().strftime("%Y-%m-%d %H-%M"))

		# Create Excel and add first sheet "parameters"
		with pd.ExcelWriter(self.file_name, engine='xlsxwriter') as writer:
			parameter_sheet.to_excel(writer, sheet_name="Parameters", index=False, header=False)
		print("File Saved: ", self.file_name)

# Formula of modeling
	def func(self, media_cost, a, b, c):
		return a / (1 + b * media_cost**c)

# 1, Fit model of each metric and create a curve line
# 2, Find diminishing return report
# 3, Generate result: num_of_data, slope, X/Y_hat value at DR point, mse, p_value
# 4, Save graphs to .png
	def modeling(self, temp_final, ct, f, ch, p=None, cost=None):
		n_rows = len(temp_final)
		# Do not model if weekly data is less than 26
		if n_rows<26:
			result = [ct, f, ch, n_rows, "No enough data"]
			if cost != None:
				if self.partner == "Yes":
					result = [ct, f, ch, p, n_rows, "No enough data"]
			return result

		# set X and Y for modeling
		else:
			temp_final = temp_final.sort_values(['Media Cost', self.measure], ascending = [True, True])

			if cost==None:
				xdata = temp_final['Media Cost'] / temp_final['Media Cost'].mean()
				ydata = temp_final[self.measure] / temp_final[self.measure].mean()
			else:
				xdata = temp_final['Media Cost']
				ydata = temp_final[self.measure] * self.cost_per

			# Fit X and Y with curve formula
			try:
				popt, pcov = curve_fit(self.func, xdata, ydata, bounds=self.bounds, maxfev=5000)

			#If model fails due to an unclear linear relationship, plot to .png and exit this function
			except:
				fig, ax = plt.subplots(figsize=(8,6))
				ax.plot(xdata, ydata, '.')
				ax.set_xlabel("Media Cost")
				ax.set_ylabel("Revenue")
				ax.set_title("{}_{}_{}".format(ct, f, ch))
				result = [ct, f, ch, n_rows, "Model does not converge"]
				if self.partner == "Yes":
					if cost != None:
						result = [ct, f, ch, p, n_rows, "Modl does not converge"]
						ax.set_title("{}_{}_{}_{}".format(ct, f, ch, p))

				self.image_num_fail += 1
				fig.savefig("img_fail_{}.png".format(self.image_num_fail), bbox_inches='tight', pad_inches=0.3, facecolor='white', transparent=False)
				plt.close(fig)
				return result

			# calculate mse and p_value
			if cost == None:
				mse = mean_squared_error(temp_final[self.measure], y_hat * temp_final[self.measure].mean())
				statistics, pvalue = stats.ttest_ind(temp_final[self.measure], y_hat * temp_final[self.measure].mean())
			else:
				mse = mean_squared_error(temp_final[self.measure], y_hat / self.cost_per)
				statistics, pvalue = stats.ttest_ind(temp_final[self.measure], y_hat / self.cost_per)


			# On the curve, find 100000 points and calculate slopes of each
			# Find the point where absolute value is closest to 1
			abs_diff = []
			slopes = []
			x1_values = []
			y1_values = []

			for x1 in np.linspace(xdata.min(), xdata.max(), 10**5):
				x2 = x1 + 0.001
				y1 = self.func(x1, a,b,c)
				y2 = self.func(x2, a,b,c)
				m = (y2-y1)/(x2-x1)
				slopes.append(m)
				abs_diff.append(np.abs(m-1))
				x1_values.append(x1)
				y1_values.append(y1)

			min_abs_diff = np.argmin(abs_diff)

			# set graph: scatter plot for historical data; curve for modeling line
			fig, ax = plt.subplots(figsize=(8,6))
			ax.plot(xdata, ydata, '.')
			ax.plot(xdata, y_hat, c='red')
			# plot DR point if exists
			if slopes[min_abs_diff] > 0.9:
				ax.plot(x1_values[min_abs_diff], y1_values[min_abs_diff], marker='o', markersize=10, markeredgecolor='red', markerfacecolor='red')
			ax.set_xlabel("Media Cost")
			ax.set_ylabel("Revenue")

			# set image title
			if self.partner == "Yes":
				ax.set_title("{}_{}_{}_{}".format(ct, f, ch, p))
			else:
				ax.set_title("{}_{}_{}".format(ct, f, ch))

			# Save image to .png
			self.image_num += 1
			fig.savefig("img_good_{}.png".format(self.image_num), bbox_inches='tight', pad_inches=0.3, facecolor='white', transparent=False)
			plt.close(fig)

			# Return all the results as a list
			if self.partner == "No":
				if cost == None:
					result = [ct, f, ch, n_rows, round(slopes[min_abs_diff],2), int(x1_values[min_abs_diff]*temp_final['Media Cost'].mean()),
								int(y1_values[min_abs_diff]*temp_final[self.measure].mean()), int(mse), round(pvalue,4)]

				else:
					result = [ct, f, ch, n_rows, round(slopes[min_abs_diff],2), int(x1_values[min_abs_diff]),
								int(y1_values[min_abs_diff]/self.cost_per), int(mse), round(pvalue,4)]
			else:
				if cost == None:
					result = [ct, f, ch, p, n_rows, round(slopes[min_abs_diff],2), int(x1_values[min_abs_diff]*temp_final['Media Cost'].mean()),
								int(y1_values[min_abs_diff]*temp_final[self.measure].mean()), int(mse), round(pvalue,4)]
				else:
					result = [ct, f, ch, p, n_rows, round(slopes[min_abs_diff],2), int(x1_values[min_abs_diff]),
								int(y1_values[min_abs_diff]/self.cost_per), int(mse), round(pvalue,4)]
			return result


# Filtering with each metric and then fit model by calling modeling() function
	def find_diminishing_points(self):

		# results by cost per
		results_cp = []
		# retults by index
		results_index = []
		results_fail = []

		# Filter each country
		for ct in list(self.temp.Country.unique()):
			temp_ct = self.temp[self.temp.Country == ct]
			# Filter each funnel
			for f in list(temp_ct.Funnel.unique()):
				temp_f = temp_ct[temp_ct.Funnel == f]
				# Filder each channel
				for ch in list(temp_f.Channel.unique()):
					temp_ch = temp_f[temp_f.Channel == ch]
					# If by parter is yes: filder each partner
					if self.partner == "No":
						temp_final = temp_ch[temp_ch['Media Cost']>0]
						result_cp = self.modeling(temp_final, ct, f, ch, cost=self.cost_per)
						# result_index = self.modeling(temp_final, ct, f, ch)
						if len(result_cp)<=6:
							results_fail.append(result_cp)
						else:
							results_cp.append(result_cp)
							# results_index.append(result_index)
					else:
						p_list = list(temp_ch.Partner.unique())
						for p in p_list:
							temp_final = temp_ch[temp_ch.Partner == p]
							temp_final = temp_final[temp_final['Media Cost']>0]
							result_cp = self.modeling(temp_final, ct, f, ch, p, cost=self.cost_per)
							# result_index = self.modeling(temp_final, ct, f, ch, p)
							if len(result_cp)<=6:
								results_fail.append(result_cp)
							else:
								results_cp.append(result_cp)


		if self.partner == "No":
			output_cp = pd.DataFrame(results_cp, columns=['Country', 'Funnel', 'Channel', '#_of_week', 'Slope',
									'Media cost', '{}'.format(self.measure), 'mse', 'p_value'])
			df_fail = pd.DataFrame(results_fail, columns=['Country', 'Funnel', 'Channel', '#_of_week', 'Reason'])
		else:
			output_cp = pd.DataFrame(results_cp, columns=['Country', 'Funnel', 'Channel', 'Partner', '#_of_week',
									'Slope', '{}'.format(self.measure), 'mse', 'p_value'])
			df_fail = pd.DataFrame(results_fail, columns=['Country', 'Funnel', 'Channel', 'Partner', '#_of_week', 'Reason'])

		output_cp['DR_Notes'] = ["Point Exists" if np.abs(x-1)<0.1 else "Point Does Not Exist" if x<0.9 else "Invest More" for x in output_cp['Slope']]
		output_cp.loc[output_cp.Slope<0.9, ['media_cost', '{}'.format(self.measure)]] = "NA", "NA"

		with pd.ExcelWriter(self.file_name, engine='openpyxl', mode='a') as writer:
			output_cp.to_excel(writer, sheet_name = "By Revenue", index=False)
			df_fail.to_excel(writer, sheet_name = "Fail Modeling", index=False)
			# output_index.to_excel(writer, sheet_name = "By Index", index=False)
		
		wb = openpyxl.load_workbook(self.file_name)
		ws1 = wb["By Revenue"]
		ws2 = wb["Fail Modeling"]
		output_len = len(output_cp)
		fail_len = len(df_fail)
		# find all .png files
		img_good_list = glob.glob("img_good_*.png")
		img_fail_list = glob.glob("img_fail_*.png")

		# Paste each image to sheets:
		for n, i in enumerate(img_good_list):
			# Read one image
			img = openpyxl.drawing.image.Image(i)
			img.height = 384
			img.width = 528
			# There are 2 columns for images and to determine the start cell of each image:
				# int(n/2): row # of image
				# 23 cells: height of image
				# 4 cells: add some space between every two images vertically
				# output_len: first row will go below the table
			padding = int(n/2) * 23 + 4 + output_len

			# images with odd column will be pasted to column A, otherwise do column I or G
			if n%2 == 0:
				img.anchor = "A{}".format(padding)
			else:
				img.anchor = "I{}".format(padding)
			ws1.add_image(img)

		for n, i in enumerate(img_fail_list):
			img = openpyxl.drawing.image.Image(i)
			img.height = 384
			img.width = 528
			padding = int(n/2) * 23 + 4 + output_len
			if n%2 == 0:
				img.anchor = "A{}".format(padding)
			else:
				img.anchor = "I{}".format(padding)
			ws2.add_image(img)
		wb.save(self.file_name)

		# Remove all .png files from folder
		for i in img_good_list:
			os.remove(i)
		for i in img_fail_list:
			os.remove(i)
		print("\nModeling Completed !!")

def run(self, countries, funnels, channels, partner, measure, start_date, end_date, cost_per):

	# set init parameters from Jupyter Notebook
	self.countries = countries
	self.funnels = funnels
	self.channels = channels
	self.partner = partner
	self.measure = measure
	# set start date to be the Monday before input start_date
	self.start_date = pd.to_datetime(start_date-datetime.timedelta(start_date.weekday()))
	# set end date to be the Sunday after input end_date
	self.end_date = pd.to_datetime(end_date - datetime.timedelta(6-end_date.weekday( )))
	self.cost_per = cost_per

	# call all functions in class
	# Load data from S3 for first-time run only
	if (type(self.df) == type(None)) is True:
		self.load_df()
	# filter df with parameter inputs and sum up by week
	self.temp_df()
	self.create_file()
	self.find_diminishing_points()


