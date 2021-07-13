import argparse
import time 
import datetime
import pandas as pd
import matplotlib.pyplot as plot
from speedtest import Speedtest
from influxdb import InfluxDBClient
from statsmodels.tsa.api import SimpleExpSmoothing, Holt

""" legge le opzioni e gli argomenti passati da linea di comando """

def parse_args():

    parser = argparse.ArgumentParser(prog="netMonitor.py")

    parser.add_argument("-t","--test", help="esegue uno speedtest 'times' volte con frequenza 'frequency'",
             nargs='*', type=int, metavar=('times', 'frequency'))
    parser.add_argument("-p","--plot", help="mostra il grafico dei dati raccolti",
            action="store_true")
    parser.add_argument("-f","--forecast", help="esegue una previsione usando i dati raccolti",
            nargs='*', type=float, metavar=('alpha', 'beta'))

    args = parser.parse_args()

    return args

'''----------------------------------------------------------------------------------------------'''

""" esegue lo speedtest sia in download e ritorna
    un dizionario contenente i risultati """

def test():
    s = Speedtest()

    #ottengo il miglior server disponibile
    s.get_best_server()
    
    #eseguo lo speedtest
    s.download(threads=1)
    s.upload(threads=1)

    return s.results.dict()

'''----------------------------------------------------------------------------------------------'''

'''  scrive i risultati di uno speedtest nella tabella measurement 
    tramite il client di influxdb '''

def write2Influx(client, measurement, data):
    
    #salvo l'istante di scrittura
    local_time = datetime.datetime.now()

    #genero il punto da inserire nel db
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

'''----------------------------------------------------------------------------------------------'''

''' esegue una query sul database e trasforma
    il risultato in un dataframe '''

def influx2DataFrame(client, query):
    
    #ottengo il risultato della query e la trasformo in un dataframe
    points = client.query(query).get_points()
    tmp_dataframe = pd.DataFrame(points)

    #trasformo la colonna contenente il tempo nell'indice del dataframe
    datetime_index = pd.DatetimeIndex(pd.to_datetime(tmp_dataframe["time"]).values)
    dataframe = tmp_dataframe.set_index(datetime_index.to_period(freq='3t'))
    dataframe.drop('time', axis=1, inplace=True)

    return dataframe

'''----------------------------------------------------------------------------------------------'''

''' esegue una previsione usando il Simple Exponential Smoothing '''

def ses(dataframe, alpha, nForecast):
    fit = SimpleExpSmoothing(dataframe).fit(smoothing_level=alpha, optimized=False)
    forecast = fit.forecast(nForecast).rename(r'$\alpha=' + str(alpha) + '$')
    forecast.plot(style='--', marker='o', color='red', legend=True)
    plot.show()

'''----------------------------------------------------------------------------------------------'''

''' funzione principale '''

def main():
    
    args = parse_args()
    print(args)

    '''client = InfluxDBClient("127.0.0.1", 8086, "alessio", "gestione21", "speedtest")
    dataframe = influx2DataFrame(client, 'select ping from speedtest')
    print(dataframe)
    dataframe.plot.line()
    ses(dataframe, 0.2, 3) '''
    


if __name__ == '__main__':
    main()
