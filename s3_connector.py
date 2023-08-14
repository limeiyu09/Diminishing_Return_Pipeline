import boto3
import sys
import time
import re
import pandas as pd
import gzip
import io
import datetime
import zipfile
import json
from aws_creds import *
import glob
pd.set_option('display.max_columns', None)
from openpyxl import load_workbook

class data_loading:
	def __init__(self, bucket = "xxx", prefix = "xxx/"):
		# bucket is main bucket
		# prefix is the sub bucket under main bucket
		self.bucket = bucket
		self.prefix = prefix
		self.s3_client = boto3.client('s3',
									aws_access_key_id = aws_access_key_id,
									aws_secret_access_key = aws_secret_access_key)
		self.s3_paginator = self.s3_client.get_paginator('list_objects_v2')
	
	def load_keys(self, delimiter='/', start_after=''):
		bucket = self.bucket
		prefix = self.prefix
		prefix = prefix[1:] if prefix.startswith(delimiter) else prefix
		start_after = (start_after or prefix) if prefix.endswith(delimiter) else start_after
		for page in self.s3_paginator.paginate(Bucket = bucket, Prefix = prefix, StartAfter = start_after):
			for content in page.get('Contents', ()):
				yield content['Key']

	def get_export_dates_available(self):
		cur_keys = [] # get all sub folder names (data generated date etc) under sub bucket
		for key in sefl.load_keys(self.bucket):
			cur_keys.append(key)

		pattern = 'xxxx/Generated_(\d{4}-\d{2}-\d{2})/'
		daily_exports = [k for k in cur_keys if re.match(pattern, k)]
		print("Total keys found: {}".format(len(cur_keys)))
		print("Daily Exports found: {}".format(len(daily_exports)))

		report_export_dates = [pd.to_datetime(re.findall(pattern, k)[0]) for k in daily_exports]
		report_export_dates = sorted(list(set(report_export_dates)))
		report_export_dates = [d.strftime("%Y-%m-%d") for d in report_export_dates]
		print("Total days of cached data: ", len(report_export_dates)) # check length of date list
		print("Most recent days with data cached: ", report_export_dates[-5:]) # show last 5 output

		self.cur_keys = cur_keys
		self.daily_exports = daily_exports
		self.report_export_dates = report_export_dates

	def load_s3_zipped_csv(self, key):
		obj = self.s3_client.get_object(Bucket=self.bucket, Key = key)
		buffer = io.BytesIO(obj["Body"].read())
		z = zipfile.ZipFile(buffer)
		temp = pd.read_csv(z.open(z.infolist()[0]), skiprows=6)
		return temp

	def load_date_exports(self, date, print_size = False, print_dates = False):
		daily_exports = self.daily_exports
		daily_exports_folder = 'xxx/xxx/'
		date_folder = "{}Geenrated_{}".format(daily_exports_folder, date)
		date_exports = [k for k in daily_exports if k[:len(date_folder)] == date_folder]
		dfs = []
		tot = 0

		for i, key in enumerate(date_exports):
			sys.stdout.write("\rLoading file {} of {}: {}...".format(i, len(date_exports), key[len(date_folder):]))
			temp = self.load_s3_zipped_csv(key)
			# or use below if sub folders are not zipped
			obj = self.s3_client.get_object(Bucket=bucket, Key=key)
			temp = self.read_csv(obj['Body'], skiprows=6)
			tot += len(temp)
			dfs.append(temp)
		df = pd.concat(dfs, ignore_index=True)
		return df