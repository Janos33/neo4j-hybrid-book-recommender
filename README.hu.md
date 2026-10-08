# Könyvajánló

[English](README.md) | [Magyar](README.hu.md)

Flask-alapú webalkalmazás, amely Neo4j gráfból ajánl könyveket. A katalógus
adatait, a népszerűséget, a tartalmi hasonlóságot és a kollaboratív szűrést
ötvözi. Ez egy szakdolgozat részeként készült kísérleti prototípus, nem
éles használatra kész alkalmazás. Célja egy hibrid könyvajánlási megközelítés
bemutatása és kiértékelése.

A tároló az alkalmazás és a modellek felépítéséhez szükséges kódot tartalmazza,
de adatbázis-importot vagy mintaadatokat nem: a Neo4j-adatbázisban előzetesen
létre kell hozni az alább leírt szerkezetű adatokat.

> **Neo4j-adatbázis szükséges:** Az alkalmazás megfelelő sémával és adatokkal
> feltöltött, elérhető Neo4j-adatbázis nélkül nem használható működő
> könyvajánlóként. Ez a tároló nem tartalmaz adatbázist vagy mintaadatokat.
> Neo4j-konfiguráció és futó adatbázis nélkül az ajánlás és a keresés nem fog
> működni.

## A projekt állapota

Ez a szakdolgozathoz készült kutatási prototípus egy hibrid ajánlási megközelítés
bemutatására és kiértékelésére; nem kész, éles használatra szánt szolgáltatás.
A Neo4j gráfalapú szűrését tartalomalapú TF-IDF-hasonlósággal és
elemalapú, k legközelebbi szomszédon alapuló kollaboratív szűréssel ötvözi. A
szakdolgozat prototípusa angol nyelvű könyvadatokat használt; a magyar nyelvű
tartalom támogatása jövőbeli fejlesztési lehetőségként szerepel.

Az alábbiak a [`tests/results/`](tests/results/) mappában rögzített mérési
eredmények, nem más adatokra, gépekre vagy telepítésekre érvényes garanciák. A
benchmark forgatókönyvenként 20 kéréssel futott:

| Forgatókönyv | Átlagos válaszidő | Minimum–maximum válaszidő | Átlagos CPU | Csúcs CPU | Átlagos RAM | Csúcs RAM |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Alapállapot | 185,99 ms | 168,93–233,59 ms | 2,9% | 8,0% | 719,00 MB | 719,05 MB |
| Komplex gráfszűrés | 25,10 ms | 18,77–98,52 ms | 2,6% | 6,0% | 719,05 MB | 719,05 MB |
| Hibrid (teljes terhelés) | 236,61 ms | 180,70–445,88 ms | 41,9% | 57,9% | 760,10 MB | 874,21 MB |

A külön offline kollaboratív kiértékelés 500-as mintát használt, és
2025-12-14-én a következő eredményeket rögzítette: Precision 6,35%, Recall
4,43%, F1 0,0500, nDCG 0,0598 és MRR 0,1320. Az offline értékelési adatok
hiányosak: egy olyan releváns könyv, amelyet a felhasználó még nem értékelt,
hamis negatív találatként jelenhet meg. Ezek helyi teszteredmények, nem éles
telepítésen vagy felhasználói vizsgálaton született eredmények.

A jelenlegi alkalmazás külön beállított és feltöltött Neo4j-adatbázist igényel,
a modellek helyi gyorsítótárfájlokba mentődnek, és az app a Flask fejlesztői
szerverét használja engedélyezett hibakeresési móddal. Éles használat előtt
megfelelő telepítési konfigurációra, biztonsági és adatvédelmi
felülvizsgálatra, üzemeltetési monitorozásra, valamint a céladatokon és
célfelhasználókkal végzett validációra lenne szükség. A szakdolgozat lehetséges
jövőbeli irányként említi a magyar nyelvű katalógusadatokat, az éles
környezetben történő további tesztelést, a mélyebb tartalomelemzést és az
elosztott telepítést.

## Követelmények és konfiguráció

- Python a projekt által használt csomagokkal: `Flask`, `python-dotenv`,
  `neo4j`, `numpy`, `pandas`, `scipy` és `scikit-learn`.
- Az alkalmazás számára elérhető, futó Neo4j-adatbázis.
- Az opcionális benchmark szkriptekhez ezenfelül `requests` és `psutil` is
  szükséges.

Telepítsd a Python-függőségeket a projekt gyökérkönyvtárából:

```powershell
python -m pip install -r requirements.txt
```

Másold az `.env.example` fájlt `.env` néven, majd állítsd be a Neo4j-kapcsolat
adatait:

```env
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=change-me
```

Az `app.py` induláskor betölti ezt a fájlt, és hibát jelez, ha valamelyik
változó hiányzik. Valódi hitelesítési adatokat ne tölts fel a tárolóba. A
gyökérkönyvtár `.gitignore` fájlja kizárja a `.env` fájlt; az `.env.example`
csak helykitöltő értékeket tartalmaz.

Az alkalmazást a projekt gyökérkönyvtárából indítsd:

```powershell
python app.py
```

A Flask-szerver elindítása önmagában nem elegendő az ajánló használatához:
futnia kell a Neo4j-adatbázisnak, érvényesnek kell lennie a `.env`-ben megadott
kapcsolati beállításoknak, és az adatbázist fel kell tölteni az alább leírt
sémával és adatokkal. Az alkalmazás jelenleg elkapja a modell-inicializálási
hibákat, ezért adatbázis-kapcsolati hiba mellett is elindulhat, de az
adatbázisfüggő funkciók ilyenkor nem működnek.

A Flask fejlesztői szerver a `http://127.0.0.1:5000` címen figyel. Az
`app.py` fájlban engedélyezve van a hibakeresési mód; ezt a fejlesztői szervert
ne tedd közvetlenül elérhetővé nem megbízható hálózaton.

## A Neo4j gráfmodell

Az alkalmazás az alábbi címkéket, tulajdonságokat és kapcsolati irányokat
használja:

| Címke | Az alkalmazás által használt kötelező tulajdonságok | Szerep |
| --- | --- | --- |
| `Book` | `book_id`, `title` | Katalóguselemek és ajánlható könyvek. |
| `Author` | `author_id`, `name` | Könyvszerzők, valamint szerzőkeresés és -preferenciák. |
| `Tag` | `tag_id`, `tag_name` | Műfajok/címkék, valamint műfajkeresés és -preferenciák. |
| `User` | `user_id` | Könyveket értékelő felhasználók. |
| `AgeGroup` | `id` | Könyvek szűréséhez használt korcsoportok. |

| Kapcsolat | Kötelező tulajdonság | Irány és szerep |
| --- | --- | --- |
| `(:Author)-[:AUTHOR_OF]->(:Book)` | Nincs | Szerzőt kapcsol könyvhöz. |
| `(:Book)-[:HAS_TAG]->(:Tag)` | Nincs | Műfajt/címkét kapcsol könyvhöz. |
| `(:AgeGroup)-[:READ_BY]->(:Book)` | Nincs | Korcsoportot kapcsol az ajánlott könyvekhez. |
| `(:User)-[:RATED]->(:Book)` | `rating` | A felhasználó könyvre adott numerikus értékelése. |

A `book_id`, `author_id` és `tag_id` értékek legyenek stabilak és ne legyenek
üresen hagyva. Az értékeiknek egyezniük kell a gráfban tárolt adatok és a webes
felületről érkező azonosítók között. A kiválasztott könyvek azonosítóit mindkét
ajánlómotor használja; a szerző- és címkeazonosítókat a gráfszűrők használják.
A kollaboratív modell tanításához a `User.user_id` értékét is meg kell adni. Az
értékelések legyenek numerikusak és azonos skálát használjanak.

A szűréshez és rangsoroláshoz az alkalmazás további `Book` tulajdonságokat is
használ:

| Tulajdonság | Elvárt érték | Felhasználás |
| --- | --- | --- |
| `average_rating` | Numerikus érték vagy numerikussá alakítható szöveg | Minimális értékelés szűrő és népszerűség. |
| `ratings_count` | Egész szám vagy egész számmá alakítható szöveg | Népszerűség kiszámítása. |
| `original_publication_year` | Egész szám | Megjelenési év szerinti szűrés. |

A `title` nélküli könyvek nem kerülnek be az ajánlásokba és a tartalmi
modellbe. A hiányzó értékelés- és darabszámadatok a népszerűség számításakor
nullának számítanak. Egy könyvhöz több szerző és címke is tartozhat; az ajánló
mindet összegyűjti.

### Példa a séma beállítására

Az alábbi Cypher-parancsok egyedi értékeket biztosító megszorításokat és az
automatikus kiegészítéshez szükséges teljes szöveges indexeket hoznak létre.
Futtasd őket a Neo4j Browserben vagy más Neo4j Cypher-kliensben. A megszorítások
nem hoznak létre és nem importálnak katalógusadatokat.

```cypher
CREATE CONSTRAINT book_id_unique IF NOT EXISTS
FOR (b:Book) REQUIRE b.book_id IS UNIQUE;

CREATE CONSTRAINT author_id_unique IF NOT EXISTS
FOR (a:Author) REQUIRE a.author_id IS UNIQUE;

CREATE CONSTRAINT tag_id_unique IF NOT EXISTS
FOR (t:Tag) REQUIRE t.tag_id IS UNIQUE;

CREATE CONSTRAINT user_id_unique IF NOT EXISTS
FOR (u:User) REQUIRE u.user_id IS UNIQUE;

CREATE CONSTRAINT age_group_id_unique IF NOT EXISTS
FOR (ag:AgeGroup) REQUIRE ag.id IS UNIQUE;

CREATE FULLTEXT INDEX bookTitleIndex IF NOT EXISTS
FOR (b:Book) ON EACH [b.title];

CREATE FULLTEXT INDEX authorNameIndex IF NOT EXISTS
FOR (a:Author) ON EACH [a.name];

CREATE FULLTEXT INDEX genreNameIndex IF NOT EXISTS
FOR (t:Tag) ON EACH [t.tag_name];
```

A korcsoport-azonosítóknak pontosan egyezniük kell a felület által küldött
értékekkel: `0-12`, `13-17`, `18-25`, `26-40`, `41-60` és `60+`. A megfelelő
gráfszerkezet például:

```cypher
(:AgeGroup {id: "18-25"})-[:READ_BY]->(:Book {book_id: "book-123"})
```

Példa egy értékelési kapcsolatra:

```cypher
(:User {user_id: "user-1"})-[:RATED {rating: 4.5}]->
(:Book {book_id: "book-123"})
```

A fenti azonosítók csak szemléltető példák. Ahhoz, hogy az alkalmazás hasznos
eredményeket adjon, importálj vagy hozz létre valódi könyveket, szerzőket,
címkéket, korcsoportokat, felhasználókat, értékeléseket és kapcsolatokat.

## Az alkalmazás működése

1. **Indítás és adatbázis-kapcsolat.** Az `app.py` beolvassa a Neo4j-kapcsolat
   beállításait a `.env` fájlból, létrehozza az adatbázis-illesztőt, majd
   inicializálja az ajánlószolgáltatásokat.
2. **Modellek betöltése vagy tanítása.** A tartalmi modell beolvassa az egyes
   címmel rendelkező könyveket, a címkéik nevét és a szerzőik nevét. TF-IDF
   reprezentációt készít, majd elmenti a `data/vector_model.pkl` fájlba. A
   kollaboratív modell beolvassa a `(:User)-[:RATED]->(:Book)` rekordokat,
   ritka könyv/felhasználó értékelési mátrixot épít, koszinusztávolság-alapú
   legközelebbi szomszéd modellt tanít, majd elmenti a `data/collab_model.pkl`
   fájlba. A következő indításkor a meglévő gyorsítótárakat tölti be. Ha
   megváltoztak az adatbázis adatai, és újra szeretnéd építeni valamelyik
   modellt, töröld a hozzá tartozó gyorsítótárfájlt.
3. **Keresés/automatikus kiegészítés.** A böngésző a
   `GET /api/search?q=...&type=...` végpontot hívja. A keresés a
   `bookTitleIndex`, `authorNameIndex` és `genreNameIndex` teljes szöveges
   indexeket használja. Legfeljebb tíz találatot ad vissza. A két karakternél
   rövidebb keresőkifejezésekre üres listát ad.
4. **Ajánláskérés.** A böngésző a felhasználó szűrőit, preferenciáit és
   eredménybeállításait elküldi a `POST /recommend` végpontra. A szerver kizárja
   a cím nélküli könyveket, alkalmazza az engedélyezett kor-, év-, szerző- és
   címkeszűrőket, valamint a kizárásokat, majd rangsorolja a fennmaradó
   könyveket.
5. **Hibrid rangsorolás.** A pontszám a preferált műfajok és szerzők
   egyezéséből, illetve az opcionális tartalmi és kollaboratív pontszámokból
   tevődik össze. Ha egy könyvnek nincs személyre szabott pontszáma, a
   népszerűség alapján kerül sorba; ez a `average_rating * log10(ratings_count
   + 1)` képlettel számolódik. Egyébként a népszerűség kis mértékben módosítja
   a pontszámot. A beállítható véletlen összetevő kissé változtathat a sorrenden.
   Az eredmények számát a kérés beállításai szabják meg.
6. **Találati oldal.** A megfelelő könyvek, a szerzők nevei és a pontszámok a
   `templates/result.html` sablonban jelennek meg.

A tartalmi és kollaboratív pontozáshoz kiválasztott kedvenc könyvek és
sikeresen betöltött vagy betanított modellek szükségesek. A tartalmi modell a
könyvcímek, szerzők és címkék szövegét hasonlítja össze. A kollaboratív modell
hasonlóan értékelt könyveket keres. Ha nincs használható kiválasztott könyv,
vagy az adott módszer súlya nulla, az adott összetevő nem ad pontszámot.

Induláskor a modell inicializálásának hibáit az alkalmazás figyelmeztetésként
kiírja, de a Flask alkalmazás tovább fut. Ezzel szemben egy hiányzó `.env`
beállítás egyértelmű konfigurációs hibával leállítja az indítást.

## HTTP-végpontok

| Végpont | Metódus | Leírás |
| --- | --- | --- |
| `/` | `GET` | Megjeleníti az ajánláskérő űrlapot. |
| `/recommend` | `POST` | JSON formátumú preferenciákat/szűrőket fogad, és megjeleníti a találati oldalt. |
| `/api/search` | `GET` | JSON formátumú automatikus kiegészítési találatokat ad vissza `book`, `author` vagy `genre` kereséshez. |

Az ajánláskérés általános felépítése:

```json
{
  "constraints": {
    "age": {"active": false, "values": []},
    "period": {"active": false, "custom_min": "", "custom_max": ""},
    "authors": {"active": false, "values": []},
    "genres": {"active": false, "values": []},
    "excluded_authors": {"active": false, "values": []},
    "excluded_genres": {"active": false, "values": []}
  },
  "preferences": {
    "genres": {"weight": 0, "values": []},
    "authors": {"weight": 0, "values": []},
    "books": {"values": [], "weight_content": 0, "weight_collab": 0}
  },
  "settings": {"min_rating": 0, "randomness": 0.1, "limit": 35}
}
```

A `values` mezőben a keresés által visszaadott `tag_id`, `author_id` vagy
`book_id` értékek szerepelnek. A felület állítja össze ezt a kérést, és
általában a súlyokat, illetve a beállításokat is meghatározza.

## Értékelő szkriptek

- A `tests/evaluate_collaborative.py` ugyanazt a gyökérkönyvtárban található
  `.env` fájlt tölti be, lekérdezi az értékeléseket, és tanító-/teszthalmazra
  bontva kiértékeli a legközelebbi szomszéd alapú ajánlót. A precision, recall,
  F1, nDCG és MRR mutatókat jelenti. A kiértékeléshez elegendő számú
  felhasználó és értékelés kell a felosztáshoz és a szomszédok kereséséhez.
- A `tests/benchmark_suite.py` ismételt kéréseket küld egy futó Flask
  szervernek, és rögzíti a válaszidőket, valamint a folyamat erőforrásadatait.
