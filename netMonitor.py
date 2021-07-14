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

    parser.add_argument("-t","--test", help="esegue uno speedtest 'times' volte con frequenza 'rate'",
            nargs=2, type=int, metavar=('times', 'rate'), default=[5, 180])
    parser.add_argument("-f","--forecast", help="esegue una previsione usando l'alpha (e beta) specificato", 
            nargs='+', type=float, metavar=('alpha', 'beta'), default=[0.75])

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
    dataframe = tmp_dataframe.set_index(datetime_index.to_period(freq='t'))
    dataframe.drop('time', axis=1, inplace=True)

    return dataframe

'''----------------------------------------------------------------------------------------------'''

''' esegue una previsione usando il Simple Exponential Smoothing '''

def ses(dataframe, alpha):
    fit = SimpleExpSmoothing(dataframe).fit(smoothing_level=alpha, optimized=False)
    forecast = fit.forecast(1).rename(r'$\alpha=' + str(alpha) + '$')
    forecast.plot(style='--', marker='o', color='red', legend=True)
    plot.savefig('ping', format='pdf')

'''----------------------------------------------------------------------------------------------'''

''' esegue una previsione usando il Double Exponential Smoothing '''

def des(dataframe, alpha, beta):
    fit = Holt(dataframe, exponential=True).fit(smoothing_level=alpha, smoothing_trend=beta, optimized=False)
    forecast = fit.forecast(2).rename("Exponential trend")
    forecast.plot(style='--', marker='o', color='red', legend=True)
    plot.show()

'''----------------------------------------------------------------------------------------------'''

''' funzione principale '''

def main():

    args = parse_args()
    print(args)
    times = args.test.pop(0)
    
    if times <= 0:
        print("times deve essere un intero maggiore di zero")
        exit(-1)

    rate = args.test.pop(0)

    if rate <= 0:
        print("rate deve essere un intero maggiore di zero")
        exit(-1)

    alpha = args.forecast.pop()
    if alpha > 1: 
        print('alpha deve essere compreso tra 0 e 1')
        exit(-1)

    beta = 0
    if len(args.forecast) > 0:
        beta = args.forecast.pop()
        if beta > 1: 
            print('beta deve essere compreso tra 0 e 1')
            exit(-1)

    user = input('Inserire lo username di influxdb: ')
    password = input('Inserire la password di influxdb: ')
    database_name = input('Inserire il nome del database di influxdb: ')

    client = InfluxDBClient(username=user, password=password, database=database_name)

    client.drop_measurement("speedtest")

    for i in range(times):
        init_time = time.time()
        results = test()
        write2Influx(client, "speedtest", results)
        final_time = time.time()
        time.sleep(rate - (final_time - init_time))

    dataframe = influx2DataFrame(client, 'select ping from speedtest')
    print(dataframe)
    dataframe.plot.line()
    if beta == 0:
        ses(dataframe, alpha)
    else:
        des(dataframe, alpha, beta)


if __name__ == '__main__':
    main()
