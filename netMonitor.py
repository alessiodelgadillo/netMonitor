#!/usr/bin/env python3
import argparse
import time
import os
import pandas as pd
import matplotlib.pyplot as plot
import warnings
from datetime import datetime
from speedtest import Speedtest
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

def write_point(points, data):

    #salvo l'istante di scrittura
    local_time = datetime.now()

    #genero il punto da inserire nel db
    point = {
            "time": local_time,
            "download": data["download"]/1000000,
            "upload": data["upload"]/1000000,
            "ping": data["ping"]
            }

    points.append(point)

'''----------------------------------------------------------------------------------------------'''

''' esegue una query sul database e trasforma il risultato in un dataframe '''

def points2DataFrame(points, rate):

    tmp_dataframe = pd.DataFrame(points)

    #trasformo la colonna contenente il tempo nell'indice del dataframe
    datetime_index = pd.DatetimeIndex(pd.to_datetime(tmp_dataframe["time"]).values)
    freq = str(rate) + 't'
    dataframe = tmp_dataframe.set_index(datetime_index.to_period(freq=freq))

    #rimuovo la colonna del tempo
    dataframe.drop('time', axis=1, inplace=True)

    return dataframe

'''----------------------------------------------------------------------------------------------'''

''' esegue una previsione usando il Simple Exponential Smoothing '''

def ses(dataframe, alpha):
    fit = SimpleExpSmoothing(dataframe).fit(smoothing_level=alpha, optimized=False)
    forecast = fit.forecast(1).rename('Simple Exp Smoothing')
    fit.fittedvalues.plot(style='--', marker='o', color='red')
    forecast.plot(style='--', marker='o', color='red', legend=True)

'''----------------------------------------------------------------------------------------------'''

''' esegue una previsione usando il Double Exponential Smoothing '''

def des(dataframe, alpha, beta):
    fit = Holt(dataframe, exponential=True).fit(smoothing_level=alpha, smoothing_trend=beta, optimized=False)
    forecast = fit.forecast(2).rename("Exponential trend")
    fit.fittedvalues.plot(style='--', marker='o', color='red')
    forecast.plot(style='--', marker='o', color='red', legend=True)

'''----------------------------------------------------------------------------------------------'''

def create_graphs(data, attribute, alpha, beta, rate):

    #recupero i dati del test
    dataframe = pd.DataFrame(data[attribute])
    print(dataframe)

    #genero il grafico
    dataframe.plot.line()

    #Simple Exponential Smoothing
    if beta == 0:
        ses(dataframe, alpha)
        plot.xlim(dataframe.index[0], datetime.fromtimestamp(time.time()+ rate * (2*60)))
    else:
        #Double Exponential Smoothing
        des(dataframe, alpha, beta)
        plot.xlim(dataframe.index[0], datetime.fromtimestamp(time.time()+ rate *(3*60)))

    #creo i grafici delle previsioni
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
    #leggo i parametri passati da linea di comando e controlli i valori
    args = parse_args()

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

    points = []

    #eseguo i test
    for i in range(series):

        init_time = time.time()
        print('Avvio speedtest numero ' + str(i+1))
        results = test()
        print('Speedtest terminato')
        final_time = time.time()

        write_point(points, results)

        if (i != 4):
            time.sleep(rate*60 - (final_time - init_time))

    #creo le directory per i dati
    if not os.path.exists(DATA):
        os.makedirs(DATA)
    os.chdir(DATA)

    directory = datetime.now().strftime("%Y-%m-%d_%H.%M.%S")
    os.makedirs(directory)
    os.chdir(directory)

    dataframe = points2DataFrame(points, rate)

    #esporto dati in csv
    if export==True:
        dataframe.to_csv("./data.csv")

    #creo i grafici delle previsioni
    if not os.path.exists(GRAPHICS):
        os.makedirs(GRAPHICS)

    warnings.simplefilter(action='ignore', category=FutureWarning)
    create_graphs(dataframe, 'ping', alpha, beta, rate)
    create_graphs(dataframe, 'download', alpha, beta, rate)
    create_graphs(dataframe, 'upload', alpha, beta, rate)

'''----------------------------------------------------------------------------------------------'''

if __name__ == '__main__':
    main()
