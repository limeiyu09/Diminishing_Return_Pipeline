from IPython.display import display
import ipywidgets as widgets
import datetime

import diminishing_return_class
dr = diminishing_return_class.diminishing_return()

start_date = widgets.DatePicker(
	description='Start Date',
	disabled=False,
	max=datetime.date.today()
)

end_date = widgets.DatePicker(
	description='End Date',
	disabled=False,
)

countries = widgets.SelectMultiple(
	options=['United States', 'Canada', 'Australia', 'United Kingdom'],
	description='Country(ies)',
	disabled=False
)

funnels = widgets.SelectMultiple(
	options = ['Attract', 'Engage', 'Acquire', 'Upcell'],
	description='Funnel(s)',
	desabled=False
)

channels = widgets.SelectMultiple(
	options=['Video', 'Programmatic Display', 'Direct Display',
			'Social', 'Search'],
	description='Channel(s)',
	disabled=False
)

partner = widgets.Dropdown(
	options=['Yes', 'No'],
	description='By Partner'
)

measure = widgets.Dropdown(
	options=['Impressions', 'Clicks','Page Views', 'ESV', 'Conversions'],
	description='Measure'
)

cost_per = widgets.BoundedIntText(
	min=0,
	max=10000,
	step=100,
	description='Cost Per',
	desabled=False
)

button = widgets.Button(description='Submit')
output = widgets.Output()

def on_button_clicked(x):
	with output:
		assert start_date.value < end_date.value, "End Date must be greater than Start Date!!!"
		assert (end_date.value - start_date.value).days / 7 > 25, "Data range must be more than half year!!!"
		dr.run(list(countries.value), list(funnels.value), list(channels.value), partner.value,
			measure.value, start_date.value, end_date.value, cost_per.value)
button.on_click(on_button_clicked)

print("** Hold Ctrl to select multiple countries, funnels, and channels.")
display(start_date, end_date, countries, funnels, channels, partner, measure, cost_per)

display(button, output)