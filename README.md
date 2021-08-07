# netMonitor

## Introduzione

**netMonitor** è uno script in python che periodicamente esegue uno speedtest e ne memorizza i risultati in un time-series database. 
Al termine del ciclo di test viene creato un grafico dei dati raccolti e viene fatta una previsione sullo stato futuro usando il *Simple Exponential Smoothing* e il *Dobule Exponential Smoothing*.

## Implementazione

Gli speedtest sono stati eseguiti con [speedtest.net](https://www.speedtest.net/) usando la libreria python [speedtest-cli](https://pypi.org/project/speedtest-cli/) e si lascia la possibilità all'utente di poter scegliere il numero di test da eseguire e la loro frequenza; tuttavia, per non stressare troppo la rete durante i test e quindi evitare di influenzare i risultati stessi, è stato scelto di impostare una frequenza minima di test (che è anche quella di default) di 3 minuti. 

Come database per raccogliere le serie temporali si è scelto di usare [InfluxDB](https://www.influxdata.com/) versione 1.6.4 per motivi di portabilità e di semplicità d'uso. 
Di seguito, un esempio di come sono organizzati i dati all'interno di InfluxDB:

|         time        |      download      |  ping  |       upload       |
|:-------------------:|:------------------:|:------:|:------------------:|
| 1626470236134025000 | 21.32500982365902  | 30.353 | 14.516783280552598 |
| 1626470415512741000 | 22.80587330588549  | 22.204 | 16.20905327065146  |
| 1626470596755387000 | 23.909459381492344 | 22.001 | 16.17956008944771  |
| 1626470776157024000 | 23.820717306110698 | 22.884 | 16.240073142308347 |
| 1626470956881627000 | 23.38635241425917  | 22.972 | 16.380493128365202 |

Una volta che i vari test sono terminati, tramite una query in stile SQL (e.g.: `select ping from speedtest`) è possibile recuperare i dati da utilizzare per i grafici; in particolare, al fine di poter utilizzare gli algoritmi di previsione della libreria `statsmodels`, i risultati delle query vengono trasformati in dataframe con indice temporale tramite la libreria `pandas`.

Durante l'esecuzione dello script viene creata (se non esiste) la directory `data`, all'interno della quale è possibile trovare le directory contenenti i grafici dei dati e delle previsioni in formato `.pdf` ed eventualmente i dati esportati in formato `.csv`.

### Struttura del progetto

Esempio di come si presenta la directory al termine di alcune esecuzioni:

```bash
.
├── requirements.txt
├── netMonitor.py*
├── data/
│   ├── 2021-07-19_16.02.09/
│   │   └── graphics/
│   │       ├── download.pdf
│   │       ├── ping.pdf
│   │       └── upload.pdf
│   ├── 2021-07-19_15.46.07/
│   │   └── graphics/
│   ├── 2021-07-19_16.16.12/
│   │   └── graphics/
│   │       ├── download.pdf
│   │       ├── ping.pdf
│   │       └── upload.pdf
│   ├── 2021-07-21_15.10.58/
│   │   ├── data.csv
│   │   └── graphics/
│   │       ├── download.pdf
│   │       ├── ping.pdf
│   │       └── upload.pdf
│   └── 2021-07-19_15.26.06/
│       └── graphics/
└── README.md
```

## Installazione

### InfluxDB

Su Linux, per quanto riguarda le derivate Debian, la versione 1.6.1 di InfluxDB può essere ottenuta tramite:
```bash
sudo apt install influxdb influxdb-client
```
**Nota**: accertarsi che il servizio di influx sia correttamente attivato

```bash
systemctl status influxdb
sudo systemctl restart influxdb
```
A questo punto è necessario configurare InfluxDB

1. avviare il servizio tramite
    ```bash
    influx
    ```
    la risposta che si dovrebbe ottenere è
    ```bash
    Connected to http://localhost:8086 version 1.6.4
    InfluxDB shell version: 1.6.4
    ```
2. creare un nuovo database
    ```bash
    create database <database>
    use <database>
    ```
3. creare un nuovo utente
    ```bash
    create user <username> with password '<password>' with all privileges
    ```

### Python

- `matplotlib`, versione 3.4.2 
- `pandas`, versione 1.3.0 
- `influxdb`, versione 5.3.1 
- `speedtest-cli`, versione 2.1.3 
- `statsmodels`, versione 0.12.2

È possibile installare i pacchetti richiesti tramite

```bash
pip install -r requirements.txt
```

## Esecuzione

```bash
netMonitor.py [-h] [-t series [rate]] [-f alpha [beta]] [-e]
```
### Flags

| Flag                                          | Descrizione                                                  |
|-----------------------------------------------|--------------------------------------------------------------|
| -h, --help                                    | show this help message and exit                              |
| -t series [rate],<br/> --test series [rate]   | esegue uno speedtest `<series>` volte con frequenza `<rate>` |
| -f alpha [beta],<br/> --forecast alpha [beta] | esegue una previsione usando `<alpha>` (e `<beta>`)          |
| -e, --export                                  | esporta i dati raccolti in formato csv                       |
