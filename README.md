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

Hvis du har opptil 10 dokumenter som skal transkriberes, kan du bruke notebooken [`DHLAB_Transkribus.ipynb`](./DHLAB_Transkribus.ipynb) for å logge på Transkribus og laste opp dokumentene til en av dine dokumentsamlinger (`collections`).

Hvis du har mange dokumenter anbefaler vi at du bruker bare henter ut dokument-ID-ene fra Nettbiblioteket me notebooken og heller kjører skriptet [`handskrift.py`](./handskrift.py) i terminalen for å laste dem opp til Transkribus.

> **OBS:** Husk å fylle inn riktig påloggingsinformasjon for Transkribus:

```shell
python -m  handskrift -c $COLLECTION_ID -u $USERNAME -p $PASSWORD -i $DOCUMENT_ID_FILE
```
