# 2D Topologieoptimierung mit Streamlit

Simulation mechanischer Strukturen &amp; Topologieoptimierung

Dieses Projekt implementiert eine interaktive 2D-Topologieoptimierung basierend auf einem Feder-Netzwerk-Modell (Finite-Elemente-ähnlicher Ansatz). Die Anwendung ermöglicht es, Strukturen zu optimieren, Lasten zu definieren und den Optimierungsprozess visuell darzustellen. Die Benutzeroberfläche wurde mit Streamlit umgesetzt.

## Funktionen

- Interaktive Definition der Strukturgröße  
- Frei definierbarer Kraftangriffspunkt und Kraftrichtung  
- Iterative Topologieoptimierung durch Entfernen energiearmer Knoten  
- Visualisierung der Originalstruktur, der Optimierungsschritte und der verformten Struktur  
- Speichern und Laden von Simulationen über TinyDB  
- Fortsetzen gespeicherter Optimierungen  

## Projektstruktur

```
project/
│
├── app.py             # Streamlit Benutzeroberfläche
├── main.py            # Simulationslogik und FEM-Modell
├── db_connector.py    # Datenbankverwaltung (TinyDB)
├── requirements.txt   # Python-Abhängigkeiten
├── db.json            # Datenbank (wird automatisch erstellt)
└── README.md          # Diese Datei
```

## Voraussetzungen und Installation

Für die Ausführung wird Python 3.10 oder neuer benötigt. Zusätzlich muss pip installiert sein. Die installierte Python-Version kann mit folgendem Befehl überprüft werden:

```bash
python --version
```

Anschließend muss das Repository heruntergeladen oder geklont werden:

```bash
git clone <repository-url>
cd <repository-ordner>
```

Es wird empfohlen, eine virtuelle Umgebung zu erstellen und zu aktivieren.

Windows:

```bash
python -m venv venv
venv\Scripts\activate
```

Mac / Linux:

```bash
python -m venv venv
source venv/bin/activate
```

Danach können die benötigten Abhängigkeiten installiert werden:

```bash
pip install -r requirements.txt
```

## Ausführung der Anwendung

Die Anwendung wird im Projektordner mit folgendem Befehl gestartet:

```bash
streamlit run app.py
```

Nach dem Start öffnet sich die Anwendung automatisch im Standardbrowser. Falls dies nicht geschieht, kann sie manuell unter folgender Adresse aufgerufen werden:

```
http://localhost:8501
```

## Verwendung

Nach dem Start der Anwendung können die Strukturgröße sowie der Kraftangriffspunkt und die Kraftrichtung über die Benutzeroberfläche definiert werden. Durch Klicken auf „Simulation starten“ wird die Optimierung ausgeführt. Die Originalstruktur, die einzelnen Optimierungsschritte und die resultierende verformte Struktur werden grafisch dargestellt. Simulationen können gespeichert und zu einem späteren Zeitpunkt wieder geladen und fortgesetzt werden.

## Speicherung

Simulationen werden automatisch in der Datei

```
db.json
```

gespeichert. Diese Datei wird beim ersten Speichern automatisch erstellt.

## Technische Details

Das zugrunde liegende Modell basiert auf einem Feder-Netzwerk mit globaler Steifigkeitsmatrix. Die Topologieoptimierung erfolgt durch iterative Entfernung von Knoten mit geringem Energiebeitrag unter Berücksichtigung von Konnektivität, Lastpfaden und mechanischer Stabilität. Zur Implementierung wurden die Bibliotheken NumPy, NetworkX, Matplotlib, Streamlit und TinyDB verwendet.
