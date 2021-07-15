import argparse
import time 
import os
import pandas as pd
import matplotlib.pyplot as plot
from datetime import datetime 
from speedtest import Speedtest
from influxdb import InfluxDBClient
from statsmodels.tsa.api import SimpleExpSmoothing, Holt


GRAPHICS_PATH = './graphics'


''' legge le opzioni e gli argomenti passati da linea di comando '''

def parse_args():

    parser = argparse.ArgumentParser(prog="netMonitor.py")

    parser.add_argument("-t","--test", help="esegue uno speedtest 'times' volte",
            nargs=1, type=int, metavar='times', default=5)
    parser.add_argument("-f","--forecast", help="esegue una previsione usando l'alpha (e beta) specificato", 
            nargs='+', type=float, metavar=('alpha', 'beta'), default=[0.75])

    args = parser.parse_args()

    return args

'''----------------------------------------------------------------------------------------------'''

''' esegue lo speedtest sia in download e ritorna un dizionario contenente i risultati '''

def test():
    s = Speedtest()

    #ottengo il miglior server disponibile
    s.get_best_server()

    #eseguo lo speedtest
    s.download(threads=1)
    s.upload(threads=1)

    return s.results.dict()

'''----------------------------------------------------------------------------------------------'''

''' scrive i risultati di uno speedtest nella tabella measurement tramite il client di influxdb '''

def write2Influx(client, measurement, data):

    #salvo l'istante di scrittura
    local_time = datetime.now()

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

''' esegue una query sul database e trasforma il risultato in un dataframe '''

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

def ses(dataframe, alpha):
    fit = SimpleExpSmoothing(dataframe).fit(smoothing_level=alpha, optimized=False)
    forecast = fit.forecast(1).rename('Simple Exp Smoothing')
    forecast.plot(style='--', marker='o', color='red', legend=True)

    plot.xlim(dataframe.index[0], datetime.fromtimestamp(time.time()+360))

'''----------------------------------------------------------------------------------------------'''

''' esegue una previsione usando il Double Exponential Smoothing '''

def des(dataframe, alpha, beta):
    fit = Holt(dataframe, exponential=True).fit(smoothing_level=alpha, smoothing_trend=beta, optimized=False)
    forecast = fit.forecast(2).rename("Exponential trend")
    forecast.plot(style='--', marker='o', color='red', legend=True)

    plot.xlim(dataframe.index[0], datetime.fromtimestamp(time.time()+540))

'''----------------------------------------------------------------------------------------------'''

def create_graphs(client, attribute, alpha, beta):
    
    dataframe = influx2DataFrame(client, 'select ' + attribute + ' from speedtest')
    print(dataframe)
    dataframe.plot.line()

    if beta == 0:
        ses(dataframe, alpha)
    else:
        des(dataframe, alpha, beta)

    plot.xlabel('Time')
    if attribute=='ping':
        plot.ylabel('Ping (ms)')
    elif attribute=='download':
        plot.ylabel('Download (Mbps)')
    else:
        plot.ylabel('Upload (Mbps)')

    plot.grid(axis='both', which='both')
    plot.savefig(f'{GRAPHICS_PATH}/{attribute}', format='pdf')


'''----------------------------------------------------------------------------------------------'''

''' funzione principale '''

def main():

    args = parse_args()
    print(args)
    times = args.test
    
    if times <= 0:
        print('times deve essere un intero maggiore di zero')
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
        print('Starting speedtest number ' + str(i+1))
        results = test()
        write2Influx(client, "speedtest", results)
        final_time = time.time()
        if i != (times-1):
            time.sleep(180 - (final_time - init_time))

    if not os.path.exists(GRAPHICS_PATH):
        os.makedirs(GRAPHICS_PATH)

    create_graphs(client, 'ping', alpha, beta)
    create_graphs(client, 'download', alpha, beta)
    create_graphs(client, 'upload', alpha, beta)

    client.close()

'''----------------------------------------------------------------------------------------------'''

if __name__ == '__main__':
    main()
