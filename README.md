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
| 1631622920457355000 | 24.571354287547912 | 22.117 | 16.241842538478338 |
| 1631623100204038000 | 22.589696803266417 | 23.085 | 16.215603196816343 |
| 1631623279513725000 | 19.398868337080096 | 19.098 | 16.237599057090050 |
| 1631623459206425000 | 22.962247152610168 | 18.781 | 16.294962333008190 |
| 1631623640059035000 | 26.211082259028903 | 18.360 | 16.207804152626400 |

Una volta che i vari test sono terminati, tramite una query in stile SQL (e.g.: `select ping from speedtest`) è possibile recuperare i dati da utilizzare per i grafici; in particolare, al fine di poter utilizzare gli algoritmi di previsione della libreria `statsmodels`, i risultati delle query vengono trasformati in dataframe con indice temporale tramite la libreria `pandas`.

Durante l'esecuzione dello script viene creata (se non esiste) la directory `data`, all'interno della quale è possibile trovare le directory contenenti i grafici dei dati e delle previsioni in formato `.pdf` ed eventualmente i dati esportati in formato `.csv`.

### Struttura del progetto

Esempio di come si presenta la directory al termine di alcune esecuzioni:

```bash
.
├── README.md
├── requirements.txt
├── netMonitor.py*
└── data/
    ├── 2021-09-14_12.47.20/
    │   ├── data.csv
    │   └── graphics/
    │       ├── download.pdf
    │       ├── ping.pdf
    │       └── upload.pdf
    ├── 2021-09-14_11.46.37/
    │   ├── data.csv
    │   └── graphics/
    │       ├── download.pdf
    │       ├── ping.pdf
    │       └── upload.pdf
    └── 2021-09-10_16.41.09/
        ├── data.csv
        └── graphics/
            ├── download.pdf
            ├── ping.pdf
            └── upload.pdf
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
