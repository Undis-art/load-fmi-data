# FMI data to pandas DataFrames made easy

Easy to use tools for loading open weather data of Finnish Meteorological Institute into pandas DataFrames.

## What is supported

Tools are provided for loading hourly weather observations and forecasts.

### Past observations: **get\_observations**

Past observations can be downloaded with **get\_observations**, which accepts the following arguments:
- **place** -- str. Name of a Finnish city.
- **fmisid** -- str or int. Observation station id, can be found from FMI website: https://www.ilmatieteenlaitos.fi/havaintoasemat
- **parameter** -- str. Name of the parameter to load. Parameters supported by this query are:
temperature, temperature\_avg, temperature\_max, temperature\_min, humidity, relative\_humidity, wind\_speed\_avg, wind\_speed\_max, wind\_speed\_min, wind\_direction, rain\_accumulated, rain\_intensity\_max, air\_pressure.
- **hours** -- int. How many past hours to load.
- **start_date, end_date** -- str as "YYYY-MM-DD" or date obj. Alternative to hours argument. If only start\_date supplied, load from start\_date until current moment. If only end\_date supplied, load from 2018-01-01 until end\_date.

Example usage:

```
# Load temperature observations of Helsinki since beginning of 09/2022
temp_df = get_observations(
        place="Helsinki",
        parameter="temperature",
        start_date="2022-09-01",
        )
```


### Forecasts: **get_forecast**

Weather forecasts can be downloaded with **get_forecast**, which accepts the following arguments:
- **place** -- str. Name of a Finnish city.
- **fmisid** -- str or int. Observation station id, can be found from FMI website: https://www.ilmatieteenlaitos.fi/havaintoasemat
- **parameter** -- str. Name of the parameter to load. Parameters supported by this query are:
air\_pressure, temperature, humidity, wind\_direction, wind\_speed.
- **model** -- str, optional. Name of the prediction model, one of ["harmonie", "hirlam"]. Default is "harmonie", which is the new model.
- **hours** -- int, optional. How many hours ahead to load.

Example usage:

```
# Load wind speed forecast of weather station Alajärvi, Möksy (fmisid 101533)
# for forecoming 24 hours
wind_forecast = get_forecast(
        fmisid="101533",
        parameter="wind_speed",
        hours=24,
        )
```

## Setup

After loading the contents of repository in a directory. Recommended steps:

#### Create a virtual environment

In Linux:

```
python -m venv venv
```

In Windows:

```
virtualenv venv
```

#### Activate virtual environment

In Linux:
```
source venv/bin/activate
```
In Windows:
```
venv/Scripts/activate
```

#### Install required packages

```
pip install -r requirements.txt
```

#### Ready to go

Now your environment is ready for running the code. Working examples can be found in example.py file.

#### Deactivate virtual environment

When you are done, deactivate virtual environment by
```
deactivate
```

