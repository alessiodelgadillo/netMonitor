import time 
import datetime
import pandas as pd
import matplotlib.pyplot as plot
from speedtest import Speedtest
from influxdb import InfluxDBClient
from statsmodels.tsa.api import SimpleExpSmoothing, Holt


def test(): 
    s = Speedtest()
    s.get_best_server()

    s.download(threads=1)
    s.upload(threads=1)

    return s.results.dict()

def write2Influx(client, measurement, data):

    local_time = datetime.datetime.now()

    point = [
            {
                "measurement": measurement,
                "time": local_time,
                "fields": {
                    "download": data["download"]/1000000,
                    "upload": data["upload"]/1000000,
                    "ping": data["ping"]
                    }
                }
            ]
    client.write_points(point)

def influx2DataFrame(client, query):
    points = client.query(query).get_points()
    tmp_dataframe = pd.DataFrame(points)
    datetime_index = pd.DatetimeIndex(pd.to_datetime(tmp_dataframe["time"]).values)
    dataframe = tmp_dataframe.set_index(datetime_index.to_period(freq='3t'))
    dataframe.drop('time', axis=1, inplace=True)
    return dataframe

def ses(dataframe, alpha, nForecast):
    fit = SimpleExpSmoothing(dataframe).fit(smoothing_level=alpha, optimized=False)
    forecast = fit.forecast(nForecast).rename(r'$\alpha=' + str(alpha) + '$')
    forecast.plot(style='--', marker='o', color='red', legend=True)
    plot.show()

def main():
    client = InfluxDBClient("127.0.0.1", 8086, "alessio", "gestione21", "speedtest")
    dataframe = influx2DataFrame(client, 'select ping from speedtest')
    print(dataframe)
    dataframe.plot.line()
    ses(dataframe, 0.2, 3)

if __name__ == '__main__':
    main()
