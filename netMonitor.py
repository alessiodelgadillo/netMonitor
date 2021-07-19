#!/usr/bin/env python3
import argparse
import time 
import os
import pandas as pd
import matplotlib.pyplot as plot
import warnings
from datetime import datetime 
from speedtest import Speedtest
from influxdb import InfluxDBClient
from statsmodels.tsa.api import SimpleExpSmoothing, Holt

DATA = './data'
GRAPHICS = './graphics'


''' legge le opzioni e gli argomenti passati da linea di comando '''

def parse_args():

    parser = argparse.ArgumentParser(prog="netMonitor.py")

    parser.add_argument("-t","--test", help="esegue uno speedtest <series> volte con frequenza <rate>",
            nargs='+', type=int, metavar=('series', 'rate'), default=[5, 3])
    parser.add_argument("-f","--forecast", help="esegue una previsione usando l'<alpha> (e <beta>) specificato", 
            nargs='+', type=float, metavar=('alpha', 'beta'), default=[0.75])
    parser.add_argument("-e", "--export", help="esporta i dati raccolti in formato csv", action="store_true")

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

def influx2DataFrame(client, query, rate):

    #ottengo il risultato della query e la trasformo in un dataframe
    points = client.query(query).get_points()
    tmp_dataframe = pd.DataFrame(points)

    #trasformo la colonna contenente il tempo nell'indice del dataframe
    datetime_index = pd.DatetimeIndex(pd.to_datetime(tmp_dataframe["time"]).values)
    freq = str(rate) + 't'
    dataframe = tmp_dataframe.set_index(datetime_index.to_period(freq=freq))
    dataframe.drop('time', axis=1, inplace=True)

    return dataframe

'''----------------------------------------------------------------------------------------------'''

''' esegue una previsione usando il Simple Exponential Smoothing '''

def ses(dataframe, alpha):
    fit = SimpleExpSmoothing(dataframe).fit(smoothing_level=alpha, optimized=False)
    forecast = fit.forecast(1).rename('Simple Exp Smoothing')
    forecast.plot(style='--', marker='o', color='red', legend=True)

'''----------------------------------------------------------------------------------------------'''

''' esegue una previsione usando il Double Exponential Smoothing '''

def des(dataframe, alpha, beta):
    fit = Holt(dataframe, exponential=True).fit(smoothing_level=alpha, smoothing_trend=beta, optimized=False)
    forecast = fit.forecast(2).rename("Exponential trend")
    forecast.plot(style='--', marker='o', color='red', legend=True)

'''----------------------------------------------------------------------------------------------'''

def create_graphs(client, attribute, alpha, beta, rate):
    
    dataframe = influx2DataFrame(client, 'select ' + attribute + ' from speedtest', rate)
    print(dataframe)
    dataframe.plot.line()
    if beta == 0:
        ses(dataframe, alpha)
        plot.xlim(dataframe.index[0], datetime.fromtimestamp(time.time()+ rate * (2*60)))
    else:
        des(dataframe, alpha, beta)
        plot.xlim(dataframe.index[0], datetime.fromtimestamp(time.time()+ rate *(3*60)))

    plot.xlabel('Time')
    if attribute=='ping':
        plot.ylabel('Ping (ms)')
    elif attribute=='download':
        plot.ylabel('Download (Mbps)')
    else:
        plot.ylabel('Upload (Mbps)')

    plot.grid(axis='both', which='both')
    plot.savefig(f'{GRAPHICS}/{attribute}.pdf', format='pdf')


'''----------------------------------------------------------------------------------------------'''

''' funzione principale '''

def main():

    args = parse_args()
    print(args)
    series = args.test.pop(0)
    
    if series <= 1:
        print('series deve essere un intero maggiore di uno')
        exit(-1)

    rate = 3
    if len(args.test) > 0:
        rate = args.test.pop(0)
        if rate < 3:
            print('rate deve essere maggiore di 3')
            exit(-1)


    alpha = args.forecast.pop(0)
    if alpha > 1 or alpha < 0: 
        print('alpha deve essere compreso tra 0 e 1')
        exit(-1)

    beta = 0
    if len(args.forecast) > 0:
        beta = args.forecast.pop(0)
        if beta > 1 or beta < 0: 
            print('beta deve essere compreso tra 0 e 1')
            exit(-1)


    export = args.export
    user = input('Inserire lo username di influxdb: ')
    password = input('Inserire la password di influxdb: ')
    database_name = input('Inserire il nome del database di influxdb: ')

    client = InfluxDBClient(username=user, password=password, database=database_name)

    client.drop_measurement("speedtest")
    
    for i in range(series):
        init_time = time.time()
        print('Starting speedtest number ' + str(i+1))
        results = test()
        write2Influx(client, "speedtest", results)
        final_time = time.time()
        if i != (series-1):
            time.sleep(rate*60 - (final_time - init_time))

    if not os.path.exists(DATA):
        os.makedirs(DATA)
    
    os.chdir(DATA)

    directory = datetime.now().strftime("%Y-%m-%d_%H.%M.%S")
    os.makedirs(directory)
     
    os.chdir(directory)

    if export==True:
        dataframe = influx2DataFrame(client, 'select * from speedtest', rate)
        dataframe.to_csv("./data.csv")

    if not os.path.exists(GRAPHICS):
        os.makedirs(GRAPHICS)
    
    warnings.simplefilter(action='ignore', category=FutureWarning)
    create_graphs(client, 'ping', alpha, beta, rate)
    create_graphs(client, 'download', alpha, beta, rate)
    create_graphs(client, 'upload', alpha, beta, rate)
    client.close()


'''----------------------------------------------------------------------------------------------'''

if __name__ == '__main__':
    main()
