# Nachtlotse

**English:** [Go to the English home page](Home)

Ein Lotse bringt Schiffe sicher durch schwieriges Fahrwasser. Nachtlotse
macht das Gleiche für deine Beobachtungsnacht.

Das Programm beantwortet eine Frage: Was fotografiere ich heute Nacht? Du
sagst ihm, wo du stehst und mit welcher Ausrüstung. Es rechnet den Himmel
über deinem Standort für diese Nacht durch und gibt dir eine kurze Liste mit
Zielen, jedes mit einer Bewertung (GO, MARGINAL oder SKIP) und der
Begründung dazu.

![Der Reiter Shortlist in der Nachtlotse-App](images/gui-shortlist.png)

## Wo du anfängst

- Neu hier: [Installieren](Installieren), danach [Erster Start](Erster-Start).
- Eine Nacht planen: [Eine Nacht planen](Eine-Nacht-planen) erklärt Liste und Bewertungen.
- Warum steht ein Ziel da, wo es steht: [Wie die Rangfolge entsteht](Wie-die-Rangfolge-entsteht) und [Bewertungen](Bewertungen).
- Irgendetwas stimmt nicht: [Fehlerbehebung](Fehlerbehebung) und [Fragen und Antworten](Fragen-und-Antworten).

## Was Nachtlotse kann

Nachtlotse sortiert die Objekte seines eingebauten Katalogs (236
Deep-Sky-Objekte) für jede Nacht, die du auswählst. Dabei zählen dein echter
Horizont und das echte Bildfeld deiner Kamera. In die Bewertung fließen
Wetter, Taugefahr, Mondlicht und die Frage ein, wie dunkel die Nacht
überhaupt wird.

Dazu zeigt es Kometen, Supernovae und Novae, die gerade hell genug sind
([Aktuelle Ereignisse](Aktuelle-Ereignisse)), wie ein Ziel in deinen
Bildausschnitt passt ([Bildausschnitt](Bildausschnitt)) und welcher deiner
Standorte den klarsten Himmel hat ([Bester Himmel](Bester-Himmel)).

Du kannst es auf der Kommandozeile benutzen (`lotse`) oder als Mac-App
(`lotse gui`). Beide rechnen mit derselben Engine und kommen zum selben
Ergebnis.

## Der Grundsatz

Die Astronomie wird gerechnet, nie geschätzt. Höhen, Zeiten und Bildausschnitt
stammen aus den JPL-Ephemeriden über die Bibliotheken `skyfield` und
`astroplan`, und Tests prüfen sie gegen bekannte Werte. Wenn etwas nicht
bekannt ist, etwa die Himmelshelligkeit eines Standorts oder die Helligkeit
eines lichtschwachen Nebels, sagt Nachtlotse das, statt eine Zahl zu
erfinden. Ein KI-Modell kommt nur beim optionalen Nachtbriefing zum Einsatz,
und auch dort formuliert es nur Zahlen, die die Engine schon berechnet hat.
