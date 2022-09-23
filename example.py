import fmi

# Load temperature observations of Helsinki since beginning of 09/2022
temp_df = fmi.get_observations(
        place="Helsinki",
        parameter="temperature",
        start_date="2022-09-01",
        )

# Load wind speed forecast of weather station Alajärvi, Möksy (fmisid 101533)
# for forecoming 24 hours
wind_forecast = fmi.get_forecast(
        fmisid="101533",
        parameter="wind_speed",
        hours=24,
        )

