"""
A module for loading weather data and forecasts from FMI open data.
Oulun Energia uses temperature data of fmisid = 101799, Pellonpää.
Functions:
    get_observations(): Load past temperature observations.
    get_forecast(): Load temperature forecast.
    _fmi_inputchecks(): Validity check of input arguments.
    _get_param_name(): Return chosen parameter's name in FMI data.
    _get_datetime_limits(): Infer and return start and end of timerange.
    _do_query(): Query FMI using stored query id and related parameters.
    _tree_to_df(): FMI supplies data as XML. Turn into pandas df.
"""

from datetime import datetime, timedelta, date

import pandas as pd
from owslib.wfs import WebFeatureService
import xml.etree.ElementTree as ET

def get_observations(
        place=None,
        fmisid=None,
        parameter=None,
        hours=None,
        start_date=None,
        end_date=None,
        ):
    """
    Load past observations of outdoor temperature for a city or fmisid.
    PARAMETERS
    place -- str. Name of a Finnish city.
    fmisid -- str or int. Observation station id, can be found from FMI
    website. In Oulu: Pellonpää - 101799, Vihreäsaari - 101794,
    Lentoasema - 101786.
    parameter -- str. Name of the parameter to load. Valid values:
        "temperature", "temperature_avg", "temperature_max",
        "temperature_min", "humidity", "relative_humidity", "wind_speed_avg",
        "wind_speed_max", "wind_speed_min", "wind_direction",
        "rain_accumulated", "rain_intensity_max", "air_pressure".
    hours -- int. How many past hours to load.
    start_date, end_date -- str as "YYYY-MM-DD" or date obj. Alternative to
    hours argument. If only start_date supplied, load from start_date until
    current moment. If only end_date supplied, load from 2018-01-01 until 
    end_date.
    VALUE
    A pandas data frame with columns:
        "date"  -- datetime, UTC.
        "value" -- float.
    """
    _fmi_inputchecks(place, fmisid, parameter)

    params = {"place": place} if place else {"fmisid": fmisid}
    params["parameters"] = _get_param_name(parameter, "observation")
    queryid = "fmi::observations::weather::hourly::simple"

    # start and end times of period to load -> pandas df
    def _load_obs(start, end):
        params["starttime"] = start.isoformat()
        params["endtime"]   = end.isoformat()
        tree    = _do_query(queryid, params)
        df      = _tree_to_df(tree)
        return df

    start, end = _get_datetime_limits(start_date, end_date, hours)

    # The following headache is due to FMI returning max 744 hours
    # with one query.
    hours = divmod((end-start).total_seconds(), 3600)[0]
    too_long = hours > 744

    if not too_long:
        return _load_obs(start, end)
    else:
        # Load one month at time

        # Get last hour of month:
        def _month_last_h(dt):
            dt = dt.replace(day=28)
            dt = dt + timedelta(days=4)
            dt = dt.replace(day=1)
            dt = datetime.combine(dt.date(), datetime.min.time())
            dt = dt - timedelta(hours=1)
            return(dt)

        # initialize df
        df = pd.DataFrame(columns=["date", "value"])
        end_reached = False

        while not end_reached:
            # Define 1 month chunk from the beginning:
            block_start = start
            last_hour = _month_last_h(start)
            if end < last_hour:
                end_reached = True
                block_end = end
            else:
                block_end = last_hour

            # Load one month:
            load_more_df = _load_obs(block_start, block_end)
            df = pd.concat([df, load_more_df], ignore_index=True)

            # Set new start
            start = block_end + timedelta(hours=1)

    return df


def get_forecast(
        place=None,
        fmisid=None,
        parameter=None,
        model="harmonie",
        hours=None
        ):
    """
    Load FMI forecast for the given place (city) or fmisid (observation
    station id). By default, return Harmonie algorithm forecast 66 hours
    ahead. Alternative model is model="hirlam" and fewer hours ahead can be
    fetched by supplying the hours argument.
    ARGUMENTS
    place -- str. Name of a Finnish city.
    fmisid -- str. Observation station id, can be found from FMI website.
    parameter -- str. Name of the parameter to load. Valid values:
        "air_pressure", "temperature", "humidity", "wind_direction",
        "wind_speed".
    model -- str. Choose "harmonie" or "hirlam", default "harmonie".
    hours -- int. How many future hours to load.
    VALUE
    A pandas dataframe.
    """
    # input checks & collect parameters for FMI query
    _fmi_inputchecks(place, fmisid, parameter, model)
    params = {"place": place} if place else {"fmisid": fmisid}
    params["parameters"] = _get_param_name(parameter, "forecast")

    now = datetime.now().replace(microsecond=0, second=0)
    # According to FMI, harmonie predicts 66 following hours and 
    # hirlam 54. Use hours argument if provided, otherwise use a default:
    if hours:
        h = hours
    elif model == "harmonie":
        h = 66
    else:
        h = 54

    params["endtime"] = (now + timedelta(hours=h)).isoformat()

    # Choose queryid according to model
    if model == "harmonie":
        queryid = "fmi::forecast::harmonie::hybrid::point::simple"
    else:
        queryid = "fmi::forecast::hirlam::surface::point::simple"

    tree = _do_query(queryid, params)
    df   = _tree_to_df(tree)

    return df
        

def _fmi_inputchecks(place, fmisid, parameter, model=None):
    """
    Check validity of function arguments.

    PARAMETERS
    place -- str. A city name in Finland.
    fmisid -- str. Observation station id.
    parameter -- str. Parameter name.
    model -- str. Forecast model name (optional).
    """
    if not parameter:
        raise ValueError("argument 'parameter' not provided")

    if not place and not fmisid: 
        raise ValueError("Please provide either place or fmisid argument")
    if model:
        if not model in ["harmonie", "hirlam"]:
           raise ValueError("""Unknown model.
                   Please choose harmonie or hirlam, default is harmonie.""")


def _get_param_name(wanted_param:str, query_type=None) -> str:
    """
    Return the name of wanted parameter in FMI XML.

    PARAMETERS
    wanted_param -- string. The wanted parameter.
    query_type -- string. One of "observation", "forecast".

    VALUE
    string
    """
    if not query_type:
        raise ValueError("parameter 'query_type' not provided.")
    
    valid = ["observation", "forecast"]
    if query_type not in valid:
        raise ValueError("query_type '" + query_type + "' not one of \
                expected: " + ", ".join(valid) + ".")

    if query_type == "observation":

        legit_params = ["temperature", "temperature_avg", "temperature_max",
                "temperature_min", "humidity", "relative_humidity",
                "wind_speed_avg", "wind_speed_max", "wind_speed_min",
                "wind_direction", "rain_accumulated", "rain_intensity_max",
                "air_pressure"]
        if wanted_param not in legit_params:
            raise ValueError("Asked parameter '" + wanted_param +
                    "' does not match any expected value. Legit values are: "\
                    + ", ".join(legit_params) + ".")

        match wanted_param:
            case "temperature":
                return "TA_PT1H_AVG"
            case "temperature_avg":
                return "TA_PT1H_AVG"
            case "temperature_max":
                return "TA_PT1H_MAX"
            case "temperature_min":
                return "TA_PT1H_MIN"
            case "humidity":
                return "RH_PT1H_AVG"
            case "relative_humidity":
                return "RH_PT1H_AVG"
            case "wind_speed":
                return "WS_PT1H_AVG"
            case "wind_speed_avg":
                return "WS_PT1H_AVG"
            case "wind_speed_max":
                return "WS_PT1H_MAX"
            case "wind_speed_min":
                return "WS_PT1H_MIN"
            case "wind_direction":
                return "WD_PT1H_AVG"
            case "rain_accumulated":
                return "PRA_PT1H_ACC"
            case "rain_intensity_max":
                return "PRI_PT1H_MAX"
            case "air_pressure":
                return "PA_PT1H_AVG"

    elif query_type == "forecast":

        legit_params = ["air_pressure", "temperature", "humidity",
                "wind_direction", "wind_speed"]
        if wanted_param not in legit_params:
            raise ValueError("Asked parameter '" + wanted_param +
                    "' does not match any expected value. Legit values are: "\
                    + ", ".join(legit_params) + ".")

        match wanted_param:
            case "air_pressure":
                return "Pressure"
            case "temperature":
                return "Temperature"
            case "humidity":
                return "Humidity"
            case "wind_direction":
                return "WindDirection"
            case "wind_speed":
                return "WindSpeedMS"


def _get_datetime_limits(start_date=None, end_date=None, hours=None):
    """
    According to given time information, return start and end of timerange.
    PARAMETERS
    hours -- int. How many hours to load.
    start_date, end_date -- str as "YYYY-MM-DD" or date obj. Alternative to
    hours argument. If only start_date supplied, load from start_date until
    current moment. If only end_date supplied, load from 2018-01-01 until 
    end_date.
    VALUE
    A tuple (start, end) of datetime objects.
    """
    if start_date:
        if isinstance(start_date, str):
            start_date = datetime.strptime(start_date, "%Y-%m-%d")
        start = datetime.combine(start_date, datetime.min.time())
    if end_date:
        if isinstance(end_date, str):
            end_date = datetime.strptime(end_date, "%Y-%m-%d")
        end = datetime.combine(end_date, datetime.max.time())
        end = end.replace(microsecond=0, second=0)

    if not any([hours, start_date, end_date]):
        raise ValueError("None provided: hours/start_date/end_date")
    if all([hours, start_date, end_date]):
        raise ValueError(
                "All provided: hours/start_date/end_date. All three should not \
                be given."
                )

    # set initial start and end time:
    now = datetime.now().replace(microsecond=0, second=0)
    if not start_date and not end_date:
        # Default to loading most recent observations
        start = (now - timedelta(hours=hours))
        end = now
    elif end_date and not start_date:
        if hours:
            start = end - timedelta(hours=hours)
        else:
            start = datetime(2018, 1, 1, 0, 0, 0)
    elif start_date and not end_date:
        if hours:
            end = start + timedelta(hours=hours)
        else:
            end = now
                
    # No use trying to load future:
    end = min(now, end)

    return (start, end)

def _do_query(queryid, params):
    """
    Query FMI open data by providing queryid and query parameters.
    ARGUMENTS
    queryid -- string. Id of the FMI stored query.
    params -- dict. Parameters passed for query.
    Options for both queryid and params can be found in
    http://opendata.fmi.fi/wfs?service=WFS&version=2.0.0&request=describeStoredQueries&.
    VALUE
    A xml.etree.ElementTree object including the data in query response.
    """
    
    # Create connection
    wfs20 = WebFeatureService(
            url='https://opendata.fmi.fi/wfs',
            version='2.0.0')
    # Perform query using queryid and params:
    data = wfs20.getfeature(
        storedQueryID=queryid,
        storedQueryParams=params
        )
    xml_str = data.read().decode("utf-8") # to string
    tree = ET.fromstring(xml_str) # to tree element
    return tree


def _tree_to_df(tree):
    """
    Take a tree object of FMI data and transform into a pandas dataframe.
    """

    times = []
    values = []
    const_tags = [
            "{http://www.opengis.net/gml/3.2}pos",
            "{http://xml.fmi.fi/schema/wfs/2.0}ParameterName"]
    time_tag = "{http://xml.fmi.fi/schema/wfs/2.0}Time"
    value_tag = "{http://xml.fmi.fi/schema/wfs/2.0}ParameterValue"
    for el in tree.iter():
        if not el.text.isspace() and not el.tag in const_tags:
            if el.tag == time_tag:
                times.append(el.text)
            elif el.tag == value_tag:
                values.append(el.text)


    df = pd.DataFrame({"date": times, "value": values})

    #Set column types
    df.date = pd.to_datetime(
            df["date"],
            infer_datetime_format=True,
            utc=True)
    df.value = df["value"].astype("float")
    return df
