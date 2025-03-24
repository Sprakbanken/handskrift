# Håndskriftsgjenkjenning

Ressurser for håndskriftsgjenkjenning og integrasjon mellom Transkribus og Nettbiblioteket

## Installasjon

Koden er skrevet i python, og krever at du har versjon 3.10 eller høyere.

Opprett et virtuelt miljø og installer nødvendig programvare med pip:

```shell
python -m venv .venv
source .venv/bin/activate

pip install -U -r requirements.txt
```

## Last opp dokumenter til Transkribus

Hent bilder av digitaliserte dokumenter fra Nettbiblioteket og last dem opp til Transkribus for å gjenkjenne teksten i bildene.

Hvis du kun har noen få dokumenter som skal transkriberes, kan du bruke notebooken [`DHLAB_Transkribus.ipynb`](./DHLAB_Transkribus.ipynb) for å logge på Transkribus og laste opp dokumentene til en av dine dokumentsamlinger (`collections`).

Hvis det er flere enn 10 dokumenter som skal lastes opp, anbefaler vi å bare hente ut dokument-ID-ene fra Nettbiblioteket med notebooken og heller laste dem opp ved å kjøre skriptet [`handskrift.py`](./handskrift.py) i terminalen i en skjerm-uavhengig økt (med `screen`, `tmux` eller lignende).

> **OBS:** Husk å fylle inn riktig påloggingsinformasjon for Transkribus:

```shell
screen
source .venv/bin/activate
python -m  handskrift -c $COLLECTION_ID -u $USERNAME -p $PASSWORD -i $DOCUMENT_ID_FILE
```
