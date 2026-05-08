# data/raw — Synthetic Dutch Legal Documents

> **SYNTHETIC DATA — NOT REAL LEGISLATION**
>
> The HTML files in this directory are hand-authored synthetic documents that
> mimic the structure of real Dutch legal texts from wetten.overheid.nl and
> FIOD internal guidelines. They are **not** copies of any actual government
> publication. They are designed for:
>
> 1. Testing the hierarchical chunker without network access.
> 2. Demonstrating RBAC separation between public and classified documents.
> 3. End-to-end smoke testing of the ingestion and retrieval pipeline.

## File inventory

### Public documents (`classification: public`, accessible to all roles)

| File | Content | Articles |
|------|---------|----------|
| `wet_ib_2001_art_3_1.html` | Art. 3.1 — Belastbaar inkomen uit werk en woning | 1 artikel, 3 lids |
| `wet_ib_2001_art_3_8.html` | Art. 3.8–3.9 — Winst en belastbare winst | 2 artikels, 3 lids |
| `wet_ib_2001_art_3_14.html` | Art. 3.14 — Niet-aftrekbare kosten (80%-regel) | 1 artikel, 3 lids |
| `wet_ib_2001_art_3_16.html` | Art. 3.16 — Werkruimte aftrekbaarheid | 1 artikel, 4 lids |
| `wet_ib_2001_art_3_20.html` | Art. 3.20 — Privégebruik auto / bijtelling | 1 artikel, 3 lids |
| `wet_ib_2001_art_3_46.html` | Art. 3.46 — Investering definitie | 1 artikel, 3 lids |
| `wet_ib_2001_art_3_76.html` | Art. 3.76 — Zelfstandigenaftrek | 1 artikel, 3 lids |
| `wet_ib_2001_art_3_77.html` | Art. 3.77 — Startersaftrek | 1 artikel, 3 lids |
| `wet_ib_2001_art_3_113.html` | Art. 3.113 — Eigenwoningschuld | 1 artikel, 3 lids |
| `wet_ib_2001_art_3_114.html` | Art. 3.114 — Eigenwoningforfait | 1 artikel, 3 lids |
| `wet_ib_2001_art_4_6.html` | Art. 4.6 — Aanmerkelijk belang (Box 2) | 1 artikel, 3 lids |
| `wet_ib_2001_art_5_2.html` | Art. 5.2 — Rendementsgrondslag (Box 3) | 1 artikel, 3 lids |
| `wet_ib_2001_art_8_1.html` | Art. 8.1 — Arbeidskorting en heffingskortingen | 1 artikel, 3 lids |

### FIOD classified documents (`classification: fiod`, accessible to role `fiod` only)

These documents simulate internal FIOD (Fiscale Inlichtingen- en Opsporingsdienst)
investigation guidelines. They are used to test that RBAC pre-filtering at the
Qdrant query stage prevents public and helpdesk users from seeing classified content.

| File | Content |
|------|---------|
| `fiod_intern_001_signalen_vermogensfraude.html` | Signaleringskaart onverklaard vermogen — risicoindicatoren |
| `fiod_intern_002_constructies_offshore.html` | Typologieën offshore belastingconstructies |
| `fiod_intern_003_invordering_bestuurders.html` | Procedure aansprakelijkstelling bestuurders |

## HTML structure

Every document follows a consistent structure parseable by `src/ingestion/chunker.py`:

```html
<div class="wet-document">
  <div class="hoofdstuk" data-nummer="3">
    <div class="afdeling" data-nummer="3.2">
      <div class="artikel" data-nummer="3.16">
        <h4 class="artikel-opschrift">Artikel 3.16. Werkruimte</h4>
        <div class="lid" data-nummer="1">
          <span class="lid-nummer">1.</span>
          <p class="lid-tekst">De kosten van een werkruimte...</p>
          <div class="sub" data-letter="a">
            <span class="sub-letter">a.</span>
            <p class="sub-tekst">indien de belastingplichtige...</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</div>
```

Document-level metadata is carried in `<meta>` tags:

| Meta name | Example value | Used for |
|-----------|--------------|---------|
| `bwb-id` | `BWBR0011353` | `doc_id` in ChunkMetadata |
| `wet-naam` | `Wet inkomstenbelasting 2001` | `wet` field |
| `classification` | `public` / `fiod` | RBAC classification |
| `allowed-roles` | `public,helpdesk,fiod` | RBAC role filter in Qdrant |
| `effective-date` | `2024-01-01` | `effective_date` for cache versioning |
